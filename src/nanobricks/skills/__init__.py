"""Built-in skills for Nanobricks.

This package contains the standard skills that come with Nanobricks:
- logging: Automatic logging of inputs/outputs
- api: REST API exposure via FastAPI
- cli: Command-line interface via Typer
- observability: Metrics and tracing
- ui: Web UI via Streamlit
- persistence: State saving/loading
- ai: AI reasoning and enhancement
- mcp: Model Context Protocol server
"""

# Import and register skills when this package is imported
from nanobricks.skills.a2a import A2AMessage, SkillA2A
from nanobricks.skills.acp import RESTEndpoint, RESTResponse, SkillACP
from nanobricks.skills.agui import ComponentType, SkillAGUI, UIBuilder, UIComponent
from nanobricks.skills.ai import SkillAI, create_ai_skill
from nanobricks.skills.api import SkillApi
from nanobricks.skills.cli import CliSkill
from nanobricks.skills.logging import LoggingSkill
from nanobricks.skills.mcp import MCPToolConfig, SkillMCP, create_mcp_server

__all__ = [
    "LoggingSkill",
    "SkillApi",
    "CliSkill",
    "SkillAI",
    "create_ai_skill",
    "SkillMCP",
    "MCPToolConfig",
    "create_mcp_server",
    "SkillA2A",
    "A2AMessage",
    "SkillAGUI",
    "UIBuilder",
    "UIComponent",
    "ComponentType",
    "SkillACP",
    "RESTEndpoint",
    "RESTResponse",
]
