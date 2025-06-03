from typing import Any

# Import skills to trigger registration
from nanobricks import Nanobrick, skill


@skill("cli", command="transform", input_type="json", output_format="json")
class DataTransformerBrick(Nanobrick[list[dict[str, Any]], dict[str, Any]]):
    """Transforms and analyzes JSON data collections."""

    async def invoke(self, input: list[dict[str, Any]], *, deps=None) -> dict[str, Any]:
        if not input:
            return {"error": "No data provided", "count": 0}

        # Analyze the data
        total_items = len(input)
        all_keys = set()
        for item in input:
            if isinstance(item, dict):
                all_keys.update(item.keys())

        # Calculate statistics per field
        field_stats = {}
        for key in all_keys:
            values = [
                item.get(key)
                for item in input
                if isinstance(item, dict) and key in item
            ]
            if values:
                field_stats[key] = {
                    "count": len(values),
                    "types": list(set(type(v).__name__ for v in values)),
                    "sample": values[0] if values else None,
                }

                # Add numeric stats if applicable
                numeric_values = [v for v in values if isinstance(v, (int, float))]
                if numeric_values:
                    field_stats[key]["numeric_stats"] = {
                        "min": min(numeric_values),
                        "max": max(numeric_values),
                        "avg": sum(numeric_values) / len(numeric_values),
                    }

        return {
            "summary": {
                "total_items": total_items,
                "fields": list(all_keys),
                "field_count": len(all_keys),
            },
            "field_analysis": field_stats,
            "sample_data": input[:3] if len(input) > 3 else input,
        }


if __name__ == "__main__":
    transformer = DataTransformerBrick()

    # Show example usage
    import asyncio

    sample_data = [
        {"name": "Alice", "age": 30, "city": "New York"},
        {"name": "Bob", "age": 25, "city": "San Francisco"},
        {"name": "Charlie", "age": 35, "city": "New York"},
        {"name": "Diana", "age": 28, "city": "Chicago"},
    ]

    result = asyncio.run(transformer.invoke(sample_data))

    print("📊 Data Transformer CLI")
    print("=" * 60)
    print("\nThis CLI accepts JSON arrays and provides data analysis.")

    print("\n📝 Example Input:")
    import json

    print(json.dumps(sample_data, indent=2))

    print("\n📈 Example Output:")
    print(json.dumps(result, indent=2))

    print("\n" + "=" * 60)
    print("🚀 CLI Usage Examples")
    print("=" * 60)

    print("\n1️⃣ From JSON file:")
    print("  python -m examples.skills.cli_json invoke data.json --from-file")

    print("\n2️⃣ Inline JSON:")
    print('  python -m examples.skills.cli_json invoke \'[{"id":1},{"id":2}]\'')

    print("\n3️⃣ Pretty output:")
    print("  python -m examples.skills.cli_json invoke data.json --from-file --pretty")

    print("\n4️⃣ Save to file:")
    print(
        "  python -m examples.skills.cli_json invoke data.json --from-file --output result.json"
    )

    print("\n5️⃣ Pipe from other commands:")
    print(
        "  curl https://api.example.com/data | python -m examples.skills.cli_json invoke -"
    )

    print("\n6️⃣ Show CLI info:")
    print("  python -m examples.skills.cli_json info")

    print("\n" + "=" * 60)

    # Run the CLI
    import sys

    if len(sys.argv) == 1:
        # Create sample data file for demo
        with open("sample_data.json", "w") as f:
            json.dump(sample_data, f, indent=2)
        print("\n💾 Created sample_data.json for testing")
        print(
            "🎯 Try: python examples/skills/cli_json.py invoke sample_data.json --from-file --pretty\n"
        )
        sys.argv.extend(["--help"])

    transformer.run_cli()
