"""Example demonstrating developer experience tools."""

import asyncio
import json
import time
from pathlib import Path

from nanobricks import NanobrickBase
from nanobricks.transformers import JSONParser, UpperCaseTransformer, FilterTransformer
from nanobricks.validators import TypeValidator, LengthValidator
from nanobricks.devtools import (
    CompositionDebugger,
    PerformanceProfiler,
    PipelineViz,
    TypeStubGenerator,
    visualize
)


# Example bricks for demonstration
class DataProcessor(NanobrickBase[dict, dict, None]):
    """Processes data with artificial delay."""
    
    name = "data_processor"
    version = "1.0.0"
    
    def __init__(self, delay_ms: float = 10):
        self.delay_ms = delay_ms
    
    async def invoke(self, input: dict, *, deps=None) -> dict:
        # Simulate processing
        await asyncio.sleep(self.delay_ms / 1000)
        
        # Process data
        result = {
            'processed': True,
            'item_count': len(input.get('items', [])),
            'timestamp': time.time()
        }
        
        # Merge with input
        return {**input, **result}


class DataEnricher(NanobrickBase[dict, dict, None]):
    """Enriches data with additional information."""
    
    name = "data_enricher"
    version = "1.0.0"
    
    async def invoke(self, input: dict, *, deps=None) -> dict:
        # Add enrichment
        enriched = input.copy()
        enriched['enriched'] = True
        enriched['metadata'] = {
            'source': 'enricher',
            'version': self.version
        }
        
        # Simulate some memory usage
        temp_data = [i for i in range(1000)]  # Create some objects
        
        return enriched


async def demo_composition_debugger():
    """Demonstrate composition debugger."""
    print("\n" + "="*60)
    print("🔍 COMPOSITION DEBUGGER DEMO")
    print("="*60)
    
    # Create pipeline
    pipeline = (
        JSONParser() >> TypeValidator(dict) >> DataProcessor(delay_ms=20) >> DataEnricher() >> LengthValidator(min_length=1)
    )
    
    # Debug the pipeline
    debugger = CompositionDebugger(
        capture_inputs=True,
        capture_outputs=True,
        capture_timing=True
    )
    
    input_data = '{"items": [1, 2, 3], "name": "test"}'
    
    try:
        result, trace = await debugger.debug_pipeline(
            pipeline,
            input_data,
            show_live=True
        )
        
        print(f"\n✅ Pipeline completed successfully!")
        print(f"Final result: {result}")
        
    except Exception as e:
        print(f"\n❌ Pipeline failed: {e}")


async def demo_performance_profiler():
    """Demonstrate performance profiler."""
    print("\n" + "="*60)
    print("⚡ PERFORMANCE PROFILER DEMO")
    print("="*60)
    
    # Create pipeline with varying performance characteristics
    pipeline = (
        JSONParser() >> DataProcessor(delay_ms=5) >>    # Fast
        DataProcessor(delay_ms=50) |   # Slow (hotspot)
        DataProcessor(delay_ms=10) |   # Medium
        DataEnricher()
    )
    
    # Profile the pipeline
    profiler = PerformanceProfiler(
        track_memory=True,
        track_cpu=True,
        track_gc=True
    )
    
    input_data = '{"items": [1, 2, 3, 4, 5]}'
    
    report = await profiler.profile_pipeline(
        pipeline,
        input_data,
        runs=10,
        warmup_runs=2
    )
    
    # Display report
    profiler.display_report(report)


def demo_pipeline_visualizer():
    """Demonstrate pipeline visualizer."""
    print("\n" + "="*60)
    print("🎨 PIPELINE VISUALIZER DEMO")
    print("="*60)
    
    # Create complex pipeline
    from nanobricks.patterns import Branch, Parallel
    
    # Branch based on data type
    branch_pipeline = Branch({
        lambda x: isinstance(x, str): JSONParser() >> UpperCaseTransformer(),
        lambda x: isinstance(x, dict): DataProcessor() >> DataEnricher(),
        lambda x: True: TypeValidator(str)  # Default
    })
    
    # Parallel processing
    parallel_pipeline = Parallel([
        DataProcessor(delay_ms=10),
        DataProcessor(delay_ms=20),
        DataEnricher()
    ])
    
    # Composite pipeline
    pipeline = (
        TypeValidator(str) |
        branch_pipeline |
        parallel_pipeline
    )
    
    # Visualize in different formats
    print("\n📊 Text Visualization:")
    visualizer = PipelineViz(show_types=True, show_metadata=True)
    visualizer.visualize(pipeline)
    
    print("\n📊 Mermaid Diagram:")
    visualizer_mermaid = PipelineViz(export_format="mermaid")
    visualizer_mermaid.visualize(pipeline)
    
    print("\n📊 Graphviz DOT:")
    visualizer_dot = PipelineViz(export_format="graphviz")
    visualizer_dot.visualize(pipeline)


def demo_type_stub_generator():
    """Demonstrate type stub generator."""
    print("\n" + "="*60)
    print("📝 TYPE STUB GENERATOR DEMO")
    print("="*60)
    
    # Generate stub for our custom bricks
    generator = TypeStubGenerator(
        include_docstrings=True,
        use_generic_base=True
    )
    
    # Generate for DataProcessor
    stub = generator.generate_stub_for_brick(DataProcessor)
    print("\n✨ Generated stub for DataProcessor:")
    print("-" * 40)
    print(stub)
    
    # Generate for DataEnricher
    stub = generator.generate_stub_for_brick(DataEnricher)
    print("\n✨ Generated stub for DataEnricher:")
    print("-" * 40)
    print(stub)
    
    # Show package stub generation
    print("\n📦 To generate stubs for entire package:")
    print("```python")
    print("stubs = generator.generate_stubs_for_package(Path('src/nanobricks'))")
    print("generator.write_stubs(stubs)")
    print("```")


async def demo_combined_workflow():
    """Demonstrate combined workflow using multiple tools."""
    print("\n" + "="*60)
    print("🚀 COMBINED WORKFLOW DEMO")
    print("="*60)
    
    # Create pipeline
    pipeline = (
        JSONParser() >> FilterTransformer(lambda x: 'items' in x) >> DataProcessor(delay_ms=15) >> DataEnricher()
    )
    
    # 1. Visualize structure
    print("\n1️⃣ Pipeline Structure:")
    visualize(pipeline, format="text")
    
    # 2. Debug execution
    print("\n2️⃣ Debug Execution:")
    debugger = CompositionDebugger()
    input_data = '{"items": [1, 2, 3], "user": "test"}'
    
    result, trace = await debugger.debug_pipeline(
        pipeline,
        input_data,
        show_live=False
    )
    
    print(f"✓ Execution completed in {trace.duration_ms:.2f}ms")
    print(f"✓ {len(trace.events)} events captured")
    
    # 3. Profile performance
    print("\n3️⃣ Performance Profile:")
    profiler = PerformanceProfiler()
    report = await profiler.profile_pipeline(
        pipeline,
        input_data,
        runs=5,
        show_progress=False
    )
    
    print(f"✓ Average duration: {report.total_duration_ms:.2f}ms")
    print(f"✓ Memory change: {report.total_memory_delta_mb:+.2f}MB")
    
    if report.hotspots:
        print(f"✓ Hotspot: {report.hotspots[0][0]} ({report.hotspots[0][1]:.1f}%)")
    
    # 4. Generate type stubs
    print("\n4️⃣ Type Stubs Generated:")
    generator = TypeStubGenerator()
    for brick in [JSONParser, FilterTransformer, DataProcessor, DataEnricher]:
        stub = generator.generate_stub_for_brick(brick)
        lines = stub.split('\n')
        print(f"✓ {brick.__name__}: {lines[0]}")  # Just show class definition


async def main():
    """Run all demonstrations."""
    
    # 1. Composition Debugger
    await demo_composition_debugger()
    
    # 2. Performance Profiler
    await demo_performance_profiler()
    
    # 3. Pipeline Visualizer
    demo_pipeline_visualizer()
    
    # 4. Type Stub Generator
    demo_type_stub_generator()
    
    # 5. Combined Workflow
    await demo_combined_workflow()
    
    print("\n" + "="*60)
    print("✅ All developer tools demonstrated!")
    print("="*60)


if __name__ == "__main__":
    asyncio.run(main())