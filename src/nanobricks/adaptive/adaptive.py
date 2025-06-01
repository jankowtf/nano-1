"""Adaptive nanobricks that self-tune and learn."""

import asyncio
import time
from abc import ABC, abstractmethod
from collections import deque
from dataclasses import dataclass, field
from typing import Any

from nanobricks import NanobrickProtocol


@dataclass
class PerformanceMetrics:
    """Performance metrics for adaptive behavior."""

    latency_ms: float
    success: bool
    error: str | None = None
    input_size: int = 0
    output_size: int = 0
    timestamp: float = field(default_factory=time.time)

    @property
    def throughput(self) -> float:
        """Calculate throughput (bytes/ms)."""
        if self.latency_ms > 0:
            return (self.input_size + self.output_size) / self.latency_ms
        return 0.0


class AdaptationPolicy(ABC):
    """Base class for adaptation policies."""

    @abstractmethod
    def should_adapt(self, metrics: list[PerformanceMetrics]) -> bool:
        """Determine if adaptation is needed."""
        pass

    @abstractmethod
    def get_adaptations(self, metrics: list[PerformanceMetrics]) -> dict[str, Any]:
        """Get adaptation parameters."""
        pass


class AdaptiveBrick(NanobrickProtocol[Any, Any, Any]):
    """A nanobrick that adapts based on performance."""

    def __init__(
        self,
        wrapped: NanobrickProtocol,
        policy: AdaptationPolicy,
        window_size: int = 100,
        adaptation_interval: float = 10.0,
        enable_auto_recovery: bool = True,
    ):
        """Initialize adaptive brick.

        Args:
            wrapped: The brick to make adaptive
            policy: Adaptation policy to use
            window_size: Size of metrics window
            adaptation_interval: Seconds between adaptations
            enable_auto_recovery: Enable automatic error recovery
        """
        self.wrapped = wrapped
        self.policy = policy
        self.window_size = window_size
        self.adaptation_interval = adaptation_interval
        self.enable_auto_recovery = enable_auto_recovery

        # Metrics tracking
        self._metrics: deque[PerformanceMetrics] = deque(maxlen=window_size)
        self._last_adaptation = time.time()
        self._current_params: dict[str, Any] = {}

        # Error recovery
        self._error_counts: dict[str, int] = {}
        self._recovery_strategies: list[callable] = []

        # Background adaptation task
        self._adaptation_task: asyncio.Task | None = None

        # Copy attributes from wrapped
        self.name = f"Adaptive[{wrapped.name}]"
        self.version = wrapped.version

    async def invoke(self, input: Any, *, deps: Any | None = None) -> Any:
        """Invoke with adaptive behavior."""
        start_time = time.perf_counter()
        input_size = len(str(input))

        try:
            # Apply current adaptations
            adapted_input = self._apply_input_adaptations(input)

            # Invoke wrapped brick
            result = await self.wrapped.invoke(adapted_input, deps=deps)

            # Record success metrics
            latency_ms = (time.perf_counter() - start_time) * 1000
            output_size = len(str(result))

            metric = PerformanceMetrics(
                latency_ms=latency_ms,
                success=True,
                input_size=input_size,
                output_size=output_size,
            )
            self._record_metric(metric)

            # Apply output adaptations
            return self._apply_output_adaptations(result)

        except Exception as e:
            # Record error metrics
            latency_ms = (time.perf_counter() - start_time) * 1000
            error_type = type(e).__name__

            metric = PerformanceMetrics(
                latency_ms=latency_ms,
                success=False,
                error=str(e),
                input_size=input_size,
            )
            self._record_metric(metric)

            # Try error recovery
            if self.enable_auto_recovery:
                recovery_result = await self._try_recovery(input, e, deps)
                if recovery_result is not None:
                    return recovery_result

            raise

    def invoke_sync(self, input: Any, *, deps: Any | None = None) -> Any:
        """Synchronous invoke."""
        return asyncio.run(self.invoke(input, deps=deps))

    def _record_metric(self, metric: PerformanceMetrics):
        """Record a performance metric."""
        self._metrics.append(metric)

        # Check if adaptation needed
        current_time = time.time()
        if current_time - self._last_adaptation >= self.adaptation_interval:
            self._last_adaptation = current_time
            self._check_adaptation()

    def _check_adaptation(self):
        """Check if adaptation is needed."""
        if len(self._metrics) < 10:  # Need minimum data
            return

        metrics_list = list(self._metrics)

        if self.policy.should_adapt(metrics_list):
            adaptations = self.policy.get_adaptations(metrics_list)
            self._apply_adaptations(adaptations)

    def _apply_adaptations(self, adaptations: dict[str, Any]):
        """Apply adaptation parameters."""
        self._current_params.update(adaptations)

        # Apply to wrapped brick if it supports it
        if hasattr(self.wrapped, "apply_adaptations"):
            self.wrapped.apply_adaptations(adaptations)

    def _apply_input_adaptations(self, input: Any) -> Any:
        """Apply input adaptations."""
        # Example: Batch size adjustment
        if "batch_size" in self._current_params and isinstance(input, list):
            batch_size = self._current_params["batch_size"]
            if len(input) > batch_size:
                # Process in smaller batches
                return input[:batch_size]

        return input

    def _apply_output_adaptations(self, output: Any) -> Any:
        """Apply output adaptations."""
        # Example: Result caching
        if self._current_params.get("enable_cache", False):
            # Could implement caching logic here
            pass

        return output

    async def _try_recovery(
        self, input: Any, error: Exception, deps: Any | None
    ) -> Any | None:
        """Try to recover from error."""
        error_type = type(error).__name__

        # Track error frequency
        self._error_counts[error_type] = self._error_counts.get(error_type, 0) + 1

        # Try recovery strategies
        for strategy in self._recovery_strategies:
            try:
                result = await strategy(self, input, error, deps)
                if result is not None:
                    return result
            except:
                continue

        # Default recovery strategies
        if error_type == "TimeoutError":
            # Retry with longer timeout
            return await self._retry_with_backoff(input, deps)
        elif error_type == "ValueError":
            # Try input sanitization
            sanitized = self._sanitize_input(input)
            if sanitized != input:
                return await self.wrapped.invoke(sanitized, deps=deps)

        return None

    async def _retry_with_backoff(
        self, input: Any, deps: Any | None, max_retries: int = 3
    ) -> Any:
        """Retry with exponential backoff."""
        for attempt in range(max_retries):
            try:
                await asyncio.sleep(2**attempt)
                return await self.wrapped.invoke(input, deps=deps)
            except Exception:
                if attempt == max_retries - 1:
                    raise

        return None

    def _sanitize_input(self, input: Any) -> Any:
        """Sanitize input to prevent common errors."""
        if isinstance(input, str):
            # Remove problematic characters
            return input.strip().replace("\x00", "")
        elif isinstance(input, dict):
            # Recursively sanitize
            return {k: self._sanitize_input(v) for k, v in input.items()}
        elif isinstance(input, list):
            return [self._sanitize_input(item) for item in input]

        return input

    def add_recovery_strategy(self, strategy: callable):
        """Add a custom recovery strategy."""
        self._recovery_strategies.append(strategy)

    def get_metrics_summary(self) -> dict[str, Any]:
        """Get summary of performance metrics."""
        if not self._metrics:
            return {}

        metrics_list = list(self._metrics)
        success_metrics = [m for m in metrics_list if m.success]
        error_metrics = [m for m in metrics_list if not m.success]

        summary = {
            "total_invocations": len(metrics_list),
            "success_rate": (
                len(success_metrics) / len(metrics_list) if metrics_list else 0
            ),
            "error_count": len(error_metrics),
            "current_adaptations": self._current_params,
        }

        if success_metrics:
            latencies = [m.latency_ms for m in success_metrics]
            summary.update(
                {
                    "avg_latency_ms": sum(latencies) / len(latencies),
                    "min_latency_ms": min(latencies),
                    "max_latency_ms": max(latencies),
                }
            )

        if error_metrics:
            summary["error_types"] = {}
            for metric in error_metrics:
                error_type = metric.error.split(":")[0] if metric.error else "Unknown"
                summary["error_types"][error_type] = (
                    summary["error_types"].get(error_type, 0) + 1
                )

        return summary

    def __or__(self, other):
        """Compose with another brick."""
        from nanobricks.composition import Pipeline

        return Pipeline(self, other)


def create_adaptive_brick(
    brick: NanobrickProtocol, policy: AdaptationPolicy | None = None, **kwargs
) -> AdaptiveBrick:
    """Create an adaptive version of a brick.

    Args:
        brick: Brick to make adaptive
        policy: Adaptation policy (uses default if None)
        **kwargs: Additional arguments for AdaptiveBrick

    Returns:
        Adaptive brick
    """
    if policy is None:
        # Use default threshold policy
        from nanobricks.adaptive.policies import ThresholdPolicy

        policy = ThresholdPolicy()

    return AdaptiveBrick(brick, policy, **kwargs)
