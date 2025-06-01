"""Performance profiler for nanobricks."""

import asyncio
import gc
import time
import tracemalloc
from collections import defaultdict
from dataclasses import dataclass
from typing import Any

import psutil
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

from nanobricks import NanobrickProtocol


@dataclass
class PerformanceMetrics:
    """Performance metrics for a brick execution."""

    brick_name: str
    start_time: float
    end_time: float
    cpu_percent_before: float
    cpu_percent_after: float
    memory_before: int
    memory_after: int
    memory_peak: int
    gc_stats_before: dict[int, int]
    gc_stats_after: dict[int, int]
    input_size: int
    output_size: int
    error: Exception | None = None

    @property
    def duration_ms(self) -> float:
        """Execution duration in milliseconds."""
        return (self.end_time - self.start_time) * 1000

    @property
    def memory_delta(self) -> int:
        """Memory usage change in bytes."""
        return self.memory_after - self.memory_before

    @property
    def memory_delta_mb(self) -> float:
        """Memory usage change in MB."""
        return self.memory_delta / (1024 * 1024)

    @property
    def gc_collections(self) -> dict[int, int]:
        """GC collections during execution."""
        return {
            gen: self.gc_stats_after.get(gen, 0) - self.gc_stats_before.get(gen, 0)
            for gen in range(3)
        }


@dataclass
class ProfileReport:
    """Complete profiling report."""

    pipeline_name: str
    total_duration_ms: float
    total_memory_delta_mb: float
    brick_metrics: list[PerformanceMetrics]
    hotspots: list[tuple[str, float]]  # (brick_name, percentage)
    memory_leaks: list[tuple[str, float]]  # (brick_name, MB)
    recommendations: list[str]


class PerformanceProfiler:
    """Performance profiler for nanobricks."""

    def __init__(
        self,
        console: Console | None = None,
        track_memory: bool = True,
        track_cpu: bool = True,
        track_gc: bool = True,
        sample_interval: float = 0.01,
        memory_snapshots: bool = False,
    ):
        """Initialize performance profiler.

        Args:
            console: Rich console for output
            track_memory: Whether to track memory usage
            track_cpu: Whether to track CPU usage
            track_gc: Whether to track garbage collection
            sample_interval: Sampling interval for continuous monitoring
            memory_snapshots: Whether to take memory snapshots
        """
        self.console = console or Console()
        self.track_memory = track_memory
        self.track_cpu = track_cpu
        self.track_gc = track_gc
        self.sample_interval = sample_interval
        self.memory_snapshots = memory_snapshots

        # Metrics storage
        self._metrics: list[PerformanceMetrics] = []
        self._process = psutil.Process()

        # Memory tracking
        if self.memory_snapshots:
            tracemalloc.start()

    def wrap_brick(self, brick: NanobrickProtocol) -> NanobrickProtocol:
        """Wrap a brick to capture performance metrics."""

        class ProfiledBrick:
            """Wrapper that captures performance metrics."""

            def __init__(self, inner: NanobrickProtocol, profiler: PerformanceProfiler):
                self._inner = inner
                self._profiler = profiler
                self.name = getattr(inner, "name", inner.__class__.__name__)
                self.version = getattr(inner, "version", "1.0.0")

            async def invoke(self, input: Any, *, deps: Any = None) -> Any:
                """Invoke with profiling."""
                # Pre-execution metrics
                gc_before = (
                    {i: gc.get_count()[i] for i in range(3)}
                    if self._profiler.track_gc
                    else {}
                )
                memory_before = (
                    self._profiler._get_memory_usage()
                    if self._profiler.track_memory
                    else 0
                )
                cpu_before = (
                    self._profiler._get_cpu_percent() if self._profiler.track_cpu else 0
                )
                input_size = self._profiler._get_size(input)

                # Take memory snapshot
                if self._profiler.memory_snapshots:
                    snapshot_before = tracemalloc.take_snapshot()

                start_time = time.time()
                memory_peak = memory_before

                try:
                    # Execute brick
                    result = await self._inner.invoke(input, deps=deps)

                    # Post-execution metrics
                    end_time = time.time()
                    gc_after = (
                        {i: gc.get_count()[i] for i in range(3)}
                        if self._profiler.track_gc
                        else {}
                    )
                    memory_after = (
                        self._profiler._get_memory_usage()
                        if self._profiler.track_memory
                        else 0
                    )
                    cpu_after = (
                        self._profiler._get_cpu_percent()
                        if self._profiler.track_cpu
                        else 0
                    )
                    output_size = self._profiler._get_size(result)

                    # Memory peak tracking
                    if self._profiler.track_memory:
                        memory_peak = max(memory_peak, memory_after)

                    # Take memory snapshot
                    if self._profiler.memory_snapshots:
                        snapshot_after = tracemalloc.take_snapshot()
                        self._analyze_memory_diff(
                            snapshot_before, snapshot_after, self.name
                        )

                    # Record metrics
                    metrics = PerformanceMetrics(
                        brick_name=self.name,
                        start_time=start_time,
                        end_time=end_time,
                        cpu_percent_before=cpu_before,
                        cpu_percent_after=cpu_after,
                        memory_before=memory_before,
                        memory_after=memory_after,
                        memory_peak=memory_peak,
                        gc_stats_before=gc_before,
                        gc_stats_after=gc_after,
                        input_size=input_size,
                        output_size=output_size,
                    )
                    self._profiler._metrics.append(metrics)

                    return result

                except Exception as e:
                    # Record error metrics
                    end_time = time.time()
                    metrics = PerformanceMetrics(
                        brick_name=self.name,
                        start_time=start_time,
                        end_time=end_time,
                        cpu_percent_before=cpu_before,
                        cpu_percent_after=cpu_before,
                        memory_before=memory_before,
                        memory_after=memory_before,
                        memory_peak=memory_peak,
                        gc_stats_before=gc_before,
                        gc_stats_after=gc_before,
                        input_size=input_size,
                        output_size=0,
                        error=e,
                    )
                    self._profiler._metrics.append(metrics)
                    raise

            def invoke_sync(self, input: Any, *, deps: Any = None) -> Any:
                """Synchronous invoke with profiling."""
                return asyncio.run(self.invoke(input, deps=deps))

            def __or__(self, other):
                """Compose with profiling."""
                # Wrap the other brick too
                if not isinstance(other, ProfiledBrick):
                    other = self._profiler.wrap_brick(other)

                # Create composite
                from nanobricks.composition import CompositeBrick

                composite = CompositeBrick([self._inner, other._inner])
                return self._profiler.wrap_brick(composite)

        return ProfiledBrick(brick, self)

    def _get_memory_usage(self) -> int:
        """Get current memory usage in bytes."""
        return self._process.memory_info().rss

    def _get_cpu_percent(self) -> float:
        """Get current CPU usage percentage."""
        return self._process.cpu_percent(interval=None)

    def _get_size(self, obj: Any) -> int:
        """Get approximate size of object in bytes."""
        try:
            import sys

            return sys.getsizeof(obj)
        except:
            return 0

    def _analyze_memory_diff(self, snapshot1, snapshot2, brick_name: str):
        """Analyze memory allocation differences."""
        top_stats = snapshot2.compare_to(snapshot1, "lineno")

        # Find allocations related to the brick
        for stat in top_stats[:10]:
            if stat.size_diff > 1024 * 1024:  # More than 1MB
                self.console.print(
                    f"[yellow]Memory allocation in {brick_name}: "
                    f"{stat.size_diff / 1024 / 1024:.2f} MB at {stat.traceback[0]}[/yellow]"
                )

    async def profile_pipeline(
        self,
        pipeline: NanobrickProtocol,
        input: Any,
        deps: Any = None,
        runs: int = 1,
        warmup_runs: int = 0,
        show_progress: bool = True,
    ) -> ProfileReport:
        """Profile a pipeline execution.

        Args:
            pipeline: Pipeline to profile
            input: Input data
            deps: Dependencies
            runs: Number of profiling runs
            warmup_runs: Number of warmup runs
            show_progress: Whether to show progress

        Returns:
            Profile report
        """
        # Clear previous metrics
        self._metrics.clear()

        # Wrap pipeline
        wrapped = self.wrap_brick(pipeline)

        # Warmup runs
        if warmup_runs > 0:
            if show_progress:
                self.console.print(f"[dim]Running {warmup_runs} warmup runs...[/dim]")

            for _ in range(warmup_runs):
                await wrapped.invoke(input, deps=deps)

            # Clear warmup metrics
            self._metrics.clear()

        # Profiling runs
        if show_progress:
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=self.console,
            ) as progress:
                task = progress.add_task(f"Profiling {runs} runs...", total=runs)

                for i in range(runs):
                    await wrapped.invoke(input, deps=deps)
                    progress.update(task, advance=1)
        else:
            for _ in range(runs):
                await wrapped.invoke(input, deps=deps)

        # Generate report
        return self._generate_report(pipeline)

    def _generate_report(self, pipeline: NanobrickProtocol) -> ProfileReport:
        """Generate profiling report from collected metrics."""
        if not self._metrics:
            return ProfileReport(
                pipeline_name=getattr(pipeline, "name", pipeline.__class__.__name__),
                total_duration_ms=0,
                total_memory_delta_mb=0,
                brick_metrics=[],
                hotspots=[],
                memory_leaks=[],
                recommendations=[],
            )

        # Aggregate metrics by brick
        brick_stats = defaultdict(
            lambda: {
                "count": 0,
                "total_time": 0,
                "total_memory": 0,
                "max_memory": 0,
                "errors": 0,
            }
        )

        total_duration = 0
        total_memory = 0

        for metric in self._metrics:
            stats = brick_stats[metric.brick_name]
            stats["count"] += 1
            stats["total_time"] += metric.duration_ms
            stats["total_memory"] += metric.memory_delta
            stats["max_memory"] = max(stats["max_memory"], metric.memory_delta)
            if metric.error:
                stats["errors"] += 1

            total_duration += metric.duration_ms
            total_memory += metric.memory_delta

        # Identify hotspots (bricks taking >20% of time)
        hotspots = []
        for brick_name, stats in brick_stats.items():
            percentage = (
                (stats["total_time"] / total_duration * 100)
                if total_duration > 0
                else 0
            )
            if percentage > 20:
                hotspots.append((brick_name, percentage))

        hotspots.sort(key=lambda x: x[1], reverse=True)

        # Identify memory leaks (bricks with high memory retention)
        memory_leaks = []
        for brick_name, stats in brick_stats.items():
            avg_memory_mb = stats["total_memory"] / stats["count"] / (1024 * 1024)
            if avg_memory_mb > 10:  # More than 10MB average
                memory_leaks.append((brick_name, avg_memory_mb))

        memory_leaks.sort(key=lambda x: x[1], reverse=True)

        # Generate recommendations
        recommendations = []

        if hotspots:
            recommendations.append(
                f"Performance hotspot detected: {hotspots[0][0]} "
                f"uses {hotspots[0][1]:.1f}% of execution time"
            )

        if memory_leaks:
            recommendations.append(
                f"Memory concern: {memory_leaks[0][0]} "
                f"retains {memory_leaks[0][1]:.1f}MB on average"
            )

        # Check for high GC activity
        gc_activity = sum(sum(m.gc_collections.values()) for m in self._metrics)
        if gc_activity > len(self._metrics) * 5:
            recommendations.append(
                "High GC activity detected. Consider optimizing object allocation."
            )

        return ProfileReport(
            pipeline_name=getattr(pipeline, "name", pipeline.__class__.__name__),
            total_duration_ms=(
                total_duration / len(self._metrics) if self._metrics else 0
            ),
            total_memory_delta_mb=(
                total_memory / len(self._metrics) / (1024 * 1024)
                if self._metrics
                else 0
            ),
            brick_metrics=self._metrics,
            hotspots=hotspots,
            memory_leaks=memory_leaks,
            recommendations=recommendations,
        )

    def display_report(self, report: ProfileReport):
        """Display profiling report in console."""
        # Header
        self.console.print(
            f"\n[bold blue]Performance Profile: {report.pipeline_name}[/bold blue]"
        )
        self.console.print(f"Average Duration: {report.total_duration_ms:.2f}ms")
        self.console.print(
            f"Average Memory Change: {report.total_memory_delta_mb:+.2f}MB\n"
        )

        # Brick performance table
        if report.brick_metrics:
            # Aggregate by brick name
            brick_summary = defaultdict(
                lambda: {"count": 0, "total_time": 0, "avg_memory": 0, "max_memory": 0}
            )

            for metric in report.brick_metrics:
                summary = brick_summary[metric.brick_name]
                summary["count"] += 1
                summary["total_time"] += metric.duration_ms
                summary["avg_memory"] += metric.memory_delta_mb
                summary["max_memory"] = max(
                    summary["max_memory"], metric.memory_delta_mb
                )

            # Calculate averages
            for summary in brick_summary.values():
                summary["avg_time"] = summary["total_time"] / summary["count"]
                summary["avg_memory"] = summary["avg_memory"] / summary["count"]

            # Create table
            table = Table(title="Brick Performance Summary")
            table.add_column("Brick", style="cyan")
            table.add_column("Calls", style="white")
            table.add_column("Avg Time (ms)", style="yellow")
            table.add_column("Total Time %", style="green")
            table.add_column("Avg Memory (MB)", style="magenta")

            total_time = sum(s["total_time"] for s in brick_summary.values())

            for brick_name, summary in sorted(
                brick_summary.items(), key=lambda x: x[1]["total_time"], reverse=True
            ):
                time_percentage = (
                    (summary["total_time"] / total_time * 100) if total_time > 0 else 0
                )

                table.add_row(
                    brick_name,
                    str(summary["count"]),
                    f"{summary['avg_time']:.2f}",
                    f"{time_percentage:.1f}%",
                    f"{summary['avg_memory']:+.2f}",
                )

            self.console.print(table)

        # Hotspots
        if report.hotspots:
            self.console.print("\n[bold red]Performance Hotspots:[/bold red]")
            for brick, percentage in report.hotspots:
                self.console.print(f"  • {brick}: {percentage:.1f}% of execution time")

        # Memory concerns
        if report.memory_leaks:
            self.console.print("\n[bold yellow]Memory Concerns:[/bold yellow]")
            for brick, memory_mb in report.memory_leaks:
                self.console.print(f"  • {brick}: {memory_mb:.1f}MB average retention")

        # Recommendations
        if report.recommendations:
            self.console.print("\n[bold green]Recommendations:[/bold green]")
            for rec in report.recommendations:
                self.console.print(f"  • {rec}")

    def compare_profiles(self, report1: ProfileReport, report2: ProfileReport):
        """Compare two profile reports."""
        table = Table(title="Profile Comparison")
        table.add_column("Metric", style="cyan")
        table.add_column("Profile 1", style="yellow")
        table.add_column("Profile 2", style="green")
        table.add_column("Change", style="magenta")

        # Overall metrics
        time_change = report2.total_duration_ms - report1.total_duration_ms
        time_change_pct = (
            (time_change / report1.total_duration_ms * 100)
            if report1.total_duration_ms > 0
            else 0
        )

        memory_change = report2.total_memory_delta_mb - report1.total_memory_delta_mb

        table.add_row(
            "Average Duration",
            f"{report1.total_duration_ms:.2f}ms",
            f"{report2.total_duration_ms:.2f}ms",
            f"{time_change:+.2f}ms ({time_change_pct:+.1f}%)",
        )

        table.add_row(
            "Average Memory",
            f"{report1.total_memory_delta_mb:+.2f}MB",
            f"{report2.total_memory_delta_mb:+.2f}MB",
            f"{memory_change:+.2f}MB",
        )

        self.console.print(table)


def profile_pipeline(
    pipeline: NanobrickProtocol, input: Any, deps: Any = None, runs: int = 10, **kwargs
) -> ProfileReport:
    """Convenience function to profile a pipeline.

    Args:
        pipeline: Pipeline to profile
        input: Input data
        deps: Dependencies
        runs: Number of profiling runs
        **kwargs: Additional arguments for PerformanceProfiler

    Returns:
        Profile report
    """
    profiler = PerformanceProfiler(**kwargs)
    return asyncio.run(profiler.profile_pipeline(pipeline, input, deps, runs))
