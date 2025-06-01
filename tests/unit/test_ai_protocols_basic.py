"""Basic tests for AI protocol adapters and skills."""

from unittest.mock import Mock

import pytest

from nanobricks.agent.ai_protocol import (
    Message,
    ProtocolConfig,
    ProtocolRegistry,
    ProtocolType,
)
from nanobricks.protocol import NanobrickBase
from nanobricks.skills.a2a import A2AMessage, SkillA2A
from nanobricks.skills.acp import RESTEndpoint, RESTResponse, SkillACP
from nanobricks.skills.agui import ComponentType, SkillAGUI, UIBuilder


class TestProtocolCore:
    """Test core protocol functionality."""

    def test_message_creation(self):
        """Test creating a message."""
        msg = Message(
            id="test-123",
            type="test",
            content={"data": "value"},
            metadata={"key": "value"},
        )

        assert msg.id == "test-123"
        assert msg.type == "test"
        assert msg.content == {"data": "value"}
        assert msg.metadata == {"key": "value"}

    def test_protocol_config(self):
        """Test protocol configuration."""
        config = ProtocolConfig(
            protocol_type=ProtocolType.A2A,
            endpoint="ws://localhost:8080",
            auth={"token": "secret"},
            timeout=60.0,
            retry_count=5,
        )

        assert config.protocol_type == ProtocolType.A2A
        assert config.endpoint == "ws://localhost:8080"
        assert config.auth["token"] == "secret"
        assert config.timeout == 60.0
        assert config.retry_count == 5


class TestA2ASkill:
    """Test A2A skill functionality."""

    def test_a2a_message(self):
        """Test A2A message creation."""
        msg = A2AMessage(
            agent_id="agent-1", content={"action": "test"}, reply_to="msg-123"
        )

        assert msg.agent_id == "agent-1"
        assert msg.content == {"action": "test"}
        assert msg.reply_to == "msg-123"
        assert msg.conversation_id is not None

    def test_a2a_skill_creation(self):
        """Test creating A2A skill."""
        skill = SkillA2A(agent_id="test-agent")

        assert skill.agent_id == "test-agent"
        assert skill._peers == set()
        assert not skill._connected

    def test_a2a_enhanced_brick(self):
        """Test A2A enhanced brick creation."""
        # Create mock brick
        brick = Mock(spec=NanobrickBase)
        brick.name = "test_brick"
        brick.version = "1.0.0"

        # Enhance with A2A
        skill = SkillA2A()
        enhanced = skill.enhance(brick)

        # Check enhanced brick has correct methods
        assert hasattr(enhanced, "send_to")
        assert hasattr(enhanced, "broadcast")
        assert hasattr(enhanced, "on_message")


class TestAGUISkill:
    """Test AGUI skill functionality."""

    def test_ui_builder(self):
        """Test UI builder functionality."""
        builder = UIBuilder()

        # Build a simple UI
        ui = (
            builder.text("Hello World")
            .button("Click Me", on_click="handler1")
            .input("Enter text")
            .build()
        )

        assert len(ui) == 3
        assert ui[0].type == ComponentType.TEXT
        assert ui[0].props["content"] == "Hello World"
        assert ui[1].type == ComponentType.BUTTON
        assert ui[1].props["label"] == "Click Me"
        assert ui[1].handlers.get("click") == "handler1"
        assert ui[2].type == ComponentType.INPUT

    def test_agui_skill_creation(self):
        """Test creating AGUI skill."""
        skill = SkillAGUI(session_id="test-session")

        assert skill.session_id == "test-session"
        assert skill._auto_render
        assert skill._ui_state is None

    def test_agui_enhanced_brick(self):
        """Test AGUI enhanced brick creation."""
        # Create mock brick
        brick = Mock(spec=NanobrickBase)
        brick.name = "ui_brick"
        brick.version = "1.0.0"

        # Enhance with AGUI
        skill = SkillAGUI()
        enhanced = skill.enhance(brick)

        # Check enhanced brick has correct methods
        assert hasattr(enhanced, "create_ui")
        assert hasattr(enhanced, "render")
        assert hasattr(enhanced, "update_ui")
        assert hasattr(enhanced, "show_dialog")


class TestACPSkill:
    """Test ACP skill functionality."""

    def test_rest_endpoint(self):
        """Test REST endpoint configuration."""
        endpoint = RESTEndpoint(
            path="/api/v1/agent",
            method="POST",
            headers={"Content-Type": "application/json"},
            timeout=45.0,
        )

        assert endpoint.path == "/api/v1/agent"
        assert endpoint.method == "POST"
        assert endpoint.headers["Content-Type"] == "application/json"
        assert endpoint.timeout == 45.0

        # Test full URL
        assert (
            endpoint.full_url("https://api.example.com")
            == "https://api.example.com/api/v1/agent"
        )

    def test_rest_response(self):
        """Test REST response."""
        response = RESTResponse(
            status=200,
            data={"result": "success"},
            headers={"Content-Type": "application/json"},
        )

        assert response.status == 200
        assert response.data == {"result": "success"}
        assert response.is_success

        # Test failed response
        error_response = RESTResponse(
            status=404, data={"error": "Not found"}, headers={}
        )
        assert not error_response.is_success

    def test_acp_skill_creation(self):
        """Test creating ACP skill."""
        skill = SkillACP(
            base_url="https://api.example.com",
            auth={"type": "bearer", "token": "secret"},
        )

        assert skill._base_url == "https://api.example.com"
        assert skill._auth == {"type": "bearer", "token": "secret"}
        assert skill._retry_count == 3

    def test_acp_enhanced_brick(self):
        """Test ACP enhanced brick creation."""
        # Create mock brick
        brick = Mock(spec=NanobrickBase)
        brick.name = "api_brick"
        brick.version = "1.0.0"

        # Enhance with ACP
        skill = SkillACP()
        enhanced = skill.enhance(brick)

        # Check enhanced brick has correct methods
        assert hasattr(enhanced, "call_api")
        assert hasattr(enhanced, "register_endpoint")
        assert hasattr(enhanced, "add_interceptor")
        assert hasattr(enhanced, "stream_to_api")


class TestProtocolRegistry:
    """Test protocol registry functionality."""

    def test_protocol_types(self):
        """Test protocol type enum."""
        assert ProtocolType.MCP.value == "mcp"
        assert ProtocolType.A2A.value == "a2a"
        assert ProtocolType.AGUI.value == "agui"
        assert ProtocolType.ACP.value == "acp"
        assert ProtocolType.CUSTOM.value == "custom"

    def test_registry_list(self):
        """Test listing registered protocols."""
        protocols = ProtocolRegistry.list_protocols()

        # Check that our protocols are registered
        assert ProtocolType.A2A in protocols
        assert ProtocolType.AGUI in protocols
        assert ProtocolType.ACP in protocols


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
