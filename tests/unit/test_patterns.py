"""Tests for advanced composition patterns."""

import asyncio
from typing import Any

import pytest

from nanobricks.patterns import (
    Branch,
    Cache,
    FanIn,
    FanOut,
    Map,
    Parallel,
    Pipeline,
    Reduce,
    Retry,
    Switch,
)
from nanobricks.protocol import NanobrickBase


class AddOne(NanobrickBase[int, int, None]):
    """Test brick that adds one."""

    def __init__(self):
        self.name = "AddOne"
        self.version = "1.0.0"

    async def invoke(self, input: int, *, deps: None = None) -> int:
        return input + 1


class MultiplyByTwo(NanobrickBase[int, int, None]):
    """Test brick that multiplies by two."""

    def __init__(self):
        self.name = "MultiplyByTwo"
        self.version = "1.0.0"

    async def invoke(self, input: int, *, deps: None = None) -> int:
        return input * 2


class FailingNanobrick(NanobrickBase[Any, Any, None]):
    """Test brick that always fails."""

    def __init__(self, error_msg: str = "Test error"):
        self.name = "FailingBrick"
        self.version = "1.0.0"
        self.error_msg = error_msg
        self.call_count = 0

    async def invoke(self, input: Any, *, deps: None = None) -> Any:
        self.call_count += 1
        raise ValueError(self.error_msg)


class SlowBrick(NanobrickBase[int, int, None]):
    """Test brick with delay."""

    def __init__(self, delay: float = 0.1):
        self.name = "SlowBrick"
        self.version = "1.0.0"
        self.delay = delay

    async def invoke(self, input: int, *, deps: None = None) -> int:
        await asyncio.sleep(self.delay)
        return input


@pytest.mark.asyncio
class TestBranch:
    """Tests for Branch pattern."""

    async def test_true_branch(self):
        """Test branch takes true path."""
        branch = Branch(
            condition=lambda x: x > 0, true_path=AddOne(), false_path=MultiplyByTwo()
        )

        result = await branch.invoke(5)
        assert result == 6  # AddOne path

    async def test_false_branch(self):
        """Test branch takes false path."""
        branch = Branch(
            condition=lambda x: x > 0, true_path=AddOne(), false_path=MultiplyByTwo()
        )

        result = await branch.invoke(-5)
        assert result == -10  # MultiplyByTwo path


@pytest.mark.asyncio
class TestParallel:
    """Tests for Parallel pattern."""

    async def test_parallel_execution(self):
        """Test parallel execution of multiple bricks."""
        parallel = Parallel([AddOne(), MultiplyByTwo(), AddOne()])

        results = await parallel.invoke(5)
        assert results == [6, 10, 6]

    async def test_parallel_is_concurrent(self):
        """Test that execution is actually parallel."""
        import time

        start = time.time()
        parallel = Parallel([SlowBrick(0.1), SlowBrick(0.1), SlowBrick(0.1)])

        await parallel.invoke(1)
        elapsed = time.time() - start

        # Should take ~0.1s, not 0.3s
        assert elapsed < 0.2


@pytest.mark.asyncio
class TestFanOutFanIn:
    """Tests for FanOut/FanIn patterns."""

    async def test_fan_out(self):
        """Test fan-out to multiple branches."""
        fan_out = FanOut({"add": AddOne(), "multiply": MultiplyByTwo()})

        results = await fan_out.invoke(5)
        assert results == {"add": 6, "multiply": 10}

    async def test_fan_in_list(self):
        """Test fan-in with list merger."""
        fan_in = FanIn(lambda results: sum(results))

        result = await fan_in.invoke([1, 2, 3, 4])
        assert result == 10

    async def test_fan_in_dict(self):
        """Test fan-in with dict merger."""
        fan_in = FanIn(lambda results: results["a"] + results["b"])

        result = await fan_in.invoke({"a": 5, "b": 3})
        assert result == 8


@pytest.mark.asyncio
class TestPipeline:
    """Tests for Pipeline pattern."""

    async def test_pipeline_execution(self):
        """Test sequential pipeline execution."""
        pipeline = Pipeline([AddOne(), MultiplyByTwo(), AddOne()])

        result = await pipeline.invoke(5)
        assert result == 13  # ((5 + 1) * 2) + 1

    async def test_pipeline_with_error_handler(self):
        """Test pipeline with error recovery."""

        def error_handler(error: Exception, last_value: Any) -> Any:
            return last_value * 10

        pipeline = Pipeline(
            [AddOne(), FailingNanobrick(), MultiplyByTwo()], error_handler=error_handler
        )

        result = await pipeline.invoke(5)
        assert result == 120  # ((5 + 1) * 10) * 2


@pytest.mark.asyncio
class TestRetry:
    """Tests for Retry pattern."""

    async def test_retry_on_failure(self):
        """Test retry logic."""
        failing_brick = FailingNanobrick()
        retry = Retry(failing_brick, max_retries=3, backoff=0.01)

        with pytest.raises(ValueError):
            await retry.invoke(5)

        assert failing_brick.call_count == 4  # 1 initial + 3 retries

    async def test_retry_succeeds_eventually(self):
        """Test retry succeeds on second attempt."""

        class FlakeyBrick(NanobrickBase[int, int, None]):
            def __init__(self):
                self.name = "FlakeyBrick"
                self.version = "1.0.0"
                self.attempts = 0

            async def invoke(self, input: int, *, deps: None = None) -> int:
                self.attempts += 1
                if self.attempts < 2:
                    raise ValueError("Not yet!")
                return input * 2

        flakey = FlakeyBrick()
        retry = Retry(flakey, max_retries=3)

        result = await retry.invoke(5)
        assert result == 10
        assert flakey.attempts == 2


@pytest.mark.asyncio
class TestMap:
    """Tests for Map pattern."""

    async def test_map_sequential(self):
        """Test sequential mapping."""
        mapper = Map(AddOne(), parallel=False)

        results = await mapper.invoke([1, 2, 3, 4])
        assert results == [2, 3, 4, 5]

    async def test_map_parallel(self):
        """Test parallel mapping."""
        mapper = Map(AddOne(), parallel=True)

        results = await mapper.invoke([1, 2, 3, 4])
        assert results == [2, 3, 4, 5]


@pytest.mark.asyncio
class TestReduce:
    """Tests for Reduce pattern."""

    async def test_reduce_sum(self):
        """Test reduce for summation."""

        class Summer(NanobrickBase[tuple[int, int], int, None]):
            def __init__(self):
                self.name = "Summer"
                self.version = "1.0.0"

            async def invoke(self, input: tuple[int, int], *, deps: None = None) -> int:
                acc, item = input
                return acc + item

        reducer = Reduce(Summer(), initial=0)

        result = await reducer.invoke([1, 2, 3, 4])
        assert result == 10


@pytest.mark.asyncio
class TestSwitch:
    """Tests for Switch pattern."""

    async def test_switch_routing(self):
        """Test switch routes correctly."""
        switch = Switch(
            selector=lambda x: "even" if x % 2 == 0 else "odd",
            cases={"even": MultiplyByTwo(), "odd": AddOne()},
        )

        assert await switch.invoke(4) == 8  # even -> multiply
        assert await switch.invoke(5) == 6  # odd -> add

    async def test_switch_default(self):
        """Test switch default case."""
        switch = Switch(
            selector=lambda x: str(x), cases={"1": AddOne()}, default=MultiplyByTwo()
        )

        assert await switch.invoke(1) == 2  # case "1"
        assert await switch.invoke(5) == 10  # default


@pytest.mark.asyncio
class TestCache:
    """Tests for Cache pattern."""

    async def test_cache_hit(self):
        """Test cache returns cached value."""
        slow_brick = SlowBrick(0.1)
        cached = Cache(slow_brick)

        # First call
        import time

        start = time.time()
        result1 = await cached.invoke(5)
        elapsed1 = time.time() - start

        # Second call (should be cached)
        start = time.time()
        result2 = await cached.invoke(5)
        elapsed2 = time.time() - start

        assert result1 == result2 == 5
        assert elapsed1 > 0.09  # First call is slow
        assert elapsed2 < 0.01  # Second call is fast

    async def test_cache_ttl(self):
        """Test cache TTL expiration."""
        cached = Cache(AddOne(), ttl=0.05)

        # First call
        result1 = await cached.invoke(5)
        assert result1 == 6

        # Within TTL
        result2 = await cached.invoke(5)
        assert result2 == 6

        # After TTL
        await asyncio.sleep(0.06)
        result3 = await cached.invoke(5)
        assert result3 == 6  # Still correct, just re-executed
