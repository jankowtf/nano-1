"""Performance profiler for nanobricks."""

import asyncio
import gc
import time
from collections import defaultdict
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

import psutil

from nanobricks import NanobrickProtocol


@dataclass
class ProfileStats:
    """Statistics for a profiled brick."""

    brick_name: str
    call_count: int = 0
    total_time_ms: float = 0.0
    min_time_ms: float = float("inf")
    max_time_ms: float = 0.0
    avg_time_ms: float = 0.0
    memory_before_mb: float = 0.0
    memory_after_mb: float = 0.0
    memory_delta_mb: float = 0.0
    errors: int = 0

    def update(self, duration_ms: float, memory_delta_mb: float = 0):
        """Update statistics with new measurement."""
        self.call_count += 1
        self.total_time_ms += duration_ms
        self.min_time_ms = min(self.min_time_ms, duration_ms)
        self.max_time_ms = max(self.max_time_ms, duration_ms)
        self.avg_time_ms = self.total_time_ms / self.call_count
        self.memory_delta_mb += memory_delta_mb

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "brick_name": self.brick_name,
            "call_count": self.call_count,
            "total_time_ms": round(self.total_time_ms, 2),
            "min_time_ms": round(self.min_time_ms, 2),
            "max_time_ms": round(self.max_time_ms, 2),
            "avg_time_ms": round(self.avg_time_ms, 2),
            "memory_delta_mb": round(self.memory_delta_mb, 2),
            "errors": self.errors,
        }


class BrickProfiler:
    """Profile nanobricks performance."""

    def __init__(
        self,
        measure_memory: bool = True,
        gc_collect: bool = False,
    ):
        """Initialize profiler.

        Args:
            measure_memory: Measure memory usage
            gc_collect: Run garbage collection before measurements
        """
        self.measure_memory = measure_memory
        self.gc_collect = gc_collect
        self.stats: dict[str, ProfileStats] = defaultdict(lambda: ProfileStats(""))
        self._process = psutil.Process()

    def wrap_brick(self, brick: NanobrickProtocol) -> NanobrickProtocol:
        """Wrap a brick with profiling.

        Args:
            brick: Brick to wrap

        Returns:
            Wrapped brick with profiling
        """
        profiler = self

        class ProfiledBrick:
            """Brick wrapped with profiling."""

            def __init__(self, wrapped: NanobrickProtocol):
                self._wrapped = wrapped
                self.name = getattr(wrapped, "name", wrapped.__class__.__name__)
                self.version = getattr(wrapped, "version", "0.0.0")

                # Initialize stats
                if self.name not in profiler.stats:
                    profiler.stats[self.name] = ProfileStats(self.name)

            async def invoke(self, input: Any, *, deps: Any = None) -> Any:
                """Invoke with profiling."""
                stats = profiler.stats[self.name]

                # Prepare for measurement
                if profiler.gc_collect:
                    gc.collect()

                # Memory before
                memory_before = 0
                if profiler.measure_memory:
                    memory_before = profiler._process.memory_info().rss / 1024 / 1024

                # Time execution
                start_time = time.perf_counter()

                try:
                    result = await self._wrapped.invoke(input, deps=deps)

                    # Calculate metrics
                    duration_ms = (time.perf_counter() - start_time) * 1000

                    memory_delta = 0
                    if profiler.measure_memory:
                        memory_after = profiler._process.memory_info().rss / 1024 / 1024
                        memory_delta = memory_after - memory_before

                    # Update stats
                    stats.update(duration_ms, memory_delta)

                    return result

                except Exception:
                    stats.errors += 1
                    raise

            def invoke_sync(self, input: Any, *, deps: Any = None) -> Any:
                """Synchronous invoke with profiling."""
                return asyncio.run(self.invoke(input, deps=deps))

            def __rshift__(self, other):
                """Compose with profiling."""
                from nanobricks.composition import Pipeline

                return Pipeline(self, other)

        return ProfiledBrick(brick)
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
