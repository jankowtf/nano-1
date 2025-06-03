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
    def __or__(self, other):
        """Backwards compatibility for | operator. DEPRECATED: Use >> instead."""
        import warnings
        warnings.warn(
            "The | operator for nanobrick composition is deprecated. "
            "Use >> instead. This will be removed in v0.3.0.",
            DeprecationWarning,
            stacklevel=2
        )
        return self.__rshift__(other)
