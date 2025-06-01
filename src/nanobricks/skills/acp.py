"""ACP (Agent Communication Protocol) skill for REST-based AI compatibility."""

import asyncio
import uuid
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any
from urllib.parse import urljoin

import aiohttp

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
class RESTEndpoint:
    """REST endpoint configuration."""

    path: str
    method: str = "POST"
    headers: dict[str, str] = field(default_factory=dict)
    auth: dict[str, str] | None = None
    timeout: float = 30.0

    def full_url(self, base_url: str) -> str:
        """Get full URL."""
        return urljoin(base_url, self.path)


@dataclass
class RESTResponse:
    """REST response wrapper."""

    status: int
    data: Any
    headers: dict[str, str]
    timestamp: datetime = field(default_factory=datetime.utcnow)

    @property
    def is_success(self) -> bool:
        """Check if response is successful."""
        return 200 <= self.status < 300

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "status": self.status,
            "data": self.data,
            "headers": self.headers,
            "timestamp": self.timestamp.isoformat(),
        }


class ACPProtocolAdapter(BaseAIProtocolAdapter):
    """ACP protocol adapter for REST-based communication."""

    def __init__(self, config: ProtocolConfig):
        """Initialize ACP adapter."""
        super().__init__(config)
        self._session: aiohttp.ClientSession | None = None
        self._base_url = config.endpoint or "http://localhost:8000"
        self._auth_headers = self._build_auth_headers(config.auth)
        self._endpoints: dict[str, RESTEndpoint] = {}
        self._response_queue: asyncio.Queue = asyncio.Queue()

    def _build_auth_headers(self, auth: dict[str, str] | None) -> dict[str, str]:
        """Build authentication headers."""
        if not auth:
            return {}

        auth_type = auth.get("type", "bearer")
        if auth_type == "bearer":
            token = auth.get("token", "")
            return {"Authorization": f"Bearer {token}"}
        elif auth_type == "api_key":
            key_name = auth.get("key_name", "X-API-Key")
            key_value = auth.get("key_value", "")
            return {key_name: key_value}
        elif auth_type == "basic":
            username = auth.get("username", "")
            password = auth.get("password", "")
            import base64

            creds = base64.b64encode(f"{username}:{password}".encode()).decode()
            return {"Authorization": f"Basic {creds}"}

        return {}

    async def send(self, message: Message) -> None:
        """Send message via REST."""
        if not self._connected:
            raise RuntimeError("Not connected")

        # Determine endpoint
        endpoint_name = message.metadata.get("endpoint", "default")
        endpoint = self._endpoints.get(
            endpoint_name, RESTEndpoint(path="/agent/message")
        )

        # Prepare request
        url = endpoint.full_url(self._base_url)
        headers = {
            **self._auth_headers,
            **endpoint.headers,
            "Content-Type": "application/json",
            "X-Message-ID": message.id,
            "X-Message-Type": message.type,
        }

        # Send request
        try:
            async with self._session.request(
                endpoint.method,
                url,
                json=message.to_dict(),
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=endpoint.timeout),
            ) as response:
                data = (
                    await response.json()
                    if response.content_type == "application/json"
                    else await response.text()
                )

                rest_response = RESTResponse(
                    status=response.status, data=data, headers=dict(response.headers)
                )

                # Queue response for receive
                response_msg = Message(
                    id=str(uuid.uuid4()),
                    type="rest_response",
                    content=rest_response.to_dict(),
                    metadata={"original_message_id": message.id},
                )
                await self._response_queue.put(response_msg)

        except TimeoutError:
            error_msg = Message(
                id=str(uuid.uuid4()),
                type="error",
                content={"error": "Request timeout", "message_id": message.id},
                metadata={"original_message_id": message.id},
            )
            await self._response_queue.put(error_msg)
        except Exception as e:
            error_msg = Message(
                id=str(uuid.uuid4()),
                type="error",
                content={"error": str(e), "message_id": message.id},
                metadata={"original_message_id": message.id},
            )
            await self._response_queue.put(error_msg)

    async def receive(self) -> Message | None:
        """Receive message from queue."""
        if not self._connected:
            return None

        try:
            return await asyncio.wait_for(self._response_queue.get(), timeout=1.0)
        except TimeoutError:
            return None

    async def connect(self) -> None:
        """Connect to REST service."""
        if not self._session:
            self._session = aiohttp.ClientSession()
        self._connected = True

        # Test connection with health check
        try:
            health_endpoint = self._endpoints.get(
                "health", RESTEndpoint(path="/health")
            )
            url = health_endpoint.full_url(self._base_url)
            async with self._session.get(
                url, timeout=aiohttp.ClientTimeout(total=5.0)
            ) as response:
                if response.status != 200:
                    print(f"Warning: Health check returned {response.status}")
        except Exception as e:
            print(f"Warning: Health check failed: {e}")

    async def disconnect(self) -> None:
        """Disconnect from REST service."""
        self._connected = False
        if self._session:
            await self._session.close()
            self._session = None

    def register_endpoint(self, name: str, endpoint: RESTEndpoint) -> None:
        """Register a REST endpoint."""
        self._endpoints[name] = endpoint

    def get_endpoint(self, name: str) -> RESTEndpoint | None:
        """Get registered endpoint."""
        return self._endpoints.get(name)


# Register ACP adapter
ProtocolRegistry.register(ProtocolType.ACP, ACPProtocolAdapter)


class SkillACP(Skill):
    """Agent Communication Protocol skill for REST-based AI integration."""

    def __init__(
        self,
        base_url: str | None = None,
        auth: dict[str, str] | None = None,
        adapter: ACPProtocolAdapter | None = None,
        retry_count: int = 3,
        retry_delay: float = 1.0,
    ):
        """Initialize ACP skill."""
        super().__init__()
        self._base_url = base_url
        self._auth = auth
        self._adapter = adapter
        self._retry_count = retry_count
        self._retry_delay = retry_delay
        self._interceptors: list[Callable[[Message], Message]] = []
        self._response_handlers: dict[str, Callable[[RESTResponse], Any]] = {}

    def _create_enhanced_brick(self, brick: NanobrickBase) -> NanobrickEnhanced:
        """Create enhanced brick with ACP capabilities."""

        class ACPNanobrickEnhanced(NanobrickEnhanced):
            """Brick enhanced with REST API communication."""

            def __init__(self, wrapped: NanobrickBase, skill: SkillACP):
                """Initialize enhanced brick."""
                super().__init__(wrapped, skill)
                self._acp_skill = skill

            async def invoke(self, input: Any, *, deps: dict | None = None) -> Any:
                """Invoke with ACP capabilities."""
                # Connect if not connected
                if (
                    not self._acp_skill._adapter
                    or not self._acp_skill._adapter.is_connected()
                ):
                    await self._acp_skill.connect()

                # Process input
                result = await self.wrapped.invoke(input, deps=deps)

                # Send result to API if configured
                if (
                    hasattr(self._acp_skill, "_auto_sync")
                    and self._acp_skill._auto_sync
                ):
                    await self._acp_skill.sync_result(result)

                return result

            def invoke_sync(self, input: Any, *, deps: dict | None = None) -> Any:
                """Sync invoke."""
                return asyncio.run(self.invoke(input, deps=deps))

            async def call_api(
                self,
                endpoint: str,
                data: Any,
                method: str = "POST",
                headers: dict[str, str] | None = None,
            ) -> RESTResponse:
                """Call REST API endpoint."""
                return await self._acp_skill.call_api(endpoint, data, method, headers)

            def register_endpoint(self, name: str, endpoint: RESTEndpoint) -> None:
                """Register API endpoint."""
                self._acp_skill.register_endpoint(name, endpoint)

            def add_interceptor(
                self, interceptor: Callable[[Message], Message]
            ) -> None:
                """Add message interceptor."""
                self._acp_skill.add_interceptor(interceptor)

            def on_response(
                self, message_type: str, handler: Callable[[RESTResponse], Any]
            ) -> None:
                """Register response handler."""
                self._acp_skill.on_response(message_type, handler)

            async def stream_to_api(
                self, endpoint: str, data_stream: asyncio.Queue, batch_size: int = 10
            ) -> None:
                """Stream data to API in batches."""
                await self._acp_skill.stream_to_api(endpoint, data_stream, batch_size)

        return ACPNanobrickEnhanced(brick, self)

    async def connect(self) -> None:
        """Connect to REST API."""
        # Create adapter if not provided
        if not self._adapter:
            config = ProtocolConfig(
                protocol_type=ProtocolType.ACP,
                endpoint=self._base_url,
                auth=self._auth,
                retry_count=self._retry_count,
            )
            self._adapter = ProtocolRegistry.create(config)

        # Connect adapter
        await self._adapter.connect()

    async def disconnect(self) -> None:
        """Disconnect from REST API."""
        if self._adapter:
            await self._adapter.disconnect()

    async def call_api(
        self,
        endpoint: str,
        data: Any,
        method: str = "POST",
        headers: dict[str, str] | None = None,
    ) -> RESTResponse:
        """Call REST API endpoint."""
        # Create message
        message = Message(
            id=str(uuid.uuid4()),
            type="api_call",
            content=data,
            metadata={"endpoint": endpoint, "method": method, "headers": headers or {}},
        )

        # Apply interceptors
        for interceptor in self._interceptors:
            message = interceptor(message)

        # Send with retry
        last_error = None
        for attempt in range(self._retry_count):
            try:
                await self._adapter.send(message)

                # Wait for response
                response_msg = await self._adapter.receive()
                if response_msg and response_msg.type == "rest_response":
                    response = RESTResponse(
                        status=response_msg.content["status"],
                        data=response_msg.content["data"],
                        headers=response_msg.content["headers"],
                    )

                    # Call handlers
                    if message.type in self._response_handlers:
                        handler = self._response_handlers[message.type]
                        if asyncio.iscoroutinefunction(handler):
                            await handler(response)
                        else:
                            handler(response)

                    return response
                elif response_msg and response_msg.type == "error":
                    raise Exception(response_msg.content["error"])

            except Exception as e:
                last_error = e
                if attempt < self._retry_count - 1:
                    await asyncio.sleep(self._retry_delay * (attempt + 1))

        raise last_error or Exception("Failed to get response")

    def register_endpoint(self, name: str, endpoint: RESTEndpoint) -> None:
        """Register API endpoint."""
        if isinstance(self._adapter, ACPProtocolAdapter):
            self._adapter.register_endpoint(name, endpoint)

    def add_interceptor(self, interceptor: Callable[[Message], Message]) -> None:
        """Add message interceptor."""
        self._interceptors.append(interceptor)

    def on_response(
        self, message_type: str, handler: Callable[[RESTResponse], Any]
    ) -> None:
        """Register response handler."""
        self._response_handlers[message_type] = handler

    async def sync_result(self, result: Any) -> None:
        """Sync result to API."""
        await self.call_api(
            "sync", {"result": result, "timestamp": datetime.utcnow().isoformat()}
        )

    async def stream_to_api(
        self, endpoint: str, data_stream: asyncio.Queue, batch_size: int = 10
    ) -> None:
        """Stream data to API in batches."""
        batch = []

        while True:
            try:
                # Collect batch
                while len(batch) < batch_size:
                    try:
                        item = await asyncio.wait_for(data_stream.get(), timeout=1.0)
                        if item is None:  # End of stream
                            break
                        batch.append(item)
                    except TimeoutError:
                        break

                # Send batch if not empty
                if batch:
                    await self.call_api(endpoint, {"batch": batch, "count": len(batch)})
                    batch = []

                # Check if stream ended
                if data_stream.empty():
                    await asyncio.sleep(0.1)
                    if data_stream.empty():  # Double check
                        break

            except Exception:
                # Continue on errors
                await asyncio.sleep(1.0)
