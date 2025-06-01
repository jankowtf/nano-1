"""Protocol adapter abstraction for AI communication protocols."""

import asyncio
from abc import ABC, abstractmethod
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import (
    Any,
    Protocol,
    runtime_checkable,
)


class ProtocolType(Enum):
    """Supported AI protocol types."""

    MCP = "mcp"  # Model Context Protocol
    A2A = "a2a"  # Agent-to-Agent
    AGUI = "agui"  # Agent GUI
    ACP = "acp"  # Agent Communication Protocol (REST)
    CUSTOM = "custom"


@dataclass
class Message:
    """Generic message for protocol communication."""

    id: str
    type: str
    content: Any
    metadata: dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "type": self.type,
            "content": self.content,
            "metadata": self.metadata,
            "timestamp": self.timestamp.isoformat(),
        }


@dataclass
class ProtocolConfig:
    """Configuration for protocol adapters."""

    protocol_type: ProtocolType
    endpoint: str | None = None
    auth: dict[str, str] | None = None
    timeout: float = 30.0
    retry_count: int = 3
    custom_params: dict[str, Any] = field(default_factory=dict)


@runtime_checkable
class AIProtocolAdapter(Protocol):
    """Protocol definition for AI adapters."""

    protocol_type: ProtocolType

    async def send(self, message: Message) -> None:
        """Send a message."""
        ...

    async def receive(self) -> Message | None:
        """Receive a message."""
        ...

    async def connect(self) -> None:
        """Establish connection."""
        ...

    async def disconnect(self) -> None:
        """Close connection."""
        ...

    def is_connected(self) -> bool:
        """Check connection status."""
        ...


class BaseAIProtocolAdapter(ABC):
    """Base class for AI protocol adapters."""

    def __init__(self, config: ProtocolConfig):
        """Initialize adapter."""
        self.config = config
        self.protocol_type = config.protocol_type
        self._connected = False
        self._message_handlers: dict[str, list[Callable]] = {}
        self._error_handlers: list[Callable] = []

    @abstractmethod
    async def send(self, message: Message) -> None:
        """Send a message through the protocol."""
        pass

    @abstractmethod
    async def receive(self) -> Message | None:
        """Receive a message from the protocol."""
        pass

    @abstractmethod
    async def connect(self) -> None:
        """Establish protocol connection."""
        pass

    @abstractmethod
    async def disconnect(self) -> None:
        """Close protocol connection."""
        pass

    def is_connected(self) -> bool:
        """Check if connected."""
        return self._connected

    def register_handler(self, message_type: str, handler: Callable) -> None:
        """Register a message handler."""
        if message_type not in self._message_handlers:
            self._message_handlers[message_type] = []
        self._message_handlers[message_type].append(handler)

    def register_error_handler(self, handler: Callable) -> None:
        """Register an error handler."""
        self._error_handlers.append(handler)

    async def _handle_message(self, message: Message) -> None:
        """Handle incoming message."""
        handlers = self._message_handlers.get(message.type, [])
        for handler in handlers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(message)
                else:
                    handler(message)
            except Exception as e:
                await self._handle_error(e, message)

    async def _handle_error(self, error: Exception, context: Any = None) -> None:
        """Handle errors."""
        for handler in self._error_handlers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(error, context)
                else:
                    handler(error, context)
            except Exception:
                # Ignore errors in error handlers
                pass


class ProtocolBridge:
    """Bridge for cross-protocol communication."""

    def __init__(self):
        """Initialize bridge."""
        self._adapters: dict[str, AIProtocolAdapter] = {}
        self._routes: dict[str, list[str]] = {}
        self._transformers: dict[tuple, Callable] = {}

    def register_adapter(self, name: str, adapter: AIProtocolAdapter) -> None:
        """Register a protocol adapter."""
        self._adapters[name] = adapter

    def add_route(self, from_adapter: str, to_adapters: list[str]) -> None:
        """Add routing rule."""
        self._routes[from_adapter] = to_adapters

    def register_transformer(
        self,
        from_protocol: ProtocolType,
        to_protocol: ProtocolType,
        transformer: Callable[[Message], Message],
    ) -> None:
        """Register message transformer between protocols."""
        self._transformers[(from_protocol, to_protocol)] = transformer

    async def start(self) -> None:
        """Start the bridge."""
        # Connect all adapters
        for adapter in self._adapters.values():
            if not adapter.is_connected():
                await adapter.connect()

        # Start message routing
        tasks = []
        for name, adapter in self._adapters.items():
            task = asyncio.create_task(self._route_messages(name, adapter))
            tasks.append(task)

        # Wait for all routing tasks
        await asyncio.gather(*tasks)

    async def stop(self) -> None:
        """Stop the bridge."""
        for adapter in self._adapters.values():
            if adapter.is_connected():
                await adapter.disconnect()

    async def _route_messages(
        self, adapter_name: str, adapter: AIProtocolAdapter
    ) -> None:
        """Route messages from one adapter to others."""
        while adapter.is_connected():
            try:
                message = await adapter.receive()
                if message and adapter_name in self._routes:
                    # Route to configured destinations
                    for dest_name in self._routes[adapter_name]:
                        if dest_name in self._adapters:
                            dest_adapter = self._adapters[dest_name]
                            # Transform message if needed
                            transformed = await self._transform_message(
                                message,
                                adapter.protocol_type,
                                dest_adapter.protocol_type,
                            )
                            await dest_adapter.send(transformed)
            except Exception:
                # Continue on errors
                await asyncio.sleep(0.1)

    async def _transform_message(
        self, message: Message, from_protocol: ProtocolType, to_protocol: ProtocolType
    ) -> Message:
        """Transform message between protocols."""
        key = (from_protocol, to_protocol)
        if key in self._transformers:
            transformer = self._transformers[key]
            if asyncio.iscoroutinefunction(transformer):
                return await transformer(message)
            else:
                return transformer(message)
        return message


class ProtocolRegistry:
    """Registry for protocol adapters."""

    _adapters: dict[ProtocolType, type[BaseAIProtocolAdapter]] = {}

    @classmethod
    def register(
        cls, protocol_type: ProtocolType, adapter_class: type[BaseAIProtocolAdapter]
    ) -> None:
        """Register an adapter class."""
        cls._adapters[protocol_type] = adapter_class

    @classmethod
    def create(cls, config: ProtocolConfig) -> BaseAIProtocolAdapter:
        """Create adapter instance."""
        if config.protocol_type not in cls._adapters:
            raise ValueError(f"Unknown protocol type: {config.protocol_type}")

        adapter_class = cls._adapters[config.protocol_type]
        return adapter_class(config)

    @classmethod
    def list_protocols(cls) -> list[ProtocolType]:
        """List registered protocols."""
        return list(cls._adapters.keys())
