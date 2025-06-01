"""AI reasoning trace and step-by-step thinking support."""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any
import uuid


class ReasoningStepType(Enum):
    """Types of reasoning steps."""

    OBSERVATION = "observation"
    HYPOTHESIS = "hypothesis"
    ANALYSIS = "analysis"
    CONCLUSION = "conclusion"
    QUESTION = "question"
    ASSUMPTION = "assumption"
    VALIDATION = "validation"
    DECISION = "decision"
    ACTION = "action"


@dataclass
class ReasoningStep:
    """A single step in the reasoning process."""

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    type: ReasoningStepType = ReasoningStepType.OBSERVATION
    content: str = ""
    confidence: float = 1.0  # 0.0 to 1.0
    evidence: list[str] = field(default_factory=list)
    alternatives: list[str] = field(default_factory=list)
    parent_id: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.utcnow)

    def add_evidence(self, evidence: str) -> None:
        """Add supporting evidence."""
        self.evidence.append(evidence)

    def add_alternative(self, alternative: str) -> None:
        """Add alternative consideration."""
        self.alternatives.append(alternative)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "type": self.type.value,
            "content": self.content,
            "confidence": self.confidence,
            "evidence": self.evidence,
            "alternatives": self.alternatives,
            "parent_id": self.parent_id,
            "metadata": self.metadata,
            "timestamp": self.timestamp.isoformat(),
        }


@dataclass
class ReasoningTrace:
    """Complete reasoning trace for a problem."""

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    problem: str = ""
    steps: list[ReasoningStep] = field(default_factory=list)
    conclusion: str | None = None
    confidence: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)
    created: datetime = field(default_factory=datetime.utcnow)
    completed: datetime | None = None

    def add_step(
        self,
        step_type: ReasoningStepType,
        content: str,
        confidence: float = 1.0,
        parent_id: str | None = None,
        **kwargs,
    ) -> ReasoningStep:
        """Add a reasoning step."""
        step = ReasoningStep(
            type=step_type,
            content=content,
            confidence=confidence,
            parent_id=parent_id,
            **kwargs,
        )
        self.steps.append(step)
        return step

    def observe(self, observation: str, confidence: float = 1.0) -> ReasoningStep:
        """Add an observation."""
        return self.add_step(ReasoningStepType.OBSERVATION, observation, confidence)

    def hypothesize(self, hypothesis: str, confidence: float = 0.8) -> ReasoningStep:
        """Add a hypothesis."""
        return self.add_step(ReasoningStepType.HYPOTHESIS, hypothesis, confidence)

    def analyze(self, analysis: str, confidence: float = 0.9) -> ReasoningStep:
        """Add analysis."""
        return self.add_step(ReasoningStepType.ANALYSIS, analysis, confidence)

    def question(self, question: str) -> ReasoningStep:
        """Add a question to explore."""
        return self.add_step(ReasoningStepType.QUESTION, question, 0.5)

    def assume(self, assumption: str, confidence: float = 0.7) -> ReasoningStep:
        """Add an assumption."""
        return self.add_step(ReasoningStepType.ASSUMPTION, assumption, confidence)

    def validate(self, validation: str, confidence: float = 0.9) -> ReasoningStep:
        """Add validation."""
        return self.add_step(ReasoningStepType.VALIDATION, validation, confidence)

    def decide(self, decision: str, confidence: float = 0.85) -> ReasoningStep:
        """Add a decision."""
        return self.add_step(ReasoningStepType.DECISION, decision, confidence)

    def conclude(self, conclusion: str, confidence: float = 0.9) -> None:
        """Set the conclusion."""
        self.conclusion = conclusion
        self.confidence = confidence
        self.completed = datetime.utcnow()
        # Also add as a step
        self.add_step(ReasoningStepType.CONCLUSION, conclusion, confidence)

    def get_path(self, step_id: str) -> list[ReasoningStep]:
        """Get the path to a specific step."""
        step_map = {step.id: step for step in self.steps}
        path = []

        current = step_map.get(step_id)
        while current:
            path.insert(0, current)
            current = step_map.get(current.parent_id) if current.parent_id else None

        return path

    def get_confidence_range(self) -> tuple[float, float]:
        """Get min and max confidence across all steps."""
        if not self.steps:
            return (0.0, 0.0)

        confidences = [step.confidence for step in self.steps]
        return (min(confidences), max(confidences))

    def get_summary(self) -> dict[str, Any]:
        """Get trace summary."""
        step_counts = {}
        for step in self.steps:
            step_type = step.type.value
            step_counts[step_type] = step_counts.get(step_type, 0) + 1

        min_conf, max_conf = self.get_confidence_range()

        return {
            "id": self.id,
            "problem": self.problem,
            "conclusion": self.conclusion,
            "overall_confidence": self.confidence,
            "step_count": len(self.steps),
            "step_types": step_counts,
            "confidence_range": {"min": min_conf, "max": max_conf},
            "duration": (
                (self.completed - self.created).total_seconds()
                if self.completed
                else None
            ),
        }

    def to_markdown(self) -> str:
        """Convert trace to markdown format."""
        lines = [
            f"# Reasoning Trace: {self.problem}",
            f"\n**Created**: {self.created.isoformat()}",
            "",
        ]

        # Add steps
        for i, step in enumerate(self.steps, 1):
            emoji = {
                ReasoningStepType.OBSERVATION: "👁️",
                ReasoningStepType.HYPOTHESIS: "💡",
                ReasoningStepType.ANALYSIS: "🔍",
                ReasoningStepType.CONCLUSION: "✅",
                ReasoningStepType.QUESTION: "❓",
                ReasoningStepType.ASSUMPTION: "💭",
                ReasoningStepType.VALIDATION: "✓",
                ReasoningStepType.DECISION: "🎯",
                ReasoningStepType.ACTION: "⚡",
            }.get(step.type, "•")

            lines.append(f"## {i}. {emoji} {step.type.value.title()}")
            lines.append(f"\n{step.content}")
            lines.append(f"\n*Confidence: {step.confidence:.0%}*")

            if step.evidence:
                lines.append("\n**Evidence:**")
                for evidence in step.evidence:
                    lines.append(f"- {evidence}")

            if step.alternatives:
                lines.append("\n**Alternatives considered:**")
                for alt in step.alternatives:
                    lines.append(f"- {alt}")

            lines.append("")

        # Add conclusion
        if self.conclusion:
            lines.append("## 🎯 Conclusion")
            lines.append(f"\n{self.conclusion}")
            lines.append(f"\n*Overall Confidence: {self.confidence:.0%}*")

            if self.completed:
                duration = (self.completed - self.created).total_seconds()
                lines.append(f"\n*Reasoning completed in {duration:.1f} seconds*")

        return "\n".join(lines)


class ReasoningTracer:
    """Manages reasoning traces."""

    def __init__(self):
        """Initialize tracer."""
        self._traces: dict[str, ReasoningTrace] = {}
        self._active_trace: ReasoningTrace | None = None

    def start_trace(self, problem: str, **metadata) -> ReasoningTrace:
        """Start a new reasoning trace."""
        trace = ReasoningTrace(problem=problem, metadata=metadata)
        self._traces[trace.id] = trace
        self._active_trace = trace
        return trace

    def get_trace(self, trace_id: str) -> ReasoningTrace | None:
        """Get a specific trace."""
        return self._traces.get(trace_id)

    def get_active_trace(self) -> ReasoningTrace | None:
        """Get the currently active trace."""
        return self._active_trace

    def set_active_trace(self, trace_id: str) -> None:
        """Set the active trace."""
        self._active_trace = self._traces.get(trace_id)

    def list_traces(self) -> list[dict[str, Any]]:
        """List all traces."""
        return [trace.get_summary() for trace in self._traces.values()]

    def clear_traces(self) -> None:
        """Clear all traces."""
        self._traces.clear()
        self._active_trace = None


# Chain of Thought utilities
class ChainOfThought:
    """Utilities for chain-of-thought reasoning."""

    @staticmethod
    def format_cot_prompt(
        problem: str, examples: list[tuple[str, str]] | None = None
    ) -> str:
        """Format a chain-of-thought prompt."""
        prompt_parts = []

        # Add examples if provided
        if examples:
            prompt_parts.append("Here are some examples of step-by-step reasoning:\n")
            for i, (example_problem, example_solution) in enumerate(examples, 1):
                prompt_parts.append(f"Example {i}:")
                prompt_parts.append(f"Problem: {example_problem}")
                prompt_parts.append(f"Solution: {example_solution}")
                prompt_parts.append("")

        # Add the actual problem
        prompt_parts.append("Now, let's solve this problem step by step:")
        prompt_parts.append(f"Problem: {problem}")
        prompt_parts.append("\nLet me think through this systematically:")

        return "\n".join(prompt_parts)

    @staticmethod
    def extract_steps_from_text(text: str) -> list[str]:
        """Extract reasoning steps from text."""
        steps = []

        # Look for numbered steps
        import re

        numbered_pattern = (
            r"(?:^|\n)\s*(?:\d+\.?|Step \d+:?)\s*(.+?)(?=\n\s*(?:\d+\.?|Step \d+:|$))"
        )
        numbered_matches = re.findall(numbered_pattern, text, re.MULTILINE | re.DOTALL)
        if numbered_matches:
            steps.extend([match.strip() for match in numbered_matches])
            return steps

        # Look for bullet points
        bullet_pattern = r"(?:^|\n)\s*[-•*]\s*(.+?)(?=\n\s*[-•*]|\n\n|$)"
        bullet_matches = re.findall(bullet_pattern, text, re.MULTILINE)
        if bullet_matches:
            steps.extend([match.strip() for match in bullet_matches])
            return steps

        # Fall back to paragraph splitting
        paragraphs = text.strip().split("\n\n")
        steps = [p.strip() for p in paragraphs if p.strip()]

        return steps

    @staticmethod
    def create_trace_from_text(problem: str, reasoning_text: str) -> ReasoningTrace:
        """Create a reasoning trace from text output."""
        trace = ReasoningTrace(problem=problem)
        steps = ChainOfThought.extract_steps_from_text(reasoning_text)

        # Classify each step
        for step_text in steps:
            step_lower = step_text.lower()

            # Determine step type based on content
            if any(word in step_lower for word in ["observe", "notice", "see", "find"]):
                step_type = ReasoningStepType.OBSERVATION
            elif any(
                word in step_lower
                for word in ["hypothesis", "might", "could be", "possibly"]
            ):
                step_type = ReasoningStepType.HYPOTHESIS
            elif any(
                word in step_lower
                for word in ["analyze", "examine", "consider", "look at"]
            ):
                step_type = ReasoningStepType.ANALYSIS
            elif any(
                word in step_lower
                for word in ["conclude", "therefore", "thus", "finally"]
            ):
                step_type = ReasoningStepType.CONCLUSION
            elif "?" in step_text:
                step_type = ReasoningStepType.QUESTION
            elif any(word in step_lower for word in ["assume", "suppose", "let's say"]):
                step_type = ReasoningStepType.ASSUMPTION
            elif any(
                word in step_lower
                for word in ["validate", "verify", "check", "confirm"]
            ):
                step_type = ReasoningStepType.VALIDATION
            elif any(word in step_lower for word in ["decide", "choose", "select"]):
                step_type = ReasoningStepType.DECISION
            else:
                step_type = ReasoningStepType.ANALYSIS

            trace.add_step(step_type, step_text)

        # Extract conclusion if present
        if steps and any(
            word in steps[-1].lower() for word in ["conclude", "therefore", "thus"]
        ):
            trace.conclude(steps[-1], 0.85)

        return trace
