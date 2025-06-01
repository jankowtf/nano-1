"""Tests for performance optimization features."""

import asyncio
import time
from unittest.mock import MagicMock, patch

import pytest

from nanobricks.performance import (
    NanobrickBatched,
    Benchmark,
    NanobrickCached,
    ConnectionPool,
    FusedPipeline,
    MemoryPool,
    fuse_pipeline,
    get_system_metrics,
    with_batching,
    with_cache,
)
from nanobricks.protocol import NanobrickBase


class SlowBrick(NanobrickBase[int, int, None]):
    """Test brick that adds delay."""

    def __init__(self, delay: float = 0.01):
        super().__init__(name="slow", version="1.0.0")
        self.delay = delay
        self.call_count = 0

    async def invoke(self, input: int, *, deps: None = None) -> int:
        self.call_count += 1
        await asyncio.sleep(self.delay)
        return input * 2


class ErrorNanobrick(NanobrickBase[int, int, None]):
    """Test brick that raises errors."""

    def __init__(self):
        super().__init__(name="error", version="1.0.0")

    async def invoke(self, input: int, *, deps: None = None) -> int:
        if input < 0:
            raise ValueError("Negative input not allowed")
        return input


class TestCachedBrick:
    """Test caching functionality."""

    @pytest.mark.asyncio
    async def test_cache_hit(self):
        """Test cache hits."""
        slow_brick = SlowBrick(delay=0.1)
        cached = NanobrickCached(slow_brick, max_size=10)

        # First call - cache miss
        start = time.time()
        result1 = await cached.invoke(5)
        duration1 = time.time() - start

        assert result1 == 10
        assert slow_brick.call_count == 1
        assert duration1 >= 0.1

        # Second call - cache hit
        start = time.time()
        result2 = await cached.invoke(5)
        duration2 = time.time() - start

        assert result2 == 10
        assert slow_brick.call_count == 1  # No additional call
        assert duration2 < 0.01  # Much faster

    @pytest.mark.asyncio
    async def test_cache_ttl(self):
        """Test cache TTL expiration."""
        slow_brick = SlowBrick()
        cached = NanobrickCached(slow_brick, max_size=10, ttl=0.1)

        # First call
        result1 = await cached.invoke(5)
        assert result1 == 10
        assert slow_brick.call_count == 1

        # Wait for TTL to expire
        await asyncio.sleep(0.15)

        # Second call - should be cache miss
        result2 = await cached.invoke(5)
        assert result2 == 10
        assert slow_brick.call_count == 2

    @pytest.mark.asyncio
    async def test_cache_lru_eviction(self):
        """Test LRU eviction."""
        slow_brick = SlowBrick()
        cached = NanobrickCached(slow_brick, max_size=3)

        # Fill cache
        for i in range(3):
            await cached.invoke(i)
        assert slow_brick.call_count == 3

        # Add one more - should evict oldest
        await cached.invoke(3)
        assert slow_brick.call_count == 4

        # Access first item - should be cache miss
        await cached.invoke(0)
        assert slow_brick.call_count == 5

    @pytest.mark.asyncio
    async def test_cache_error_caching(self):
        """Test error caching."""
        error_brick = ErrorNanobrick()
        cached = NanobrickCached(error_brick, cache_errors=True)

        # First call - raises error
        with pytest.raises(ValueError):
            await cached.invoke(-1)

        # Second call - cached error
        with pytest.raises(ValueError):
            await cached.invoke(-1)

    def test_cache_info(self):
        """Test cache statistics."""
        slow_brick = SlowBrick()
        cached = NanobrickCached(slow_brick, max_size=10)

        info = cached.cache_info()
        assert info["size"] == 0
        assert info["max_size"] == 10
        assert info["ttl"] is None


class TestBatchedBrick:
    """Test batching functionality."""

    @pytest.mark.asyncio
    async def test_batch_processing(self):
        """Test batch processing."""
        slow_brick = SlowBrick()
        batched = NanobrickBatched(slow_brick, batch_size=5)

        inputs = [1, 2, 3, 4, 5]
        results = await batched.invoke(inputs)

        assert results == [2, 4, 6, 8, 10]
        assert slow_brick.call_count == 5

    def test_sync_batch(self):
        """Test synchronous batch invoke."""
        slow_brick = SlowBrick()
        batched = NanobrickBatched(slow_brick)

        results = batched.invoke_sync([1, 2, 3])
        assert results == [2, 4, 6]


class TestFusedPipeline:
    """Test pipeline fusion."""

    @pytest.mark.asyncio
    async def test_fused_execution(self):
        """Test fused pipeline execution."""
        brick1 = SlowBrick(delay=0.01)
        brick2 = SlowBrick(delay=0.01)
        brick3 = SlowBrick(delay=0.01)

        fused = FusedPipeline([brick1, brick2, brick3])

        result = await fused.invoke(2)
        # 2 -> 4 -> 8 -> 16
        assert result == 16

    @pytest.mark.asyncio
    async def test_fused_composition(self):
        """Test composing fused pipelines."""
        brick1 = SlowBrick()
        brick2 = SlowBrick()
        brick3 = SlowBrick()

        fused1 = FusedPipeline([brick1, brick2])
        fused2 = fused1 | brick3

        assert isinstance(fused2, FusedPipeline)
        assert len(fused2._bricks) == 3

    def test_empty_pipeline_error(self):
        """Test that empty pipeline raises error."""
        with pytest.raises(ValueError, match="Need at least one brick"):
            FusedPipeline([])


class TestMemoryPool:
    """Test memory pooling."""

    def test_pool_acquire_release(self):
        """Test acquiring and releasing from pool."""
        factory = lambda: {"id": id({})}
        pool = MemoryPool(factory, size=3)

        # Acquire objects
        obj1 = pool.acquire()
        obj2 = pool.acquire()

        assert obj1 != obj2
        assert len(pool._in_use) == 2

        # Release back to pool
        pool.release(obj1)
        assert len(pool._in_use) == 1

        # Acquire again - should get same object
        obj3 = pool.acquire()
        assert obj3 == obj1

    def test_pool_overflow(self):
        """Test pool behavior when exhausted."""
        factory = lambda: {"id": id({})}
        pool = MemoryPool(factory, size=2)

        # Exhaust pool
        objs = [pool.acquire() for _ in range(3)]

        # Should create new object
        assert len(objs) == 3
        assert len(pool._pool) == 0

    def test_pool_reset(self):
        """Test object reset on release."""

        class ResettableObj:
            def __init__(self):
                self.value = 1

            def reset(self):
                self.value = 0

        pool = MemoryPool(ResettableObj, size=1)

        obj = pool.acquire()
        obj.value = 42
        pool.release(obj)

        obj2 = pool.acquire()
        assert obj2.value == 0  # Was reset


class TestConnectionPool:
    """Test connection pooling."""

    @pytest.mark.asyncio
    async def test_pool_lifecycle(self):
        """Test connection pool lifecycle."""
        conn_id = 0

        def factory():
            nonlocal conn_id
            conn_id += 1
            return {"id": conn_id, "closed": False}

        pool = ConnectionPool(factory, min_size=2, max_size=5)

        # Acquire connection
        conn = await pool.acquire()
        assert conn["id"] in [1, 2]

        stats = pool.get_stats()
        assert stats["created"] == 2
        assert stats["in_use"] == 1

        # Release connection
        await pool.release(conn)

        stats = pool.get_stats()
        assert stats["available"] == 2
        assert stats["in_use"] == 0

        # Close pool
        await pool.close()

    @pytest.mark.asyncio
    async def test_pool_max_size(self):
        """Test pool maximum size enforcement."""
        factory = lambda: {"id": id({})}
        pool = ConnectionPool(factory, min_size=1, max_size=2)

        # Acquire up to max
        conn1 = await pool.acquire()
        conn2 = await pool.acquire()

        # Try to acquire more - should timeout
        with pytest.raises(asyncio.TimeoutError):
            await asyncio.wait_for(pool.acquire(), timeout=0.1)

        # Release one
        await pool.release(conn1)

        # Now should work
        conn3 = await pool.acquire()
        assert conn3 == conn1

        await pool.close()

    @pytest.mark.asyncio
    async def test_pool_async_factory(self):
        """Test pool with async factory."""

        async def async_factory():
            await asyncio.sleep(0.01)
            return {"id": id({})}

        pool = ConnectionPool(async_factory)
        conn = await pool.acquire()
        assert "id" in conn

        await pool.release(conn)
        await pool.close()


class TestBenchmark:
    """Test benchmarking utilities."""

    @pytest.mark.asyncio
    async def test_benchmark_sync_function(self):
        """Test benchmarking synchronous function."""

        def test_func():
            time.sleep(0.001)
            return 42

        benchmark = Benchmark("test_sync")
        result = await benchmark.measure(test_func, iterations=10, warmup=2)

        assert result.name == "test_sync"
        assert result.iterations == 10
        assert result.avg_time >= 0.001
        assert result.ops_per_sec > 0

    @pytest.mark.asyncio
    async def test_benchmark_async_function(self):
        """Test benchmarking async function."""

        async def test_func():
            await asyncio.sleep(0.001)
            return 42

        benchmark = Benchmark("test_async")
        result = await benchmark.measure(test_func, iterations=10, warmup=2)

        assert result.name == "test_async"
        assert result.iterations == 10
        assert result.avg_time >= 0.001


class TestUtilityFunctions:
    """Test utility functions."""

    def test_with_cache(self):
        """Test with_cache helper."""
        brick = SlowBrick()
        cached = with_cache(brick, max_size=50, ttl=60)

        assert isinstance(cached, CachedBrick)
        assert cached._max_size == 50
        assert cached._ttl == 60

    def test_with_batching(self):
        """Test with_batching helper."""
        brick = SlowBrick()
        batched = with_batching(brick, batch_size=20, timeout=0.5)

        assert isinstance(batched, BatchedBrick)
        assert batched._batch_size == 20
        assert batched._timeout == 0.5

    def test_fuse_pipeline_helper(self):
        """Test fuse_pipeline helper."""
        bricks = [SlowBrick(), SlowBrick(), SlowBrick()]
        fused = fuse_pipeline(bricks)

        assert isinstance(fused, FusedPipeline)
        assert len(fused._bricks) == 3

    @patch("nanobricks.performance.psutil")
    def test_get_system_metrics(self, mock_psutil):
        """Test system metrics collection."""
        # Mock psutil responses
        mock_psutil.cpu_percent.return_value = 25.0
        mock_psutil.cpu_count.return_value = 8
        mock_psutil.cpu_freq.return_value = MagicMock(_asdict=lambda: {"current": 2400})
        mock_psutil.virtual_memory.return_value = MagicMock(
            _asdict=lambda: {"percent": 50}
        )
        mock_psutil.disk_io_counters.return_value = MagicMock(
            _asdict=lambda: {"read_bytes": 1000}
        )
        mock_psutil.net_io_counters.return_value = MagicMock(
            _asdict=lambda: {"bytes_sent": 2000}
        )

        metrics = get_system_metrics()

        assert metrics["cpu"]["percent"] == 25.0
        assert metrics["cpu"]["count"] == 8
        assert metrics["memory"]["percent"] == 50
        assert metrics["disk_io"]["read_bytes"] == 1000
        assert metrics["network_io"]["bytes_sent"] == 2000
        assert "timestamp" in metrics

    def test_get_system_metrics_no_psutil(self):
        """Test system metrics without psutil."""
        with patch.dict("sys.modules", {"psutil": None}):
            metrics = get_system_metrics()
            assert metrics["error"] == "psutil not installed"
            assert "timestamp" in metrics
