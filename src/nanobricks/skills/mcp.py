"""
MCP (Model Context Protocol) server skill for nanobricks.

Exposes nanobricks as tools that can be used by LLMs via the MCP protocol.
"""

import inspect
import json
from dataclasses import dataclass
from typing import Any

from nanobricks.protocol import NanobrickProtocol
from nanobricks.skill import Skill

# Try to import MCP SDK if available
try:
    from mcp import Server, Tool
    from mcp.server import stdio_server
    from mcp.types import TextContent, ToolResponse

    HAS_MCP = True
except ImportError:
    HAS_MCP = False
    # Define stub types
    Server = Any
    Tool = Any
    ToolResponse = Any


@dataclass
class MCPToolConfig:
    """Configuration for exposing a nanobrick as an MCP tool."""

    name: str | None = None
    description: str | None = None
    include_in_prompt: bool = True
    example_inputs: list[dict[str, Any]] | None = None
    schema_override: dict[str, Any] | None = None


class SkillMCP(Skill):
    """
    MCP server skill for exposing nanobricks as tools.

    This skill allows nanobricks to be discovered and invoked by LLMs
    through the Model Context Protocol.
    """

    def __init__(
        self,
        server_name: str = "nanobricks",
        version: str = "1.0.0",
        description: str = "Nanobricks exposed as MCP tools",
        auto_generate_schemas: bool = True,
    ):
        super().__init__()
        self.server_name = server_name
        self.version = version
        self.description = description
        self.auto_generate_schemas = auto_generate_schemas
        self._tools: dict[str, tuple[NanobrickProtocol, MCPToolConfig]] = {}
        self._server: Server | None = None

    def _create_enhanced_brick(self, brick: NanobrickProtocol) -> NanobrickProtocol:
        """Create MCP-enabled brick."""
        # For MCP, we don't modify the brick itself
        # Instead, we register it for exposure
        return brick

    def expose_tool(
        self, brick: NanobrickProtocol, config: MCPToolConfig | None = None
    ) -> None:
        """
        Expose a nanobrick as an MCP tool.

        Args:
            brick: The nanobrick to expose
            config: Optional configuration for the tool
        """
        config = config or MCPToolConfig()
        tool_name = config.name or brick.name.replace(" ", "_").lower()
        self._tools[tool_name] = (brick, config)

    def create_server(self) -> Server | None:
        """Create and configure the MCP server."""
        if not HAS_MCP:
            print("Warning: MCP SDK not installed. Cannot create server.")
            return None

        server = Server(self.server_name)

        # Register all tools
        for tool_name, (brick, config) in self._tools.items():
            self._register_tool(server, tool_name, brick, config)

        # Add server metadata
        @server.list_tools()
        async def list_tools():
            """List all available nanobrick tools."""
            tools = []
            for tool_name, (brick, config) in self._tools.items():
                description = (
                    config.description or brick.__doc__ or f"Invoke {brick.name}"
                )
                schema = (
                    self._generate_schema(brick) if self.auto_generate_schemas else {}
                )

                if config.schema_override:
                    schema.update(config.schema_override)

                tools.append(
                    Tool(name=tool_name, description=description, inputSchema=schema)
                )
            return tools

        self._server = server
        return server

    def _register_tool(
        self,
        server: Server,
        tool_name: str,
        brick: NanobrickProtocol,
        config: MCPToolConfig,
    ):
        """Register a single tool with the server."""

        @server.call_tool()
        async def call_tool(name: str, arguments: dict[str, Any]) -> ToolResponse:
            """Handle tool invocation."""
            if name != tool_name:
                return None

            try:
                # Extract input from arguments
                input_data = arguments.get("input", arguments)
                deps = arguments.get("deps", None)

                # Invoke the brick
                result = await brick.invoke(input_data, deps=deps)

                # Format response
                if isinstance(result, dict):
                    content = json.dumps(result, indent=2)
                else:
                    content = str(result)

                return ToolResponse(content=[TextContent(type="text", text=content)])

            except Exception as e:
                return ToolResponse(
                    content=[TextContent(type="text", text=f"Error: {str(e)}")],
                    isError=True,
                )

    def _generate_schema(self, brick: NanobrickProtocol) -> dict[str, Any]:
        """Generate JSON schema for a nanobrick's input."""
        # Try to extract schema from type hints
        schema = {"type": "object", "properties": {}, "required": []}

        # Check if brick has explicit schema
        if hasattr(brick, "input_schema"):
            return brick.input_schema

        # Try to infer from invoke signature
        try:
            sig = inspect.signature(brick.invoke)
            for param_name, param in sig.parameters.items():
                if param_name in ["self", "deps"]:
                    continue

                # Basic type mapping
                param_type = param.annotation
                json_type = self._python_type_to_json_type(param_type)

                if json_type:
                    schema["properties"][param_name] = {"type": json_type}
                    if param.default is inspect.Parameter.empty:
                        schema["required"].append(param_name)
        except:
            # If we can't inspect, provide generic schema
            schema["properties"]["input"] = {
                "type": "object",
                "description": "Input data for the nanobrick",
            }

        return schema

    def _python_type_to_json_type(self, python_type: Any) -> str | None:
        """Convert Python type to JSON schema type."""
        type_map = {
            str: "string",
            int: "integer",
            float: "number",
            bool: "boolean",
            list: "array",
            dict: "object",
        }

        # Handle origin types (List[X], Dict[X,Y], etc)
        origin = getattr(python_type, "__origin__", None)
        if origin:
            python_type = origin

        return type_map.get(python_type)

    async def run_server(self):
        """Run the MCP server."""
        if not self._server:
            self._server = self.create_server()

        if self._server:
            await stdio_server(self._server)
        else:
            raise RuntimeError("Cannot run server - MCP SDK not available")

    def generate_prompts(self) -> list[dict[str, Any]]:
        """Generate prompt templates for the exposed tools."""
        prompts = []

        for tool_name, (brick, config) in self._tools.items():
            if not config.include_in_prompt:
                continue

            prompt = {
                "name": f"use_{tool_name}",
                "description": f"Prompt for using the {tool_name} tool",
                "arguments": [
                    {
                        "name": "task",
                        "description": "Description of what to accomplish",
                        "required": True,
                    }
                ],
            }

            # Build prompt template
            template_parts = [
                f"Use the {tool_name} tool to accomplish the following task:",
                "{{task}}",
                "",
            ]

            if config.example_inputs:
                template_parts.append("Examples:")
                for i, example in enumerate(config.example_inputs, 1):
                    template_parts.append(f"{i}. Input: {json.dumps(example)}")
                template_parts.append("")

            template_parts.append(f"Call the {tool_name} tool with appropriate input.")

            prompt["template"] = "\n".join(template_parts)
            prompts.append(prompt)

        return prompts


class MCPClient:
    """
    Client for testing MCP-enabled nanobricks.

    This is useful for development and testing without a full LLM.
    """

    def __init__(self, skill: SkillMCP):
        self.skill = skill

    async def list_tools(self) -> list[dict[str, Any]]:
        """List available tools."""
        tools = []
        for tool_name, (brick, config) in self.skill._tools.items():
            tools.append(
                {
                    "name": tool_name,
                    "description": config.description or brick.__doc__,
                    "brick": brick.name,
                }
            )
        return tools

    async def invoke_tool(self, tool_name: str, arguments: dict[str, Any]) -> Any:
        """Invoke a tool directly."""
        if tool_name not in self.skill._tools:
            raise ValueError(f"Unknown tool: {tool_name}")

        brick, _ = self.skill._tools[tool_name]
        input_data = arguments.get("input", arguments)
        deps = arguments.get("deps", None)

        return await brick.invoke(input_data, deps=deps)


def create_mcp_server(
    bricks: list[NanobrickProtocol],
    server_name: str = "nanobricks",
    configs: dict[str, MCPToolConfig] | None = None,
) -> SkillMCP:
    """
    Convenience function to create an MCP server from nanobricks.

    Args:
        bricks: List of nanobricks to expose
        server_name: Name of the MCP server
        configs: Optional tool configurations by brick name

    Returns:
        Configured SkillMCP instance
    """
    skill = SkillMCP(server_name=server_name)
    configs = configs or {}

    for brick in bricks:
        config = configs.get(brick.name, MCPToolConfig())
        skill.expose_tool(brick, config)

    return skill
