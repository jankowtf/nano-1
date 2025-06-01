"""
Example demonstrating MCP (Model Context Protocol) integration.

Shows how to expose nanobricks as tools for LLMs.
"""

import asyncio
import json
from typing import Any

from nanobricks.protocol import NanobrickBase
from nanobricks.skills.mcp import MCPClient, MCPToolConfig, SkillMCP, create_mcp_server
from nanobricks.transformers.json_transformer import JSONParser
from nanobricks.validators.schema_validator import SchemaValidator

# Example nanobricks to expose as MCP tools


class DataAnalyzer(NanobrickBase[list[float], dict[str, float], None]):
    """Analyze numerical data and return statistics."""

    def __init__(self):
        self.name = "DataAnalyzer"
        self.version = "1.0.0"

    async def invoke(
        self, input: list[float], *, deps: None = None
    ) -> dict[str, float]:
        if not input:
            return {"error": "No data provided"}

        return {
            "count": len(input),
            "sum": sum(input),
            "mean": sum(input) / len(input),
            "min": min(input),
            "max": max(input),
            "range": max(input) - min(input),
        }


class TextSummarizer(NanobrickBase[str, dict[str, Any], None]):
    """Summarize text by extracting key information."""

    def __init__(self):
        self.name = "TextSummarizer"
        self.version = "1.0.0"
        self.input_schema = {
            "type": "string",
            "minLength": 10,
            "description": "Text to summarize",
        }

    async def invoke(self, input: str, *, deps: None = None) -> dict[str, Any]:
        # Simple mock summarization
        words = input.split()
        sentences = input.split(".")

        return {
            "word_count": len(words),
            "sentence_count": len([s for s in sentences if s.strip()]),
            "first_sentence": sentences[0].strip() if sentences else "",
            "key_words": list(set(word.lower() for word in words if len(word) > 5))[:5],
        }


class EntityExtractor(NanobrickBase[str, list[dict[str, str]], None]):
    """Extract entities from text."""

    def __init__(self):
        self.name = "EntityExtractor"
        self.version = "1.0.0"

    async def invoke(self, input: str, *, deps: None = None) -> list[dict[str, str]]:
        # Mock entity extraction
        entities = []

        # Find capitalized words (mock "names")
        words = input.split()
        for word in words:
            if word and word[0].isupper() and len(word) > 1:
                entities.append(
                    {
                        "text": word,
                        "type": "PERSON",  # Simplified
                        "confidence": 0.8,
                    }
                )

        # Find numbers (mock "quantities")
        import re

        numbers = re.findall(r"\b\d+\b", input)
        for num in numbers:
            entities.append({"text": num, "type": "NUMBER", "confidence": 0.95})

        return entities


async def example_basic_mcp_setup():
    """Example: Basic MCP server setup."""
    print("\n=== Basic MCP Setup Example ===")

    # Create MCP skill
    skill = SkillMCP(
        server_name="nanobricks_tools",
        version="1.0.0",
        description="Nanobricks exposed as MCP tools for LLMs",
    )

    # Create nanobricks
    analyzer = DataAnalyzer()
    summarizer = TextSummarizer()
    extractor = EntityExtractor()

    # Expose them as tools with configurations
    skill.expose_tool(
        analyzer,
        MCPToolConfig(
            name="analyze_data",
            description="Analyze numerical data to get statistics",
            example_inputs=[[1, 2, 3, 4, 5], [10.5, 20.3, 15.8, 30.2]],
        ),
    )

    skill.expose_tool(
        summarizer,
        MCPToolConfig(
            name="summarize_text",
            description="Summarize text content",
            example_inputs=[
                "This is a long text that needs to be summarized. It contains multiple sentences. Some are important."
            ],
        ),
    )

    skill.expose_tool(
        extractor,
        MCPToolConfig(
            name="extract_entities",
            description="Extract named entities from text",
            include_in_prompt=True,
        ),
    )

    # Generate prompts for LLM
    prompts = skill.generate_prompts()
    print(f"\nGenerated {len(prompts)} prompt templates:")
    for prompt in prompts:
        print(f"\n{prompt['name']}:")
        print(
            prompt["template"][:200] + "..."
            if len(prompt["template"]) > 200
            else prompt["template"]
        )


async def example_mcp_client_testing():
    """Example: Testing MCP tools with the client."""
    print("\n=== MCP Client Testing Example ===")

    # Create and configure skill
    skill = SkillMCP()

    # Add tools
    analyzer = DataAnalyzer()
    summarizer = TextSummarizer()

    skill.expose_tool(analyzer, MCPToolConfig(name="analyze"))
    skill.expose_tool(summarizer, MCPToolConfig(name="summarize"))

    # Create client for testing
    client = MCPClient(skill)

    # List available tools
    tools = await client.list_tools()
    print("\nAvailable tools:")
    for tool in tools:
        print(f"  - {tool['name']}: {tool['description']}")

    # Test the analyzer tool
    print("\n\nTesting 'analyze' tool:")
    data = [10, 20, 30, 40, 50]
    print(f"Input: {data}")

    result = await client.invoke_tool("analyze", {"input": data})
    print(f"Result: {json.dumps(result, indent=2)}")

    # Test the summarizer tool
    print("\n\nTesting 'summarize' tool:")
    text = "Nanobricks are modular components. They compose easily. This makes them powerful for building complex systems."
    print(f"Input: {text[:50]}...")

    result = await client.invoke_tool("summarize", {"input": text})
    print(f"Result: {json.dumps(result, indent=2)}")


async def example_pipeline_as_tool():
    """Example: Exposing a complete pipeline as an MCP tool."""
    print("\n=== Pipeline as MCP Tool Example ===")

    # Create a pipeline of nanobricks
    schema = {
        "text": str,
        "analyze": bool
    }

    # Pipeline: Validate -> Extract -> Summarize
    validator = SchemaValidator(schema, required_fields=["text"])
    extractor = EntityExtractor()
    summarizer = TextSummarizer()

    # Create a composite brick
    class TextPipeline(NanobrickBase[dict[str, Any], dict[str, Any], None]):
        """Complete text processing pipeline."""

        def __init__(self):
            self.name = "TextPipeline"
            self.version = "1.0.0"
            self.validator = validator
            self.extractor = extractor
            self.summarizer = summarizer

        async def invoke(
            self, input: dict[str, Any], *, deps: None = None
        ) -> dict[str, Any]:
            # Validate input
            validated = await self.validator.invoke(input)

            text = validated["text"]

            # Extract entities
            entities = await self.extractor.invoke(text)

            # Summarize if requested
            summary = None
            if validated.get("analyze", False):
                summary = await self.summarizer.invoke(text)

            return {"entities": entities, "summary": summary, "processed": True}

    # Expose pipeline as MCP tool
    skill = SkillMCP()
    pipeline = TextPipeline()

    skill.expose_tool(
        pipeline,
        MCPToolConfig(
            name="process_text",
            description="Complete text processing pipeline with entity extraction and optional summarization",
            example_inputs=[
                {"text": "John visited Paris in 2023.", "analyze": True},
                {"text": "The meeting is at 3pm tomorrow.", "analyze": False},
            ],
        ),
    )

    # Test with client
    client = MCPClient(skill)

    test_input = {
        "text": "Alice and Bob met in London. They discussed the new project worth $1000000.",
        "analyze": True,
    }

    print(f"\nProcessing: {test_input['text']}")
    result = await client.invoke_tool("process_text", test_input)

    print(f"\nEntities found: {len(result['entities'])}")
    for entity in result["entities"]:
        print(f"  - {entity['text']} ({entity['type']})")

    if result["summary"]:
        print(f"\nSummary: {json.dumps(result['summary'], indent=2)}")


async def example_multi_protocol_setup():
    """Example: Setting up for multiple AI protocols."""
    print("\n=== Multi-Protocol Setup Example ===")

    # This demonstrates the extensibility of the skill system
    # We can have multiple protocol skills on the same nanobrick

    analyzer = DataAnalyzer()

    # Add MCP protocol
    mcp_skill = SkillMCP(server_name="analyzer_mcp")
    mcp_skill.expose_tool(
        analyzer, MCPToolConfig(name="analyze", description="Statistical analysis tool")
    )

    # Mock other protocol skills (would be implemented similarly)
    class SkillA2A:
        """Mock A2A protocol skill."""

        def __init__(self, agent_id: str):
            self.agent_id = agent_id
            print(f"  A2A agent registered: {agent_id}")

    class SkillACP:
        """Mock ACP protocol skill."""

        def __init__(self, endpoint: str):
            self.endpoint = endpoint
            print(f"  ACP endpoint registered: {endpoint}")

    # Apply multiple protocol skills
    print("\nRegistering analyzer with multiple protocols:")

    # MCP for LLM tool usage
    print("  MCP tool registered: analyze")

    # A2A for agent-to-agent communication
    a2a_skill = SkillA2A("agent.analyzer.v1")

    # ACP for REST API
    acp_skill = SkillACP("/api/v1/analyze")

    print("\nThe same nanobrick is now accessible via:")
    print("  - MCP: As 'analyze' tool for LLMs")
    print("  - A2A: As 'agent.analyzer.v1' for other agents")
    print("  - ACP: As REST endpoint '/api/v1/analyze'")

    # Test via MCP client
    client = MCPClient(mcp_skill)
    result = await client.invoke_tool("analyze", {"input": [1, 2, 3, 4, 5]})
    print(f"\nMCP invocation result: {result}")


async def example_tool_discovery():
    """Example: Tool discovery and capability listing."""
    print("\n=== Tool Discovery Example ===")

    # Create a collection of tools
    bricks = [
        DataAnalyzer(),
        TextSummarizer(),
        EntityExtractor(),
        JSONParser(),
        SchemaValidator({"name": str, "value": (int, float)}),
    ]

    # Create MCP server with all tools
    configs = {
        "DataAnalyzer": MCPToolConfig(
            name="analyze", description="Analyze numerical data"
        ),
        "TextSummarizer": MCPToolConfig(name="summarize", description="Summarize text"),
        "EntityExtractor": MCPToolConfig(
            name="extract", description="Extract entities"
        ),
        "JSONParser": MCPToolConfig(name="json_parse", description="Parse JSON data"),
        "SchemaValidator": MCPToolConfig(
            name="validate", description="Validate against schema"
        ),
    }

    skill = create_mcp_server(bricks, "tool_collection", configs)

    # Discover tools
    client = MCPClient(skill)
    tools = await client.list_tools()

    print(f"\nDiscovered {len(tools)} tools:")
    print("\nTool Catalog:")
    print("-" * 60)

    for tool in tools:
        print(f"\nTool: {tool['name']}")
        print(f"  Brick: {tool['brick']}")
        print(f"  Description: {tool['description']}")

    # Generate unified prompt
    prompts = skill.generate_prompts()
    print(f"\n\nGenerated {len(prompts)} prompt templates for LLM integration")


async def main():
    """Run all MCP examples."""
    await example_basic_mcp_setup()
    await example_mcp_client_testing()
    await example_pipeline_as_tool()
    await example_multi_protocol_setup()
    await example_tool_discovery()


if __name__ == "__main__":
    asyncio.run(main())
