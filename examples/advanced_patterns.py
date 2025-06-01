"""
Example demonstrating advanced composition patterns.

Shows branching, parallel execution, and error recovery.
"""

import asyncio
from typing import Dict, List, Any

from nanobricks.protocol import NanobrickBase
from nanobricks.patterns import (
    Branch, Parallel, FanOut, FanIn, Pipeline,
    Retry, Map, Switch, Cache
)


# Example nanobricks for demonstration

class DataValidator(NanobrickBase[Dict[str, Any], Dict[str, Any], None]):
    """Validates data structure."""
    
    def __init__(self):
        self.name = "DataValidator"
        self.version = "1.0.0"
    
    async def invoke(self, input: Dict[str, Any], *, deps: None = None) -> Dict[str, Any]:
        if "data" not in input:
            raise ValueError("Missing 'data' field")
        if not isinstance(input["data"], list):
            raise ValueError("'data' must be a list")
        return input


class DataEnricher(NanobrickBase[Dict[str, Any], Dict[str, Any], None]):
    """Enriches data with metadata."""
    
    def __init__(self):
        self.name = "DataEnricher"
        self.version = "1.0.0"
    
    async def invoke(self, input: Dict[str, Any], *, deps: None = None) -> Dict[str, Any]:
        import datetime
        return {
            **input,
            "enriched_at": datetime.datetime.now().isoformat(),
            "item_count": len(input.get("data", []))
        }


class DataProcessor(NanobrickBase[Dict[str, Any], Dict[str, Any], None]):
    """Processes data items."""
    
    def __init__(self, processing_type: str = "standard"):
        self.name = f"DataProcessor[{processing_type}]"
        self.version = "1.0.0"
        self.processing_type = processing_type
    
    async def invoke(self, input: Dict[str, Any], *, deps: None = None) -> Dict[str, Any]:
        data = input.get("data", [])
        
        if self.processing_type == "standard":
            processed = [item * 2 for item in data]
        elif self.processing_type == "advanced":
            processed = [item ** 2 for item in data]
        else:
            processed = data
        
        return {**input, "data": processed}


class ItemProcessor(NanobrickBase[int, int, None]):
    """Processes individual items."""
    
    def __init__(self):
        self.name = "ItemProcessor"
        self.version = "1.0.0"
    
    async def invoke(self, input: int, *, deps: None = None) -> int:
        # Simulate some processing
        await asyncio.sleep(0.01)
        return input * 10


async def example_branch_pattern():
    """Example: Conditional branching based on data size."""
    print("\n=== Branch Pattern Example ===")
    
    # Create branching logic
    branch = Branch(
        condition=lambda x: len(x.get("data", [])) > 3,
        true_path=DataProcessor("advanced"),  # Complex processing for large datasets
        false_path=DataProcessor("standard")  # Simple processing for small datasets
    )
    
    # Small dataset
    small_data = {"data": [1, 2, 3]}
    result = await branch.invoke(small_data)
    print(f"Small dataset result: {result}")
    
    # Large dataset
    large_data = {"data": [1, 2, 3, 4, 5]}
    result = await branch.invoke(large_data)
    print(f"Large dataset result: {result}")


async def example_parallel_pattern():
    """Example: Parallel processing of data."""
    print("\n=== Parallel Pattern Example ===")
    
    # Create parallel processor
    parallel = Parallel([
        DataValidator(),
        DataEnricher(),
        DataProcessor("standard")
    ])
    
    data = {"data": [1, 2, 3]}
    results = await parallel.invoke(data)
    
    print("Parallel execution results:")
    for i, result in enumerate(results):
        print(f"  Task {i}: {result}")


async def example_fan_out_fan_in():
    """Example: Fan-out to multiple processors and merge results."""
    print("\n=== Fan-Out/Fan-In Pattern Example ===")
    
    # Fan-out to different processing strategies
    fan_out = FanOut({
        "standard": DataProcessor("standard"),
        "advanced": DataProcessor("advanced"),
        "enriched": DataEnricher()
    })
    
    # Fan-in to merge results
    def merge_results(results: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "comparison": {
                "standard": results["standard"]["data"],
                "advanced": results["advanced"]["data"],
                "metadata": results["enriched"]
            }
        }
    
    fan_in = FanIn(merge_results)
    
    # Create pipeline
    pipeline = fan_out | fan_in
    
    data = {"data": [1, 2, 3]}
    result = await pipeline.invoke(data)
    print(f"Merged results: {result}")


async def example_error_recovery():
    """Example: Error recovery with retry pattern."""
    print("\n=== Error Recovery Pattern Example ===")
    
    # Create a flaky processor that fails sometimes
    class FlakyProcessor(NanobrickBase[Dict[str, Any], Dict[str, Any], None]):
        def __init__(self):
            self.name = "FlakyProcessor"
            self.version = "1.0.0"
            self.attempts = 0
        
        async def invoke(self, input: Dict[str, Any], *, deps: None = None) -> Dict[str, Any]:
            self.attempts += 1
            if self.attempts < 3:
                raise ConnectionError(f"Network error (attempt {self.attempts})")
            return {**input, "processed": True}
    
    # Wrap with retry
    flaky = FlakyProcessor()
    reliable = Retry(flaky, max_retries=3, backoff=0.1)
    
    data = {"data": [1, 2, 3]}
    try:
        result = await reliable.invoke(data)
        print(f"Success after {flaky.attempts} attempts: {result}")
    except Exception as e:
        print(f"Failed after retries: {e}")


async def example_map_pattern():
    """Example: Map processing over collection."""
    print("\n=== Map Pattern Example ===")
    
    # Process each item in parallel
    mapper = Map(ItemProcessor(), parallel=True)
    
    import time
    start = time.time()
    results = await mapper.invoke([1, 2, 3, 4, 5])
    elapsed = time.time() - start
    
    print(f"Processed items: {results}")
    print(f"Time taken: {elapsed:.3f}s (parallel processing)")


async def example_switch_pattern():
    """Example: Multi-way branching based on data type."""
    print("\n=== Switch Pattern Example ===")
    
    # Route based on data type
    def detect_type(data: Dict[str, Any]) -> str:
        if "numbers" in data:
            return "numeric"
        elif "text" in data:
            return "textual"
        else:
            return "unknown"
    
    # Create processors for each type
    class NumericProcessor(NanobrickBase[Dict[str, Any], Dict[str, Any], None]):
        def __init__(self):
            self.name = "NumericProcessor"
            self.version = "1.0.0"
        
        async def invoke(self, input: Dict[str, Any], *, deps: None = None) -> Dict[str, Any]:
            numbers = input.get("numbers", [])
            return {"sum": sum(numbers), "avg": sum(numbers) / len(numbers) if numbers else 0}
    
    class TextProcessor(NanobrickBase[Dict[str, Any], Dict[str, Any], None]):
        def __init__(self):
            self.name = "TextProcessor"
            self.version = "1.0.0"
        
        async def invoke(self, input: Dict[str, Any], *, deps: None = None) -> Dict[str, Any]:
            text = input.get("text", [])
            return {"word_count": sum(len(s.split()) for s in text)}
    
    # Create switch
    switch = Switch(
        selector=detect_type,
        cases={
            "numeric": NumericProcessor(),
            "textual": TextProcessor()
        },
        default=DataEnricher()  # Default processor
    )
    
    # Test different data types
    numeric_data = {"numbers": [1, 2, 3, 4, 5]}
    text_data = {"text": ["Hello world", "How are you"]}
    unknown_data = {"other": "data"}
    
    print(f"Numeric result: {await switch.invoke(numeric_data)}")
    print(f"Text result: {await switch.invoke(text_data)}")
    print(f"Unknown result: {await switch.invoke(unknown_data)}")


async def example_cache_pattern():
    """Example: Caching expensive computations."""
    print("\n=== Cache Pattern Example ===")
    
    # Create expensive processor
    class ExpensiveProcessor(NanobrickBase[int, int, None]):
        def __init__(self):
            self.name = "ExpensiveProcessor"
            self.version = "1.0.0"
            self.call_count = 0
        
        async def invoke(self, input: int, *, deps: None = None) -> int:
            self.call_count += 1
            print(f"  Computing result for {input} (call #{self.call_count})")
            await asyncio.sleep(0.1)  # Simulate expensive operation
            return input ** 3
    
    # Wrap with cache
    processor = ExpensiveProcessor()
    cached = Cache(processor, ttl=1.0)
    
    # First calls (will compute)
    print("First calls:")
    for i in [5, 10, 5]:  # Note: 5 is repeated
        result = await cached.invoke(i)
        print(f"  Result for {i}: {result}")
    
    print(f"\nTotal computations: {processor.call_count}")
    
    # Clear cache and try again
    cached.clear_cache()
    print("\nAfter cache clear:")
    result = await cached.invoke(5)
    print(f"  Result for 5: {result}")
    print(f"Total computations: {processor.call_count}")


async def example_complex_pipeline():
    """Example: Complex pipeline combining multiple patterns."""
    print("\n=== Complex Pipeline Example ===")
    
    # Build a complex data processing pipeline
    pipeline = Pipeline([
        # Validate with retry
        Retry(DataValidator(), max_retries=2),
        
        # Branch based on size
        Branch(
            condition=lambda x: len(x.get("data", [])) > 5,
            true_path=Pipeline([
                # Large datasets: parallel processing
                FanOut({
                    "chunk1": DataProcessor("standard"),
                    "chunk2": DataProcessor("advanced")
                }),
                FanIn(lambda r: {"data": r["chunk1"]["data"] + r["chunk2"]["data"]})
            ]),
            false_path=DataProcessor("standard")  # Small datasets: simple processing
        ),
        
        # Enrich all results
        DataEnricher(),
        
        # Cache final results
        Cache(DataProcessor("standard"), ttl=60)
    ])
    
    # Test with different data
    small_data = {"data": [1, 2, 3]}
    large_data = {"data": [1, 2, 3, 4, 5, 6, 7, 8]}
    
    print("Processing small dataset:")
    result = await pipeline.invoke(small_data)
    print(f"  Result: {result}")
    
    print("\nProcessing large dataset:")
    result = await pipeline.invoke(large_data)
    print(f"  Result: {result}")


async def main():
    """Run all examples."""
    await example_branch_pattern()
    await example_parallel_pattern()
    await example_fan_out_fan_in()
    await example_error_recovery()
    await example_map_pattern()
    await example_switch_pattern()
    await example_cache_pattern()
    await example_complex_pipeline()


if __name__ == "__main__":
    asyncio.run(main())