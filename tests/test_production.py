"""Tests for production features."""

import asyncio

import pytest

from nanobricks.production import (
    Bulkhead,
    CircuitBreaker,
    CircuitState,
    GracefulShutdown,
    HealthCheck,
    HealthStatus,
    with_production_features,
)
from nanobricks.protocol import NanobrickBase


class UnreliableBrick(NanobrickBase[int, int, None]):
    """Brick that can be configured to fail."""

    def __init__(self, failure_rate: float = 0.0):
        super().__init__(name="unreliable", version="1.0.0")
        self.failure_rate = failure_rate
        self.call_count = 0

    async def invoke(self, input: int, *, deps: None = None) -> int:
        self.call_count += 1

        # Simulate failures based on rate
        if self.call_count <= int(self.failure_rate * 10):
            raise ValueError("Simulated failure")

        # Simulate some processing time
        await asyncio.sleep(0.01)
        return input * 2


class SlowBrick(NanobrickBase[str, str, None]):
    """Brick that takes time to process."""

    def __init__(self, delay_seconds: float = 0.1):
        super().__init__(name="slow", version="1.0.0")
        self.delay_seconds = delay_seconds

    async def invoke(self, input: str, *, deps: None = None) -> str:
        await asyncio.sleep(self.delay_seconds)
        return f"processed: {input}"


class TestCircuitBreaker:
    """Test circuit breaker functionality."""

    @pytest.mark.asyncio
    async def test_circuit_opens_on_failures(self):
        """Test that circuit opens after threshold failures."""
        brick = UnreliableBrick(failure_rate=1.0)  # Always fails
        cb = CircuitBreaker(brick, failure_threshold=3)

        assert cb.state == CircuitState.CLOSED

        # First 3 failures should be allowed
        for i in range(3):
            with pytest.raises(ValueError):
                await cb.invoke(i)

        # Circuit should now be open
        assert cb.state == CircuitState.OPEN
        assert cb.stats.consecutive_failures == 3

        # Further calls should be rejected
        with pytest.raises(RuntimeError, match="Circuit breaker is OPEN"):
            await cb.invoke(4)

    @pytest.mark.asyncio
    async def test_circuit_recovery(self):
        """Test circuit recovery after timeout."""
        brick = UnreliableBrick(failure_rate=0.3)  # Fails first 3 calls
        cb = CircuitBreaker(
            brick,
            failure_threshold=3,
            success_threshold=2,
            timeout_seconds=0.1,
        )

        # Trigger circuit open with exactly 3 failures
        for i in range(3):
            with pytest.raises(ValueError):
                await cb.invoke(i)

        assert cb.state == CircuitState.OPEN

        # Wait for timeout
        await asyncio.sleep(0.15)

        # Circuit should attempt reset (half-open)
        # Call 4 should succeed since brick only fails first 3 calls
        result = await cb.invoke(10)
        assert result == 20
        assert cb.state == CircuitState.HALF_OPEN

        # One more success should close the circuit
        result = await cb.invoke(11)
        assert result == 22
        assert cb.state == CircuitState.CLOSED

    @pytest.mark.asyncio
    async def test_fallback_function(self):
        """Test fallback function when circuit is open."""
        brick = UnreliableBrick(failure_rate=1.0)

        def fallback(input: int, deps) -> int:
            return -1

        cb = CircuitBreaker(brick, failure_threshold=2, fallback=fallback)

        # First failure - circuit still closed, exception raised
        with pytest.raises(ValueError):
            await cb.invoke(0)

        # Second failure triggers circuit open, fallback used immediately
        result = await cb.invoke(1)
        assert result == -1
        assert cb.state == CircuitState.OPEN

        # Further calls use fallback when open
        result = await cb.invoke(5)
        assert result == -1

    @pytest.mark.asyncio
    async def test_error_type_filtering(self):
        """Test that only specified error types trigger the circuit."""

        class CustomBrick(NanobrickBase[int, int, None]):
            def __init__(self):
                super().__init__(name="custom", version="1.0.0")
                self.call_count = 0

            async def invoke(self, input: int, *, deps: None = None) -> int:
                self.call_count += 1
                if self.call_count <= 2:
                    raise ValueError("Expected error")
                elif self.call_count == 3:
                    raise TypeError("Unexpected error")
                return input

        brick = CustomBrick()
        cb = CircuitBreaker(brick, failure_threshold=3, error_types={ValueError})

        # ValueError should count towards circuit
        for i in range(2):
            with pytest.raises(ValueError):
                await cb.invoke(i)

        # TypeError should not trigger circuit
        with pytest.raises(TypeError):
            await cb.invoke(3)

        # Circuit should still be closed
        assert cb.state == CircuitState.CLOSED
        # Consecutive failures should be 2 (TypeError doesn't increment)
        assert cb.stats.consecutive_failures == 2


class TestBulkhead:
    """Test bulkhead isolation."""

    @pytest.mark.asyncio
    async def test_concurrent_limit(self):
        """Test that bulkhead limits concurrent executions."""
        brick = SlowBrick(delay_seconds=0.1)
        bulkhead = Bulkhead(brick, max_concurrent=2)

        # Start 3 concurrent tasks
        tasks = [asyncio.create_task(bulkhead.invoke(f"task{i}")) for i in range(3)]

        # Give tasks time to start
        await asyncio.sleep(0.05)

        # Only 2 should be active
        assert bulkhead.active_count == 2

        # Wait for all to complete
        results = await asyncio.gather(*tasks)
        assert len(results) == 3
        assert all(r.startswith("processed:") for r in results)

    @pytest.mark.asyncio
    async def test_queue_size_limit(self):
        """Test that bulkhead rejects when queue is full."""
        brick = SlowBrick(delay_seconds=0.1)
        bulkhead = Bulkhead(brick, max_concurrent=1, max_queue_size=1)

        # Start 3 tasks - 1 active, 1 queued, 1 should be rejected
        task1 = asyncio.create_task(bulkhead.invoke("task1"))
        task2 = asyncio.create_task(bulkhead.invoke("task2"))

        # Give time for queue to fill
        await asyncio.sleep(0.01)

        # Third task should be rejected
        with pytest.raises(RuntimeError, match="queue full"):
            await bulkhead.invoke("task3")

        # Verify stats
        assert bulkhead.stats["rejected"] == 1

        # Clean up
        await asyncio.gather(task1, task2)

    @pytest.mark.asyncio
    async def test_timeout(self):
        """Test bulkhead timeout."""
        brick = SlowBrick(delay_seconds=1.0)
        bulkhead = Bulkhead(brick, max_concurrent=1, timeout_seconds=0.1)

        # Start a long-running task
        task1 = asyncio.create_task(bulkhead.invoke("task1"))

        # Second task should timeout waiting for semaphore
        await asyncio.sleep(0.01)
        with pytest.raises(RuntimeError, match="timeout"):
            await bulkhead.invoke("task2")

        # Clean up
        task1.cancel()
        try:
            await task1
        except asyncio.CancelledError:
            pass


class TestHealthCheck:
    """Test health check functionality."""

    @pytest.mark.asyncio
    async def test_healthy_operation(self):
        """Test health check for healthy brick."""
        brick = SlowBrick(delay_seconds=0.01)
        hc = HealthCheck(brick)

        # Initial state should be healthy
        assert hc.status == HealthStatus.HEALTHY
        assert hc.is_healthy

        # Make some successful calls
        for i in range(5):
            await hc.invoke(f"test{i}")

        # Check health
        result = await hc.check_health()
        assert result.status == HealthStatus.HEALTHY
        assert result.details["error_rate"] == 0
        assert result.details["consecutive_failures"] == 0

    @pytest.mark.asyncio
    async def test_unhealthy_detection(self):
        """Test health check detects unhealthy state."""
        brick = UnreliableBrick(failure_rate=1.0)
        hc = HealthCheck(brick, failure_threshold=3)

        # Make failing calls
        for i in range(3):
            with pytest.raises(ValueError):
                await hc.invoke(i)

        # Check health
        result = await hc.check_health()
        assert result.status == HealthStatus.UNHEALTHY
        assert result.details["consecutive_failures"] == 3
        assert not hc.is_healthy

    @pytest.mark.asyncio
    async def test_degraded_detection(self):
        """Test health check detects degraded state."""
        brick = SlowBrick(delay_seconds=2.0)  # Very slow
        hc = HealthCheck(brick)

        # Make a slow call
        await hc.invoke("test")

        # Check health - should be degraded due to slow response
        result = await hc.check_health()
        assert result.status == HealthStatus.DEGRADED
        assert result.details["avg_response_time_ms"] > 1000

    @pytest.mark.asyncio
    async def test_custom_health_check(self):
        """Test custom health check function."""
        brick = SlowBrick()

        health_results = []

        def custom_check():
            from nanobricks.production import HealthCheckResult

            # Alternate between healthy and degraded
            status = (
                HealthStatus.HEALTHY
                if len(health_results) % 2 == 0
                else HealthStatus.DEGRADED
            )
            result = HealthCheckResult(
                status=status,
                message=f"Custom check #{len(health_results)}",
            )
            health_results.append(result)
            return result

        hc = HealthCheck(brick, custom_check=custom_check)

        # First check should be healthy
        result = await hc.check_health()
        assert result.status == HealthStatus.HEALTHY

        # Second check should be degraded
        result = await hc.check_health()
        assert result.status == HealthStatus.DEGRADED

    @pytest.mark.asyncio
    async def test_background_health_checks(self):
        """Test background health check task."""
        brick = SlowBrick()
        hc = HealthCheck(brick, check_interval_seconds=0.1)

        # Start background checks
        await hc.start_health_checks()

        # Wait for a few checks
        await asyncio.sleep(0.35)

        # Should have performed checks
        assert hc._last_check is not None

        # Stop checks
        await hc.stop_health_checks()


class TestGracefulShutdown:
    """Test graceful shutdown functionality."""

    @pytest.mark.asyncio
    async def test_shutdown_tasks(self):
        """Test that shutdown cancels registered tasks."""
        shutdown = GracefulShutdown(timeout_seconds=1)

        # Create and register some tasks
        task_results = []

        async def long_task(name):
            try:
                await asyncio.sleep(10)
                task_results.append(f"{name} completed")
            except asyncio.CancelledError:
                task_results.append(f"{name} cancelled")
                raise

        task1 = asyncio.create_task(long_task("task1"))
        task2 = asyncio.create_task(long_task("task2"))

        shutdown.register_task(task1)
        shutdown.register_task(task2)

        # Give tasks time to start
        await asyncio.sleep(0.01)

        # Trigger shutdown
        await shutdown.shutdown()

        # Give cancelled tasks time to complete their exception handling
        await asyncio.sleep(0.1)

        # Tasks should be cancelled
        assert "task1 cancelled" in task_results
        assert "task2 cancelled" in task_results

    @pytest.mark.asyncio
    async def test_shutdown_handlers(self):
        """Test custom shutdown handlers."""
        shutdown = GracefulShutdown()

        handler_calls = []

        def sync_handler():
            handler_calls.append("sync")

        async def async_handler():
            handler_calls.append("async")

        shutdown.register_handler(sync_handler)
        shutdown.register_handler(async_handler)

        # Trigger shutdown
        await shutdown.shutdown()

        # Handlers should have been called
        assert "sync" in handler_calls
        assert "async" in handler_calls

    @pytest.mark.asyncio
    async def test_brick_cleanup(self):
        """Test that bricks are cleaned up on shutdown."""

        class CleanableBrick(NanobrickBase[str, str, None]):
            def __init__(self):
                super().__init__(name="cleanable", version="1.0.0")
                self.cleaned_up = False

            async def invoke(self, input: str, *, deps: None = None) -> str:
                return input

            async def cleanup(self):
                self.cleaned_up = True

        brick = CleanableBrick()
        shutdown = GracefulShutdown()
        shutdown.register_brick(brick)

        # Trigger shutdown
        await shutdown.shutdown()

        # Brick should be cleaned up
        assert brick.cleaned_up

    @pytest.mark.asyncio
    async def test_wait_for_shutdown(self):
        """Test waiting for shutdown signal."""
        shutdown = GracefulShutdown()

        # Create a task that waits for shutdown
        wait_completed = False

        async def waiter():
            nonlocal wait_completed
            await shutdown.wait_for_shutdown()
            wait_completed = True

        wait_task = asyncio.create_task(waiter())

        # Give time to start waiting
        await asyncio.sleep(0.01)
        assert not wait_completed

        # Trigger shutdown
        await shutdown.shutdown()

        # Wait task should complete
        await wait_task
        assert wait_completed


class TestProductionFeatures:
    """Test combined production features."""

    @pytest.mark.asyncio
    async def test_with_production_features(self):
        """Test applying multiple production features."""
        brick = SlowBrick(delay_seconds=0.01)

        # Apply production features
        prod_brick = with_production_features(
            brick,
            circuit_breaker=True,
            bulkhead=5,
            health_check=True,
            failure_threshold=3,
        )

        # Verify features are applied (outermost to innermost: HealthCheck -> Bulkhead -> CircuitBreaker)
        assert "HealthCheck" in prod_brick.name
        assert "Bulkhead" in prod_brick.brick.name
        assert "CircuitBreaker" in prod_brick.brick.brick.name

        # Should work normally
        result = await prod_brick.invoke("test")
        assert result == "processed: test"

    @pytest.mark.asyncio
    async def test_feature_composition(self):
        """Test that production features compose correctly."""
        brick = UnreliableBrick(failure_rate=0.3)

        # Apply features
        prod_brick = with_production_features(
            brick,
            circuit_breaker=True,
            bulkhead=2,
            health_check=True,
        )

        # Make some calls
        results = []
        errors = []

        for i in range(10):
            try:
                result = await prod_brick.invoke(i)
                results.append(result)
            except Exception as e:
                errors.append(e)

        # Should have some successes and failures
        assert len(results) > 0
        assert len(errors) > 0

        # Circuit breaker should be tracking (it's nested inside)
        cb = prod_brick.brick.brick  # HealthCheck -> Bulkhead -> CircuitBreaker
        assert cb.stats.total_calls == 10
