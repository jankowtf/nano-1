"""A2A (Agent-to-Agent) skill for nanobricks."""

import asyncio
import uuid
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from nanobricks.agent.ai_protocol import (
    BaseAIProtocolAdapter,
    Message,
    ProtocolConfig,
    ProtocolRegistry,
    ProtocolType,
)
from nanobricks.protocol import NanobrickBase
from nanobricks.skill import NanobrickEnhanced, Skill


@dataclass
class A2AMessage:
    """Agent-to-agent message."""

    agent_id: str
    content: Any
    reply_to: str | None = None
    conversation_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = field(default_factory=datetime.utcnow)

    def to_protocol_message(self) -> Message:
        """Convert to protocol message."""
        return Message(
            id=str(uuid.uuid4()),
            type="a2a_message",
            content={
                "agent_id": self.agent_id,
                "content": self.content,
                "reply_to": self.reply_to,
                "conversation_id": self.conversation_id,
            },
            metadata={"timestamp": self.timestamp.isoformat()},
        )


class A2AProtocolAdapter(BaseAIProtocolAdapter):
    """A2A protocol adapter implementation."""

    def __init__(self, config: ProtocolConfig):
        """Initialize A2A adapter."""
        super().__init__(config)
        self._message_queue: asyncio.Queue = asyncio.Queue()
        self._agents: dict[str, SkillA2A] = {}
        self._running = False
        self._task: asyncio.Task | None = None

    async def send(self, message: Message) -> None:
        """Send message to agent."""
        if not self._connected:
            raise RuntimeError("Not connected")

        # Extract agent ID from message
        agent_id = message.content.get("agent_id")
        if agent_id and agent_id in self._agents:
            agent = self._agents[agent_id]
            # Convert back to A2A message
            a2a_msg = A2AMessage(
                agent_id=message.content["agent_id"],
                content=message.content["content"],
                reply_to=message.content.get("reply_to"),
                conversation_id=message.content.get(
                    "conversation_id", str(uuid.uuid4())
                ),
            )
            await agent._receive_message(a2a_msg)

    async def receive(self) -> Message | None:
        """Receive message from queue."""
        if not self._connected:
            return None

        try:
            return await asyncio.wait_for(self._message_queue.get(), timeout=1.0)
        except TimeoutError:
            return None

    async def connect(self) -> None:
        """Start A2A protocol."""
        self._connected = True
        self._running = True

    async def disconnect(self) -> None:
        """Stop A2A protocol."""
        self._running = False
        self._connected = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass

    def register_agent(self, agent_id: str, agent: "SkillA2A") -> None:
        """Register an agent."""
        self._agents[agent_id] = agent

    def unregister_agent(self, agent_id: str) -> None:
        """Unregister an agent."""
        self._agents.pop(agent_id, None)

    async def broadcast(self, message: Message) -> None:
        """Broadcast message to all agents."""
        for agent in self._agents.values():
            await self.send(message)


# Register A2A adapter
ProtocolRegistry.register(ProtocolType.A2A, A2AProtocolAdapter)


class SkillA2A(Skill):
    """Agent-to-Agent communication skill."""

    def __init__(
        self,
        agent_id: str | None = None,
        adapter: A2AProtocolAdapter | None = None,
        auto_reply: bool = False,
        reply_handler: Callable[[A2AMessage], Any] | None = None,
    ):
        """Initialize A2A skill."""
        super().__init__()
        self.agent_id = agent_id or str(uuid.uuid4())
        self._adapter = adapter
        self._message_handlers: list[Callable[[A2AMessage], None]] = []
        self._conversations: dict[str, list[A2AMessage]] = {}
        self._auto_reply = auto_reply
        self._reply_handler = reply_handler
        self._peers: set[str] = set()
        self._connected = False

    def _create_enhanced_brick(self, brick: NanobrickBase) -> NanobrickEnhanced:
        """Create enhanced brick with A2A capabilities."""

        class A2ANanobrickEnhanced(NanobrickEnhanced):
            """Brick enhanced with A2A communication."""

            def __init__(self, wrapped: NanobrickBase, skill: SkillA2A):
                """Initialize enhanced brick."""
                super().__init__(wrapped, skill)
                self._a2a_skill = skill

            async def invoke(self, input: Any, *, deps: dict | None = None) -> Any:
                """Invoke with A2A capabilities."""
                # Connect if not connected
                if not self._a2a_skill._connected:
                    await self._a2a_skill.connect()

                # Process input
                result = await self.wrapped.invoke(input, deps=deps)

                # Broadcast result if configured
                if (
                    hasattr(self._a2a_skill, "_broadcast_results")
                    and self._a2a_skill._broadcast_results
                ):
                    await self._a2a_skill.broadcast(
                        {
                            "type": "result",
                            "brick": self.wrapped.name,
                            "input": input,
                            "result": result,
                        }
                    )

                return result

            def invoke_sync(self, input: Any, *, deps: dict | None = None) -> Any:
                """Sync invoke."""
                return asyncio.run(self.invoke(input, deps=deps))

            async def send_to(self, agent_id: str, content: Any) -> None:
                """Send message to specific agent."""
                await self._a2a_skill.send_to(agent_id, content)

            async def broadcast(self, content: Any) -> None:
                """Broadcast to all peers."""
                await self._a2a_skill.broadcast(content)

            def on_message(self, handler: Callable[[A2AMessage], None]) -> None:
                """Register message handler."""
                self._a2a_skill.on_message(handler)

            async def request_reply(
                self, agent_id: str, content: Any, timeout: float = 30.0
            ) -> Any | None:
                """Send message and wait for reply."""
                return await self._a2a_skill.request_reply(agent_id, content, timeout)

        return A2ANanobrickEnhanced(brick, self)

    async def connect(self, endpoint: str | None = None) -> None:
        """Connect to A2A network."""
        if self._connected:
            return

        # Create adapter if not provided
        if not self._adapter:
            config = ProtocolConfig(
                protocol_type=ProtocolType.A2A,
                endpoint=endpoint,
            )
            self._adapter = ProtocolRegistry.create(config)

        # Connect adapter
        await self._adapter.connect()

        # Register this agent
        if isinstance(self._adapter, A2AProtocolAdapter):
            self._adapter.register_agent(self.agent_id, self)

        self._connected = True

    async def disconnect(self) -> None:
        """Disconnect from A2A network."""
        if not self._connected:
            return

        # Unregister agent
        if isinstance(self._adapter, A2AProtocolAdapter):
            self._adapter.unregister_agent(self.agent_id)

        # Disconnect adapter
        if self._adapter:
            await self._adapter.disconnect()

        self._connected = False

    async def send_to(self, agent_id: str, content: Any) -> None:
        """Send message to specific agent."""
        msg = A2AMessage(
            agent_id=agent_id,
            content=content,
        )

        # Store in conversation
        if msg.conversation_id not in self._conversations:
            self._conversations[msg.conversation_id] = []
        self._conversations[msg.conversation_id].append(msg)

        # Send via adapter
        await self._adapter.send(msg.to_protocol_message())

    async def broadcast(self, content: Any) -> None:
        """Broadcast message to all peers."""
        for peer_id in self._peers:
            await self.send_to(peer_id, content)

    async def request_reply(
        self, agent_id: str, content: Any, timeout: float = 30.0
    ) -> Any | None:
        """Send message and wait for reply."""
        # Create unique message ID
        msg_id = str(uuid.uuid4())

        # Create reply future
        reply_future = asyncio.Future()

        # Register temporary handler
        def reply_handler(msg: A2AMessage):
            if msg.reply_to == msg_id:
                reply_future.set_result(msg.content)

        self.on_message(reply_handler)

        # Send message
        msg = A2AMessage(
            agent_id=agent_id,
            content=content,
        )
        msg.id = msg_id  # Override ID
        await self._adapter.send(msg.to_protocol_message())

        try:
            # Wait for reply
            return await asyncio.wait_for(reply_future, timeout=timeout)
        except TimeoutError:
            return None
        finally:
            # Remove handler
            self._message_handlers.remove(reply_handler)

    def on_message(self, handler: Callable[[A2AMessage], None]) -> None:
        """Register message handler."""
        self._message_handlers.append(handler)

    async def _receive_message(self, message: A2AMessage) -> None:
        """Internal message receiver."""
        # Store in conversation
        if message.conversation_id not in self._conversations:
            self._conversations[message.conversation_id] = []
        self._conversations[message.conversation_id].append(message)

        # Call handlers
        for handler in self._message_handlers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(message)
                else:
                    handler(message)
            except Exception:
                # Ignore handler errors
                pass

        # Auto-reply if configured
        if self._auto_reply and self._reply_handler and not message.reply_to:
            try:
                reply_content = self._reply_handler(message)
                if asyncio.iscoroutine(reply_content):
                    reply_content = await reply_content

                if reply_content is not None:
                    reply_msg = A2AMessage(
                        agent_id=message.agent_id,
                        content=reply_content,
                        reply_to=getattr(message, "id", None),
                        conversation_id=message.conversation_id,
                    )
                    await self._adapter.send(reply_msg.to_protocol_message())
            except Exception:
                # Ignore auto-reply errors
                pass

    def add_peer(self, agent_id: str) -> None:
        """Add a peer agent."""
        self._peers.add(agent_id)

    def remove_peer(self, agent_id: str) -> None:
        """Remove a peer agent."""
        self._peers.discard(agent_id)

    def get_conversation(self, conversation_id: str) -> list[A2AMessage]:
        """Get conversation history."""
        return self._conversations.get(conversation_id, [])
