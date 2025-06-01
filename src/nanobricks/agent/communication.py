"""Agent communication implementation."""

import asyncio
import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Optional

from nanobricks.agent.protocols import A2AProtocol, MessageType
from nanobricks.protocol import NanobrickProtocol


@dataclass
class AgentMessage:
    """A message between agents."""

    id: str
    from_agent: str
    to_agent: str | None  # None for broadcast
    message_type: MessageType
    content: Any
    metadata: dict[str, Any]
    timestamp: datetime

    @classmethod
    def create(
        cls,
        from_agent: str,
        to_agent: str | None,
        message_type: MessageType,
        content: Any,
        metadata: dict[str, Any] | None = None,
    ) -> "AgentMessage":
        """Create a new message."""
        return cls(
            id=str(uuid.uuid4()),
            from_agent=from_agent,
            to_agent=to_agent,
            message_type=message_type,
            content=content,
            metadata=metadata or {},
            timestamp=datetime.now(),
        )


class AgentRegistry:
    """Registry for discovering agents."""

    def __init__(self):
        self._agents: dict[str, Agent] = {}
        self._capabilities: dict[str, set[str]] = {}
        self._lock = asyncio.Lock()

    async def register(self, agent: "Agent"):
        """Register an agent."""
        async with self._lock:
            self._agents[agent.id] = agent

            # Register capabilities
            for capability in agent.capabilities:
                if capability not in self._capabilities:
                    self._capabilities[capability] = set()
                self._capabilities[capability].add(agent.id)

    async def unregister(self, agent_id: str):
        """Unregister an agent."""
        async with self._lock:
            agent = self._agents.pop(agent_id, None)
            if agent:
                # Remove from capabilities
                for capability in agent.capabilities:
                    if capability in self._capabilities:
                        self._capabilities[capability].discard(agent_id)

    async def get_agent(self, agent_id: str) -> Optional["Agent"]:
        """Get agent by ID."""
        async with self._lock:
            return self._agents.get(agent_id)

    async def discover(self, capability: str | None = None) -> list[dict[str, Any]]:
        """Discover agents."""
        async with self._lock:
            if capability:
                agent_ids = self._capabilities.get(capability, set())
                agents = [self._agents[aid] for aid in agent_ids if aid in self._agents]
            else:
                agents = list(self._agents.values())

            return [
                {
                    "id": agent.id,
                    "name": agent.name,
                    "capabilities": agent.capabilities,
                    "metadata": agent.metadata,
                }
                for agent in agents
            ]


# Global registry
_global_registry = AgentRegistry()


class Agent(A2AProtocol):
    """An agent that can communicate with other agents."""

    def __init__(
        self,
        id: str,
        name: str,
        brick: NanobrickProtocol | None = None,
        capabilities: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
        auto_register: bool = True,
    ):
        """Initialize agent.

        Args:
            id: Unique agent ID
            name: Human-readable name
            brick: Optional nanobrick to wrap
            capabilities: List of capabilities
            metadata: Additional metadata
            auto_register: Auto-register with global registry
        """
        self.id = id
        self.name = name
        self.brick = brick
        self.capabilities = capabilities or []
        self.metadata = metadata or {}

        # Message queue
        self._inbox: asyncio.Queue[AgentMessage] = asyncio.Queue()
        self._outbox: list[AgentMessage] = []

        # Add brick capabilities
        if brick:
            self.capabilities.append(f"brick:{brick.name}")

        # Auto-register
        self._registered = False
        if auto_register:
            asyncio.create_task(self._auto_register())

    async def _auto_register(self):
        """Auto-register with global registry."""
        await _global_registry.register(self)
        self._registered = True

    async def send_message(
        self,
        to_agent: str,
        message_type: MessageType,
        content: Any,
        metadata: dict[str, Any] | None = None,
    ) -> str:
        """Send a message to another agent."""
        message = AgentMessage.create(
            from_agent=self.id,
            to_agent=to_agent,
            message_type=message_type,
            content=content,
            metadata=metadata,
        )

        # Store in outbox
        self._outbox.append(message)

        # Deliver to target
        target = await _global_registry.get_agent(to_agent)
        if target:
            await target._receive(message)
        else:
            # Create error response
            error_msg = AgentMessage.create(
                from_agent="system",
                to_agent=self.id,
                message_type=MessageType.ERROR,
                content=f"Agent {to_agent} not found",
                metadata={"original_message_id": message.id},
            )
            await self._inbox.put(error_msg)

        return message.id

    async def receive_messages(
        self,
        message_types: list[MessageType] | None = None,
        timeout: float | None = None,
    ) -> list[AgentMessage]:
        """Receive messages."""
        messages = []
        end_time = asyncio.get_event_loop().time() + timeout if timeout else None

        while True:
            try:
                remaining = None
                if end_time:
                    remaining = end_time - asyncio.get_event_loop().time()
                    if remaining <= 0:
                        break

                message = await asyncio.wait_for(self._inbox.get(), timeout=remaining)

                if message_types is None or message.message_type in message_types:
                    messages.append(message)
                else:
                    # Put back if not matching filter
                    await self._inbox.put(message)

                # Check if more messages available
                if self._inbox.empty():
                    break

            except TimeoutError:
                break

        return messages

    async def broadcast(
        self,
        message_type: MessageType,
        content: Any,
        metadata: dict[str, Any] | None = None,
    ) -> list[str]:
        """Broadcast to all agents."""
        agents = await _global_registry.discover()
        message_ids = []

        for agent_info in agents:
            if agent_info["id"] != self.id:  # Don't send to self
                msg_id = await self.send_message(
                    to_agent=agent_info["id"],
                    message_type=message_type,
                    content=content,
                    metadata=metadata,
                )
                message_ids.append(msg_id)

        return message_ids

    async def discover_agents(
        self,
        capability: str | None = None,
        timeout: float = 5.0,
    ) -> list[dict[str, Any]]:
        """Discover other agents."""
        # Send discovery request
        if capability:
            await self.broadcast(
                MessageType.DISCOVER,
                {"capability": capability},
            )
        else:
            await self.broadcast(MessageType.DISCOVER, {})

        # Collect announcements
        await asyncio.sleep(0.1)  # Give time for responses

        messages = await self.receive_messages(
            message_types=[MessageType.ANNOUNCE],
            timeout=timeout,
        )

        # Also get from registry
        registry_agents = await _global_registry.discover(capability)

        # Merge results
        discovered = {a["id"]: a for a in registry_agents}

        for msg in messages:
            agent_info = msg.content
            if isinstance(agent_info, dict) and "id" in agent_info:
                discovered[agent_info["id"]] = agent_info

        return list(discovered.values())

    async def _receive(self, message: AgentMessage):
        """Receive a message (internal)."""
        # Handle discovery requests
        if message.message_type == MessageType.DISCOVER:
            capability = (
                message.content.get("capability")
                if isinstance(message.content, dict)
                else None
            )

            if capability is None or capability in self.capabilities:
                # Send announcement
                announce = AgentMessage.create(
                    from_agent=self.id,
                    to_agent=message.from_agent,
                    message_type=MessageType.ANNOUNCE,
                    content={
                        "id": self.id,
                        "name": self.name,
                        "capabilities": self.capabilities,
                        "metadata": self.metadata,
                    },
                )

                sender = await _global_registry.get_agent(message.from_agent)
                if sender:
                    await sender._inbox.put(announce)
        else:
            # Regular message
            await self._inbox.put(message)

    async def process_with_brick(self, input: Any) -> Any:
        """Process input with wrapped brick."""
        if not self.brick:
            raise ValueError("No brick attached to agent")

        return await self.brick.invoke(input)

    async def request_processing(
        self,
        target_agent: str,
        input: Any,
        timeout: float = 30.0,
    ) -> Any:
        """Request another agent to process data."""
        # Send request
        request_id = await self.send_message(
            to_agent=target_agent,
            message_type=MessageType.REQUEST,
            content={"input": input},
            metadata={"reply_to": self.id},
        )

        # Wait for response
        messages = await self.receive_messages(
            message_types=[MessageType.RESPONSE, MessageType.ERROR],
            timeout=timeout,
        )

        for msg in messages:
            if msg.metadata.get("request_id") == request_id:
                if msg.message_type == MessageType.ERROR:
                    raise RuntimeError(f"Processing error: {msg.content}")
                return msg.content.get("output")

        raise TimeoutError(f"No response from {target_agent}")

    async def handle_requests(self):
        """Handle incoming processing requests."""
        while True:
            messages = await self.receive_messages(
                message_types=[MessageType.REQUEST],
                timeout=1.0,
            )

            for msg in messages:
                asyncio.create_task(self._handle_request(msg))

    async def _handle_request(self, request: AgentMessage):
        """Handle a single request."""
        try:
            # Extract input
            input_data = request.content.get("input")

            # Process with brick
            output = await self.process_with_brick(input_data)

            # Send response
            await self.send_message(
                to_agent=request.from_agent,
                message_type=MessageType.RESPONSE,
                content={"output": output},
                metadata={"request_id": request.id},
            )

        except Exception as e:
            # Send error
            await self.send_message(
                to_agent=request.from_agent,
                message_type=MessageType.ERROR,
                content=str(e),
                metadata={"request_id": request.id},
            )

    async def shutdown(self):
        """Shutdown agent."""
        if self._registered:
            await _global_registry.unregister(self.id)


def create_agent(
    brick: NanobrickProtocol,
    name: str | None = None,
    capabilities: list[str] | None = None,
) -> Agent:
    """Create an agent from a nanobrick.

    Args:
        brick: Nanobrick to wrap
        name: Agent name (defaults to brick name)
        capabilities: Additional capabilities

    Returns:
        Agent instance
    """
    agent_id = f"agent_{uuid.uuid4().hex[:8]}"
    agent_name = name or f"Agent[{brick.name}]"

    return Agent(
        id=agent_id,
        name=agent_name,
        brick=brick,
        capabilities=capabilities,
    )
