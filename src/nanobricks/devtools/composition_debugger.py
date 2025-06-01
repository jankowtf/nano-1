"""Composition debugger for nanobricks pipelines."""

import asyncio
import inspect
import time
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.tree import Tree

from nanobricks import NanobrickProtocol


@dataclass
class DebugEvent:
    """Debug event captured during execution."""

    timestamp: float
    brick_name: str
    event_type: str  # 'input', 'output', 'error', 'timing'
    data: Any
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class ExecutionTrace:
    """Complete execution trace for a pipeline."""

    pipeline_name: str
    start_time: float
    end_time: float
    events: list[DebugEvent]
    input_data: Any
    output_data: Any
    error: Exception | None = None

    @property
    def duration_ms(self) -> float:
        """Total execution time in milliseconds."""
        return (self.end_time - self.start_time) * 1000

    def get_brick_events(self, brick_name: str) -> list[DebugEvent]:
        """Get all events for a specific brick."""
        return [e for e in self.events if e.brick_name == brick_name]

    def get_timings(self) -> dict[str, float]:
        """Get timing information for each brick."""
        timings = {}
        brick_starts = {}

        for event in self.events:
            if event.event_type == "input":
                brick_starts[event.brick_name] = event.timestamp
            elif event.event_type == "output" and event.brick_name in brick_starts:
                duration = (event.timestamp - brick_starts[event.brick_name]) * 1000
                timings[event.brick_name] = duration

        return timings


class CompositionDebugger:
    """Debugger for nanobrick compositions."""

    def __init__(
        self,
        console: Console | None = None,
        capture_inputs: bool = True,
        capture_outputs: bool = True,
        capture_timing: bool = True,
        max_data_size: int = 1000,
        save_traces: bool = False,
        trace_dir: Path | None = None,
    ):
        """Initialize composition debugger.

        Args:
            console: Rich console for output
            capture_inputs: Whether to capture input data
            capture_outputs: Whether to capture output data
            capture_timing: Whether to capture timing information
            max_data_size: Maximum size of data to capture (for display)
            save_traces: Whether to save traces to disk
            trace_dir: Directory to save traces
        """
        self.console = console or Console()
        self.capture_inputs = capture_inputs
        self.capture_outputs = capture_outputs
        self.capture_timing = capture_timing
        self.max_data_size = max_data_size
        self.save_traces = save_traces
        self.trace_dir = trace_dir or Path("debug_traces")

        if self.save_traces:
            self.trace_dir.mkdir(exist_ok=True)

        # Current trace being recorded
        self._current_trace: ExecutionTrace | None = None
        self._trace_history: list[ExecutionTrace] = []

    def wrap_brick(self, brick: NanobrickProtocol) -> NanobrickProtocol:
        """Wrap a brick to capture debug information."""

        class DebuggedBrick:
            """Wrapper that captures debug information."""

            def __init__(self, inner: NanobrickProtocol, debugger: CompositionDebugger):
                self._inner = inner
                self._debugger = debugger
                self.name = getattr(inner, "name", inner.__class__.__name__)
                self.version = getattr(inner, "version", "1.0.0")

            async def invoke(self, input: Any, *, deps: Any = None) -> Any:
                """Invoke with debugging."""
                if self._debugger._current_trace is None:
                    # Start new trace
                    self._debugger._current_trace = ExecutionTrace(
                        pipeline_name=self.name,
                        start_time=time.time(),
                        end_time=0,
                        events=[],
                        input_data=input,
                        output_data=None,
                    )

                # Capture input event
                if self._debugger.capture_inputs:
                    self._debugger._record_event(
                        DebugEvent(
                            timestamp=time.time(),
                            brick_name=self.name,
                            event_type="input",
                            data=self._debugger._truncate_data(input),
                            metadata={
                                "input_type": type(input).__name__,
                                "input_size": self._debugger._get_size(input),
                            },
                        )
                    )

                start_time = time.time()
                try:
                    # Execute brick
                    result = await self._inner.invoke(input, deps=deps)

                    # Capture output event
                    if self._debugger.capture_outputs:
                        self._debugger._record_event(
                            DebugEvent(
                                timestamp=time.time(),
                                brick_name=self.name,
                                event_type="output",
                                data=self._debugger._truncate_data(result),
                                metadata={
                                    "output_type": type(result).__name__,
                                    "output_size": self._debugger._get_size(result),
                                },
                            )
                        )

                    # Capture timing
                    if self._debugger.capture_timing:
                        self._debugger._record_event(
                            DebugEvent(
                                timestamp=time.time(),
                                brick_name=self.name,
                                event_type="timing",
                                data=None,
                                metadata={
                                    "duration_ms": (time.time() - start_time) * 1000
                                },
                            )
                        )

                    return result

                except Exception as e:
                    # Capture error event
                    self._debugger._record_event(
                        DebugEvent(
                            timestamp=time.time(),
                            brick_name=self.name,
                            event_type="error",
                            data=str(e),
                            metadata={
                                "error_type": type(e).__name__,
                                "traceback": inspect.trace(),
                            },
                        )
                    )
                    if self._debugger._current_trace:
                        self._debugger._current_trace.error = e
                    raise

            def invoke_sync(self, input: Any, *, deps: Any = None) -> Any:
                """Synchronous invoke with debugging."""
                return asyncio.run(self.invoke(input, deps=deps))

            def __or__(self, other):
                """Compose with debugging."""
                # Wrap the other brick too
                if not isinstance(other, DebuggedBrick):
                    other = self._debugger.wrap_brick(other)

                # Create composite
                from nanobricks.composition import CompositeBrick

                composite = CompositeBrick([self._inner, other._inner])
                return self._debugger.wrap_brick(composite)

        return DebuggedBrick(brick, self)

    def _record_event(self, event: DebugEvent):
        """Record a debug event."""
        if self._current_trace:
            self._current_trace.events.append(event)

    def _truncate_data(self, data: Any) -> Any:
        """Truncate data for display."""
        data_str = str(data)
        if len(data_str) > self.max_data_size:
            return data_str[: self.max_data_size] + "..."
        return data

    def _get_size(self, data: Any) -> int:
        """Get approximate size of data."""
        try:
            return len(str(data))
        except:
            return -1

    async def debug_pipeline(
        self,
        pipeline: NanobrickProtocol,
        input: Any,
        deps: Any = None,
        show_live: bool = True,
    ) -> tuple[Any, ExecutionTrace]:
        """Debug a pipeline execution.

        Args:
            pipeline: Pipeline to debug
            input: Input data
            deps: Dependencies
            show_live: Whether to show live debugging output

        Returns:
            Tuple of (result, trace)
        """
        # Wrap pipeline
        wrapped = self.wrap_brick(pipeline)

        # Reset trace
        self._current_trace = None

        # Execute
        try:
            if show_live:
                self.console.print("\n[bold blue]🔍 Debugging Pipeline[/bold blue]")
                self.console.print(f"Input: {self._truncate_data(input)}\n")

            result = await wrapped.invoke(input, deps=deps)

            if self._current_trace:
                self._current_trace.end_time = time.time()
                self._current_trace.output_data = result
                self._trace_history.append(self._current_trace)

                if show_live:
                    self.display_trace(self._current_trace)

                if self.save_traces:
                    self._save_trace(self._current_trace)

                return result, self._current_trace

        except Exception as e:
            if self._current_trace:
                self._current_trace.end_time = time.time()
                self._current_trace.error = e
                self._trace_history.append(self._current_trace)

                if show_live:
                    self.display_trace(self._current_trace)

                if self.save_traces:
                    self._save_trace(self._current_trace)

            raise

    def display_trace(self, trace: ExecutionTrace):
        """Display execution trace in console."""
        # Header
        status = "✅ Success" if trace.error is None else "❌ Failed"
        self.console.print(f"\n[bold]{status}[/bold] - {trace.duration_ms:.2f}ms total")

        # Build execution flow
        tree = Tree(f"[bold blue]{trace.pipeline_name}[/bold blue]")

        current_node = tree
        brick_nodes = {}

        for event in trace.events:
            if event.event_type == "input":
                node = current_node.add(f"[green]→ {event.brick_name}[/green]")
                brick_nodes[event.brick_name] = node
                node.add(f"Input: {event.data}")

            elif event.event_type == "output" and event.brick_name in brick_nodes:
                node = brick_nodes[event.brick_name]
                node.add(f"Output: {event.data}")

            elif event.event_type == "error" and event.brick_name in brick_nodes:
                node = brick_nodes[event.brick_name]
                node.add(f"[red]Error: {event.data}[/red]")

        self.console.print(tree)

        # Timing table
        if self.capture_timing:
            timings = trace.get_timings()
            if timings:
                table = Table(title="Brick Timings")
                table.add_column("Brick", style="cyan")
                table.add_column("Duration (ms)", style="magenta")
                table.add_column("Percentage", style="green")

                total_time = sum(timings.values())
                for brick, duration in sorted(
                    timings.items(), key=lambda x: x[1], reverse=True
                ):
                    percentage = (duration / total_time * 100) if total_time > 0 else 0
                    table.add_row(brick, f"{duration:.2f}", f"{percentage:.1f}%")

                self.console.print("\n", table)

        # Error details
        if trace.error:
            error_panel = Panel(
                f"[red]{type(trace.error).__name__}[/red]: {trace.error}",
                title="Error Details",
                border_style="red",
            )
            self.console.print("\n", error_panel)

    def compare_traces(self, trace1: ExecutionTrace, trace2: ExecutionTrace):
        """Compare two execution traces."""
        table = Table(title="Trace Comparison")
        table.add_column("Metric", style="cyan")
        table.add_column("Trace 1", style="yellow")
        table.add_column("Trace 2", style="green")
        table.add_column("Difference", style="magenta")

        # Duration
        table.add_row(
            "Total Duration",
            f"{trace1.duration_ms:.2f}ms",
            f"{trace2.duration_ms:.2f}ms",
            f"{trace2.duration_ms - trace1.duration_ms:+.2f}ms",
        )

        # Event counts
        table.add_row(
            "Total Events",
            str(len(trace1.events)),
            str(len(trace2.events)),
            str(len(trace2.events) - len(trace1.events)),
        )

        # Success/failure
        table.add_row(
            "Status",
            "Success" if trace1.error is None else "Failed",
            "Success" if trace2.error is None else "Failed",
            "Same" if (trace1.error is None) == (trace2.error is None) else "Different",
        )

        self.console.print(table)

        # Compare brick timings
        timings1 = trace1.get_timings()
        timings2 = trace2.get_timings()

        if timings1 and timings2:
            timing_table = Table(title="Timing Comparison")
            timing_table.add_column("Brick", style="cyan")
            timing_table.add_column("Trace 1 (ms)", style="yellow")
            timing_table.add_column("Trace 2 (ms)", style="green")
            timing_table.add_column("Change", style="magenta")

            all_bricks = set(timings1.keys()) | set(timings2.keys())
            for brick in sorted(all_bricks):
                t1 = timings1.get(brick, 0)
                t2 = timings2.get(brick, 0)
                change = ((t2 - t1) / t1 * 100) if t1 > 0 else 0

                timing_table.add_row(
                    brick,
                    f"{t1:.2f}" if brick in timings1 else "N/A",
                    f"{t2:.2f}" if brick in timings2 else "N/A",
                    (
                        f"{change:+.1f}%"
                        if brick in timings1 and brick in timings2
                        else "N/A"
                    ),
                )

            self.console.print("\n", timing_table)

    def _save_trace(self, trace: ExecutionTrace):
        """Save trace to disk."""
        import json
        from datetime import datetime

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = self.trace_dir / f"trace_{trace.pipeline_name}_{timestamp}.json"

        # Convert trace to serializable format
        trace_data = {
            "pipeline_name": trace.pipeline_name,
            "start_time": trace.start_time,
            "end_time": trace.end_time,
            "duration_ms": trace.duration_ms,
            "input_data": str(trace.input_data),
            "output_data": str(trace.output_data),
            "error": str(trace.error) if trace.error else None,
            "events": [
                {
                    "timestamp": e.timestamp,
                    "brick_name": e.brick_name,
                    "event_type": e.event_type,
                    "data": str(e.data),
                    "metadata": e.metadata,
                }
                for e in trace.events
            ],
        }

        with open(filename, "w") as f:
            json.dump(trace_data, f, indent=2)

    def analyze_performance(self, traces: list[ExecutionTrace]) -> dict[str, Any]:
        """Analyze performance across multiple traces."""
        if not traces:
            return {}

        # Aggregate statistics
        stats = {
            "total_executions": len(traces),
            "successful": sum(1 for t in traces if t.error is None),
            "failed": sum(1 for t in traces if t.error is not None),
            "average_duration_ms": sum(t.duration_ms for t in traces) / len(traces),
            "min_duration_ms": min(t.duration_ms for t in traces),
            "max_duration_ms": max(t.duration_ms for t in traces),
            "brick_stats": defaultdict(
                lambda: {
                    "count": 0,
                    "total_time_ms": 0,
                    "min_time_ms": float("inf"),
                    "max_time_ms": 0,
                }
            ),
        }

        # Aggregate brick statistics
        for trace in traces:
            timings = trace.get_timings()
            for brick, duration in timings.items():
                brick_stat = stats["brick_stats"][brick]
                brick_stat["count"] += 1
                brick_stat["total_time_ms"] += duration
                brick_stat["min_time_ms"] = min(brick_stat["min_time_ms"], duration)
                brick_stat["max_time_ms"] = max(brick_stat["max_time_ms"], duration)

        # Calculate averages
        for brick, stat in stats["brick_stats"].items():
            if stat["count"] > 0:
                stat["average_time_ms"] = stat["total_time_ms"] / stat["count"]

        return stats


def debug_pipeline(
    pipeline: NanobrickProtocol, input: Any, deps: Any = None, **kwargs
) -> tuple[Any, ExecutionTrace]:
    """Convenience function to debug a pipeline.

    Args:
        pipeline: Pipeline to debug
        input: Input data
        deps: Dependencies
        **kwargs: Additional arguments for CompositionDebugger

    Returns:
        Tuple of (result, trace)
    """
    debugger = CompositionDebugger(**kwargs)
    return asyncio.run(debugger.debug_pipeline(pipeline, input, deps))
