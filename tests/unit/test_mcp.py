"""Tests for MCP server skill."""

import pytest

from nanobricks.protocol import NanobrickBase
from nanobricks.skills.mcp import MCPClient, MCPToolConfig, SkillMCP, create_mcp_server


class CalculatorBrick(NanobrickBase[dict[str, float], float, None]):
    """A simple calculator nanobrick."""

    def __init__(self):
        self.name = "Calculator"
        self.version = "1.0.0"

    async def invoke(self, input: dict[str, float], *, deps: None = None) -> float:
        operation = input.get("operation", "add")
        a = input.get("a", 0)
        b = input.get("b", 0)

        if operation == "add":
            return a + b
        elif operation == "subtract":
            return a - b
        elif operation == "multiply":
            return a * b
        elif operation == "divide":
            return b / a if a != 0 else float("inf")
        else:
            raise ValueError(f"Unknown operation: {operation}")


class TextProcessorBrick(NanobrickBase[str, str, None]):
    """Process text in various ways."""

    def __init__(self):
        self.name = "TextProcessor"
        self.version = "1.0.0"
        self.input_schema = {"type": "string", "description": "Text to process"}

    async def invoke(self, input: str, *, deps: None = None) -> str:
        # Simple text reversal
        return input[::-1]


@pytest.mark.asyncio
class TestSkillMCP:
    """Tests for MCP skill."""

    async def test_basic_setup(self):
        """Test basic MCP skill setup."""
        skill = SkillMCP(
            server_name="test_server", version="1.0.0", description="Test MCP server"
        )

        assert skill.server_name == "test_server"
        assert skill.version == "1.0.0"
        assert skill.description == "Test MCP server"

    async def test_expose_tool(self):
        """Test exposing a nanobrick as a tool."""
        skill = SkillMCP()
        calc = CalculatorBrick()

        config = MCPToolConfig(
            name="calc",
            description="Perform calculations",
            example_inputs=[{"operation": "add", "a": 1, "b": 2}],
        )

        skill.expose_tool(calc, config)

        assert "calc" in skill._tools
        brick, stored_config = skill._tools["calc"]
        assert brick is calc
        assert stored_config.name == "calc"
        assert stored_config.description == "Perform calculations"

    async def test_generate_prompts(self):
        """Test prompt generation."""
        skill = SkillMCP()
        calc = CalculatorBrick()

        config = MCPToolConfig(
            name="calc",
            description="Calculator tool",
            example_inputs=[{"operation": "add", "a": 5, "b": 3}],
        )

        skill.expose_tool(calc, config)
        prompts = skill.generate_prompts()

        assert len(prompts) == 1
        prompt = prompts[0]
        assert prompt["name"] == "use_calc"
        assert "calc tool" in prompt["description"]
        assert '{"operation": "add", "a": 5, "b": 3}' in prompt["template"]

    async def test_schema_generation(self):
        """Test automatic schema generation."""
        skill = SkillMCP(auto_generate_schemas=True)

        # Test with explicit schema
        text_proc = TextProcessorBrick()
        schema = skill._generate_schema(text_proc)
        assert schema == text_proc.input_schema

        # Test with inferred schema
        calc = CalculatorBrick()
        schema = skill._generate_schema(calc)
        assert schema["type"] == "object"
        assert "properties" in schema

    async def test_python_type_to_json_type(self):
        """Test type conversion."""
        skill = SkillMCP()

        assert skill._python_type_to_json_type(str) == "string"
        assert skill._python_type_to_json_type(int) == "integer"
        assert skill._python_type_to_json_type(float) == "number"
        assert skill._python_type_to_json_type(bool) == "boolean"
        assert skill._python_type_to_json_type(list) == "array"
        assert skill._python_type_to_json_type(dict) == "object"


@pytest.mark.asyncio
class TestMCPClient:
    """Tests for MCP client."""

    async def test_client_list_tools(self):
        """Test listing tools via client."""
        skill = SkillMCP()
        calc = CalculatorBrick()
        text = TextProcessorBrick()

        skill.expose_tool(calc, MCPToolConfig(name="calc"))
        skill.expose_tool(text, MCPToolConfig(name="text"))

        client = MCPClient(skill)
        tools = await client.list_tools()

        assert len(tools) == 2
        tool_names = [t["name"] for t in tools]
        assert "calc" in tool_names
        assert "text" in tool_names

    async def test_client_invoke_tool(self):
        """Test invoking tools via client."""
        skill = SkillMCP()
        calc = CalculatorBrick()

        skill.expose_tool(calc, MCPToolConfig(name="calc"))

        client = MCPClient(skill)

        # Test successful invocation
        result = await client.invoke_tool("calc", {"operation": "add", "a": 10, "b": 5})
        assert result == 15

        # Test unknown tool
        with pytest.raises(ValueError, match="Unknown tool"):
            await client.invoke_tool("unknown", {})


@pytest.mark.asyncio
class TestCreateMCPServer:
    """Tests for convenience function."""

    async def test_create_mcp_server(self):
        """Test creating MCP server from bricks."""
        calc = CalculatorBrick()
        text = TextProcessorBrick()

        configs = {
            "Calculator": MCPToolConfig(name="calc", description="Math operations"),
            "TextProcessor": MCPToolConfig(name="text_proc", include_in_prompt=False),
        }

        skill = create_mcp_server(
            [calc, text], server_name="my_server", configs=configs
        )

        assert skill.server_name == "my_server"
        assert "calc" in skill._tools
        assert "text_proc" in skill._tools

        # Check configurations were applied
        _, calc_config = skill._tools["calc"]
        assert calc_config.description == "Math operations"

        _, text_config = skill._tools["text_proc"]
        assert not text_config.include_in_prompt
