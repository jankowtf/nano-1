"""Generic AI interface for provider-agnostic AI integration."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Protocol, runtime_checkable
import uuid


class MessageRole(Enum):
    """Standard message roles for AI conversations."""

    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    FUNCTION = "function"
    TOOL = "tool"


class ModelCapability(Enum):
    """AI model capabilities."""

    TEXT_GENERATION = "text_generation"
    CHAT = "chat"
    EMBEDDINGS = "embeddings"
    FUNCTION_CALLING = "function_calling"
    VISION = "vision"
    AUDIO = "audio"
    CODE_GENERATION = "code_generation"
    REASONING = "reasoning"


@dataclass
class AIMessage:
    """Generic AI message."""

    role: MessageRole
    content: str
    name: str | None = None
    function_call: dict[str, Any] | None = None
    tool_calls: list[dict[str, Any]] | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        data = {
            "role": self.role.value,
            "content": self.content,
        }
        if self.name:
            data["name"] = self.name
        if self.function_call:
            data["function_call"] = self.function_call
        if self.tool_calls:
            data["tool_calls"] = self.tool_calls
        if self.metadata:
            data["metadata"] = self.metadata
        return data


@dataclass
class AIRequest:
    """Generic AI request."""

    messages: list[AIMessage]
    model: str | None = None
    temperature: float = 0.7
    max_tokens: int | None = None
    top_p: float = 1.0
    frequency_penalty: float = 0.0
    presence_penalty: float = 0.0
    stop: list[str] | None = None
    functions: list[dict[str, Any]] | None = None
    tools: list[dict[str, Any]] | None = None
    response_format: dict[str, Any] | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def add_message(self, role: MessageRole, content: str, **kwargs) -> None:
        """Add a message to the request."""
        self.messages.append(AIMessage(role=role, content=content, **kwargs))

    def get_conversation_text(self) -> str:
        """Get conversation as text."""
        lines = []
        for msg in self.messages:
            lines.append(f"{msg.role.value}: {msg.content}")
        return "\n".join(lines)


@dataclass
class AIResponse:
    """Generic AI response."""

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    content: str = ""
    role: MessageRole = MessageRole.ASSISTANT
    finish_reason: str | None = None
    function_call: dict[str, Any] | None = None
    tool_calls: list[dict[str, Any]] | None = None
    usage: dict[str, int] | None = None
    model: str | None = None
    created: datetime = field(default_factory=datetime.utcnow)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_message(self) -> AIMessage:
        """Convert response to message."""
        return AIMessage(
            role=self.role,
            content=self.content,
            function_call=self.function_call,
            tool_calls=self.tool_calls,
            metadata=self.metadata,
        )


@dataclass
class ModelInfo:
    """Information about an AI model."""

    id: str
    name: str
    provider: str
    capabilities: set[ModelCapability]
    context_window: int
    max_output_tokens: int | None = None
    cost_per_1k_input: float | None = None
    cost_per_1k_output: float | None = None
    supports_streaming: bool = True
    supports_functions: bool = False
    supports_vision: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def supports_chat(self) -> bool:
        """Check if model supports chat."""
        return ModelCapability.CHAT in self.capabilities

    @property
    def supports_reasoning(self) -> bool:
        """Check if model supports reasoning."""
        return ModelCapability.REASONING in self.capabilities


@runtime_checkable
class AIProvider(Protocol):
    """Protocol for AI providers."""

    async def complete(self, request: AIRequest) -> AIResponse:
        """Complete an AI request."""
        ...

    async def stream(self, request: AIRequest):
        """Stream AI response."""
        ...

    def list_models(self) -> list[ModelInfo]:
        """List available models."""
        ...

    def get_model_info(self, model_id: str) -> ModelInfo | None:
        """Get information about a model."""
        ...


class BaseAIProvider(ABC):
    """Base class for AI providers."""

    def __init__(self, api_key: str | None = None, **config):
        """Initialize provider."""
        self.api_key = api_key
        self.config = config
        self._models: dict[str, ModelInfo] = {}

    @abstractmethod
    async def complete(self, request: AIRequest) -> AIResponse:
        """Complete an AI request."""
        pass

    async def stream(self, request: AIRequest):
        """Stream AI response."""
        # Default implementation - just yield complete response
        response = await self.complete(request)
        yield response

    def list_models(self) -> list[ModelInfo]:
        """List available models."""
        return list(self._models.values())

    def get_model_info(self, model_id: str) -> ModelInfo | None:
        """Get information about a model."""
        return self._models.get(model_id)

    def validate_request(self, request: AIRequest) -> None:
        """Validate request before sending."""
        if not request.messages:
            raise ValueError("Request must have at least one message")

        # Check model if specified
        if request.model and request.model not in self._models:
            raise ValueError(f"Unknown model: {request.model}")

        # Validate token limits
        if request.model:
            model = self._models[request.model]
            if request.max_tokens and request.max_tokens > (
                model.max_output_tokens or float("inf")
            ):
                raise ValueError(
                    f"Max tokens exceeds model limit: {model.max_output_tokens}"
                )


class AIProviderRegistry:
    """Registry for AI providers."""

    _providers: dict[str, type[BaseAIProvider]] = {}
    _instances: dict[str, BaseAIProvider] = {}

    @classmethod
    def register(cls, name: str, provider_class: type[BaseAIProvider]) -> None:
        """Register a provider class."""
        cls._providers[name] = provider_class

    @classmethod
    def create(cls, name: str, **config) -> BaseAIProvider:
        """Create provider instance."""
        if name not in cls._providers:
            raise ValueError(f"Unknown provider: {name}")

        # Check if already instantiated
        instance_key = f"{name}:{hash(frozenset(config.items()))}"
        if instance_key not in cls._instances:
            provider_class = cls._providers[name]
            cls._instances[instance_key] = provider_class(**config)

        return cls._instances[instance_key]

    @classmethod
    def list_providers(cls) -> list[str]:
        """List registered providers."""
        return list(cls._providers.keys())


# Cost tracking utilities
@dataclass
class TokenUsage:
    """Token usage tracking."""

    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0

    def add(self, other: "TokenUsage") -> None:
        """Add another usage to this one."""
        self.prompt_tokens += other.prompt_tokens
        self.completion_tokens += other.completion_tokens
        self.total_tokens += other.total_tokens

    def calculate_cost(self, model_info: ModelInfo) -> float:
        """Calculate cost based on model pricing."""
        if not model_info.cost_per_1k_input or not model_info.cost_per_1k_output:
            return 0.0

        input_cost = (self.prompt_tokens / 1000) * model_info.cost_per_1k_input
        output_cost = (self.completion_tokens / 1000) * model_info.cost_per_1k_output
        return input_cost + output_cost


@dataclass
class CostTracker:
    """Track AI usage costs."""

    usage_by_model: dict[str, TokenUsage] = field(default_factory=dict)
    total_cost: float = 0.0
    request_count: int = 0

    def track_response(self, response: AIResponse, model_info: ModelInfo) -> None:
        """Track a response."""
        if response.usage:
            usage = TokenUsage(
                prompt_tokens=response.usage.get("prompt_tokens", 0),
                completion_tokens=response.usage.get("completion_tokens", 0),
                total_tokens=response.usage.get("total_tokens", 0),
            )

            # Update usage
            if model_info.id not in self.usage_by_model:
                self.usage_by_model[model_info.id] = TokenUsage()
            self.usage_by_model[model_info.id].add(usage)

            # Update cost
            self.total_cost += usage.calculate_cost(model_info)
            self.request_count += 1

    def get_summary(self) -> dict[str, Any]:
        """Get cost summary."""
        return {
            "total_cost": self.total_cost,
            "request_count": self.request_count,
            "usage_by_model": {
                model: {
                    "prompt_tokens": usage.prompt_tokens,
                    "completion_tokens": usage.completion_tokens,
                    "total_tokens": usage.total_tokens,
                }
                for model, usage in self.usage_by_model.items()
            },
        }
