"""Tests for developer tools."""

import asyncio
import json
import tempfile
from pathlib import Path

import pytest

from nanobricks import NanobrickBase
from nanobricks.devtools import (
    BrickDebugger,
    BrickProfiler,
    PipelineVisualizer,
    profile_brick,
    visualize_pipeline,
)


class TestDevtoolsBrick(NanobrickBase[str, str, None]):
    """Test brick for devtools."""

    def __init__(self, name: str = "test", delay: float = 0.01):
        super().__init__(name=name, version="1.0.0")
        self.delay = delay

    async def invoke(self, input: str, *, deps: None = None) -> str:
        await asyncio.sleep(self.delay)
        return f"{self.name}: {input}"


class ErrorNanobrick(NanobrickBase[str, str, None]):
    """Brick that always errors."""

    async def invoke(self, input: str, *, deps: None = None) -> str:
        raise ValueError("Test error")


class TestDebugger:
    """Test brick debugger."""

    @pytest.mark.asyncio
    async def test_basic_debugging(self):
        """Test basic debugging functionality."""
        debugger = BrickDebugger()
        brick = TestDevtoolsBrick("test1")
        debugged = debugger.wrap_brick(brick)

        result = await debugged.invoke("hello")
        assert result == "test1: hello"

        # Check events
        assert len(debugger.events) == 2
        assert debugger.events[0].event_type == "invoke_start"
        assert debugger.events[1].event_type == "invoke_end"
        assert debugger.events[0].data.get("input") == "hello"
        assert debugger.events[1].data.get("output") == "test1: hello"

    @pytest.mark.asyncio
    async def test_error_debugging(self):
        """Test debugging with errors."""
        debugger = BrickDebugger()
        brick = ErrorNanobrick()
        debugged = debugger.wrap_brick(brick)

        with pytest.raises(ValueError):
            await debugged.invoke("test")

        # Check error event
        assert len(debugger.events) == 2
        assert debugger.events[1].event_type == "error"
        assert debugger.events[1].data["error_type"] == "ValueError"
        assert debugger.events[1].data["error_message"] == "Test error"

    @pytest.mark.asyncio
    async def test_pipeline_debugging(self):
        """Test debugging a pipeline."""
        brick1 = TestDevtoolsBrick("brick1")
        brick2 = TestDevtoolsBrick("brick2")

        debugger = BrickDebugger()
        debugged1 = debugger.wrap_brick(brick1)
        debugged2 = debugger.wrap_brick(brick2)
        debugged_pipeline = debugged1 | debugged2

        result = await debugged_pipeline.invoke("test")
        assert "brick2: brick1: test" in result

        # Should have 4 events (2 per brick)
        assert len(debugger.events) == 4

    def test_trace_saving(self):
        """Test saving debug trace."""
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            debugger = BrickDebugger(save_to_file=Path(f.name))
            brick = TestDevtoolsBrick()
            debugged = debugger.wrap_brick(brick)

            # Run
            asyncio.run(debugged.invoke("test"))

            # Save trace
            debugger.save_trace()

            # Load and verify
            with open(f.name) as fp:
                trace = json.load(fp)

            assert len(trace) == 2
            assert trace[0]["event_type"] == "invoke_start"
            assert trace[1]["event_type"] == "invoke_end"


class TestProfiler:
    """Test brick profiler."""

    @pytest.mark.asyncio
    async def test_basic_profiling(self):
        """Test basic profiling functionality."""
        profiler = BrickProfiler(measure_memory=False)
        brick = TestDevtoolsBrick("test1", delay=0.01)
        profiled = profiler.wrap_brick(brick)

        # Run multiple times
        for i in range(5):
            await profiled.invoke(f"test_{i}")

        # Check stats
        stats = profiler.stats["test1"]
        assert stats.call_count == 5
        assert stats.total_time_ms > 50  # 5 * 10ms minimum
        assert stats.avg_time_ms >= 10
        assert stats.min_time_ms >= 10
        assert stats.max_time_ms >= 10

    @pytest.mark.asyncio
    async def test_error_counting(self):
        """Test error counting in profiler."""
        profiler = BrickProfiler(measure_memory=False)
        brick = ErrorNanobrick()
        profiled = profiler.wrap_brick(brick)

        # Run and expect errors
        for i in range(3):
            with pytest.raises(ValueError):
                await profiled.invoke("test")

        stats = profiler.stats[brick.name]
        assert stats.errors == 3

    def test_profile_brick_function(self):
        """Test profile_brick helper function."""
        brick = TestDevtoolsBrick("profiled", delay=0.001)

        stats = profile_brick(
            brick, iterations=10, warmup=2, input_generator=lambda i: f"input_{i}"
        )

        assert stats.call_count == 10
        assert stats.total_time_ms >= 10  # 10 * 1ms minimum
        assert stats.avg_time_ms >= 1

    def test_bottleneck_detection(self):
        """Test bottleneck detection."""
        profiler = BrickProfiler(measure_memory=False)

        # Create bricks with different delays
        fast_brick = TestDevtoolsBrick("fast", delay=0.001)
        slow_brick = TestDevtoolsBrick("slow", delay=0.05)

        fast_profiled = profiler.wrap_brick(fast_brick)
        slow_profiled = profiler.wrap_brick(slow_brick)

        # Run
        asyncio.run(fast_profiled.invoke("test"))
        asyncio.run(slow_profiled.invoke("test"))

        # Check bottlenecks
        bottlenecks = profiler.get_bottlenecks(threshold_pct=50)
        assert "slow" in bottlenecks
        assert "fast" not in bottlenecks


class TestVisualizer:
    """Test pipeline visualizer."""

    def test_ascii_visualization(self):
        """Test ASCII visualization."""
        brick1 = TestDevtoolsBrick("processor")
        brick2 = TestDevtoolsBrick("validator")
        pipeline = brick1 | brick2

        visualizer = PipelineVisualizer(style="ascii")
        viz = visualizer.visualize(pipeline)

        assert "Pipeline Flow:" in viz
        assert "processor" in viz
        assert "validator" in viz
        assert "INPUT" in viz
        assert "OUTPUT" in viz
        assert "▼" in viz

    def test_mermaid_visualization(self):
        """Test Mermaid visualization."""
        brick1 = TestDevtoolsBrick("step1")
        brick2 = TestDevtoolsBrick("step2")
        pipeline = [brick1, brick2]

        viz = visualize_pipeline(pipeline, style="mermaid")

        assert "graph LR" in viz
        assert "step1" in viz
        assert "step2" in viz
        assert "Input --> B0" in viz
        assert "B0 --> B1" in viz
        assert "B1 --> Output" in viz

    def test_graphviz_visualization(self):
        """Test Graphviz visualization."""
        brick = TestDevtoolsBrick("single")

        viz = visualize_pipeline(brick, style="graphviz")

        assert "digraph Pipeline" in viz
        assert "single" in viz
        assert '"Input" -> "B0"' in viz
        assert '"B0" -> "Output"' in viz

    def test_save_visualization(self):
        """Test saving visualization."""
        with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as f:
            brick = TestDevtoolsBrick("saved")

            viz = visualize_pipeline(brick, save_to=f.name)

            # Check file was created
            assert Path(f.name).exists()

            # Check content
            with open(f.name) as fp:
                content = fp.read()

            assert "saved" in content
