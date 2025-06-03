"""Production-ready features for nanobricks."""

import asyncio
import signal
import time
from collections import deque
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

from nanobricks.protocol import NanobrickProtocol, T_deps, T_in, T_out


class CircuitState(str, Enum):
    """Circuit breaker states."""

    CLOSED = "closed"  # Normal operation
    OPEN = "open"  # Failing, reject requests
    HALF_OPEN = "half_open"  # Testing if recovered


@dataclass
class CircuitStats:
    """Circuit breaker statistics."""

    total_calls: int = 0
    success_calls: int = 0
    failure_calls: int = 0
    consecutive_failures: int = 0
    last_failure_time: datetime | None = None
    state_changes: list[tuple[CircuitState, datetime]] = field(default_factory=list)


class CircuitBreaker(NanobrickProtocol[T_in, T_out, T_deps]):
    """Circuit breaker to prevent cascading failures."""

    def __init__(
        self,
        brick: NanobrickProtocol[T_in, T_out, T_deps],
        *,
        failure_threshold: int = 5,
        success_threshold: int = 2,
        timeout_seconds: float = 60,
        error_types: set[type] | None = None,
        fallback: Callable[[T_in, T_deps], T_out] | None = None,
    ):
        self.brick = brick
        self.failure_threshold = failure_threshold
        self.success_threshold = success_threshold
        self.timeout_seconds = timeout_seconds
        self.error_types = error_types or {Exception}
        self.fallback = fallback

        self._state = CircuitState.CLOSED
        self._stats = CircuitStats()
        self._half_open_successes = 0
        self._lock = asyncio.Lock()

        self.name = f"CircuitBreaker[{brick.name}]"
        self.version = brick.version

    @property
    def state(self) -> CircuitState:
        """Get current circuit state."""
        return self._state

    @property
    def stats(self) -> CircuitStats:
        """Get circuit statistics."""
        return self._stats

    def _change_state(self, new_state: CircuitState):
        """Change circuit state."""
        if self._state != new_state:
            self._state = new_state
            self._stats.state_changes.append((new_state, datetime.now()))
            if new_state == CircuitState.HALF_OPEN:
                self._half_open_successes = 0

    def _should_attempt_reset(self) -> bool:
        """Check if circuit should attempt reset."""
        if self._state != CircuitState.OPEN:
            return False

        if not self._stats.last_failure_time:
            return True

        time_since_failure = datetime.now() - self._stats.last_failure_time
        return time_since_failure.total_seconds() >= self.timeout_seconds

    async def _handle_success(self, result: T_out) -> T_out:
        """Handle successful invocation."""
        async with self._lock:
            self._stats.total_calls += 1
            self._stats.success_calls += 1
            self._stats.consecutive_failures = 0

            if self._state == CircuitState.HALF_OPEN:
                self._half_open_successes += 1
                if self._half_open_successes >= self.success_threshold:
                    self._change_state(CircuitState.CLOSED)

        return result

    async def _handle_failure(self, error: Exception) -> None:
        """Handle failed invocation."""
        async with self._lock:
            self._stats.total_calls += 1
            self._stats.failure_calls += 1
            self._stats.consecutive_failures += 1
            self._stats.last_failure_time = datetime.now()

            if self._state == CircuitState.HALF_OPEN:
                self._change_state(CircuitState.OPEN)
            elif (
                self._state == CircuitState.CLOSED
                and self._stats.consecutive_failures >= self.failure_threshold
            ):
                self._change_state(CircuitState.OPEN)

    async def invoke(self, input: T_in, *, deps: T_deps = None) -> T_out:
        """Invoke with circuit breaker protection."""
        # Check if circuit should reset
        if self._should_attempt_reset():
            self._change_state(CircuitState.HALF_OPEN)

        # Reject if open
        if self._state == CircuitState.OPEN:
            if self.fallback:
                return self.fallback(input, deps)
            raise RuntimeError(f"Circuit breaker is OPEN for {self.brick.name}")

        # Try the invocation
        try:
            result = await self.brick.invoke(input, deps=deps)
            return await self._handle_success(result)
        except Exception as e:
            if any(isinstance(e, error_type) for error_type in self.error_types):
                await self._handle_failure(e)

            if self.fallback and self._state == CircuitState.OPEN:
                return self.fallback(input, deps)
            raise

    def invoke_sync(self, input: T_in, *, deps: T_deps = None) -> T_out:
        """Synchronous version of invoke."""
        return asyncio.run(self.invoke(input, deps=deps))

    def __rshift__(self, other: "NanobrickProtocol") -> "NanobrickProtocol":
        """Compose with another brick."""
        from nanobricks.composition import Pipeline

        return Pipeline(self, other)


class Bulkhead(NanobrickProtocol[T_in, T_out, T_deps]):
    """Bulkhead pattern to isolate resources."""

    def __init__(
        self,
        brick: NanobrickProtocol[T_in, T_out, T_deps],
        *,
        max_concurrent: int = 10,
        max_queue_size: int | None = None,
        timeout_seconds: float | None = None,
    ):
        self.brick = brick
        self.max_concurrent = max_concurrent
        self.max_queue_size = max_queue_size
        self.timeout_seconds = timeout_seconds

        self._semaphore = asyncio.Semaphore(max_concurrent)
        self._queue_size = 0
        self._active_count = 0
        self._total_processed = 0
        self._total_rejected = 0
        self._lock = asyncio.Lock()

        self.name = f"Bulkhead[{brick.name}]"
        self.version = brick.version

    @property
    def active_count(self) -> int:
        """Get number of active invocations."""
        return self._active_count

    @property
    def stats(self) -> dict[str, int]:
        """Get bulkhead statistics."""
        return {
            "active": self._active_count,
            "queued": self._queue_size,
            "processed": self._total_processed,
            "rejected": self._total_rejected,
        }

    async def invoke(self, input: T_in, *, deps: T_deps = None) -> T_out:
        """Invoke with bulkhead isolation."""
        # Check queue size
        if self.max_queue_size is not None:
            async with self._lock:
                if self._queue_size >= self.max_queue_size:
                    self._total_rejected += 1
                    raise RuntimeError(
                        f"Bulkhead queue full for {self.brick.name} "
                        f"(max: {self.max_queue_size})"
                    )
                self._queue_size += 1

        try:
            # Acquire semaphore with timeout
            if self.timeout_seconds:
                try:
                    await asyncio.wait_for(
                        self._semaphore.acquire(),
                        timeout=self.timeout_seconds,
                    )
                except TimeoutError:
                    async with self._lock:
                        self._total_rejected += 1
                    raise RuntimeError(
                        f"Bulkhead timeout for {self.brick.name} "
                        f"after {self.timeout_seconds}s"
                    )
            else:
                await self._semaphore.acquire()

            # Update counters
            async with self._lock:
                if self.max_queue_size is not None:
                    self._queue_size -= 1
                self._active_count += 1

            try:
                # Invoke the brick
                result = await self.brick.invoke(input, deps=deps)

                async with self._lock:
                    self._total_processed += 1

                return result
            finally:
                # Release resources
                async with self._lock:
                    self._active_count -= 1
                self._semaphore.release()

        except Exception:
            # Decrement queue size on early failure
            if self.max_queue_size is not None:
                async with self._lock:
                    self._queue_size = max(0, self._queue_size - 1)
            raise

    def invoke_sync(self, input: T_in, *, deps: T_deps = None) -> T_out:
        """Synchronous version of invoke."""
        return asyncio.run(self.invoke(input, deps=deps))

    def __rshift__(self, other: "NanobrickProtocol") -> "NanobrickProtocol":
        """Compose with another brick."""
        from nanobricks.composition import Pipeline

        return Pipeline(self, other)


class HealthStatus(str, Enum):
    """Health check status."""

    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"


@dataclass
class HealthCheckResult:
    """Result of a health check."""

    status: HealthStatus
    message: str = ""
    details: dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)


class HealthCheck(NanobrickProtocol[T_in, T_out, T_deps]):
    """Health check wrapper for nanobricks."""

    def __init__(
        self,
        brick: NanobrickProtocol[T_in, T_out, T_deps],
        *,
        check_interval_seconds: float = 30,
        failure_threshold: int = 3,
        custom_check: Callable[[], HealthCheckResult] | None = None,
    ):
        self.brick = brick
        self.check_interval_seconds = check_interval_seconds
        self.failure_threshold = failure_threshold
        self.custom_check = custom_check

        self._status = HealthStatus.HEALTHY
        self._last_check: datetime | None = None
        self._consecutive_failures = 0
        self._invocation_times: deque = deque(maxlen=100)
        self._error_counts: dict[str, int] = {}
        self._check_task: asyncio.Task | None = None

        self.name = f"HealthCheck[{brick.name}]"
        self.version = brick.version

    async def start_health_checks(self):
        """Start background health check task."""
        if self._check_task is None or self._check_task.done():
            self._check_task = asyncio.create_task(self._health_check_loop())

    async def stop_health_checks(self):
        """Stop background health check task."""
        if self._check_task and not self._check_task.done():
            self._check_task.cancel()
            try:
                await self._check_task
            except asyncio.CancelledError:
                pass

    async def _health_check_loop(self):
        """Background health check loop."""
        while True:
            try:
                await asyncio.sleep(self.check_interval_seconds)
                await self.check_health()
            except asyncio.CancelledError:
                break
            except Exception:
                pass  # Don't let health checks crash

    async def check_health(self) -> HealthCheckResult:
        """Perform health check."""
        self._last_check = datetime.now()

        # Use custom check if provided
        if self.custom_check:
            result = self.custom_check()
        else:
            # Default health check based on recent performance
            avg_response_time = (
                sum(self._invocation_times) / len(self._invocation_times)
                if self._invocation_times
                else 0
            )

            error_rate = sum(self._error_counts.values()) / max(
                len(self._invocation_times), 1
            )

            details = {
                "avg_response_time_ms": avg_response_time,
                "error_rate": error_rate,
                "consecutive_failures": self._consecutive_failures,
            }

            if self._consecutive_failures >= self.failure_threshold:
                result = HealthCheckResult(
                    status=HealthStatus.UNHEALTHY,
                    message=f"Too many consecutive failures: {self._consecutive_failures}",
                    details=details,
                )
            elif error_rate > 0.5 or avg_response_time > 1000:
                result = HealthCheckResult(
                    status=HealthStatus.DEGRADED,
                    message="High error rate or slow response times",
                    details=details,
                )
            else:
                result = HealthCheckResult(
                    status=HealthStatus.HEALTHY,
                    message="Operating normally",
                    details=details,
                )

        self._status = result.status
        return result

    async def invoke(self, input: T_in, *, deps: T_deps = None) -> T_out:
        """Invoke with health tracking."""
        start_time = time.time()

        try:
            result = await self.brick.invoke(input, deps=deps)

            # Track success
            duration_ms = (time.time() - start_time) * 1000
            self._invocation_times.append(duration_ms)
            self._consecutive_failures = 0

            return result

        except Exception as e:
            # Track failure
            self._consecutive_failures += 1
            error_type = type(e).__name__
            self._error_counts[error_type] = self._error_counts.get(error_type, 0) + 1
            raise

    def invoke_sync(self, input: T_in, *, deps: T_deps = None) -> T_out:
        """Synchronous version of invoke."""
        return asyncio.run(self.invoke(input, deps=deps))

    def __rshift__(self, other: "NanobrickProtocol") -> "NanobrickProtocol":
        """Compose with another brick."""
        from nanobricks.composition import Pipeline

        return Pipeline(self, other)

    @property
    def status(self) -> HealthStatus:
        """Get current health status."""
        return self._status

    @property
    def is_healthy(self) -> bool:
        """Check if brick is healthy."""
        return self._status == HealthStatus.HEALTHY


class GracefulShutdown:
    """Manages graceful shutdown of nanobricks."""

    def __init__(self, timeout_seconds: float = 30):
        self.timeout_seconds = timeout_seconds
        self._shutdown_event = asyncio.Event()
        self._tasks: set[asyncio.Task] = set()
        self._bricks: list[NanobrickProtocol] = []
        self._shutdown_handlers: list[Callable] = []
        self._signal_handlers_installed = False

    def register_brick(self, brick: NanobrickProtocol):
        """Register a brick for shutdown management."""
        self._bricks.append(brick)

    def register_handler(self, handler: Callable):
        """Register a custom shutdown handler."""
        self._shutdown_handlers.append(handler)

    def register_task(self, task: asyncio.Task):
        """Register a task to be cancelled on shutdown."""
        self._tasks.add(task)
        task.add_done_callback(self._tasks.discard)

    def install_signal_handlers(self):
        """Install signal handlers for graceful shutdown."""
        if not self._signal_handlers_installed:
            for sig in (signal.SIGTERM, signal.SIGINT):
                signal.signal(sig, self._signal_handler)
            self._signal_handlers_installed = True

    def _signal_handler(self, signum, frame):
        """Handle shutdown signals."""
        asyncio.create_task(self.shutdown())

    async def wait_for_shutdown(self):
        """Wait for shutdown signal."""
        await self._shutdown_event.wait()

    async def shutdown(self):
        """Perform graceful shutdown."""
        print("Starting graceful shutdown...")
        self._shutdown_event.set()

        # Run custom shutdown handlers
        for handler in self._shutdown_handlers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler()
                else:
                    handler()
            except Exception as e:
                print(f"Error in shutdown handler: {e}")

        # Cancel all registered tasks
        for task in self._tasks:
            if not task.done():
                task.cancel()

        # Wait for tasks to complete or timeout
        if self._tasks:
            try:
                await asyncio.wait_for(
                    asyncio.gather(*self._tasks, return_exceptions=True),
                    timeout=self.timeout_seconds,
                )
            except TimeoutError:
                print(f"Shutdown timeout after {self.timeout_seconds}s")

        # Clean up bricks (if they have cleanup methods)
        for brick in self._bricks:
            if hasattr(brick, "cleanup"):
                try:
                    if asyncio.iscoroutinefunction(brick.cleanup):
                        await brick.cleanup()
                    else:
                        brick.cleanup()
                except Exception as e:
                    print(f"Error cleaning up {brick.name}: {e}")

        print("Graceful shutdown complete")


def with_production_features(
    brick: NanobrickProtocol[T_in, T_out, T_deps],
    *,
    circuit_breaker: bool = True,
    bulkhead: int | None = None,
    health_check: bool = True,
    **kwargs,
) -> NanobrickProtocol[T_in, T_out, T_deps]:
    """Apply production features to a nanobrick."""
    result = brick

    if circuit_breaker:
        result = CircuitBreaker(
            result,
            failure_threshold=kwargs.get("failure_threshold", 5),
            timeout_seconds=kwargs.get("timeout_seconds", 60),
        )

    if bulkhead is not None:
        result = Bulkhead(result, max_concurrent=bulkhead)

    if health_check:
        result = HealthCheck(result)

    return result
