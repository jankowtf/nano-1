"""Agent communication protocols."""

from enum import Enum
from typing import Any, Protocol, runtime_checkable


class MessageType(Enum):
    """Types of agent messages."""

    REQUEST = "request"
    RESPONSE = "response"
    BROADCAST = "broadcast"
    DISCOVER = "discover"
    ANNOUNCE = "announce"
    HEARTBEAT = "heartbeat"
    ERROR = "error"


@runtime_checkable
class A2AProtocol(Protocol):
    """Agent-to-Agent communication protocol."""

    async def send_message(
        self,
        to_agent: str,
        message_type: MessageType,
        content: Any,
        metadata: dict[str, Any] | None = None,
    ) -> str:
        """Send a message to another agent.

        Args:
            to_agent: Target agent ID
            message_type: Type of message
            content: Message content
            metadata: Optional metadata

        Returns:
            Message ID
        """
        ...

    async def receive_messages(
        self,
        message_types: list[MessageType] | None = None,
        timeout: float | None = None,
    ) -> list[dict[str, Any]]:
        """Receive messages.

        Args:
            message_types: Filter by message types
            timeout: Timeout in seconds

        Returns:
            List of messages
        """
        ...

    async def broadcast(
        self,
        message_type: MessageType,
        content: Any,
        metadata: dict[str, Any] | None = None,
    ) -> list[str]:
        """Broadcast to all agents.

        Args:
            message_type: Type of message
            content: Message content
            metadata: Optional metadata

        Returns:
            List of message IDs
        """
        ...

    async def discover_agents(
        self,
        capability: str | None = None,
        timeout: float = 5.0,
    ) -> list[dict[str, Any]]:
        """Discover other agents.

        Args:
            capability: Filter by capability
            timeout: Discovery timeout

        Returns:
            List of discovered agents
        """
        ...
