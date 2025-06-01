"""
Hot-swapping support for nanobricks.

Enables zero-downtime replacement of nanobricks in pipelines.
"""

import asyncio
import time
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any

from nanobricks.protocol import NanobrickBase, NanobrickProtocol, T_deps, T_in, T_out


class SwapStrategy(Enum):
    """Strategy for swapping nanobricks."""

    IMMEDIATE = "immediate"  # Switch immediately
    GRADUAL = "gradual"  # Gradual rollout based on percentage
    CANARY = "canary"  # Test with small percentage first
    BLUE_GREEN = "blue_green"  # Switch all at once after validation


@dataclass
class SwapHistory:
    """Record of a swap operation."""

    timestamp: datetime
    position: int
    old_brick: str
    new_brick: str
    strategy: SwapStrategy
    rollout_percent: float
    success: bool
    error: str | None = None


@dataclass
class SwapMetrics:
    """Metrics for swap operations."""

    total_swaps: int = 0
    successful_swaps: int = 0
    failed_swaps: int = 0
    average_swap_time_ms: float = 0.0
    current_version: int = 1


class SwappableBrick(NanobrickBase[T_in, T_out, T_deps]):
    """
    A wrapper that allows hot-swapping of the underlying nanobrick.
    """

    def __init__(
        self,
        brick: NanobrickProtocol[T_in, T_out, T_deps],
        position: int = 0,
        name: str | None = None,
    ):
        self.position = position
        self.name = name or f"SwappableBrick[{position}]"
        self.version = "1.0.0"
        self._current_brick = brick
        self._new_brick: NanobrickProtocol[T_in, T_out, T_deps] | None = None
        self._rollout_percent = 0.0
        self._swap_in_progress = False
        self._invocation_count = 0
        self._lock = asyncio.Lock()

    async def invoke(self, input: T_in, *, deps: T_deps = None) -> T_out:
        """Invoke the current or new brick based on rollout percentage."""
        async with self._lock:
            self._invocation_count += 1

            # Determine which brick to use
            if self._new_brick and self._rollout_percent > 0:
                # Use hash of invocation count for consistent routing
                use_new = (self._invocation_count % 100) < self._rollout_percent
                brick = self._new_brick if use_new else self._current_brick
            else:
                brick = self._current_brick

        # Execute outside the lock to avoid blocking
        return await brick.invoke(input, deps=deps)

    async def swap(
        self,
        new_brick: NanobrickProtocol[T_in, T_out, T_deps],
        strategy: SwapStrategy = SwapStrategy.IMMEDIATE,
        rollout_percent: float = 100.0,
    ) -> bool:
        """
        Swap to a new brick with the specified strategy.

        Returns True if swap succeeded, False otherwise.
        """
        async with self._lock:
            if self._swap_in_progress:
                return False

            self._swap_in_progress = True
            self._new_brick = new_brick

            try:
                if strategy == SwapStrategy.IMMEDIATE:
                    self._current_brick = new_brick
                    self._new_brick = None
                    self._rollout_percent = 0.0

                elif strategy == SwapStrategy.GRADUAL:
                    self._rollout_percent = min(rollout_percent, 100.0)

                elif strategy == SwapStrategy.CANARY:
                    # Start with 5% for canary
                    self._rollout_percent = 5.0

                elif strategy == SwapStrategy.BLUE_GREEN:
                    # Keep both versions ready but don't route traffic yet
                    self._rollout_percent = 0.0

                return True

            finally:
                self._swap_in_progress = False

    async def complete_swap(self):
        """Complete a gradual or blue-green swap."""
        async with self._lock:
            if self._new_brick:
                self._current_brick = self._new_brick
                self._new_brick = None
                self._rollout_percent = 0.0

    async def rollback(self):
        """Rollback to the previous brick."""
        async with self._lock:
            self._new_brick = None
            self._rollout_percent = 0.0

    async def adjust_rollout(self, percent: float):
        """Adjust the rollout percentage for gradual swaps."""
        async with self._lock:
            if self._new_brick:
                self._rollout_percent = min(max(percent, 0.0), 100.0)

    def get_status(self) -> dict[str, Any]:
        """Get current swap status."""
        return {
            "current_brick": self._current_brick.name,
            "new_brick": self._new_brick.name if self._new_brick else None,
            "rollout_percent": self._rollout_percent,
            "swap_in_progress": self._swap_in_progress,
            "invocation_count": self._invocation_count,
        }


class SwappablePipeline(NanobrickBase[T_in, T_out, T_deps]):
    """
    A pipeline that supports hot-swapping of individual components.
    """

    def __init__(
        self, bricks: list[NanobrickProtocol], name: str = "SwappablePipeline"
    ):
        self.name = name
        self.version = "1.0.0"
        self._swappable_bricks = [
            SwappableBrick(brick, i) for i, brick in enumerate(bricks)
        ]
        self._history: list[SwapHistory] = []
        self._metrics = SwapMetrics()

    async def invoke(self, input: T_in, *, deps: T_deps = None) -> T_out:
        """Execute the pipeline."""
        result = input
        for brick in self._swappable_bricks:
            result = await brick.invoke(result, deps=deps)
        return result

    async def swap(
        self,
        position: int,
        new_brick: NanobrickProtocol,
        strategy: SwapStrategy = SwapStrategy.IMMEDIATE,
        rollout_percent: float = 100.0,
        validation_func: Callable | None = None,
    ) -> bool:
        """
        Swap a brick at the specified position.

        Args:
            position: Position in the pipeline (0-indexed)
            new_brick: The new brick to swap in
            strategy: Swap strategy to use
            rollout_percent: Initial rollout percentage
            validation_func: Optional validation function

        Returns:
            True if swap succeeded, False otherwise
        """
        if position < 0 or position >= len(self._swappable_bricks):
            raise IndexError(f"Position {position} out of range")

        start_time = time.time()
        swappable = self._swappable_bricks[position]
        old_brick_name = swappable._current_brick.name

        # Validate new brick if validation function provided
        if validation_func:
            try:
                if not await validation_func(new_brick):
                    self._record_swap(
                        position,
                        old_brick_name,
                        new_brick.name,
                        strategy,
                        rollout_percent,
                        False,
                        "Validation failed",
                    )
                    return False
            except Exception as e:
                self._record_swap(
                    position,
                    old_brick_name,
                    new_brick.name,
                    strategy,
                    rollout_percent,
                    False,
                    f"Validation error: {str(e)}",
                )
                return False

        # Perform the swap
        success = await swappable.swap(new_brick, strategy, rollout_percent)

        # Update metrics
        swap_time_ms = (time.time() - start_time) * 1000
        self._update_metrics(success, swap_time_ms)

        # Record in history
        self._record_swap(
            position, old_brick_name, new_brick.name, strategy, rollout_percent, success
        )

        return success

    async def complete_swap(self, position: int):
        """Complete a gradual swap at the specified position."""
        if position < 0 or position >= len(self._swappable_bricks):
            raise IndexError(f"Position {position} out of range")

        await self._swappable_bricks[position].complete_swap()

    async def rollback(self, position: int):
        """Rollback a swap at the specified position."""
        if position < 0 or position >= len(self._swappable_bricks):
            raise IndexError(f"Position {position} out of range")

        await self._swappable_bricks[position].rollback()

    async def adjust_rollout(self, position: int, percent: float):
        """Adjust rollout percentage for a gradual swap."""
        if position < 0 or position >= len(self._swappable_bricks):
            raise IndexError(f"Position {position} out of range")

        await self._swappable_bricks[position].adjust_rollout(percent)

    def get_status(self) -> dict[str, Any]:
        """Get status of all swappable components."""
        return {
            "pipeline": self.name,
            "version": self._metrics.current_version,
            "components": [brick.get_status() for brick in self._swappable_bricks],
            "metrics": {
                "total_swaps": self._metrics.total_swaps,
                "successful_swaps": self._metrics.successful_swaps,
                "failed_swaps": self._metrics.failed_swaps,
                "average_swap_time_ms": self._metrics.average_swap_time_ms,
            },
        }

    def get_history(self, limit: int | None = None) -> list[SwapHistory]:
        """Get swap history."""
        if limit:
            return self._history[-limit:]
        return self._history.copy()

    def _record_swap(
        self,
        position: int,
        old_brick: str,
        new_brick: str,
        strategy: SwapStrategy,
        rollout_percent: float,
        success: bool,
        error: str | None = None,
    ):
        """Record a swap in history."""
        self._history.append(
            SwapHistory(
                timestamp=datetime.now(),
                position=position,
                old_brick=old_brick,
                new_brick=new_brick,
                strategy=strategy,
                rollout_percent=rollout_percent,
                success=success,
                error=error,
            )
        )

    def _update_metrics(self, success: bool, swap_time_ms: float):
        """Update swap metrics."""
        self._metrics.total_swaps += 1
        if success:
            self._metrics.successful_swaps += 1
            self._metrics.current_version += 1
        else:
            self._metrics.failed_swaps += 1

        # Update average swap time
        total_time = (
            self._metrics.average_swap_time_ms * (self._metrics.total_swaps - 1)
            + swap_time_ms
        )
        self._metrics.average_swap_time_ms = total_time / self._metrics.total_swaps


class CanaryController:
    """
    Controller for canary deployments with automatic rollout/rollback.
    """

    def __init__(
        self,
        pipeline: SwappablePipeline,
        position: int,
        success_threshold: float = 0.95,
        sample_size: int = 100,
        rollout_increments: list[float] = None,
    ):
        self.pipeline = pipeline
        self.position = position
        self.success_threshold = success_threshold
        self.sample_size = sample_size
        self.rollout_increments = rollout_increments or [5, 10, 25, 50, 100]

        self._current_stage = 0
        self._successes = 0
        self._failures = 0
        self._monitoring = False

    async def start_canary(
        self, new_brick: NanobrickProtocol, monitor_func: Callable[[Any], bool]
    ):
        """
        Start a canary deployment with automatic monitoring.

        Args:
            new_brick: The new brick to deploy
            monitor_func: Function to monitor success/failure
        """
        # Start with canary strategy
        success = await self.pipeline.swap(
            self.position, new_brick, SwapStrategy.CANARY
        )

        if not success:
            return False

        self._monitoring = True
        self._current_stage = 0

        # Start monitoring in background
        asyncio.create_task(self._monitor_canary(monitor_func))

        return True

    async def _monitor_canary(self, monitor_func: Callable[[Any], bool]):
        """Monitor canary deployment and adjust rollout."""
        while self._monitoring and self._current_stage < len(self.rollout_increments):
            # Wait for sample size
            await asyncio.sleep(1)  # Check every second

            total_samples = self._successes + self._failures
            if total_samples >= self.sample_size:
                success_rate = (
                    self._successes / total_samples if total_samples > 0 else 0
                )

                if success_rate >= self.success_threshold:
                    # Promote to next stage
                    self._current_stage += 1
                    if self._current_stage < len(self.rollout_increments):
                        await self.pipeline.adjust_rollout(
                            self.position, self.rollout_increments[self._current_stage]
                        )
                    else:
                        # Complete the rollout
                        await self.pipeline.complete_swap(self.position)
                        self._monitoring = False

                    # Reset counters for next stage
                    self._successes = 0
                    self._failures = 0
                else:
                    # Rollback due to high failure rate
                    await self.pipeline.rollback(self.position)
                    self._monitoring = False

    def record_result(self, success: bool):
        """Record the result of an invocation during canary."""
        if self._monitoring:
            if success:
                self._successes += 1
            else:
                self._failures += 1

    def stop_monitoring(self):
        """Stop canary monitoring."""
        self._monitoring = False
