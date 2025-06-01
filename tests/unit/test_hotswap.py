"""Tests for hot-swapping functionality."""

import asyncio
from typing import Any

import pytest

from nanobricks.hotswap import (
    CanaryController,
    SwappableBrick,
    SwappablePipeline,
    SwapStrategy,
)
from nanobricks.protocol import NanobrickBase


class VersionedBrick(NanobrickBase[int, int, None]):
    """Test brick with version tracking."""

    def __init__(self, version: str, multiplier: int = 1):
        self.name = f"VersionedBrick[v{version}]"
        self.version = version
        self.multiplier = multiplier
        self.invocation_count = 0

    async def invoke(self, input: int, *, deps: None = None) -> int:
        self.invocation_count += 1
        return input * self.multiplier


class FailingNanobrick(NanobrickBase[Any, Any, None]):
    """Test brick that fails."""

    def __init__(self):
        self.name = "FailingBrick"
        self.version = "1.0.0"

    async def invoke(self, input: Any, *, deps: None = None) -> Any:
        raise ValueError("Intentional failure")


@pytest.mark.asyncio
class TestSwappableBrick:
    """Tests for SwappableBrick."""

    async def test_immediate_swap(self):
        """Test immediate swapping strategy."""
        brick_v1 = VersionedBrick("1.0", multiplier=2)
        brick_v2 = VersionedBrick("2.0", multiplier=3)

        swappable = SwappableBrick(brick_v1)

        # Test with v1
        result = await swappable.invoke(5)
        assert result == 10  # 5 * 2

        # Swap to v2
        success = await swappable.swap(brick_v2, SwapStrategy.IMMEDIATE)
        assert success

        # Test with v2
        result = await swappable.invoke(5)
        assert result == 15  # 5 * 3

    async def test_gradual_swap(self):
        """Test gradual rollout strategy."""
        brick_v1 = VersionedBrick("1.0", multiplier=2)
        brick_v2 = VersionedBrick("2.0", multiplier=3)

        swappable = SwappableBrick(brick_v1)

        # Start gradual swap with 30% rollout
        success = await swappable.swap(brick_v2, SwapStrategy.GRADUAL, 30.0)
        assert success

        # Run multiple invocations and check distribution
        v1_count = 0
        v2_count = 0

        for i in range(100):
            result = await swappable.invoke(1)
            if result == 2:  # v1 result
                v1_count += 1
            elif result == 3:  # v2 result
                v2_count += 1

        # Should be approximately 70% v1, 30% v2
        assert 25 <= v2_count <= 35  # Allow some variance
        assert v1_count + v2_count == 100

    async def test_canary_swap(self):
        """Test canary deployment strategy."""
        brick_v1 = VersionedBrick("1.0", multiplier=2)
        brick_v2 = VersionedBrick("2.0", multiplier=3)

        swappable = SwappableBrick(brick_v1)

        # Start canary with 5% rollout
        success = await swappable.swap(brick_v2, SwapStrategy.CANARY)
        assert success

        status = swappable.get_status()
        assert status["rollout_percent"] == 5.0

    async def test_rollback(self):
        """Test rollback functionality."""
        brick_v1 = VersionedBrick("1.0", multiplier=2)
        brick_v2 = VersionedBrick("2.0", multiplier=3)

        swappable = SwappableBrick(brick_v1)

        # Start gradual swap
        await swappable.swap(brick_v2, SwapStrategy.GRADUAL, 50.0)

        # Rollback
        await swappable.rollback()

        # All invocations should use v1
        for _ in range(10):
            result = await swappable.invoke(5)
            assert result == 10  # v1 result


@pytest.mark.asyncio
class TestSwappablePipeline:
    """Tests for SwappablePipeline."""

    async def test_pipeline_swap(self):
        """Test swapping bricks in a pipeline."""
        brick1 = VersionedBrick("1.0", multiplier=2)
        brick2 = VersionedBrick("1.0", multiplier=3)
        brick3 = VersionedBrick("1.0", multiplier=1)

        pipeline = SwappablePipeline([brick1, brick2, brick3])

        # Test original pipeline: 5 * 2 * 3 * 1 = 30
        result = await pipeline.invoke(5)
        assert result == 30

        # Swap middle brick
        new_brick2 = VersionedBrick("2.0", multiplier=4)
        success = await pipeline.swap(1, new_brick2)
        assert success

        # Test new pipeline: 5 * 2 * 4 * 1 = 40
        result = await pipeline.invoke(5)
        assert result == 40

    async def test_pipeline_validation(self):
        """Test pipeline swap with validation."""
        brick1 = VersionedBrick("1.0", multiplier=2)
        pipeline = SwappablePipeline([brick1])

        # Validation function that rejects the swap
        async def validator(brick):
            return False

        new_brick = VersionedBrick("2.0", multiplier=3)
        success = await pipeline.swap(0, new_brick, validation_func=validator)
        assert not success

        # Original brick should still be in use
        result = await pipeline.invoke(5)
        assert result == 10

    async def test_pipeline_history(self):
        """Test swap history tracking."""
        brick1 = VersionedBrick("1.0", multiplier=2)
        pipeline = SwappablePipeline([brick1])

        # Perform swaps
        new_brick1 = VersionedBrick("2.0", multiplier=3)
        await pipeline.swap(0, new_brick1)

        new_brick2 = VersionedBrick("3.0", multiplier=4)
        await pipeline.swap(0, new_brick2)

        # Check history
        history = pipeline.get_history()
        assert len(history) == 2
        assert history[0].old_brick == "VersionedBrick[v1.0]"
        assert history[0].new_brick == "VersionedBrick[v2.0]"
        assert history[1].old_brick == "VersionedBrick[v2.0]"
        assert history[1].new_brick == "VersionedBrick[v3.0]"

    async def test_pipeline_metrics(self):
        """Test swap metrics tracking."""
        brick1 = VersionedBrick("1.0", multiplier=2)
        pipeline = SwappablePipeline([brick1])

        # Perform successful swap
        new_brick1 = VersionedBrick("2.0", multiplier=3)
        await pipeline.swap(0, new_brick1)

        # Perform failed swap (invalid position)
        try:
            await pipeline.swap(10, new_brick1)
        except IndexError:
            pass

        status = pipeline.get_status()
        metrics = status["metrics"]

        assert metrics["total_swaps"] == 1
        assert metrics["successful_swaps"] == 1
        assert metrics["failed_swaps"] == 0
        assert metrics["average_swap_time_ms"] > 0


@pytest.mark.asyncio
class TestCanaryController:
    """Tests for CanaryController."""

    async def test_canary_success(self):
        """Test successful canary deployment."""
        brick1 = VersionedBrick("1.0", multiplier=2)
        pipeline = SwappablePipeline([brick1])

        controller = CanaryController(
            pipeline,
            position=0,
            success_threshold=0.8,
            sample_size=10,
            rollout_increments=[5, 25, 50, 100],
        )

        new_brick = VersionedBrick("2.0", multiplier=3)

        # Mock monitor function (always success)
        async def monitor(result):
            return True

        success = await controller.start_canary(new_brick, monitor)
        assert success

        # Simulate successful invocations
        for _ in range(10):
            controller.record_result(True)

        # Give time for monitoring to process
        await asyncio.sleep(1.5)

        # Check that rollout increased
        status = pipeline.get_status()
        component_status = status["components"][0]
        # Should have moved to next stage (25%)
        assert component_status["rollout_percent"] > 5

    async def test_canary_rollback(self):
        """Test canary rollback on failures."""
        brick1 = VersionedBrick("1.0", multiplier=2)
        pipeline = SwappablePipeline([brick1])

        controller = CanaryController(
            pipeline, position=0, success_threshold=0.8, sample_size=10
        )

        new_brick = VersionedBrick("2.0", multiplier=3)

        # Mock monitor function
        async def monitor(result):
            return True

        await controller.start_canary(new_brick, monitor)

        # Simulate mostly failures
        for _ in range(3):
            controller.record_result(True)
        for _ in range(7):
            controller.record_result(False)

        # Give time for monitoring to process
        await asyncio.sleep(1.5)

        # Check that rollback occurred
        status = pipeline.get_status()
        component_status = status["components"][0]
        assert component_status["new_brick"] is None
        assert component_status["rollout_percent"] == 0
