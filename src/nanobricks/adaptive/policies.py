"""Adaptation policies for adaptive nanobricks."""

from typing import Any

from nanobricks.adaptive.adaptive import AdaptationPolicy, PerformanceMetrics


class ThresholdPolicy(AdaptationPolicy):
    """Simple threshold-based adaptation policy."""

    def __init__(
        self,
        latency_threshold_ms: float = 1000.0,
        error_rate_threshold: float = 0.1,
        throughput_threshold: float = 100.0,
    ):
        """Initialize threshold policy.

        Args:
            latency_threshold_ms: Maximum acceptable latency
            error_rate_threshold: Maximum acceptable error rate
            throughput_threshold: Minimum acceptable throughput
        """
        self.latency_threshold_ms = latency_threshold_ms
        self.error_rate_threshold = error_rate_threshold
        self.throughput_threshold = throughput_threshold

    def should_adapt(self, metrics: list[PerformanceMetrics]) -> bool:
        """Check if thresholds are exceeded."""
        if not metrics:
            return False

        # Calculate aggregates
        success_metrics = [m for m in metrics if m.success]
        error_rate = 1 - (len(success_metrics) / len(metrics))

        # Check error rate
        if error_rate > self.error_rate_threshold:
            return True

        if success_metrics:
            # Check latency
            avg_latency = sum(m.latency_ms for m in success_metrics) / len(
                success_metrics
            )
            if avg_latency > self.latency_threshold_ms:
                return True

            # Check throughput
            avg_throughput = sum(m.throughput for m in success_metrics) / len(
                success_metrics
            )
            if avg_throughput < self.throughput_threshold:
                return True

        return False

    def get_adaptations(self, metrics: list[PerformanceMetrics]) -> dict[str, Any]:
        """Get adaptation parameters based on thresholds."""
        adaptations = {}

        # Calculate metrics
        success_metrics = [m for m in metrics if m.success]
        error_rate = 1 - (len(success_metrics) / len(metrics))

        # Adapt based on error rate
        if error_rate > self.error_rate_threshold:
            adaptations["enable_retry"] = True
            adaptations["max_retries"] = min(5, int(error_rate * 10))

        if success_metrics:
            avg_latency = sum(m.latency_ms for m in success_metrics) / len(
                success_metrics
            )

            # Adapt based on latency
            if avg_latency > self.latency_threshold_ms:
                # Reduce batch size to improve latency
                adaptations["batch_size"] = max(
                    1, int(self.latency_threshold_ms / avg_latency * 10)
                )
                adaptations["enable_cache"] = True

        return adaptations


class GradientPolicy(AdaptationPolicy):
    """Gradient-based adaptation policy."""

    def __init__(
        self,
        learning_rate: float = 0.01,
        target_latency_ms: float = 100.0,
        target_throughput: float = 1000.0,
    ):
        """Initialize gradient policy.

        Args:
            learning_rate: How quickly to adapt
            target_latency_ms: Target latency
            target_throughput: Target throughput
        """
        self.learning_rate = learning_rate
        self.target_latency_ms = target_latency_ms
        self.target_throughput = target_throughput
        self._current_params = {"batch_size": 10, "concurrency": 1}

    def should_adapt(self, metrics: list[PerformanceMetrics]) -> bool:
        """Always adapt using gradients."""
        return len(metrics) >= 10

    def get_adaptations(self, metrics: list[PerformanceMetrics]) -> dict[str, Any]:
        """Calculate gradient-based adaptations."""
        success_metrics = [m for m in metrics if m.success]
        if not success_metrics:
            return self._current_params

        # Calculate current performance
        avg_latency = sum(m.latency_ms for m in success_metrics) / len(success_metrics)
        avg_throughput = sum(m.throughput for m in success_metrics) / len(
            success_metrics
        )

        # Calculate gradients
        latency_error = avg_latency - self.target_latency_ms
        throughput_error = self.target_throughput - avg_throughput

        # Update parameters
        if abs(latency_error) > 10:
            # Adjust batch size based on latency
            batch_adjustment = -self.learning_rate * latency_error / 100
            self._current_params["batch_size"] = max(
                1, int(self._current_params["batch_size"] * (1 + batch_adjustment))
            )

        if abs(throughput_error) > 10:
            # Adjust concurrency based on throughput
            concurrency_adjustment = self.learning_rate * throughput_error / 1000
            self._current_params["concurrency"] = max(
                1,
                min(
                    10,
                    int(self._current_params["concurrency"] + concurrency_adjustment),
                ),
            )

        return self._current_params.copy()


class RuleBasedPolicy(AdaptationPolicy):
    """Rule-based adaptation policy."""

    def __init__(self):
        """Initialize rule-based policy."""
        self.rules = []
        self._add_default_rules()

    def _add_default_rules(self):
        """Add default adaptation rules."""
        # High error rate -> Enable retry
        self.add_rule(
            condition=lambda m: self._error_rate(m) > 0.2,
            adaptation={"enable_retry": True, "max_retries": 3},
        )

        # Timeout errors -> Increase timeout
        self.add_rule(
            condition=lambda m: self._has_timeout_errors(m),
            adaptation={"timeout_multiplier": 2.0},
        )

        # Memory errors -> Reduce batch size
        self.add_rule(
            condition=lambda m: self._has_memory_errors(m),
            adaptation={"batch_size": 5, "enable_streaming": True},
        )

    def add_rule(self, condition: callable, adaptation: dict[str, Any]):
        """Add an adaptation rule."""
        self.rules.append((condition, adaptation))

    def should_adapt(self, metrics: list[PerformanceMetrics]) -> bool:
        """Check if any rule conditions are met."""
        for condition, _ in self.rules:
            if condition(metrics):
                return True
        return False

    def get_adaptations(self, metrics: list[PerformanceMetrics]) -> dict[str, Any]:
        """Apply all matching rules."""
        adaptations = {}

        for condition, adaptation in self.rules:
            if condition(metrics):
                adaptations.update(adaptation)

        return adaptations

    def _error_rate(self, metrics: list[PerformanceMetrics]) -> float:
        """Calculate error rate."""
        if not metrics:
            return 0.0
        error_count = sum(1 for m in metrics if not m.success)
        return error_count / len(metrics)

    def _has_timeout_errors(self, metrics: list[PerformanceMetrics]) -> bool:
        """Check for timeout errors."""
        return any(
            m.error and "timeout" in m.error.lower() for m in metrics if not m.success
        )

    def _has_memory_errors(self, metrics: list[PerformanceMetrics]) -> bool:
        """Check for memory errors."""
        return any(
            m.error and "memory" in m.error.lower() for m in metrics if not m.success
        )


class MLPolicy(AdaptationPolicy):
    """Machine learning based adaptation policy."""

    def __init__(self, model_path: str | None = None):
        """Initialize ML policy.

        Args:
            model_path: Path to trained model
        """
        self.model_path = model_path
        self.model = None
        self._feature_buffer = []
        self._adaptation_history = []

    def should_adapt(self, metrics: list[PerformanceMetrics]) -> bool:
        """Use ML model to predict if adaptation needed."""
        if not self.model:
            # Fall back to simple heuristic
            return len(metrics) >= 50 and self._calculate_health_score(metrics) < 0.8

        # Extract features and predict
        features = self._extract_features(metrics)
        # In real implementation, would use model.predict(features)
        return True

    def get_adaptations(self, metrics: list[PerformanceMetrics]) -> dict[str, Any]:
        """Use ML model to predict optimal adaptations."""
        features = self._extract_features(metrics)

        # In real implementation, would use model to predict adaptations
        # For now, use simple heuristics based on features
        adaptations = {}

        if features["error_rate"] > 0.1:
            adaptations["enable_retry"] = True

        if features["latency_p95"] > 1000:
            adaptations["batch_size"] = 5
            adaptations["enable_cache"] = True

        if features["throughput_trend"] < -0.1:
            adaptations["concurrency"] = 2

        # Record for future training
        self._adaptation_history.append(
            {
                "features": features,
                "adaptations": adaptations,
                "timestamp": metrics[-1].timestamp if metrics else 0,
            }
        )

        return adaptations

    def _extract_features(self, metrics: list[PerformanceMetrics]) -> dict[str, float]:
        """Extract features for ML model."""
        if not metrics:
            return {}

        success_metrics = [m for m in metrics if m.success]
        error_metrics = [m for m in metrics if not m.success]

        features = {
            "error_rate": len(error_metrics) / len(metrics),
            "sample_count": len(metrics),
        }

        if success_metrics:
            latencies = [m.latency_ms for m in success_metrics]
            features.update(
                {
                    "latency_mean": sum(latencies) / len(latencies),
                    "latency_p95": (
                        sorted(latencies)[int(len(latencies) * 0.95)]
                        if latencies
                        else 0
                    ),
                    "throughput_mean": sum(m.throughput for m in success_metrics)
                    / len(success_metrics),
                }
            )

            # Calculate trends
            if len(success_metrics) > 10:
                recent = success_metrics[-10:]
                older = (
                    success_metrics[-20:-10]
                    if len(success_metrics) > 20
                    else success_metrics[:10]
                )

                recent_throughput = sum(m.throughput for m in recent) / len(recent)
                older_throughput = sum(m.throughput for m in older) / len(older)

                features["throughput_trend"] = (
                    (recent_throughput - older_throughput) / older_throughput
                    if older_throughput > 0
                    else 0
                )

        return features

    def _calculate_health_score(self, metrics: list[PerformanceMetrics]) -> float:
        """Calculate overall health score (0-1)."""
        features = self._extract_features(metrics)

        # Simple weighted score
        score = 1.0
        score -= features.get("error_rate", 0) * 0.5
        score -= max(0, (features.get("latency_mean", 0) - 100) / 1000) * 0.3
        score -= max(0, (100 - features.get("throughput_mean", 100)) / 100) * 0.2

        return max(0, min(1, score))
