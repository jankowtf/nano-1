"""
AI reasoning skill for nanobricks.

Adds AI-powered reasoning, memory management, and cost tracking to nanobricks.
"""

import asyncio
import json
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Protocol, runtime_checkable

from nanobricks.protocol import NanobrickProtocol
from nanobricks.skill import NanobrickEnhanced, Skill


@dataclass
class ModelConfig:
    """Configuration for an AI model."""

    name: str
    provider: str  # openai, anthropic, etc.
    max_tokens: int = 1000
    temperature: float = 0.7
    cost_per_1k_input: float = 0.0
    cost_per_1k_output: float = 0.0
    supports_functions: bool = False
    supports_vision: bool = False


@dataclass
class ReasoningTrace:
    """A single step in the reasoning process."""

    timestamp: datetime
    thought: str
    action: str | None = None
    observation: str | None = None
    confidence: float = 1.0


@dataclass
class AIMemory:
    """Memory storage for AI-enhanced bricks."""

    short_term: list[dict[str, Any]] = field(default_factory=list)
    long_term: dict[str, Any] = field(default_factory=dict)
    reasoning_traces: list[ReasoningTrace] = field(default_factory=list)
    total_tokens_used: int = 0
    total_cost: float = 0.0

    def add_trace(self, trace: ReasoningTrace):
        """Add a reasoning trace."""
        self.reasoning_traces.append(trace)
        # Keep only last 100 traces in memory
        if len(self.reasoning_traces) > 100:
            self.reasoning_traces = self.reasoning_traces[-100:]

    def add_short_term(self, item: dict[str, Any]):
        """Add to short-term memory."""
        self.short_term.append(item)
        # Keep only last 20 items
        if len(self.short_term) > 20:
            self.short_term = self.short_term[-20:]

    def store_long_term(self, key: str, value: Any):
        """Store in long-term memory."""
        self.long_term[key] = value

    def recall(self, key: str) -> Any | None:
        """Recall from long-term memory."""
        return self.long_term.get(key)


@runtime_checkable
class AIProvider(Protocol):
    """Protocol for AI providers."""

    async def complete(
        self,
        prompt: str,
        model: str,
        max_tokens: int = 1000,
        temperature: float = 0.7,
        **kwargs,
    ) -> dict[str, Any]:
        """Complete a prompt and return response with token counts."""
        ...


class SkillAI(Skill):
    """
    AI reasoning skill for enhancing nanobricks with intelligence.

    Features:
    - Multi-model support
    - Reasoning traces
    - Memory management
    - Cost tracking
    - Adaptive model selection
    """

    def __init__(
        self,
        models: list[ModelConfig] | None = None,
        default_model: str | None = None,
        max_cost_per_invoke: float = 0.10,
        enable_reasoning_trace: bool = True,
        enable_memory: bool = True,
        provider: AIProvider | None = None,
    ):
        """Initialize AI skill.

        Args:
            models: List of available models
            default_model: Default model to use
            max_cost_per_invoke: Maximum cost allowed per invoke
            enable_reasoning_trace: Enable reasoning trace capture
            enable_memory: Enable memory management
            provider: AI provider implementation
        """
        super().__init__()

        # Default models if none provided
        self.models = models or [
            ModelConfig(
                name="gpt-4o-mini",
                provider="openai",
                max_tokens=4096,
                temperature=0.7,
                cost_per_1k_input=0.00015,
                cost_per_1k_output=0.0006,
                supports_functions=True,
            ),
            ModelConfig(
                name="claude-3-haiku",
                provider="anthropic",
                max_tokens=4096,
                temperature=0.7,
                cost_per_1k_input=0.00025,
                cost_per_1k_output=0.00125,
            ),
        ]

        self.model_map = {m.name: m for m in self.models}
        self.default_model = default_model or self.models[0].name
        self.max_cost_per_invoke = max_cost_per_invoke
        self.enable_reasoning_trace = enable_reasoning_trace
        self.enable_memory = enable_memory
        self.provider = provider

        # Global memory across all enhanced bricks
        self.global_memory = AIMemory()

    def _create_enhanced_brick(self, brick: NanobrickProtocol) -> NanobrickProtocol:
        """Create AI-enhanced brick."""
        skill = self

        class AINanobrickEnhanced(NanobrickEnhanced):
            """Brick enhanced with AI reasoning."""

            def __init__(self, wrapped: NanobrickProtocol, parent_skill: Skill):
                super().__init__(wrapped, parent_skill)
                self.memory = AIMemory() if skill.enable_memory else None
                self._last_reasoning: list[ReasoningTrace] | None = None

            async def invoke(self, input: Any, *, deps: dict | None = None) -> Any:
                """Invoke with AI enhancement."""
                start_time = time.time()

                # Check if we should use AI for this input
                if not self._should_use_ai(input):
                    return await self._wrapped.invoke(input, deps=deps)

                # Select best model for the task
                model_name = await self._select_model(input)
                model = skill.model_map[model_name]

                # Build context from memory
                context = self._build_context(input)

                # Generate reasoning trace
                if skill.enable_reasoning_trace:
                    trace = ReasoningTrace(
                        timestamp=datetime.now(),
                        thought=f"Processing input with {model_name}",
                        action="analyze_input",
                    )
                    if self.memory:
                        self.memory.add_trace(trace)

                try:
                    # Prepare enhanced input
                    enhanced_input = await self._enhance_input(input, context, model)

                    # Invoke wrapped brick
                    result = await self._wrapped.invoke(enhanced_input, deps=deps)

                    # Post-process with AI if needed
                    final_result = await self._enhance_output(result, input, model)

                    # Update memory
                    if self.memory:
                        self.memory.add_short_term(
                            {
                                "input": input,
                                "output": final_result,
                                "duration": time.time() - start_time,
                                "model": model_name,
                            }
                        )

                    return final_result

                except Exception as e:
                    # AI-powered error recovery
                    return await self._handle_error_with_ai(e, input, model)

            def _should_use_ai(self, input: Any) -> bool:
                """Determine if AI should be used for this input."""
                # Check cost budget
                if skill.global_memory.total_cost >= skill.max_cost_per_invoke * 0.9:
                    return False

                # Check input complexity (simple heuristic)
                if isinstance(input, (str, dict, list)):
                    complexity = len(str(input))
                    return complexity > 50  # Use AI for complex inputs

                return True

            async def _select_model(self, input: Any) -> str:
                """Select the best model for the input."""
                # Simple selection based on input type and size
                input_size = len(str(input))

                # For small inputs, use cheaper model
                if input_size < 500:
                    for model in skill.models:
                        if "haiku" in model.name or "mini" in model.name:
                            return model.name

                # For complex tasks, use more capable model
                return skill.default_model

            def _build_context(self, input: Any) -> dict[str, Any]:
                """Build context from memory."""
                context = {
                    "current_input": input,
                    "brick_name": self._wrapped.name,
                }

                if self.memory:
                    # Add recent interactions
                    context["recent_interactions"] = self.memory.short_term[-5:]

                    # Add relevant long-term memory
                    input_key = str(input)[:50]  # Simple key generation
                    if input_key in self.memory.long_term:
                        context["previous_result"] = self.memory.long_term[input_key]

                return context

            async def _enhance_input(
                self, input: Any, context: dict[str, Any], model: ModelConfig
            ) -> Any:
                """Enhance input using AI."""
                if not skill.provider:
                    # No AI provider, pass through
                    return input

                # Build prompt for input enhancement
                prompt = self._build_enhancement_prompt(input, context)

                # Get AI completion
                response = await skill.provider.complete(
                    prompt=prompt,
                    model=model.name,
                    max_tokens=model.max_tokens,
                    temperature=model.temperature,
                )

                # Track costs
                self._track_costs(response, model)

                # Parse enhanced input
                try:
                    enhanced = json.loads(response["content"])
                    return enhanced.get("enhanced_input", input)
                except:
                    return input

            async def _enhance_output(
                self, output: Any, original_input: Any, model: ModelConfig
            ) -> Any:
                """Enhance output using AI."""
                # For now, just pass through
                # Could add output validation, formatting, etc.
                return output

            async def _handle_error_with_ai(
                self, error: Exception, input: Any, model: ModelConfig
            ) -> Any:
                """Use AI to recover from errors."""
                if not skill.provider:
                    raise error

                prompt = f"""
                An error occurred while processing input in {self._wrapped.name}:
                
                Error: {str(error)}
                Input: {json.dumps(input) if isinstance(input, (dict, list)) else str(input)}
                
                Suggest a recovery strategy or alternative output.
                """

                try:
                    response = await skill.provider.complete(
                        prompt=prompt,
                        model=model.name,
                        max_tokens=500,
                        temperature=0.5,
                    )

                    # Track costs
                    self._track_costs(response, model)

                    # Try to parse recovery suggestion
                    content = response["content"]
                    if "FALLBACK:" in content:
                        fallback = content.split("FALLBACK:")[1].strip()
                        return (
                            json.loads(fallback)
                            if fallback.startswith("{")
                            else fallback
                        )

                except:
                    pass

                # Re-raise original error if recovery fails
                raise error

            def _build_enhancement_prompt(
                self, input: Any, context: dict[str, Any]
            ) -> str:
                """Build prompt for input enhancement."""
                return f"""
                You are enhancing input for a nanobrick called '{self._wrapped.name}'.
                
                Current input: {json.dumps(input) if isinstance(input, (dict, list)) else str(input)}
                
                Context:
                - Brick purpose: {self._wrapped.__doc__ or "Process data"}
                - Recent interactions: {len(context.get("recent_interactions", []))} available
                
                Analyze the input and provide an enhanced version that will work better
                with this brick. Return a JSON object with 'enhanced_input' key.
                
                Example: {{"enhanced_input": {{"processed": true, "data": ...}}}}
                """

            def _track_costs(self, response: dict[str, Any], model: ModelConfig):
                """Track token usage and costs."""
                input_tokens = response.get("input_tokens", 0)
                output_tokens = response.get("output_tokens", 0)

                input_cost = (input_tokens / 1000) * model.cost_per_1k_input
                output_cost = (output_tokens / 1000) * model.cost_per_1k_output
                total_cost = input_cost + output_cost

                skill.global_memory.total_tokens_used += input_tokens + output_tokens
                skill.global_memory.total_cost += total_cost

                if self.memory:
                    self.memory.total_tokens_used += input_tokens + output_tokens
                    self.memory.total_cost += total_cost

            def get_reasoning_trace(self) -> list[ReasoningTrace] | None:
                """Get the reasoning trace for the last invocation."""
                if self.memory:
                    return self.memory.reasoning_traces
                return None

            def get_memory_stats(self) -> dict[str, Any]:
                """Get memory statistics."""
                if not self.memory:
                    return {}

                return {
                    "short_term_items": len(self.memory.short_term),
                    "long_term_keys": len(self.memory.long_term),
                    "reasoning_traces": len(self.memory.reasoning_traces),
                    "total_tokens": self.memory.total_tokens_used,
                    "total_cost": round(self.memory.total_cost, 4),
                }

        return AINanobrickEnhanced(brick, self)

    def get_cost_report(self) -> dict[str, Any]:
        """Get cost tracking report."""
        return {
            "total_tokens": self.global_memory.total_tokens_used,
            "total_cost": round(self.global_memory.total_cost, 4),
            "cost_limit": self.max_cost_per_invoke,
            "cost_remaining": round(
                self.max_cost_per_invoke - self.global_memory.total_cost, 4
            ),
        }

    def reset_costs(self):
        """Reset cost tracking."""
        self.global_memory.total_tokens_used = 0
        self.global_memory.total_cost = 0.0


# Example AI provider implementations
class MockAIProvider:
    """Mock AI provider for testing."""

    async def complete(
        self,
        prompt: str,
        model: str,
        max_tokens: int = 1000,
        temperature: float = 0.7,
        **kwargs,
    ) -> dict[str, Any]:
        """Mock completion."""
        # Simulate some processing time
        await asyncio.sleep(0.1)

        # Return mock response
        return {
            "content": '{"enhanced_input": ' + json.dumps({"enhanced": True}) + "}",
            "input_tokens": len(prompt.split()),
            "output_tokens": 20,
        }


def create_ai_skill(provider: AIProvider | None = None, **kwargs) -> SkillAI:
    """Create an AI skill with optional provider."""
    return SkillAI(provider=provider or MockAIProvider(), **kwargs)
