"""Example demonstrating built-in skills."""

import asyncio
import logging

# Import to register built-in skills
from nanobricks import Nanobrick, skill

# Example 1: Logging Skill
print("=== 1. Logging Skill Demo ===\n")


@skill("logging", level="INFO", pretty=True)
class DataProcessorBrick(Nanobrick[dict, dict]):
    """Processes data with automatic logging."""

    async def invoke(self, input: dict, *, deps=None) -> dict:
        # Simulate some processing
        await asyncio.sleep(0.1)

        result = {
            "processed": True,
            "item_count": len(input),
            "keys": list(input.keys()),
            "summary": f"Processed {len(input)} items",
        }

        return result


async def demo_logging():
    """Demonstrate logging skill."""
    processor = DataProcessorBrick()

    # Process some data
    data = {
        "users": ["alice", "bob", "charlie"],
        "scores": [85, 92, 78],
        "timestamp": "2024-01-23",
    }

    result = await processor.invoke(data)
    print(f"Result: {result}\n")

    # Process with error (to show error logging)
    @skill("logging", log_errors=True)
    class FaultyBrick(Nanobrick[int, int]):
        async def invoke(self, input: int, *, deps=None) -> int:
            if input < 0:
                raise ValueError("Negative numbers not allowed!")
            return input * 2

    faulty = FaultyBrick()

    try:
        await faulty.invoke(-5)
    except ValueError:
        print("Error was logged!\n")


# Example 2: API Skill
print("=== 2. API Skill Demo ===\n")


@skill("api", path="/analyze", port=8080, docs=True)
class TextAnalyzerBrick(Nanobrick[str, dict]):
    """Analyzes text and returns statistics."""

    async def invoke(self, input: str, *, deps=None) -> dict:
        words = input.split()
        return {
            "text": input,
            "length": len(input),
            "word_count": len(words),
            "unique_words": len(set(words)),
            "avg_word_length": sum(len(w) for w in words) / len(words) if words else 0,
        }


async def demo_api():
    """Demonstrate API skill."""
    analyzer = TextAnalyzerBrick()

    # Normal invocation still works
    result = await analyzer.invoke("The quick brown fox jumps over the lazy dog")
    print(f"Direct result: {result}")

    # Show how to start API server
    print("\nTo start the API server, you would call:")
    print("analyzer.start_server()")
    print("Then access: http://localhost:8080/analyze")
    print("API docs at: http://localhost:8080/docs\n")


# Example 3: CLI Skill
print("=== 3. CLI Skill Demo ===\n")


@skill("cli", command="transform", input_type="json", output_format="pretty")
class DataTransformerBrick(Nanobrick[list[dict], dict]):
    """Transforms list data into summary statistics."""

    async def invoke(self, input: list[dict], *, deps=None) -> dict:
        if not input:
            return {"error": "No data provided"}

        # Calculate statistics
        total_items = len(input)
        all_keys = set()
        for item in input:
            all_keys.update(item.keys())

        return {
            "total_items": total_items,
            "unique_keys": list(all_keys),
            "first_item": input[0] if input else None,
            "last_item": input[-1] if input else None,
            "summary": f"Processed {total_items} items with {len(all_keys)} unique keys",
        }


async def demo_cli():
    """Demonstrate CLI skill."""
    transformer = DataTransformerBrick()

    # Normal invocation
    data = [
        {"name": "Alice", "age": 30, "city": "NYC"},
        {"name": "Bob", "age": 25, "city": "LA"},
        {"name": "Charlie", "age": 35, "city": "Chicago"},
    ]

    result = await transformer.invoke(data)
    print(f"Direct result: {result}")

    print("\nCLI Usage Examples:")
    print("1. Direct input:")
    print('   transform invoke \'[{"name": "Alice", "age": 30}]\'')
    print("\n2. From file:")
    print("   transform invoke data.json --from-file")
    print("\n3. With pretty output:")
    print("   transform invoke data.json -f --pretty")
    print("\n4. Get brick info:")
    print("   transform info")
    print("\n5. See examples:")
    print("   transform example\n")


# Example 4: Combining Skills
print("=== 4. Combining Multiple Skills ===\n")


@skill("logging", level="INFO")
@skill("api", path="/calculate", port=8081)
@skill("cli", command="calc")
class CalculatorBrick(Nanobrick[dict, dict]):
    """A calculator brick with multiple interfaces."""

    async def invoke(self, input: dict, *, deps=None) -> dict:
        operation = input.get("operation", "add")
        a = input.get("a", 0)
        b = input.get("b", 0)

        if operation == "add":
            result = a + b
        elif operation == "subtract":
            result = a - b
        elif operation == "multiply":
            result = a * b
        elif operation == "divide":
            result = a / b if b != 0 else "Error: Division by zero"
        else:
            result = "Error: Unknown operation"

        return {"operation": operation, "a": a, "b": b, "result": result}


async def demo_combined():
    """Demonstrate combined skills."""
    calculator = CalculatorBrick()

    # Use it (with logging active)
    result = await calculator.invoke({"operation": "multiply", "a": 7, "b": 6})

    print(f"Calculator result: {result}")
    print("\nThis brick now has:")
    print("- Automatic logging of all operations")
    print("- REST API at http://localhost:8081/calculate")
    print("- CLI command 'calc'")
    print("- All working together!\n")


async def main():
    """Run all demos."""
    # Set up logging to see the logging skill in action
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    await demo_logging()
    await demo_api()
    await demo_cli()
    await demo_combined()

    print("=== Demo Complete ===")
    print("\nBuilt-in skills demonstrated:")
    print("✅ Logging - Automatic input/output/error logging")
    print("✅ API - REST API with FastAPI")
    print("✅ CLI - Command-line interface with Typer")
    print("\nThese can be combined freely to create powerful, multi-interface bricks!")


if __name__ == "__main__":
    asyncio.run(main())
