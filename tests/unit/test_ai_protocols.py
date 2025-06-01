"""Tests for AI protocol adapters and skills."""

import asyncio
from datetime import datetime
from unittest.mock import AsyncMock, Mock

import pytest

from nanobricks.agent.ai_protocol import (
    BaseAIProtocolAdapter,
    Message,
    ProtocolBridge,
    ProtocolConfig,
    ProtocolRegistry,
    ProtocolType,
)
from nanobricks.protocol import NanobrickBase
from nanobricks.skills.a2a import A2AMessage, A2AProtocolAdapter, SkillA2A
from nanobricks.skills.acp import (
    ACPProtocolAdapter,
    RESTEndpoint,
    RESTResponse,
    SkillACP,
)
from nanobricks.skills.agui import (
    AGUIProtocolAdapter,
    ComponentType,
    SkillAGUI,
    UIBuilder,
    UIState,
)


class TestMessage:
    """Test Message class."""

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
        assert isinstance(msg.timestamp, datetime)

    def test_message_to_dict(self):
        """Test converting message to dict."""
        msg = Message(id="test-123", type="test", content={"data": "value"})

        data = msg.to_dict()
        assert data["id"] == "test-123"
        assert data["type"] == "test"
        assert data["content"] == {"data": "value"}
        assert "timestamp" in data


class TestProtocolRegistry:
    """Test ProtocolRegistry."""

    def test_register_and_create(self):
        """Test registering and creating adapters."""

        # Create mock adapter
        class MockAdapter(BaseAIProtocolAdapter):
            async def send(self, message: Message) -> None:
                pass

            async def receive(self):
                return None

            async def connect(self) -> None:
                self._connected = True

            async def disconnect(self) -> None:
                self._connected = False

        # Register
        ProtocolRegistry.register(ProtocolType.CUSTOM, MockAdapter)

        # Create
        config = ProtocolConfig(protocol_type=ProtocolType.CUSTOM)
        adapter = ProtocolRegistry.create(config)

        assert isinstance(adapter, MockAdapter)
        assert adapter.protocol_type == ProtocolType.CUSTOM


class TestProtocolBridge:
    """Test ProtocolBridge."""

    @pytest.mark.asyncio
    async def test_bridge_routing(self):
        """Test message routing between protocols."""
        # Create mock adapters
        adapter1 = Mock(spec=BaseAIProtocolAdapter)
        adapter1.protocol_type = ProtocolType.A2A
        adapter1.is_connected = Mock(return_value=True)
        adapter1.connect = AsyncMock()
        adapter1.disconnect = AsyncMock()
        adapter1.receive = AsyncMock(return_value=None)

        adapter2 = Mock(spec=BaseAIProtocolAdapter)
        adapter2.protocol_type = ProtocolType.ACP
        adapter2.is_connected = Mock(return_value=False)
        adapter2.connect = AsyncMock()
        adapter2.disconnect = AsyncMock()
        adapter2.send = AsyncMock()

        # Create bridge
        bridge = ProtocolBridge()
        bridge.register_adapter("a2a", adapter1)
        bridge.register_adapter("acp", adapter2)
        bridge.add_route("a2a", ["acp"])

        # Test connection (don't await start as it runs forever)
        start_task = asyncio.create_task(bridge.start())
        await asyncio.sleep(0.1)  # Let it initialize
        adapter2.connect.assert_called_once()

        # Clean up
        start_task.cancel()
        try:
            await start_task
        except asyncio.CancelledError:
            pass

    def test_message_transformer(self):
        """Test message transformation."""
        bridge = ProtocolBridge()

        # Register transformer
        def transform_a2a_to_acp(msg: Message) -> Message:
            return Message(
                id=msg.id, type="transformed", content={"original": msg.content}
            )

        bridge.register_transformer(
            ProtocolType.A2A, ProtocolType.ACP, transform_a2a_to_acp
        )

        # Test internal method
        assert hasattr(bridge, "_transformers")
        assert (ProtocolType.A2A, ProtocolType.ACP) in bridge._transformers


class TestA2AProtocol:
    """Test A2A protocol and skill."""

    @pytest.mark.asyncio
    async def test_a2a_adapter(self):
        """Test A2A protocol adapter."""
        config = ProtocolConfig(protocol_type=ProtocolType.A2A)
        adapter = A2AProtocolAdapter(config)

        # Test connection
        await adapter.connect()
        assert adapter.is_connected()

        # Test agent registration
        skill = Mock()
        adapter.register_agent("agent1", skill)
        assert "agent1" in adapter._agents

        # Test disconnect
        await adapter.disconnect()
        assert not adapter.is_connected()

    @pytest.mark.asyncio
    async def test_skill_a2a(self):
        """Test SkillA2A."""
        skill = SkillA2A(agent_id="test-agent")

        # Test connection
        await skill.connect()
        assert skill._connected

        # Test message handlers
        handler_called = False

        def handler(msg: A2AMessage):
            nonlocal handler_called
            handler_called = True

        skill.on_message(handler)

        # Simulate receiving message
        msg = A2AMessage(agent_id="test-agent", content="test")
        await skill._receive_message(msg)

        assert handler_called

        # Test disconnect
        await skill.disconnect()
        assert not skill._connected

    def test_a2a_enhanced_brick(self):
        """Test A2A enhanced brick."""
        # Create mock brick
        brick = Mock(spec=NanobrickBase)
        brick.name = "test_brick"
        brick.invoke = AsyncMock(return_value="result")

        # Enhance with A2A
        skill = SkillA2A()
        enhanced = skill.enhance(brick)

        # Check methods exist
        assert hasattr(enhanced, "send_to")
        assert hasattr(enhanced, "broadcast")
        assert hasattr(enhanced, "on_message")
        assert hasattr(enhanced, "request_reply")


class TestAGUIProtocol:
    """Test AGUI protocol and skill."""

    @pytest.mark.asyncio
    async def test_agui_adapter(self):
        """Test AGUI protocol adapter."""
        config = ProtocolConfig(protocol_type=ProtocolType.AGUI)
        adapter = AGUIProtocolAdapter(config)

        # Test connection
        await adapter.connect()
        assert adapter.is_connected()

        # Test session creation
        session = adapter.create_session("test-session")
        assert isinstance(session, UIState)
        assert adapter.get_session("test-session") == session

        # Test disconnect
        await adapter.disconnect()
        assert not adapter.is_connected()
        assert adapter.get_session("test-session") is None

    def test_ui_builder(self):
        """Test UI builder."""
        builder = UIBuilder()

        # Build UI
        ui = (
            builder.text("Hello World")
            .button("Click Me", on_click="handler1")
            .input("Enter text", default_value="default")
            .select(["Option 1", "Option 2"], default="Option 1")
            .build()
        )

        assert len(ui) == 4
        assert ui[0].type == ComponentType.TEXT
        assert ui[1].type == ComponentType.BUTTON
        assert ui[2].type == ComponentType.INPUT
        assert ui[3].type == ComponentType.SELECT

        # Check button handler
        assert ui[1].handlers.get("click") == "handler1"

    @pytest.mark.asyncio
    async def test_skill_agui(self):
        """Test SkillAGUI."""
        skill = SkillAGUI(session_id="test-session")

        # Mock adapter
        adapter = Mock(spec=AGUIProtocolAdapter)
        adapter.is_connected = Mock(return_value=True)
        adapter.connect = AsyncMock()
        adapter.create_session = Mock(return_value=UIState())
        adapter.send = AsyncMock()
        skill._adapter = adapter

        # Test connection
        await skill.connect()
        adapter.connect.assert_called_once()

        # Test UI rendering
        ui = skill.create_ui().text("Test").build()
        await skill.render(ui)

        adapter.send.assert_called_once()
        call_args = adapter.send.call_args[0][0]
        assert call_args.type == "ui_update"
        assert "components" in call_args.content

    def test_agui_enhanced_brick(self):
        """Test AGUI enhanced brick."""
        # Create mock brick
        brick = Mock(spec=NanobrickBase)
        brick.name = "test_brick"
        brick.invoke = AsyncMock(return_value="result")

        # Enhance with AGUI
        skill = SkillAGUI()
        enhanced = skill.enhance(brick)

        # Check methods exist
        assert hasattr(enhanced, "create_ui")
        assert hasattr(enhanced, "render")
        assert hasattr(enhanced, "update_ui")
        assert hasattr(enhanced, "on_event")
        assert hasattr(enhanced, "show_dialog")


class TestACPProtocol:
    """Test ACP protocol and skill."""

    @pytest.mark.asyncio
    async def test_acp_adapter(self):
        """Test ACP protocol adapter."""
        config = ProtocolConfig(
            protocol_type=ProtocolType.ACP,
            endpoint="http://localhost:8000",
            auth={"type": "bearer", "token": "test-token"},
        )
        adapter = ACPProtocolAdapter(config)

        # Check auth headers
        assert adapter._auth_headers == {"Authorization": "Bearer test-token"}

        # Test endpoint registration
        endpoint = RESTEndpoint(path="/test", method="GET")
        adapter.register_endpoint("test", endpoint)
        assert adapter.get_endpoint("test") == endpoint

    def test_rest_response(self):
        """Test REST response."""
        response = RESTResponse(
            status=200,
            data={"result": "success"},
            headers={"Content-Type": "application/json"},
        )

        assert response.is_success

        data = response.to_dict()
        assert data["status"] == 200
        assert data["data"] == {"result": "success"}
        assert "timestamp" in data

    @pytest.mark.asyncio
    async def test_skill_acp(self):
        """Test SkillACP."""
        skill = SkillACP(
            base_url="http://localhost:8000",
            auth={"type": "api_key", "key_name": "X-API-Key", "key_value": "secret"},
        )

        # Mock adapter
        adapter = Mock(spec=ACPProtocolAdapter)
        adapter.is_connected = Mock(return_value=True)
        adapter.connect = AsyncMock()
        adapter.send = AsyncMock()
        adapter.receive = AsyncMock(
            return_value=Message(
                id="resp-123",
                type="rest_response",
                content={"status": 200, "data": {"result": "ok"}, "headers": {}},
            )
        )
        skill._adapter = adapter

        # Test API call
        await skill.connect()
        response = await skill.call_api("/test", {"data": "value"})

        assert response.status == 200
        assert response.data == {"result": "ok"}

    def test_acp_enhanced_brick(self):
        """Test ACP enhanced brick."""
        # Create mock brick
        brick = Mock(spec=NanobrickBase)
        brick.name = "test_brick"
        brick.invoke = AsyncMock(return_value="result")

        # Enhance with ACP
        skill = SkillACP()
        enhanced = skill.enhance(brick)

        # Check methods exist
        assert hasattr(enhanced, "call_api")
        assert hasattr(enhanced, "register_endpoint")
        assert hasattr(enhanced, "add_interceptor")
        assert hasattr(enhanced, "on_response")
        assert hasattr(enhanced, "stream_to_api")


class TestProtocolIntegration:
    """Test protocol integration scenarios."""

    @pytest.mark.asyncio
    async def test_protocol_bridge_integration(self):
        """Test bridging between protocols."""
        # Create A2A adapter
        a2a_config = ProtocolConfig(protocol_type=ProtocolType.A2A)
        a2a_adapter = A2AProtocolAdapter(a2a_config)

        # Create ACP adapter (mocked)
        acp_adapter = Mock(spec=ACPProtocolAdapter)
        acp_adapter.protocol_type = ProtocolType.ACP
        acp_adapter.is_connected = Mock(return_value=False)
        acp_adapter.connect = AsyncMock()
        acp_adapter.send = AsyncMock()

        # Create bridge
        bridge = ProtocolBridge()
        bridge.register_adapter("a2a", a2a_adapter)
        bridge.register_adapter("acp", acp_adapter)
        bridge.add_route("a2a", ["acp"])

        # Register transformer
        def transform_msg(msg: Message) -> Message:
            return Message(
                id=msg.id, type="api_call", content={"a2a_content": msg.content}
            )

        bridge.register_transformer(ProtocolType.A2A, ProtocolType.ACP, transform_msg)

        # Connect adapters
        await a2a_adapter.connect()
        await acp_adapter.connect()

        assert a2a_adapter.is_connected()
        acp_adapter.connect.assert_called_once()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
