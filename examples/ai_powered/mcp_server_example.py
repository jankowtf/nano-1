"""Example of exposing nanobricks as MCP tools."""

import asyncio
from typing import Any, Dict, List

from nanobricks import NanobrickBase
from nanobricks.skills import SkillMCP, MCPToolConfig, create_mcp_server


class TextSummarizer(NanobrickBase[str, Dict[str, Any], None]):
    """Summarizes text input."""
    
    async def invoke(self, input: str, *, deps: None = None) -> Dict[str, Any]:
        """Summarize text."""
        # Simple summarization logic
        sentences = input.split(". ")
        word_count = len(input.split())
        
        return {
            "original_length": len(input),
            "word_count": word_count,
            "sentence_count": len(sentences),
            "summary": sentences[0] + "..." if sentences else input[:50] + "...",
            "key_points": [
                "First point from the text",
                "Second point extracted",
                "Main conclusion",
            ],
        }


class DataTransformer(NanobrickBase[Dict[str, Any], Dict[str, Any], None]):
    """Transforms data structures."""
    
    async def invoke(
        self, input: Dict[str, Any], *, deps: None = None
    ) -> Dict[str, Any]:
        """Transform data."""
        # Flatten nested structures
        result = {}
        
        def flatten(obj, prefix=""):
            if isinstance(obj, dict):
                for k, v in obj.items():
                    new_key = f"{prefix}.{k}" if prefix else k
                    flatten(v, new_key)
            elif isinstance(obj, list):
                for i, item in enumerate(obj):
                    flatten(item, f"{prefix}[{i}]")
            else:
                result[prefix] = obj
        
        flatten(input)
        return {
            "flattened": result,
            "field_count": len(result),
            "original_structure": input,
        }


class Calculator(NanobrickBase[Dict[str, Any], float, None]):
    """Performs calculations on numeric data."""
    
    async def invoke(
        self, input: Dict[str, Any], *, deps: None = None
    ) -> float:
        """Calculate based on input."""
        operation = input.get("operation", "sum")
        values = input.get("values", [])
        
        if not values:
            return 0.0
        
        if operation == "sum":
            return sum(values)
        elif operation == "average":
            return sum(values) / len(values)
        elif operation == "max":
            return max(values)
        elif operation == "min":
            return min(values)
        else:
            raise ValueError(f"Unknown operation: {operation}")


async def mcp_server_demo():
    """Demonstrate MCP server with nanobricks."""
    print("MCP Server Demo")
    print("=" * 50)
    
    # Create nanobricks
    summarizer = TextSummarizer(name="text_summarizer")
    transformer = DataTransformer(name="data_transformer")
    calculator = Calculator(name="calculator")
    
    # Configure MCP exposure
    configs = {
        "text_summarizer": MCPToolConfig(
            name="summarize_text",
            description="Summarizes text and extracts key points",
            include_in_prompt=True,
            example_inputs=[
                {
                    "input": "This is a long text about AI and machine learning..."
                }
            ],
        ),
        "data_transformer": MCPToolConfig(
            name="transform_data",
            description="Transforms and flattens complex data structures",
            include_in_prompt=True,
            example_inputs=[
                {
                    "input": {
                        "user": {"name": "Alice", "age": 30},
                        "scores": [85, 90, 78],
                    }
                }
            ],
        ),
        "calculator": MCPToolConfig(
            name="calculate",
            description="Performs calculations on numeric values",
            include_in_prompt=True,
            example_inputs=[
                {
                    "input": {
                        "operation": "average",
                        "values": [10, 20, 30, 40, 50],
                    }
                }
            ],
            schema_override={
                "type": "object",
                "properties": {
                    "operation": {
                        "type": "string",
                        "enum": ["sum", "average", "max", "min"],
                        "description": "Operation to perform",
                    },
                    "values": {
                        "type": "array",
                        "items": {"type": "number"},
                        "description": "List of numbers to calculate",
                    },
                },
                "required": ["operation", "values"],
            },
        ),
    }
    
    # Create MCP server
    print("\n1. Creating MCP Server:")
    mcp_skill = create_mcp_server(
        bricks=[summarizer, transformer, calculator],
        server_name="nanobricks-demo",
        configs=configs,
    )
    print(f"   Server: {mcp_skill.server_name}")
    print(f"   Version: {mcp_skill.version}")
    
    # Create MCP client for testing
    from nanobricks.skills.mcp import MCPClient
    client = MCPClient(mcp_skill)
    
    # List available tools
    print("\n2. Available Tools:")
    tools = await client.list_tools()
    for tool in tools:
        print(f"   - {tool['name']}: {tool['description']}")
        print(f"     Brick: {tool['brick']}")
    
    # Test tool invocations
    print("\n3. Testing Tool Invocations:")
    
    # Test summarizer
    print("\n   a) Text Summarization:")
    text = (
        "Artificial intelligence is transforming how we work and live. "
        "Machine learning algorithms can now understand natural language, "
        "recognize images, and make predictions. This technology is being "
        "applied in healthcare, finance, transportation, and many other fields. "
        "The future of AI looks promising but also raises important ethical questions."
    )
    
    result = await client.invoke_tool("summarize_text", {"input": text})
    print(f"      Original length: {result['original_length']} chars")
    print(f"      Summary: {result['summary']}")
    print(f"      Key points: {len(result['key_points'])}")
    
    # Test transformer
    print("\n   b) Data Transformation:")
    complex_data = {
        "user": {
            "profile": {
                "name": "Alice",
                "email": "alice@example.com",
                "preferences": {
                    "theme": "dark",
                    "notifications": True,
                },
            },
            "stats": {
                "posts": 42,
                "followers": 150,
            },
        },
        "metadata": {
            "created": "2024-01-01",
            "version": 2,
        },
    }
    
    result = await client.invoke_tool("transform_data", {"input": complex_data})
    print(f"      Flattened fields: {result['field_count']}")
    print(f"      Sample fields:")
    for key in list(result['flattened'].keys())[:3]:
        print(f"        - {key}: {result['flattened'][key]}")
    
    # Test calculator
    print("\n   c) Calculations:")
    calc_tests = [
        {"operation": "sum", "values": [10, 20, 30, 40, 50]},
        {"operation": "average", "values": [85, 90, 78, 92, 88]},
        {"operation": "max", "values": [3.14, 2.71, 1.41, 1.73]},
    ]
    
    for calc_input in calc_tests:
        result = await client.invoke_tool("calculate", {"input": calc_input})
        print(f"      {calc_input['operation']}: {result:.2f}")
    
    # Generate prompts
    print("\n4. Generated LLM Prompts:")
    prompts = mcp_skill.generate_prompts()
    for prompt in prompts[:2]:  # Show first 2
        print(f"\n   {prompt['name']}:")
        print(f"   {'-' * 40}")
        print(f"   {prompt['template'][:200]}...")
    
    print("\n5. Server Ready for LLM Integration!")
    print("   To run the server: await mcp_skill.run_server()")
    print("   Connect your LLM client to use these tools")
    
    print("\nMCP server demo complete!")


if __name__ == "__main__":
    asyncio.run(mcp_server_demo())