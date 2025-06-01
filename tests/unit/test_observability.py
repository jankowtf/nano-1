"""Tests for observability skill."""

from typing import Any

import pytest

from nanobricks.protocol import NanobrickBase
from nanobricks.skills.observability import (
    ObservabilityConfig,
    SkillObservability,
    SkillTracing,
)


class NanobrickSimple(NanobrickBase[int, int, None]):
    """Test brick for observability."""

    def __init__(self):
        self.name = "NanobrickSimple"
        self.version = "1.0.0"

    async def invoke(self, input: int, *, deps: None = None) -> int:
        return input * 2


class ErrorNanobrick(NanobrickBase[Any, Any, None]):
    """Test brick that always errors."""

    def __init__(self):
        self.name = "ErrorBrick"
        self.version = "1.0.0"

    async def invoke(self, input: Any, *, deps: None = None) -> Any:
        raise ValueError("Test error")


@pytest.mark.asyncio
class TestSkillTracing:
    """Tests for lightweight tracing skill."""

    async def test_basic_tracing(self):
        """Test basic trace collection."""
        skill = SkillTracing()
        brick = NanobrickSimple()
        traced_brick = skill.enhance(brick)

        result = await traced_brick.invoke(5)
        assert result == 10

        # Check traces
        assert len(skill.traces) == 2
        assert skill.traces[0]["operation"] == "invoke_start"
        assert skill.traces[0]["nanobrick"] == "NanobrickSimple"
        assert skill.traces[1]["operation"] == "invoke_complete"
        assert "duration_ms" in skill.traces[1]

    async def test_error_tracing(self):
        """Test error trace collection."""
        skill = SkillTracing()
        brick = ErrorNanobrick()
        traced_brick = skill.enhance(brick)

        with pytest.raises(ValueError):
            await traced_brick.invoke("test")

        # Check error trace
        assert len(skill.traces) == 2
        assert skill.traces[1]["operation"] == "invoke_error"
        assert skill.traces[1]["error"] == "Test error"
        assert skill.traces[1]["error_type"] == "ValueError"

    async def test_custom_trace_func(self):
        """Test custom trace function."""
        collected_traces = []

        def custom_trace(operation: str, details: dict[str, Any]):
            collected_traces.append(f"{operation}: {details['nanobrick']}")

        skill = SkillTracing(trace_func=custom_trace)
        brick = NanobrickSimple()
        traced_brick = skill.enhance(brick)

        await traced_brick.invoke(5)

        assert collected_traces == [
            "invoke_start: NanobrickSimple",
            "invoke_complete: NanobrickSimple",
        ]


@pytest.mark.asyncio
class TestSkillObservability:
    """Tests for full observability skill."""

    async def test_basic_observability(self):
        """Test basic observability without OpenTelemetry."""
        # This test works even without OpenTelemetry installed
        config = ObservabilityConfig(
            service_name="test_service",
            enable_tracing=False,  # Disable to avoid OTEL requirement
            enable_metrics=False,
            enable_logging=False,
        )

        skill = SkillObservability(config)
        brick = NanobrickSimple()

        # Should return original brick if OTEL not available
        observable_brick = skill.enhance(brick)

        result = await observable_brick.invoke(5)
        assert result == 10

    async def test_observable_brick_stats(self):
        """Test statistics collection."""
        # Skip if OpenTelemetry is not available
        try:
            from opentelemetry import trace
        except ImportError:
            pytest.skip("OpenTelemetry not installed")

        config = ObservabilityConfig(
            service_name="test_service", enable_tracing=True, enable_metrics=True
        )

        skill = SkillObservability(config)
        brick = NanobrickSimple()
        observable_brick = skill.enhance(brick)

        # Make several invocations
        for i in range(5):
            await observable_brick.invoke(i)

        # Check stats if it's an ObservableBrick
        if hasattr(observable_brick, "get_stats"):
            stats = observable_brick.get_stats()
            assert stats["invocation_count"] == 5
            assert stats["error_count"] == 0
            assert stats["error_rate"] == 0
            assert stats["average_duration_ms"] > 0

    async def test_observable_brick_errors(self):
        """Test error tracking."""
        # Skip if OpenTelemetry is not available
        try:
            from opentelemetry import trace
        except ImportError:
            pytest.skip("OpenTelemetry not installed")

        config = ObservabilityConfig(
            service_name="test_service", enable_tracing=True, enable_metrics=True
        )

        skill = SkillObservability(config)
        brick = ErrorNanobrick()
        observable_brick = skill.enhance(brick)

        # Make invocations that will error
        for i in range(3):
            with pytest.raises(ValueError):
                await observable_brick.invoke(i)

        # Check error stats if it's an ObservableBrick
        if hasattr(observable_brick, "get_stats"):
            stats = observable_brick.get_stats()
            assert stats["invocation_count"] == 3
            assert stats["error_count"] == 3
            assert stats["error_rate"] == 1.0

    async def test_config_custom_attributes(self):
        """Test custom attributes in config."""
        config = ObservabilityConfig(
            service_name="test_service",
            custom_attributes={"environment": "test", "team": "nanobricks"},
        )

        assert config.custom_attributes["environment"] == "test"
        assert config.custom_attributes["team"] == "nanobricks"
