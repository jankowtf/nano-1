"""Tests for enhanced developer tools."""

import asyncio

import pytest

from nanobricks import NanobrickBase
from nanobricks.devtools import (
    CompositionDebugger,
    PerformanceProfiler,
    PipelineViz,
    TypeStubGenerator,
)


class Nanobrick(NanobrickBase[str, str, None]):
    """A simple test brick."""

    name = "simple"
    version = "1.0.0"

    async def invoke(self, input: str, *, deps=None) -> str:
        return input.upper()


class DelayNanobrick(NanobrickBase[str, str, None]):
    """A brick with configurable delay."""

    name = "delay"
    version = "1.0.0"

    def __init__(self, delay_ms: float = 10):
        self.delay_ms = delay_ms

    async def invoke(self, input: str, *, deps=None) -> str:
        await asyncio.sleep(self.delay_ms / 1000)
        return input


class ErrorNanobrick(NanobrickBase[str, str, None]):
    """A brick that always errors."""

    name = "error"
    version = "1.0.0"

    async def invoke(self, input: str, *, deps=None) -> str:
        raise ValueError("Test error")


class TestCompositionDebugger:
    """Test composition debugger."""

    @pytest.mark.asyncio
    async def test_debug_simple_pipeline(self):
        """Test debugging a simple pipeline."""
        debugger = CompositionDebugger(capture_inputs=True, capture_outputs=True)
        pipeline = Nanobrick()

        result, trace = await debugger.debug_pipeline(
            pipeline, "hello", show_live=False
        )

        assert result == "HELLO"
        assert trace.pipeline_name == "simple"
        assert len(trace.events) > 0
        assert trace.error is None

    @pytest.mark.asyncio
    async def test_debug_composite_pipeline(self):
        """Test debugging a composite pipeline."""
        debugger = CompositionDebugger()
        pipeline = Nanobrick() | DelayNanobrick(delay_ms=5)

        result, trace = await debugger.debug_pipeline(pipeline, "test", show_live=False)

        assert result == "TEST"
        assert len(trace.events) >= 4  # At least 2 inputs + 2 outputs

        # Check timing
        timings = trace.get_timings()
        assert "simple" in timings
        assert "delay" in timings

    @pytest.mark.asyncio
    async def test_debug_error_pipeline(self):
        """Test debugging a pipeline with errors."""
        debugger = CompositionDebugger()
        pipeline = Nanobrick() | ErrorNanobrick()

        with pytest.raises(ValueError):
            await debugger.debug_pipeline(pipeline, "test", show_live=False)

        # Check trace was recorded
        assert len(debugger._trace_history) > 0
        trace = debugger._trace_history[-1]
        assert trace.error is not None
        assert isinstance(trace.error, ValueError)

    def test_trace_analysis(self):
        """Test trace analysis methods."""
        from nanobricks.devtools.composition_debugger import DebugEvent, ExecutionTrace

        # Create mock trace
        trace = ExecutionTrace(
            pipeline_name="test",
            start_time=1000.0,
            end_time=1000.1,
            events=[
                DebugEvent(1000.0, "brick1", "input", "data", {}),
                DebugEvent(1000.05, "brick1", "output", "DATA", {}),
                DebugEvent(1000.05, "brick2", "input", "DATA", {}),
                DebugEvent(1000.1, "brick2", "output", "DATA!", {}),
            ],
            input_data="data",
            output_data="DATA!",
        )

        assert trace.duration_ms == 100.0
        assert len(trace.get_brick_events("brick1")) == 2

        timings = trace.get_timings()
        assert timings["brick1"] == 50.0
        assert timings["brick2"] == 50.0


class TestPerformanceProfiler:
    """Test performance profiler."""

    @pytest.mark.asyncio
    async def test_profile_simple_pipeline(self):
        """Test profiling a simple pipeline."""
        profiler = PerformanceProfiler(
            track_memory=True,
            track_cpu=False,  # CPU tracking can be flaky in tests
            track_gc=True,
        )

        pipeline = Nanobrick()
        report = await profiler.profile_pipeline(
            pipeline, "test", runs=3, show_progress=False
        )

        assert report.pipeline_name == "simple"
        assert report.total_duration_ms > 0
        assert len(report.brick_metrics) == 3  # 3 runs

    @pytest.mark.asyncio
    async def test_profile_with_hotspot(self):
        """Test identifying performance hotspots."""
        profiler = PerformanceProfiler()

        # Create pipeline with hotspot
        pipeline = (
            Nanobrick()  # Fast
            | DelayNanobrick(50)  # Slow (hotspot)
            | Nanobrick()  # Fast
        )

        report = await profiler.profile_pipeline(
            pipeline, "test", runs=2, show_progress=False
        )

        # Check hotspot detection
        assert len(report.hotspots) > 0
        assert report.hotspots[0][0] == "delay"
        assert report.hotspots[0][1] > 50  # Should be >50% of time

    @pytest.mark.asyncio
    async def test_memory_tracking(self):
        """Test memory usage tracking."""
        profiler = PerformanceProfiler(track_memory=True)

        class MemoryNanobrick(NanobrickBase[str, list, None]):
            """A brick that allocates memory."""

            name = "memory"

            async def invoke(self, input: str, *, deps=None) -> list:
                # Allocate some memory
                return [i for i in range(10000)]

        pipeline = MemoryNanobrick()
        report = await profiler.profile_pipeline(
            pipeline, "test", runs=1, show_progress=False
        )

        # Memory tracking might show 0 change due to GC
        assert report.total_memory_delta_mb >= 0


class TestPipelineVisualizer:
    """Test pipeline visualizer."""

    def test_analyze_simple_pipeline(self):
        """Test analyzing a simple pipeline."""
        visualizer = PipelineViz()
        pipeline = Nanobrick()

        root = visualizer.analyze_pipeline(pipeline)

        assert root.name == "simple"
        assert root.type == "Nanobrick"
        assert len(root.children) == 0

    def test_analyze_composite_pipeline(self):
        """Test analyzing a composite pipeline."""
        from nanobricks.composition import CompositeBrick

        visualizer = PipelineViz()
        pipeline = CompositeBrick([Nanobrick(), DelayNanobrick()])

        root = visualizer.analyze_pipeline(pipeline)

        assert root.type == "CompositeBrick"
        assert len(root.children) == 2
        assert root.children[0].name == "simple"
        assert root.children[1].name == "delay"

    def test_text_visualization(self):
        """Test text format visualization."""
        visualizer = PipelineViz(export_format="text", show_types=True)
        pipeline = Nanobrick() | DelayNanobrick()

        text = visualizer._render_text(visualizer.analyze_pipeline(pipeline))

        assert "simple" in text
        assert "delay" in text
        assert "str → str" in text

    def test_mermaid_visualization(self):
        """Test Mermaid diagram generation."""
        visualizer = PipelineViz(export_format="mermaid")
        pipeline = Nanobrick() | DelayNanobrick()

        mermaid = visualizer._render_mermaid(visualizer.analyze_pipeline(pipeline))

        assert "graph TD" in mermaid
        assert "simple" in mermaid
        assert "delay" in mermaid
        assert "-->" in mermaid

    def test_compare_pipelines(self):
        """Test pipeline comparison."""
        visualizer = PipelineViz()

        pipeline1 = Nanobrick() | DelayNanobrick()
        pipeline2 = Nanobrick() | DelayNanobrick() | Nanobrick()

        comparison = visualizer.compare_pipelines(pipeline1, pipeline2)

        assert not comparison["identical"]
        assert comparison["brick_count1"] == 2
        assert comparison["brick_count2"] == 3
        assert len(comparison["differences"]) > 0


class TestTypeStubGenerator:
    """Test type stub generator."""

    def test_generate_stub_for_simple_brick(self):
        """Test generating stub for simple brick."""
        generator = TypeStubGenerator()
        stub = generator.generate_stub_for_brick(Nanobrick)

        assert "class Nanobrick" in stub
        assert "name: str = 'simple'" in stub
        assert "version: str = '1.0.0'" in stub
        assert "async def invoke" in stub
        assert "-> str:" in stub

    def test_generate_stub_with_constructor(self):
        """Test generating stub for brick with constructor."""
        generator = TypeStubGenerator(include_docstrings=True)
        stub = generator.generate_stub_for_brick(DelayBrick)

        assert "def __init__" in stub
        assert "delay_ms: float = 10" in stub
        assert '"""A brick with configurable delay."""' in stub

    def test_generate_stub_for_module(self, tmp_path):
        """Test generating stub for a module."""
        # Create test module
        module_path = tmp_path / "test_module.py"
        module_path.write_text(
            '''
"""Test module."""

from nanobricks import NanobrickBase

class TestNanobrick(NanobrickBase[str, str, None]):
    """A test brick."""
    
    name = "test"
    version = "1.0.0"
    
    async def invoke(self, input: str, *, deps=None) -> str:
        return input

def helper_function(x: int) -> int:
    """Helper function."""
    return x * 2

CONSTANT = 42
'''
        )

        generator = TypeStubGenerator()
        stub = generator.generate_stub_for_module(module_path)

        assert '"""Test module."""' in stub
        assert "class TestBrick" in stub
        assert "def helper_function(x: int) -> int:" in stub
        assert "CONSTANT: Any" in stub

    def test_type_formatting(self):
        """Test type annotation formatting."""
        generator = TypeStubGenerator()

        # Test various types
        assert generator._format_type(str) == "str"
        assert generator._format_type(None) == "None"
        assert "Any" in generator._format_type(type(lambda: None))

    def test_is_nanobrick(self):
        """Test nanobrick detection."""
        generator = TypeStubGenerator()

        assert generator._is_nanobrick(Nanobrick)
        assert not generator._is_nanobrick(str)
        assert not generator._is_nanobrick(dict)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
