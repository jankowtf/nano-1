"""
Example demonstrating observability features.

Shows distributed tracing, metrics collection, and lightweight tracing.
"""

import asyncio
import random
from typing import Dict, Any

from nanobricks.protocol import NanobrickBase
from nanobricks.composition import NanobrickComposite
from nanobricks.patterns import Pipeline, Retry, Branch
from nanobricks.skills.observability import (
    SkillObservability, ObservabilityConfig, SkillTracing
)


# Example nanobricks for demonstration

class DataFetcher(NanobrickBase[str, Dict[str, Any], None]):
    """Fetches data from a source."""
    
    def __init__(self):
        self.name = "DataFetcher"
        self.version = "1.0.0"
    
    async def invoke(self, input: str, *, deps: None = None) -> Dict[str, Any]:
        # Simulate network delay
        await asyncio.sleep(random.uniform(0.05, 0.15))
        
        # Simulate occasional failures
        if random.random() < 0.1:
            raise ConnectionError("Failed to fetch data")
        
        return {
            "source": input,
            "data": [random.randint(1, 100) for _ in range(10)],
            "timestamp": asyncio.get_event_loop().time()
        }


class DataValidator(NanobrickBase[Dict[str, Any], Dict[str, Any], None]):
    """Validates fetched data."""
    
    def __init__(self):
        self.name = "DataValidator"
        self.version = "1.0.0"
    
    async def invoke(self, input: Dict[str, Any], *, deps: None = None) -> Dict[str, Any]:
        # Quick validation
        await asyncio.sleep(0.01)
        
        if "data" not in input:
            raise ValueError("Missing 'data' field")
        
        if len(input["data"]) < 5:
            raise ValueError("Insufficient data points")
        
        return {**input, "validated": True}


class DataProcessor(NanobrickBase[Dict[str, Any], Dict[str, Any], None]):
    """Processes validated data."""
    
    def __init__(self, processing_type: str = "standard"):
        self.name = f"DataProcessor[{processing_type}]"
        self.version = "1.0.0"
        self.processing_type = processing_type
    
    async def invoke(self, input: Dict[str, Any], *, deps: None = None) -> Dict[str, Any]:
        # Simulate processing time
        if self.processing_type == "heavy":
            await asyncio.sleep(random.uniform(0.1, 0.2))
        else:
            await asyncio.sleep(random.uniform(0.02, 0.05))
        
        data = input["data"]
        
        if self.processing_type == "heavy":
            # Complex processing
            result = {
                "mean": sum(data) / len(data),
                "max": max(data),
                "min": min(data),
                "std_dev": (sum((x - sum(data)/len(data))**2 for x in data) / len(data))**0.5
            }
        else:
            # Simple processing
            result = {
                "sum": sum(data),
                "count": len(data)
            }
        
        return {**input, "result": result, "processed_by": self.processing_type}


async def example_lightweight_tracing():
    """Example: Lightweight tracing without OpenTelemetry."""
    print("\n=== Lightweight Tracing Example ===")
    
    # Create tracing skill
    skill = SkillTracing()
    
    # Build traced pipeline
    pipeline = Pipeline([
        DataFetcher().with_skill(skill),
        DataValidator().with_skill(skill),
        DataProcessor("standard").with_skill(skill)
    ])
    
    # Execute pipeline
    try:
        result = await pipeline.invoke("api.example.com")
        print(f"Pipeline result: {result['result']}")
    except Exception as e:
        print(f"Pipeline failed: {e}")
    
    # Display traces
    print("\nCollected traces:")
    for trace in skill.traces:
        operation = trace["operation"]
        nanobrick = trace.get("nanobrick", "unknown")
        duration = trace.get("duration_ms", 0)
        
        if operation == "invoke_complete":
            print(f"  ✓ {nanobrick}: {duration:.2f}ms")
        elif operation == "invoke_error":
            print(f"  ✗ {nanobrick}: {trace['error']} ({duration:.2f}ms)")
        elif operation == "invoke_start":
            print(f"  → {nanobrick} started")


async def example_custom_tracing():
    """Example: Custom trace collection."""
    print("\n=== Custom Tracing Example ===")
    
    # Create custom trace collector
    class TraceCollector:
        def __init__(self):
            self.spans = []
            self.current_span = None
        
        def trace(self, operation: str, details: Dict[str, Any]):
            if operation == "invoke_start":
                self.current_span = {
                    "name": details["nanobrick"],
                    "start_time": asyncio.get_event_loop().time(),
                    "children": []
                }
            elif operation == "invoke_complete" and self.current_span:
                self.current_span["duration_ms"] = details["duration_ms"]
                self.current_span["status"] = "success"
                self.spans.append(self.current_span)
                self.current_span = None
            elif operation == "invoke_error" and self.current_span:
                self.current_span["duration_ms"] = details["duration_ms"]
                self.current_span["status"] = "error"
                self.current_span["error"] = details["error"]
                self.spans.append(self.current_span)
                self.current_span = None
    
    collector = TraceCollector()
    skill = SkillTracing(trace_func=collector.trace)
    
    # Build complex pipeline with retry and branching
    pipeline = Pipeline([
        Retry(DataFetcher(), max_retries=2, backoff=0.1).with_skill(skill),
        DataValidator().with_skill(skill),
        Branch(
            condition=lambda x: len(x["data"]) > 8,
            true_path=DataProcessor("heavy").with_skill(skill),
            false_path=DataProcessor("standard").with_skill(skill)
        )
    ])
    
    # Execute multiple times
    sources = ["api.example.com", "api.backup.com", "api.fast.com"]
    
    for source in sources:
        print(f"\nProcessing from {source}:")
        try:
            result = await pipeline.invoke(source)
            print(f"  Success: {result.get('result', {})}")
        except Exception as e:
            print(f"  Failed: {e}")
    
    # Display trace summary
    print("\nTrace Summary:")
    for span in collector.spans:
        status_icon = "✓" if span["status"] == "success" else "✗"
        print(f"  {status_icon} {span['name']}: {span['duration_ms']:.2f}ms")
        if "error" in span:
            print(f"     Error: {span['error']}")


async def example_observability_stats():
    """Example: Observability with statistics collection."""
    print("\n=== Observability Statistics Example ===")
    
    # Create observability configuration
    config = ObservabilityConfig(
        service_name="data_pipeline",
        enable_tracing=False,  # Disable OTEL dependencies for example
        enable_metrics=False,
        enable_logging=False,
        custom_attributes={
            "environment": "development",
            "version": "1.0.0"
        }
    )
    
    skill = SkillObservability(config)
    
    # Build observable pipeline
    fetcher = DataFetcher().with_skill(skill)
    validator = DataValidator().with_skill(skill)
    processor = DataProcessor("standard").with_skill(skill)
    
    pipeline = fetcher | validator | processor
    
    # Execute multiple times to collect statistics
    print("Executing pipeline 10 times...")
    successes = 0
    failures = 0
    
    for i in range(10):
        try:
            await pipeline.invoke(f"source_{i}")
            successes += 1
        except Exception:
            failures += 1
    
    print(f"\nResults: {successes} successes, {failures} failures")
    
    # Display statistics if available
    for brick in [fetcher, validator, processor]:
        if hasattr(brick, 'get_stats'):
            stats = brick.get_stats()
            print(f"\n{stats['name']} Statistics:")
            print(f"  Invocations: {stats['invocation_count']}")
            print(f"  Errors: {stats['error_count']}")
            print(f"  Error Rate: {stats['error_rate']:.2%}")
            print(f"  Avg Duration: {stats['average_duration_ms']:.2f}ms")


async def example_distributed_tracing():
    """Example: Simulated distributed tracing."""
    print("\n=== Distributed Tracing Simulation ===")
    
    # Create a trace context propagator
    class TraceContext:
        def __init__(self):
            self.trace_id = f"trace-{random.randint(1000, 9999)}"
            self.spans = []
        
        def start_span(self, name: str, parent_id: str = None):
            span_id = f"span-{random.randint(100, 999)}"
            span = {
                "trace_id": self.trace_id,
                "span_id": span_id,
                "parent_id": parent_id,
                "name": name,
                "start_time": asyncio.get_event_loop().time(),
                "events": []
            }
            self.spans.append(span)
            return span_id
        
        def end_span(self, span_id: str, status: str = "ok"):
            for span in self.spans:
                if span["span_id"] == span_id:
                    span["end_time"] = asyncio.get_event_loop().time()
                    span["duration_ms"] = (span["end_time"] - span["start_time"]) * 1000
                    span["status"] = status
        
        def add_event(self, span_id: str, event: str, attributes: Dict[str, Any] = None):
            for span in self.spans:
                if span["span_id"] == span_id:
                    span["events"].append({
                        "name": event,
                        "attributes": attributes or {},
                        "timestamp": asyncio.get_event_loop().time()
                    })
    
    # Create traced bricks with context
    context = TraceContext()
    
    class TracedDataFetcher(DataFetcher):
        async def invoke(self, input: str, *, deps: None = None) -> Dict[str, Any]:
            span_id = context.start_span("DataFetcher")
            try:
                context.add_event(span_id, "fetch_started", {"source": input})
                result = await super().invoke(input)
                context.add_event(span_id, "fetch_completed", {"data_points": len(result["data"])})
                context.end_span(span_id)
                return result
            except Exception as e:
                context.end_span(span_id, "error")
                raise
    
    class TracedDataProcessor(DataProcessor):
        async def invoke(self, input: Dict[str, Any], *, deps: None = None) -> Dict[str, Any]:
            span_id = context.start_span(f"DataProcessor[{self.processing_type}]")
            try:
                result = await super().invoke(input)
                context.add_event(span_id, "processing_completed", {"type": self.processing_type})
                context.end_span(span_id)
                return result
            except Exception as e:
                context.end_span(span_id, "error")
                raise
    
    # Build traced pipeline
    pipeline = Pipeline([
        TracedDataFetcher(),
        DataValidator(),  # Not traced for comparison
        TracedDataProcessor("heavy")
    ])
    
    # Execute with tracing
    root_span = context.start_span("Pipeline")
    try:
        result = await pipeline.invoke("api.traced.com")
        context.end_span(root_span)
        print(f"Pipeline completed successfully")
    except Exception as e:
        context.end_span(root_span, "error")
        print(f"Pipeline failed: {e}")
    
    # Display trace tree
    print(f"\nTrace ID: {context.trace_id}")
    print("Span Tree:")
    
    def print_span(span, indent=0):
        prefix = "  " * indent + "└─ " if indent > 0 else ""
        status_icon = "✓" if span["status"] == "ok" else "✗"
        print(f"{prefix}{status_icon} {span['name']} ({span['duration_ms']:.2f}ms)")
        
        for event in span["events"]:
            event_prefix = "  " * (indent + 1) + "• "
            attrs = ", ".join(f"{k}={v}" for k, v in event["attributes"].items())
            print(f"{event_prefix}{event['name']} [{attrs}]")
    
    # Find root span and print tree
    root_spans = [s for s in context.spans if s["parent_id"] is None]
    for root in root_spans:
        print_span(root)
        # Find children
        children = [s for s in context.spans if s["parent_id"] == root["span_id"]]
        for child in children:
            print_span(child, 1)


async def main():
    """Run all observability examples."""
    await example_lightweight_tracing()
    await example_custom_tracing()
    await example_observability_stats()
    await example_distributed_tracing()


if __name__ == "__main__":
    asyncio.run(main())