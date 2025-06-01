"""Tests for performance optimization utilities."""

import asyncio
import time

import pytest

from nanobricks.composition import Pipeline
from nanobricks.performance import (
    NanobrickBatched,
    NanobrickCached,
    FusedPipeline,
    MemoryPool,
    fuse_pipeline,
    with_batching,
    with_cache,
)
from nanobricks.protocol import NanobrickBase


class CounterBrick(NanobrickBase[str, str, None]):
    """Test brick that counts invocations."""

    def __init__(self):
        self.name = "counter"
        self.version = "1.0.0"
        self.count = 0

    async def invoke(self, input: str, *, deps=None) -> str:
        self.count += 1
        return f"{input}_{self.count}"


class SlowBrick(NanobrickBase[str, str, None]):
    """Test brick with artificial delay."""

    def __init__(self, delay: float = 0.1):
        self.name = "slow"
        self.version = "1.0.0"
        self.delay = delay
        self.count = 0

    async def invoke(self, input: str, *, deps=None) -> str:
        self.count += 1
        await asyncio.sleep(self.delay)
        return input.upper()


class ErrorNanobrick(NanobrickBase[str, str, None]):
    """Test brick that raises errors."""

    def __init__(self):
        self.name = "error"
        self.version = "1.0.0"
        self.count = 0

    async def invoke(self, input: str, *, deps=None) -> str:
        self.count += 1
        if input == "error":
            raise ValueError("Test error")
        return input


class TestCachedBrick:
    """Tests for CachedBrick."""

    @pytest.mark.asyncio
    async def test_cache_hit(self):
        """Test cache hits reduce invocations."""
        brick = CounterBrick()
        cached = NanobrickCached(brick, max_size=10)

        # First call - cache miss
        result1 = await cached.invoke("test")
        assert result1 == "test_1"
        assert brick.count == 1

        # Second call - cache hit
        result2 = await cached.invoke("test")
        assert result2 == "test_1"  # Same result
        assert brick.count == 1  # No new invocation

        # Different input - cache miss
        result3 = await cached.invoke("other")
        assert result3 == "other_2"
        assert brick.count == 2

    @pytest.mark.asyncio
    async def test_cache_ttl(self):
        """Test cache TTL expiration."""
        brick = CounterBrick()
        cached = NanobrickCached(brick, max_size=10, ttl=0.1)

        # First call
        result1 = await cached.invoke("test")
        assert result1 == "test_1"

        # Immediate second call - cache hit
        result2 = await cached.invoke("test")
        assert result2 == "test_1"
        assert brick.count == 1

        # Wait for TTL expiration
        await asyncio.sleep(0.15)

        # Third call - cache miss due to expiration
        result3 = await cached.invoke("test")
        assert result3 == "test_2"
        assert brick.count == 2

    @pytest.mark.asyncio
    async def test_cache_lru_eviction(self):
        """Test LRU eviction when cache is full."""
        brick = CounterBrick()
        cached = NanobrickCached(brick, max_size=2)

        # Fill cache
        await cached.invoke("a")  # a_1
        await cached.invoke("b")  # b_2

        # Access 'a' again to make it more recent
        await cached.invoke("a")  # Still a_1

        # Add new item - should evict 'b'
        await cached.invoke("c")  # c_3

        # 'b' should be evicted, 'a' should still be cached
        result_a = await cached.invoke("a")
        assert result_a == "a_1"  # Cache hit

        result_b = await cached.invoke("b")
        assert result_b == "b_4"  # Cache miss, new invocation

    @pytest.mark.asyncio
    async def test_cache_error_handling(self):
        """Test caching of errors."""
        brick = ErrorNanobrick()
        cached = NanobrickCached(brick, max_size=10, cache_errors=True)

        # First call raises error
        with pytest.raises(ValueError):
            await cached.invoke("error")
        assert brick.count == 1

        # Second call - cached error
        with pytest.raises(ValueError):
            await cached.invoke("error")
        assert brick.count == 1  # No new invocation

        # Success case
        result = await cached.invoke("success")
        assert result == "success"

    def test_cache_info(self):
        """Test cache statistics."""
        brick = CounterBrick()
        cached = NanobrickCached(brick, max_size=10, ttl=60)

        info = cached.cache_info()
        assert info["size"] == 0
        assert info["max_size"] == 10
        assert info["ttl"] == 60

    def test_clear_cache(self):
        """Test cache clearing."""
        brick = CounterBrick()
        cached = NanobrickCached(brick, max_size=10)

        # Add to cache
        asyncio.run(cached.invoke("test"))
        assert cached.cache_info()["size"] == 1

        # Clear cache
        cached.clear_cache()
        assert cached.cache_info()["size"] == 0


class TestBatchedBrick:
    """Tests for BatchedBrick."""

    @pytest.mark.asyncio
    async def test_batch_processing(self):
        """Test batch processing of inputs."""
        brick = CounterBrick()
        batched = NanobrickBatched(brick)

        # Process batch
        inputs = ["a", "b", "c"]
        results = await batched.invoke(inputs)

        assert len(results) == 3
        assert results == ["a_1", "b_2", "c_3"]
        assert brick.count == 3

    @pytest.mark.asyncio
    async def test_batch_error_handling(self):
        """Test error handling in batches."""
        brick = ErrorNanobrick()
        batched = NanobrickBatched(brick)

        # Mix of success and error inputs
        inputs = ["success", "error", "ok"]

        # First two should succeed, then error
        results = await batched.invoke(inputs[:1])
        assert results == ["success"]

        # Error case
        with pytest.raises(ValueError):
            await batched.invoke(["error"])


class TestFusedPipeline:
    """Tests for FusedPipeline."""

    @pytest.mark.asyncio
    async def test_fused_execution(self):
        """Test fused pipeline execution."""

        class UpperNanobrick(NanobrickBase[str, str, None]):
            name = "upper"
            version = "1.0.0"

            async def invoke(self, input: str, *, deps=None) -> str:
                return input.upper()

        class AddExclamationBrick(NanobrickBase[str, str, None]):
            name = "exclaim"
            version = "1.0.0"

            async def invoke(self, input: str, *, deps=None) -> str:
                return f"{input}!"

        # Create fused pipeline
        bricks = [UpperNanobrick(), AddExclamationBrick()]
        fused = FusedPipeline(bricks)

        result = await fused.invoke("hello")
        assert result == "HELLO!"

    @pytest.mark.asyncio
    async def test_fused_composition(self):
        """Test composing fused pipelines."""

        class DoubleBrick(NanobrickBase[str, str, None]):
            name = "double"
            version = "1.0.0"

            async def invoke(self, input: str, *, deps=None) -> str:
                return input + input

        brick1 = CounterBrick()
        brick2 = DoubleBrick()

        fused1 = FusedPipeline([brick1])
        fused2 = fused1 | brick2

        assert isinstance(fused2, FusedPipeline)
        result = await fused2.invoke("x")
        assert result == "x_1x_1"

    def test_empty_pipeline_error(self):
        """Test error on empty pipeline."""
        with pytest.raises(ValueError):
            FusedPipeline([])


class TestMemoryPool:
    """Tests for MemoryPool."""

    def test_pool_acquire_release(self):
        """Test acquiring and releasing from pool."""
        created_count = 0

        def factory():
            nonlocal created_count
            created_count += 1
            return {"id": created_count}

        pool = MemoryPool(factory, size=2)

        # Pool should be pre-populated
        assert created_count == 2

        # Acquire objects
        obj1 = pool.acquire()
        obj2 = pool.acquire()
        assert obj1["id"] == 2  # LIFO order
        assert obj2["id"] == 1

        # Pool is empty, new object created
        obj3 = pool.acquire()
        assert created_count == 3
        assert obj3["id"] == 3

        # Release back to pool
        pool.release(obj1)
        pool.release(obj2)

        # Acquire again - should reuse
        obj4 = pool.acquire()
        assert obj4["id"] in [1, 2]  # Reused one of the released objects
        assert created_count == 3  # No new objects

    def test_pool_size_limit(self):
        """Test pool size is respected."""
        pool = MemoryPool(dict, size=2)

        obj1 = pool.acquire()
        obj2 = pool.acquire()
        obj3 = pool.acquire()

        # Release all
        pool.release(obj1)
        pool.release(obj2)
        pool.release(obj3)  # This one shouldn't be kept

        # Only 2 should be in pool
        reused1 = pool.acquire()
        reused2 = pool.acquire()
        new_obj = pool.acquire()

        assert reused1 is obj2 or reused1 is obj1
        assert reused2 is obj2 or reused2 is obj1
        assert new_obj is not obj3  # obj3 was discarded

    def test_pool_with_reset(self):
        """Test pool with resettable objects."""

        class ResettableDict(dict):
            def reset(self):
                self.clear()

        pool = MemoryPool(ResettableDict, size=2)

        obj = pool.acquire()
        obj["key"] = "value"

        pool.release(obj)

        # Acquire again - should be reset
        reused = pool.acquire()
        assert "key" not in reused


class TestUtilityFunctions:
    """Tests for utility functions."""

    @pytest.mark.asyncio
    async def test_with_cache(self):
        """Test with_cache utility."""
        brick = CounterBrick()
        cached = with_cache(brick, max_size=5, ttl=10)

        assert isinstance(cached, CachedBrick)
        assert cached._max_size == 5
        assert cached._ttl == 10

        # Test it works
        result1 = await cached.invoke("test")
        result2 = await cached.invoke("test")
        assert result1 == result2
        assert brick.count == 1

    @pytest.mark.asyncio
    async def test_with_batching(self):
        """Test with_batching utility."""
        brick = CounterBrick()
        batched = with_batching(brick, batch_size=5, timeout=0.5)

        assert isinstance(batched, BatchedBrick)
        assert batched._batch_size == 5
        assert batched._timeout == 0.5

        # Test it works
        results = await batched.invoke(["a", "b"])
        assert results == ["a_1", "b_2"]

    @pytest.mark.asyncio
    async def test_fuse_pipeline_from_list(self):
        """Test fuse_pipeline with list of bricks."""
        brick1 = CounterBrick()
        brick2 = CounterBrick()

        fused = fuse_pipeline([brick1, brick2])
        assert isinstance(fused, FusedPipeline)

        result = await fused.invoke("test")
        assert result == "test_1_1"

    @pytest.mark.asyncio
    async def test_fuse_pipeline_from_pipeline(self):
        """Test fuse_pipeline with Pipeline object."""
        brick1 = CounterBrick()
        brick2 = CounterBrick()
        pipeline = Pipeline(brick1, brick2)

        fused = fuse_pipeline(pipeline)
        assert isinstance(fused, FusedPipeline)

        result = await fused.invoke("test")
        assert result == "test_1_1"


@pytest.mark.asyncio
async def test_performance_improvement():
    """Test that optimizations actually improve performance."""
    # Create slow brick
    slow = SlowBrick(delay=0.05)

    # Time without cache
    start = time.time()
    for _ in range(3):
        await slow.invoke("test")
    uncached_time = time.time() - start

    # Time with cache
    cached = with_cache(slow)
    start = time.time()
    for _ in range(3):
        await cached.invoke("test")
    cached_time = time.time() - start

    # Cached should be significantly faster
    assert cached_time < uncached_time / 2
    assert slow.count == 4  # 3 uncached + 1 cached
