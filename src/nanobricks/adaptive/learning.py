"""Learning and recovery mechanisms for adaptive nanobricks."""

import asyncio
import json
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from nanobricks import NanobrickProtocol


@dataclass
class PerformancePattern:
    """A learned performance pattern."""

    input_signature: str
    avg_latency_ms: float
    success_rate: float
    optimal_params: dict[str, Any]
    sample_count: int = 0


class PerformanceLearner:
    """Learns performance patterns over time."""

    def __init__(
        self,
        learning_rate: float = 0.1,
        pattern_threshold: int = 10,
        save_path: Path | None = None,
    ):
        """Initialize performance learner.

        Args:
            learning_rate: How quickly to update patterns
            pattern_threshold: Minimum samples to establish pattern
            save_path: Path to save learned patterns
        """
        self.learning_rate = learning_rate
        self.pattern_threshold = pattern_threshold
        self.save_path = save_path

        # Learned patterns by input signature
        self.patterns: dict[str, PerformancePattern] = {}

        # Load existing patterns
        if save_path and save_path.exists():
            self.load_patterns()

    def get_input_signature(self, input: Any) -> str:
        """Generate signature for input."""
        # Simple signature based on type and size
        if isinstance(input, dict):
            sig = f"dict:{len(input)}:{sorted(input.keys())}"
        elif isinstance(input, list):
            sig = f"list:{len(input)}:{type(input[0]).__name__ if input else 'empty'}"
        elif isinstance(input, str):
            sig = f"str:{len(input)}:{input[:20]}"
        else:
            sig = f"{type(input).__name__}:{str(input)[:50]}"

        return sig

    def record_performance(
        self,
        input: Any,
        latency_ms: float,
        success: bool,
        params: dict[str, Any],
    ):
        """Record performance for an input."""
        signature = self.get_input_signature(input)

        if signature not in self.patterns:
            self.patterns[signature] = PerformancePattern(
                input_signature=signature,
                avg_latency_ms=latency_ms,
                success_rate=1.0 if success else 0.0,
                optimal_params=params.copy(),
                sample_count=1,
            )
        else:
            pattern = self.patterns[signature]

            # Update with exponential moving average
            pattern.avg_latency_ms = (
                1 - self.learning_rate
            ) * pattern.avg_latency_ms + self.learning_rate * latency_ms

            pattern.success_rate = (
                1 - self.learning_rate
            ) * pattern.success_rate + self.learning_rate * (1.0 if success else 0.0)

            pattern.sample_count += 1

            # Update optimal params if this was successful and fast
            if success and latency_ms < pattern.avg_latency_ms:
                pattern.optimal_params = params.copy()

    def get_optimal_params(self, input: Any) -> dict[str, Any] | None:
        """Get optimal parameters for an input."""
        signature = self.get_input_signature(input)
        pattern = self.patterns.get(signature)

        if pattern and pattern.sample_count >= self.pattern_threshold:
            return pattern.optimal_params

        return None

    def predict_performance(
        self, input: Any, params: dict[str, Any]
    ) -> tuple[float, float]:
        """Predict latency and success rate.

        Returns:
            Tuple of (predicted_latency_ms, predicted_success_rate)
        """
        signature = self.get_input_signature(input)
        pattern = self.patterns.get(signature)

        if pattern and pattern.sample_count >= self.pattern_threshold:
            # Adjust prediction based on parameter differences
            latency = pattern.avg_latency_ms

            # Simple heuristic: different params may affect performance
            if params != pattern.optimal_params:
                latency *= 1.2  # 20% penalty for non-optimal params

            return latency, pattern.success_rate

        # No pattern found, return defaults
        return 100.0, 0.9

    def save_patterns(self):
        """Save learned patterns to disk."""
        if not self.save_path:
            return

        data = {
            sig: {
                "avg_latency_ms": p.avg_latency_ms,
                "success_rate": p.success_rate,
                "optimal_params": p.optimal_params,
                "sample_count": p.sample_count,
            }
            for sig, p in self.patterns.items()
        }

        self.save_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.save_path, "w") as f:
            json.dump(data, f, indent=2)

    def load_patterns(self):
        """Load patterns from disk."""
        if not self.save_path or not self.save_path.exists():
            return

        with open(self.save_path) as f:
            data = json.load(f)

        self.patterns = {
            sig: PerformancePattern(
                input_signature=sig,
                avg_latency_ms=p["avg_latency_ms"],
                success_rate=p["success_rate"],
                optimal_params=p["optimal_params"],
                sample_count=p["sample_count"],
            )
            for sig, p in data.items()
        }


class ErrorRecovery:
    """Smart error recovery based on learned patterns."""

    def __init__(self, max_history: int = 1000):
        """Initialize error recovery.

        Args:
            max_history: Maximum error history to maintain
        """
        self.max_history = max_history

        # Error patterns: error_type -> input_signature -> recovery_strategies
        self.error_patterns: dict[str, dict[str, list[dict[str, Any]]]] = defaultdict(
            lambda: defaultdict(list)
        )

        # Success history for recovery strategies
        self.recovery_success: dict[str, dict[str, float]] = defaultdict(
            lambda: defaultdict(float)
        )

    async def recover_from_error(
        self,
        brick: NanobrickProtocol,
        input: Any,
        error: Exception,
        deps: Any | None = None,
    ) -> Any | None:
        """Try to recover from an error using learned strategies."""
        error_type = type(error).__name__
        input_sig = self._get_input_signature(input)

        # Get recovery strategies for this error/input pattern
        strategies = self.error_patterns[error_type][input_sig]

        # Sort by success rate
        sorted_strategies = sorted(
            strategies,
            key=lambda s: self.recovery_success[error_type].get(s["name"], 0),
            reverse=True,
        )

        # Try each strategy
        for strategy in sorted_strategies:
            try:
                result = await self._apply_strategy(brick, input, error, strategy, deps)

                # Record success
                self.recovery_success[error_type][strategy["name"]] += 0.1

                return result

            except Exception:
                # Record failure
                self.recovery_success[error_type][strategy["name"]] -= 0.05
                continue

        # Try default strategies if no learned ones work
        return await self._try_default_recovery(brick, input, error, deps)

    def record_error(
        self,
        input: Any,
        error: Exception,
        recovery_strategy: dict[str, Any] | None = None,
        recovered: bool = False,
    ):
        """Record an error and recovery attempt."""
        error_type = type(error).__name__
        input_sig = self._get_input_signature(input)

        if recovery_strategy and recovered:
            # Add to successful strategies
            strategies = self.error_patterns[error_type][input_sig]

            if recovery_strategy not in strategies:
                strategies.append(recovery_strategy)

                # Limit history
                if len(strategies) > 10:
                    strategies.pop(0)

    async def _apply_strategy(
        self,
        brick: NanobrickProtocol,
        input: Any,
        error: Exception,
        strategy: dict[str, Any],
        deps: Any | None,
    ) -> Any:
        """Apply a recovery strategy."""
        strategy_type = strategy.get("type", "retry")

        if strategy_type == "retry":
            # Retry with modifications
            delay = strategy.get("delay", 1.0)
            await asyncio.sleep(delay)

            modified_input = self._modify_input(
                input, strategy.get("modifications", {})
            )
            return await brick.invoke(modified_input, deps=deps)

        elif strategy_type == "fallback":
            # Use fallback value
            return strategy.get("value", None)

        elif strategy_type == "transform":
            # Transform input
            transform = strategy.get("transform", lambda x: x)
            transformed = transform(input)
            return await brick.invoke(transformed, deps=deps)

        else:
            raise ValueError(f"Unknown strategy type: {strategy_type}")

    async def _try_default_recovery(
        self,
        brick: NanobrickProtocol,
        input: Any,
        error: Exception,
        deps: Any | None,
    ) -> Any | None:
        """Try default recovery strategies."""
        error_type = type(error).__name__

        # Type-specific recovery
        if error_type == "TimeoutError":
            # Retry with smaller input
            if isinstance(input, list) and len(input) > 1:
                half = len(input) // 2
                result1 = await brick.invoke(input[:half], deps=deps)
                result2 = await brick.invoke(input[half:], deps=deps)

                # Combine results
                if isinstance(result1, list):
                    return result1 + result2
                else:
                    return [result1, result2]

        elif error_type == "ValueError":
            # Try type conversion
            if isinstance(input, str):
                try:
                    # Try parsing as JSON
                    parsed = json.loads(input)
                    return await brick.invoke(parsed, deps=deps)
                except:
                    pass

        elif error_type == "MemoryError":
            # Process in smaller chunks
            if hasattr(input, "__len__") and len(input) > 10:
                results = []
                chunk_size = max(1, len(input) // 10)

                for i in range(0, len(input), chunk_size):
                    chunk = input[i : i + chunk_size]
                    result = await brick.invoke(chunk, deps=deps)
                    results.append(result)

                return results

        return None

    def _get_input_signature(self, input: Any) -> str:
        """Generate signature for input."""
        # Reuse from PerformanceLearner
        if isinstance(input, dict):
            return f"dict:{len(input)}"
        elif isinstance(input, list):
            return f"list:{len(input)}"
        elif isinstance(input, str):
            return f"str:{len(input)}"
        else:
            return type(input).__name__

    def _modify_input(self, input: Any, modifications: dict[str, Any]) -> Any:
        """Apply modifications to input."""
        if isinstance(input, dict):
            modified = input.copy()
            modified.update(modifications)
            return modified
        elif isinstance(input, list) and "max_length" in modifications:
            return input[: modifications["max_length"]]
        else:
            return input
