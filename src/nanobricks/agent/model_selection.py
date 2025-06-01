"""Model selection logic for AI tasks."""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from nanobricks.agent.ai_interface import (
    AIRequest,
    ModelCapability,
    ModelInfo,
)


class TaskComplexity(Enum):
    """Task complexity levels."""

    SIMPLE = "simple"
    MODERATE = "moderate"
    COMPLEX = "complex"
    EXPERT = "expert"


class TaskDomain(Enum):
    """Task domains."""

    GENERAL = "general"
    CODING = "coding"
    MATH = "math"
    CREATIVE = "creative"
    ANALYSIS = "analysis"
    TRANSLATION = "translation"
    SUMMARIZATION = "summarization"
    CONVERSATION = "conversation"


@dataclass
class TaskRequirements:
    """Requirements for a task."""

    complexity: TaskComplexity = TaskComplexity.MODERATE
    domain: TaskDomain = TaskDomain.GENERAL
    max_tokens_needed: int | None = None
    capabilities_needed: set[ModelCapability] = field(default_factory=set)
    speed_priority: float = 0.5  # 0 = quality, 1 = speed
    cost_sensitivity: float = 0.5  # 0 = ignore cost, 1 = minimize cost
    reasoning_depth: int = 1  # 1-5, how deep reasoning should go

    def requires_vision(self) -> bool:
        """Check if task requires vision."""
        return ModelCapability.VISION in self.capabilities_needed

    def requires_functions(self) -> bool:
        """Check if task requires function calling."""
        return ModelCapability.FUNCTION_CALLING in self.capabilities_needed

    def requires_reasoning(self) -> bool:
        """Check if task requires reasoning."""
        return (
            ModelCapability.REASONING in self.capabilities_needed
            or self.reasoning_depth > 2
            or self.complexity in [TaskComplexity.COMPLEX, TaskComplexity.EXPERT]
        )


@dataclass
class ModelScore:
    """Score for a model's fitness for a task."""

    model: ModelInfo
    capability_score: float = 0.0
    complexity_score: float = 0.0
    cost_score: float = 0.0
    speed_score: float = 0.0
    overall_score: float = 0.0
    reasons: list[str] = field(default_factory=list)

    def add_reason(self, reason: str) -> None:
        """Add a reason for the score."""
        self.reasons.append(reason)


class ModelSelector:
    """Selects the best model for a task."""

    def __init__(self, available_models: list[ModelInfo]):
        """Initialize selector."""
        self.models = {model.id: model for model in available_models}
        self._complexity_tiers = self._create_complexity_tiers()

    def _create_complexity_tiers(self) -> dict[TaskComplexity, set[str]]:
        """Create model tiers by complexity."""
        tiers = {
            TaskComplexity.SIMPLE: set(),
            TaskComplexity.MODERATE: set(),
            TaskComplexity.COMPLEX: set(),
            TaskComplexity.EXPERT: set(),
        }

        for model in self.models.values():
            # Classify based on capabilities and context window
            if (
                model.context_window >= 100000
                and ModelCapability.REASONING in model.capabilities
            ):
                tiers[TaskComplexity.EXPERT].add(model.id)
                tiers[TaskComplexity.COMPLEX].add(model.id)
            elif model.context_window >= 32000:
                tiers[TaskComplexity.COMPLEX].add(model.id)
                tiers[TaskComplexity.MODERATE].add(model.id)
            elif model.context_window >= 8000:
                tiers[TaskComplexity.MODERATE].add(model.id)
                tiers[TaskComplexity.SIMPLE].add(model.id)
            else:
                tiers[TaskComplexity.SIMPLE].add(model.id)

        return tiers

    def select_model(
        self, requirements: TaskRequirements, request: AIRequest | None = None
    ) -> ModelInfo | None:
        """Select the best model for the requirements."""
        candidates = self._filter_capable_models(requirements)
        if not candidates:
            return None

        # Score each candidate
        scores = []
        for model in candidates:
            score = self._score_model(model, requirements, request)
            scores.append(score)

        # Sort by overall score
        scores.sort(key=lambda s: s.overall_score, reverse=True)

        # Return best model
        return scores[0].model if scores else None

    def rank_models(
        self, requirements: TaskRequirements, request: AIRequest | None = None
    ) -> list[ModelScore]:
        """Rank all suitable models."""
        candidates = self._filter_capable_models(requirements)

        scores = []
        for model in candidates:
            score = self._score_model(model, requirements, request)
            scores.append(score)

        # Sort by overall score
        scores.sort(key=lambda s: s.overall_score, reverse=True)
        return scores

    def _filter_capable_models(self, requirements: TaskRequirements) -> list[ModelInfo]:
        """Filter models that meet basic requirements."""
        candidates = []

        for model in self.models.values():
            # Check capabilities
            if not requirements.capabilities_needed.issubset(model.capabilities):
                continue

            # Check complexity tier
            if model.id not in self._complexity_tiers.get(
                requirements.complexity, set()
            ):
                continue

            # Check context window
            if requirements.max_tokens_needed:
                min_context = (
                    requirements.max_tokens_needed * 2
                )  # Leave room for response
                if model.context_window < min_context:
                    continue

            candidates.append(model)

        return candidates

    def _score_model(
        self,
        model: ModelInfo,
        requirements: TaskRequirements,
        request: AIRequest | None,
    ) -> ModelScore:
        """Score a model for the requirements."""
        score = ModelScore(model=model)

        # Capability score (0-1)
        capability_match = len(requirements.capabilities_needed & model.capabilities)
        total_capabilities = len(requirements.capabilities_needed) or 1
        score.capability_score = capability_match / total_capabilities

        if score.capability_score == 1.0:
            score.add_reason("Perfect capability match")
        elif score.capability_score > 0.8:
            score.add_reason("Good capability match")

        # Complexity score (0-1)
        complexity_scores = {
            TaskComplexity.SIMPLE: 0.25,
            TaskComplexity.MODERATE: 0.5,
            TaskComplexity.COMPLEX: 0.75,
            TaskComplexity.EXPERT: 1.0,
        }
        target_score = complexity_scores[requirements.complexity]

        # Penalize over/under qualified models
        if model.supports_reasoning and requirements.requires_reasoning():
            score.complexity_score = 1.0
            score.add_reason("Supports required reasoning")
        elif (
            model.context_window >= 100000
            and requirements.complexity == TaskComplexity.EXPERT
        ):
            score.complexity_score = 1.0
            score.add_reason("Large context for expert tasks")
        else:
            # Calculate based on context window
            context_score = min(1.0, model.context_window / 100000)
            score.complexity_score = 1.0 - abs(context_score - target_score)

        # Cost score (0-1)
        if model.cost_per_1k_input and model.cost_per_1k_output:
            # Lower cost = higher score
            avg_cost = (model.cost_per_1k_input + model.cost_per_1k_output) / 2
            # Normalize: $0.01 = score 1.0, $0.10 = score 0.1
            score.cost_score = max(0, 1.0 - (avg_cost / 0.1))

            if avg_cost < 0.02:
                score.add_reason("Very cost effective")
            elif avg_cost > 0.05:
                score.add_reason("Higher cost model")
        else:
            score.cost_score = 0.5  # Unknown cost

        # Speed score (0-1)
        # Estimate based on model size (context window as proxy)
        if model.context_window < 10000:
            score.speed_score = 1.0
            score.add_reason("Fast model")
        elif model.context_window < 50000:
            score.speed_score = 0.7
        else:
            score.speed_score = 0.4
            if requirements.speed_priority < 0.3:
                score.add_reason("Large but powerful model")

        # Calculate overall score with weights
        weights = {
            "capability": 0.3,
            "complexity": 0.3,
            "cost": requirements.cost_sensitivity * 0.4,
            "speed": requirements.speed_priority * 0.4,
        }

        # Normalize weights
        total_weight = sum(weights.values())
        weights = {k: v / total_weight for k, v in weights.items()}

        score.overall_score = (
            weights["capability"] * score.capability_score
            + weights["complexity"] * score.complexity_score
            + weights["cost"] * score.cost_score
            + weights["speed"] * score.speed_score
        )

        return score

    def estimate_cost(
        self,
        model: ModelInfo,
        request: AIRequest,
        estimated_output_tokens: int | None = None,
    ) -> float:
        """Estimate cost for a request."""
        if not model.cost_per_1k_input or not model.cost_per_1k_output:
            return 0.0

        # Estimate input tokens (rough approximation)
        input_chars = sum(len(msg.content) for msg in request.messages)
        input_tokens = input_chars / 4  # Rough char-to-token ratio

        # Estimate output tokens
        if estimated_output_tokens is None:
            if request.max_tokens:
                estimated_output_tokens = request.max_tokens * 0.7  # Assume 70% usage
            else:
                estimated_output_tokens = 500  # Default estimate

        input_cost = (input_tokens / 1000) * model.cost_per_1k_input
        output_cost = (estimated_output_tokens / 1000) * model.cost_per_1k_output

        return input_cost + output_cost


class TaskAnalyzer:
    """Analyzes tasks to determine requirements."""

    @staticmethod
    def analyze_request(request: AIRequest) -> TaskRequirements:
        """Analyze an AI request to determine requirements."""
        requirements = TaskRequirements()

        # Analyze message content
        total_length = sum(len(msg.content) for msg in request.messages)
        has_code = any(
            "```" in msg.content or "def " in msg.content for msg in request.messages
        )
        has_math = any(
            any(
                symbol in msg.content
                for symbol in ["∫", "∑", "∏", "√", "equation", "solve"]
            )
            for msg in request.messages
        )

        # Determine complexity
        if total_length > 5000 or len(request.messages) > 10:
            requirements.complexity = TaskComplexity.COMPLEX
        elif total_length > 2000 or len(request.messages) > 5:
            requirements.complexity = TaskComplexity.MODERATE
        else:
            requirements.complexity = TaskComplexity.SIMPLE

        # Determine domain
        if has_code:
            requirements.domain = TaskDomain.CODING
            requirements.capabilities_needed.add(ModelCapability.CODE_GENERATION)
        elif has_math:
            requirements.domain = TaskDomain.MATH
            requirements.capabilities_needed.add(ModelCapability.REASONING)

        # Check for specific needs
        if request.functions or request.tools:
            requirements.capabilities_needed.add(ModelCapability.FUNCTION_CALLING)

        # Estimate token needs
        requirements.max_tokens_needed = request.max_tokens or min(4000, total_length)

        # Check for reasoning keywords
        reasoning_keywords = [
            "think",
            "reason",
            "analyze",
            "explain",
            "why",
            "how",
            "step by step",
            "systematic",
            "logical",
            "deduce",
        ]
        if any(
            keyword in msg.content.lower()
            for msg in request.messages
            for keyword in reasoning_keywords
        ):
            requirements.capabilities_needed.add(ModelCapability.REASONING)
            requirements.reasoning_depth = 3

        return requirements

    @staticmethod
    def suggest_model_config(
        model: ModelInfo, requirements: TaskRequirements
    ) -> dict[str, Any]:
        """Suggest configuration for a model based on requirements."""
        config = {}

        # Temperature based on task
        if requirements.domain == TaskDomain.CODING:
            config["temperature"] = 0.2  # Low for accuracy
        elif requirements.domain == TaskDomain.CREATIVE:
            config["temperature"] = 0.8  # High for creativity
        elif requirements.domain == TaskDomain.MATH:
            config["temperature"] = 0.1  # Very low for precision
        else:
            config["temperature"] = 0.5  # Balanced

        # Max tokens
        if requirements.max_tokens_needed:
            config["max_tokens"] = min(
                requirements.max_tokens_needed, model.max_output_tokens or 4000
            )

        # Top-p for complex tasks
        if requirements.complexity in [TaskComplexity.COMPLEX, TaskComplexity.EXPERT]:
            config["top_p"] = 0.95

        # Response format for structured output
        if requirements.domain in [TaskDomain.CODING, TaskDomain.ANALYSIS]:
            config["response_format"] = {"type": "json_object"}

        return config
