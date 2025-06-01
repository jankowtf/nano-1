"""Performance profiler for nanobricks."""

import asyncio
import gc
import time
from collections import defaultdict
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

            def __or__(self, other):
                """Compose with profiling."""
                from nanobricks.composition import Pipeline

                return Pipeline(self, other)

        return ProfiledBrick(brick)

    def get_stats(self) -> dict[str, dict[str, Any]]:
        """Get profiling statistics.

        Returns:
            Statistics by brick name
        """
        return {name: stats.to_dict() for name, stats in self.stats.items()}

    def print_stats(self, sort_by: str = "total_time_ms"):
        """Print profiling statistics.

        Args:
            sort_by: Field to sort by
        """
        print("\n⏱️  Performance Profile:")
        print("=" * 80)
        print(
            f"{'Brick':<30} {'Calls':>8} {'Total(ms)':>10} {'Avg(ms)':>10} {'Min(ms)':>10} {'Max(ms)':>10}"
        )
        print("-" * 80)

        # Sort stats
        sorted_stats = sorted(
            self.stats.values(), key=lambda s: getattr(s, sort_by), reverse=True
        )

        for stats in sorted_stats:
            if stats.call_count > 0:
                print(
                    f"{stats.brick_name:<30} "
                    f"{stats.call_count:>8} "
                    f"{stats.total_time_ms:>10.2f} "
                    f"{stats.avg_time_ms:>10.2f} "
                    f"{stats.min_time_ms:>10.2f} "
                    f"{stats.max_time_ms:>10.2f}"
                )

        if self.measure_memory:
            print("\n💾 Memory Usage:")
            print("-" * 80)
            for stats in sorted_stats:
                if stats.call_count > 0 and stats.memory_delta_mb != 0:
                    print(
                        f"{stats.brick_name:<30} "
                        f"Delta: {stats.memory_delta_mb:>+8.2f} MB"
                    )

    def get_bottlenecks(self, threshold_pct: float = 20) -> list[str]:
        """Identify performance bottlenecks.

        Args:
            threshold_pct: Percentage of total time to consider a bottleneck

        Returns:
            List of bottleneck brick names
        """
        total_time = sum(s.total_time_ms for s in self.stats.values())
        if total_time == 0:
            return []

        bottlenecks = []
        for name, stats in self.stats.items():
            if (stats.total_time_ms / total_time) * 100 >= threshold_pct:
                bottlenecks.append(name)

        return bottlenecks

    def clear(self):
        """Clear all statistics."""
        self.stats.clear()


def profile_brick(
    brick: NanobrickProtocol,
    iterations: int = 100,
    warmup: int = 10,
    input_generator: callable | None = None,
) -> ProfileStats:
    """Profile a single brick.

    Args:
        brick: Brick to profile
        iterations: Number of iterations to run
        warmup: Number of warmup iterations
        input_generator: Function to generate input for each iteration

    Returns:
        Profile statistics
    """
    profiler = BrickProfiler()
    profiled = profiler.wrap_brick(brick)

    # Default input generator
    if input_generator is None:
        input_generator = lambda i: f"test_{i}"

    async def run_profile():
        # Warmup
        for i in range(warmup):
            await profiled.invoke(input_generator(i))

        # Clear stats after warmup
        profiler.clear()

        # Profile
        for i in range(iterations):
            await profiled.invoke(input_generator(i))

    # Run profile
    asyncio.run(run_profile())

    # Get stats
    brick_name = getattr(brick, "name", brick.__class__.__name__)
    return profiler.stats[brick_name]
