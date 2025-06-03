"""Demo of v0.1.2 type utilities for nanobricks.

This example shows how to use the new type utilities to handle
type mismatches and improve composition ergonomics.
"""

import asyncio
from typing import Dict, List

from nanobricks import (
    Nanobrick,
    Result,
    TypeAdapter,
    dict_to_json,
    json_to_dict,
    string_to_dict,
)


# Example 1: Using Result type for error handling
class SafeDivider(Nanobrick[tuple[float, float], Result[float, str]]):
    """A nanobrick that safely divides two numbers."""
    
    name = "safe_divider"
    
    async def invoke(self, input: tuple[float, float]) -> Result[float, str]:
        numerator, denominator = input
        
        if denominator == 0:
            return Result.err("Division by zero")
        
        return Result.ok(numerator / denominator)


class ResultPrinter(Nanobrick[Result[float, str], str]):
    """A nanobrick that prints Result values."""
    
    name = "result_printer"
    
    async def invoke(self, input: Result[float, str]) -> str:
        if input.is_ok:
            return f"Success: {input.unwrap()}"
        else:
            return f"Error: {input.unwrap_err()}"


# Example 2: Using type adapters to connect incompatible bricks
class ConfigReader(Nanobrick[str, str]):
    """Reads configuration from a file."""
    
    name = "config_reader"
    
    async def invoke(self, input: str) -> str:
        # Simulate reading config file
        return "host=localhost,port=8080,debug=true"


class ConfigProcessor(Nanobrick[Dict[str, str], Dict[str, any]]):
    """Processes configuration dictionary."""
    
    name = "config_processor"
    
    async def invoke(self, input: Dict[str, str]) -> Dict[str, any]:
        # Parse and validate config
        return {
            "host": input.get("host", "0.0.0.0"),
            "port": int(input.get("port", "80")),
            "debug": input.get("debug", "false").lower() == "true"
        }


# Example 3: Custom type adapter
class ListFlattener(TypeAdapter[List[List[int]], List[int]]):
    """Custom adapter that flattens nested lists."""
    
    def __init__(self):
        def flatten(nested: List[List[int]]) -> List[int]:
            return [item for sublist in nested for item in sublist]
        
        super().__init__(
            name="list_flattener",
            converter=flatten,
            input_type=List[List[int]],
            output_type=List[int]
        )


class NestedListProducer(Nanobrick[None, List[List[int]]]):
    """Produces nested lists."""
    
    name = "nested_producer"
    
    async def invoke(self, input: None) -> List[List[int]]:
        return [[1, 2], [3, 4], [5, 6]]


class ListSummer(Nanobrick[List[int], int]):
    """Sums all numbers in a list."""
    
    name = "list_summer"
    
    async def invoke(self, input: List[int]) -> int:
        return sum(input)


async def main():
    print("=== Type Utilities Demo ===\n")
    
    # Demo 1: Result type for error handling
    print("1. Result Type for Error Handling")
    divider = SafeDivider()
    printer = ResultPrinter()
    
    # Success case
    result = await divider.invoke((10.0, 2.0))
    output = await printer.invoke(result)
    print(f"  10 / 2 = {output}")
    
    # Error case
    result = await divider.invoke((10.0, 0.0))
    output = await printer.invoke(result)
    print(f"  10 / 0 = {output}")
    
    # Using Result methods
    result = await divider.invoke((20.0, 4.0))
    doubled = result.map(lambda x: x * 2)
    print(f"  20 / 4 doubled = {doubled.unwrap()}")
    print()
    
    # Demo 2: Type adapters for composition
    print("2. Type Adapters for Composition")
    
    # Without adapter - types don't match
    # config_reader outputs str, but processor expects Dict[str, str]
    # So we use string_to_dict() adapter
    
    config_pipeline = (
        ConfigReader() | 
        string_to_dict() |  # Adapter makes types compatible!
        ConfigProcessor() |
        dict_to_json(indent=2)  # Another adapter for pretty output
    )
    
    result = await config_pipeline.invoke("config.ini")
    print(f"  Config processing result:\n{result}")
    print()
    
    # Demo 3: Custom type adapters
    print("3. Custom Type Adapters")
    
    flatten_pipeline = (
        NestedListProducer() |
        ListFlattener() |  # Custom adapter
        ListSummer()
    )
    
    result = await flatten_pipeline.invoke(None)
    print(f"  Sum of [[1,2], [3,4], [5,6]] = {result}")
    print()
    
    # Demo 4: Chaining multiple adapters
    print("4. Chaining Multiple Type Conversions")
    
    class DictProducer(Nanobrick[None, Dict[str, int]]):
        name = "dict_producer"
        
        async def invoke(self, input: None) -> Dict[str, int]:
            return {"a": 1, "b": 2, "c": 3}
    
    class StringConsumer(Nanobrick[str, str]):
        name = "string_consumer"
        
        async def invoke(self, input: str) -> str:
            return f"Received JSON with {len(input)} characters"
    
    # Chain dict -> json string -> process
    json_pipeline = (
        DictProducer() |
        dict_to_json(indent=2) |  # Dict -> str (JSON)
        StringConsumer()
    )
    
    result = await json_pipeline.invoke(None)
    print(f"  {result}")
    
    # Demo 5: Error handling in type conversions
    print("\n5. Safe Type Conversions with Result")
    
    class SafeJsonParser(Nanobrick[str, Result[Dict, str]]):
        name = "safe_json_parser"
        
        async def invoke(self, input: str) -> Result[Dict, str]:
            try:
                data = json_to_dict().converter(input)
                return Result.ok(data)
            except Exception as e:
                return Result.err(f"JSON parse error: {e}")
    
    parser = SafeJsonParser()
    
    # Valid JSON
    result = await parser.invoke('{"valid": true}')
    print(f"  Valid JSON: {result}")
    
    # Invalid JSON  
    result = await parser.invoke('{invalid json}')
    print(f"  Invalid JSON: {result}")


if __name__ == "__main__":
    asyncio.run(main())