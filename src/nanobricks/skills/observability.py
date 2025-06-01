"""
Observability skill for nanobricks using OpenTelemetry.

Provides distributed tracing, metrics collection, and logging integration.
"""

import time
from collections.abc import Callable
from contextlib import contextmanager
from typing import Any

from nanobricks.protocol import NanobrickProtocol
from nanobricks.skill import NanobrickEnhanced, Skill

# Type imports for better IDE support
try:
    from opentelemetry import metrics, trace
    from opentelemetry.context import Context
    from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import (
        OTLPMetricExporter,
    )
    from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
    from opentelemetry.metrics import Meter
    from opentelemetry.sdk.metrics import MeterProvider
    from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor
    from opentelemetry.trace import Span, Tracer
    from opentelemetry.trace.propagation import set_span_in_context

    HAS_OTEL = True
except ImportError:
    HAS_OTEL = False
    # Create stub types for when OpenTelemetry is not installed
    Tracer = Any
    Span = Any
    Meter = Any
    Context = Any


class ObservabilityConfig:
    """Configuration for observability skill."""

    def __init__(
        self,
        service_name: str = "nanobricks",
        trace_endpoint: str | None = None,
        metric_endpoint: str | None = None,
        export_interval_ms: int = 5000,
        enable_tracing: bool = True,
        enable_metrics: bool = True,
        enable_logging: bool = True,
        custom_attributes: dict[str, Any] | None = None,
    ):
        self.service_name = service_name
        self.trace_endpoint = trace_endpoint or "localhost:4317"
        self.metric_endpoint = metric_endpoint or "localhost:4317"
        self.export_interval_ms = export_interval_ms
        self.enable_tracing = enable_tracing
        self.enable_metrics = enable_metrics
        self.enable_logging = enable_logging
        self.custom_attributes = custom_attributes or {}


class SkillObservability(Skill):
    """
    Adds comprehensive observability to nanobricks.

    Features:
    - Distributed tracing with automatic span creation
    - Metrics collection (counters, histograms, gauges)
    - Trace context propagation
    - Performance monitoring
    - Error tracking
    """

    def __init__(self, config: ObservabilityConfig | None = None):
        self.config = config or ObservabilityConfig()
        self._tracer: Tracer | None = None
        self._meter: Meter | None = None
        self._initialized = False

        # Metrics
        self._invocation_counter = None
        self._duration_histogram = None
        self._error_counter = None
        self._active_invocations = None

        if HAS_OTEL:
            self._initialize_observability()

    def _initialize_observability(self):
        """Initialize OpenTelemetry providers."""
        if self._initialized:
            return

        # Initialize tracing
        if self.config.enable_tracing:
            tracer_provider = TracerProvider()
            trace.set_tracer_provider(tracer_provider)

            # Add OTLP exporter
            otlp_exporter = OTLPSpanExporter(
                endpoint=self.config.trace_endpoint, insecure=True
            )
            span_processor = BatchSpanProcessor(otlp_exporter)
            tracer_provider.add_span_processor(span_processor)

            self._tracer = trace.get_tracer(self.config.service_name, "1.0.0")

        # Initialize metrics
        if self.config.enable_metrics:
            # Create metric exporter
            metric_exporter = OTLPMetricExporter(
                endpoint=self.config.metric_endpoint, insecure=True
            )

            # Create metric reader
            metric_reader = PeriodicExportingMetricReader(
                exporter=metric_exporter,
                export_interval_millis=self.config.export_interval_ms,
            )

            # Create meter provider
            meter_provider = MeterProvider(metric_readers=[metric_reader])
            metrics.set_meter_provider(meter_provider)

            self._meter = metrics.get_meter(self.config.service_name, "1.0.0")

            # Create metrics
            self._invocation_counter = self._meter.create_counter(
                name="nanobrick.invocations",
                description="Number of nanobrick invocations",
                unit="1",
            )

            self._duration_histogram = self._meter.create_histogram(
                name="nanobrick.duration",
                description="Duration of nanobrick invocations",
                unit="ms",
            )

            self._error_counter = self._meter.create_counter(
                name="nanobrick.errors",
                description="Number of nanobrick errors",
                unit="1",
            )

            self._active_invocations = self._meter.create_up_down_counter(
                name="nanobrick.active_invocations",
                description="Number of active nanobrick invocations",
                unit="1",
            )

        self._initialized = True

    def _create_enhanced_brick(self, brick: NanobrickProtocol) -> NanobrickProtocol:
        """Create enhanced brick with observability."""
        if not HAS_OTEL:
            print("Warning: OpenTelemetry not installed. Observability disabled.")
            return brick

        return ObservableBrick(brick, self)


class ObservableBrick(NanobrickEnhanced):
    """Nanobrick enhanced with observability features."""

    def __init__(self, nanobrick: NanobrickProtocol, skill: SkillObservability):
        super().__init__(nanobrick, skill)
        self.skill = skill
        self._invocation_count = 0
        self._error_count = 0
        self._total_duration_ms = 0.0

    def _get_attributes(self, input: Any = None, deps: Any = None) -> dict[str, Any]:
        """Get attributes for telemetry."""
        attributes = {
            "nanobrick.name": self._wrapped.name,
            "nanobrick.version": self._wrapped.version,
            "nanobrick.invocation_count": self._invocation_count,
        }

        # Add custom attributes
        attributes.update(self.skill.config.custom_attributes)

        # Add input type if available
        if input is not None:
            attributes["nanobrick.input_type"] = type(input).__name__

        # Add deps info if available
        if deps is not None:
            attributes["nanobrick.has_deps"] = True
            if hasattr(deps, "__len__"):
                attributes["nanobrick.deps_count"] = len(deps)

        return attributes

    @contextmanager
    def _trace_context(self, operation: str, attributes: dict[str, Any]):
        """Create a trace span context."""
        if self.skill._tracer and self.skill.config.enable_tracing:
            with self.skill._tracer.start_as_current_span(
                f"nanobrick.{operation}", attributes=attributes
            ) as span:
                yield span
        else:
            yield None

    def _record_metrics(
        self, duration_ms: float, success: bool, attributes: dict[str, Any]
    ):
        """Record metrics for the invocation."""
        if not self.skill._meter or not self.skill.config.enable_metrics:
            return

        # Record invocation count
        self.skill._invocation_counter.add(1, attributes)

        # Record duration
        self.skill._duration_histogram.record(duration_ms, attributes)

        # Record errors
        if not success:
            self.skill._error_counter.add(1, attributes)

    async def invoke(self, input: Any, *, deps: Any = None) -> Any:
        """Invoke with observability."""
        self._invocation_count += 1
        attributes = self._get_attributes(input, deps)

        # Record active invocation
        if self.skill._active_invocations:
            self.skill._active_invocations.add(1, attributes)

        start_time = time.time()
        error_occurred = False
        result = None

        try:
            with self._trace_context("invoke", attributes) as span:
                # Add input details to span
                if span and self.skill.config.enable_logging:
                    span.add_event(
                        "invocation_started",
                        attributes={"input_size": str(len(str(input)))},
                    )

                # Execute the inner nanobrick
                result = await self._wrapped.invoke(input, deps=deps)

                # Add output details to span
                if span and self.skill.config.enable_logging:
                    span.add_event(
                        "invocation_completed",
                        attributes={"output_size": str(len(str(result)))},
                    )

                return result

        except Exception as e:
            error_occurred = True
            self._error_count += 1

            # Record error in span
            if span:
                span.record_exception(e)
                span.set_status(trace.Status(trace.StatusCode.ERROR, str(e)))

            raise

        finally:
            # Calculate duration
            duration_ms = (time.time() - start_time) * 1000
            self._total_duration_ms += duration_ms

            # Record metrics
            self._record_metrics(duration_ms, not error_occurred, attributes)

            # Update active invocations
            if self.skill._active_invocations:
                self.skill._active_invocations.add(-1, attributes)

    def get_stats(self) -> dict[str, Any]:
        """Get current statistics."""
        avg_duration = (
            self._total_duration_ms / self._invocation_count
            if self._invocation_count > 0
            else 0
        )

        return {
            "name": self._wrapped.name,
            "invocation_count": self._invocation_count,
            "error_count": self._error_count,
            "error_rate": (
                self._error_count / self._invocation_count
                if self._invocation_count > 0
                else 0
            ),
            "average_duration_ms": avg_duration,
            "total_duration_ms": self._total_duration_ms,
        }


class SkillTracing(Skill):
    """Lightweight tracing skill without full OpenTelemetry."""

    def __init__(self, trace_func: Callable[[str, dict[str, Any]], None] | None = None):
        self.trace_func = trace_func or self._default_trace
        self.traces: list[dict[str, Any]] = []

    def _default_trace(self, operation: str, details: dict[str, Any]):
        """Default trace function that stores in memory."""
        self.traces.append(
            {"timestamp": time.time(), "operation": operation, **details}
        )

    def _create_enhanced_brick(self, brick: NanobrickProtocol) -> NanobrickProtocol:
        """Create enhanced brick with lightweight tracing."""
        return TracedBrick(brick, self)


class TracedBrick(NanobrickEnhanced):
    """Nanobrick with lightweight tracing."""

    def __init__(self, nanobrick: NanobrickProtocol, skill: SkillTracing):
        super().__init__(nanobrick, skill)
        self.skill = skill

    async def invoke(self, input: Any, *, deps: Any = None) -> Any:
        """Invoke with tracing."""
        start_time = time.time()

        self.skill.trace_func(
            "invoke_start",
            {"nanobrick": self._wrapped.name, "input_type": type(input).__name__},
        )

        try:
            result = await self._wrapped.invoke(input, deps=deps)

            self.skill.trace_func(
                "invoke_complete",
                {
                    "nanobrick": self._wrapped.name,
                    "duration_ms": (time.time() - start_time) * 1000,
                    "output_type": type(result).__name__,
                },
            )

            return result

        except Exception as e:
            self.skill.trace_func(
                "invoke_error",
                {
                    "nanobrick": self._wrapped.name,
                    "duration_ms": (time.time() - start_time) * 1000,
                    "error": str(e),
                    "error_type": type(e).__name__,
                },
            )
            raise
