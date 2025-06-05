"""Tests for production features."""

import asyncio

import pytest

from nanobricks.production import (
    CircuitBreaker,
    CircuitState,
    CircuitStats,
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
        if self.call_count <= 3 and self.failure_rate > 0:
            # First 3 calls fail based on rate
            raise ValueError("Simulated failure")
        elif self.failure_rate == 1.0:
            # Always fail if rate is 1.0
            raise ValueError("Simulated failure")

        return input * 2


class SlowBrick(NanobrickBase[str, str, None]):
    """Brick that simulates slow processing."""

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

        # TypeError should not count - circuit still closed
        with pytest.raises(TypeError):
            await cb.invoke(2)

        assert cb.state == CircuitState.CLOSED
        assert cb.stats.consecutive_failures == 2

        # One more ValueError should open circuit
        brick.call_count = 0  # Reset to trigger ValueError
        with pytest.raises(ValueError):
            await cb.invoke(3)

        assert cb.state == CircuitState.OPEN


# Bulkhead tests removed - feature violates simplicity principle
# Use external resource management or circuit breaker for resilience


# TestHealthCheck removed - HealthCheck class doesn't exist
# Health monitoring should be implemented via observability skill

# TestGracefulShutdown removed - GracefulShutdown class doesn't exist  
# Shutdown handling should be managed at application level


# TestProductionFeatures removed - with_production_features function doesn't exist
# Production features should be composed manually following the Simple principle