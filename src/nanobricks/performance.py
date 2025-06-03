"""Performance optimization utilities for nanobricks.

Provides caching, batching, and pipeline fusion optimizations.
"""

import asyncio
import hashlib
import pickle
import time
from collections.abc import Callable
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from datetime import datetime
from functools import lru_cache
from typing import Any, TypeVar

from nanobricks.composition import NanobrickComposite, Pipeline
from nanobricks.protocol import NanobrickProtocol

T = TypeVar("T")
T_in = TypeVar("T_in")
T_out = TypeVar("T_out")
T_deps = TypeVar("T_deps")


class NanobrickCached(NanobrickProtocol[T_in, T_out, T_deps]):
    """Wraps a nanobrick with caching capabilities."""

    def __init__(
        self,
        brick: NanobrickProtocol[T_in, T_out, T_deps],
        max_size: int = 128,
        ttl: float | None = None,
        cache_errors: bool = False,
    ):
        """Initialize cached brick.

        Args:
            brick: The nanobrick to cache
            max_size: Maximum cache size (uses LRU eviction)
            ttl: Time-to-live in seconds (None = no expiration)
            cache_errors: Whether to cache exceptions
        """
        self._brick = brick
        self._max_size = max_size
        self._ttl = ttl
        self._cache_errors = cache_errors
        self._cache: dict[str, tuple[T_out, float]] = {}
        self._error_cache: dict[str, tuple[Exception, float]] = {}
        self._access_order: list[str] = []

        # Inherit metadata
        self.name = f"cached_{brick.name}"
        self.version = brick.version

    def _make_key(self, input: T_in, deps: T_deps | None) -> str:
        """Generate cache key from input and deps."""
        try:
            # Try to pickle for hashing
            data = (input, deps)
            return hashlib.sha256(pickle.dumps(data)).hexdigest()
        except Exception:
            # Fallback to string representation
            return hashlib.sha256(str((input, deps)).encode()).hexdigest()

    def _is_expired(self, timestamp: float) -> bool:
        """Check if cache entry is expired."""
        if self._ttl is None:
            return False
        return time.time() - timestamp > self._ttl

    def _evict_lru(self) -> None:
        """Evict least recently used entry."""
        if self._access_order:
            lru_key = self._access_order.pop(0)
            self._cache.pop(lru_key, None)
            self._error_cache.pop(lru_key, None)

    async def invoke(self, input: T_in, *, deps: T_deps = None) -> T_out:
        """Invoke with caching."""
        key = self._make_key(input, deps)
        current_time = time.time()

        # Check cache hit
        if key in self._cache:
            value, timestamp = self._cache[key]
            if not self._is_expired(timestamp):
                # Update access order
                if key in self._access_order:
                    self._access_order.remove(key)
                self._access_order.append(key)
                return value
            else:
                # Remove expired entry
                del self._cache[key]
                if key in self._access_order:
                    self._access_order.remove(key)

        # Check error cache
        if self._cache_errors and key in self._error_cache:
            error, timestamp = self._error_cache[key]
            if not self._is_expired(timestamp):
                raise error
            else:
                del self._error_cache[key]

        # Cache miss - invoke brick
        try:
            result = await self._brick.invoke(input, deps=deps)

            # Store in cache
            if len(self._cache) >= self._max_size:
                self._evict_lru()

            self._cache[key] = (result, current_time)
            self._access_order.append(key)

            return result

        except Exception as e:
            if self._cache_errors:
                if len(self._error_cache) >= self._max_size:
                    self._evict_lru()
                self._error_cache[key] = (e, current_time)
            raise

    def invoke_sync(self, input: T_in, *, deps: T_deps = None) -> T_out:
        """Synchronous invoke with caching."""
        return asyncio.run(self.invoke(input, deps=deps))

    def __rshift__(self, other: NanobrickProtocol) -> NanobrickProtocol:
        """Compose with another brick."""
        return CompositeBrick(self, other)

    def __or__(self, other):
            """
            Backwards compatibility for | operator. 
            DEPRECATED: Use >> instead. Will be removed in v0.3.0.
            """
            import warnings
            warnings.warn(
                "The | operator for nanobrick composition is deprecated. "
                "Use >> instead. This will be removed in v0.3.0.",
                DeprecationWarning,
                stacklevel=2
            )
            return self.__rshift__(other)

    def clear_cache(self) -> None:
        """Clear all cached entries."""
        self._cache.clear()
        self._error_cache.clear()
        self._access_order.clear()

    def cache_info(self) -> dict[str, Any]:
        """Get cache statistics."""
        return {
            "size": len(self._cache),
            "error_size": len(self._error_cache),
            "max_size": self._max_size,
            "ttl": self._ttl,
            "hits": getattr(self, "_hits", 0),
            "misses": getattr(self, "_misses", 0),
        }


class NanobrickBatched(NanobrickProtocol[list[T_in], list[T_out], T_deps]):
    """Batches multiple invocations for efficiency."""

    def __init__(
        self,
        brick: NanobrickProtocol[T_in, T_out, T_deps],
        batch_size: int = 10,
        timeout: float = 0.1,
    ):
        """Initialize batched brick.

        Args:
            brick: The nanobrick to batch
            batch_size: Maximum batch size
            timeout: Maximum time to wait for batch to fill
        """
        self._brick = brick
        self._batch_size = batch_size
        self._timeout = timeout
        self._pending: list[tuple[T_in, asyncio.Future]] = []
        self._lock = asyncio.Lock()
        self._batch_task: asyncio.Task | None = None

        self.name = f"batched_{brick.name}"
        self.version = brick.version

    async def _process_batch(self) -> None:
        """Process pending batch."""
        async with self._lock:
            if not self._pending:
                return

            batch = self._pending[: self._batch_size]
            self._pending = self._pending[self._batch_size :]

        # Process batch items
        for input_data, future in batch:
            try:
                result = await self._brick.invoke(input_data)
                future.set_result(result)
            except Exception as e:
                future.set_exception(e)

    async def invoke(self, input: list[T_in], *, deps: T_deps = None) -> list[T_out]:
        """Batch invoke multiple inputs."""
        results = []

        for item in input:
            result = await self._brick.invoke(item, deps=deps)
            results.append(result)

        return results

    def invoke_sync(self, input: list[T_in], *, deps: T_deps = None) -> list[T_out]:
        """Synchronous batch invoke."""
        return asyncio.run(self.invoke(input, deps=deps))

    def __rshift__(self, other: NanobrickProtocol) -> NanobrickProtocol:
        """Compose with another brick."""
        return CompositeBrick(self, other)

    def __or__(self, other):
            """
            Backwards compatibility for | operator. 
            DEPRECATED: Use >> instead. Will be removed in v0.3.0.
            """
            import warnings
            warnings.warn(
                "The | operator for nanobrick composition is deprecated. "
                "Use >> instead. This will be removed in v0.3.0.",
                DeprecationWarning,
                stacklevel=2
            )
            return self.__rshift__(other)


class FusedPipeline(NanobrickProtocol[T_in, T_out, T_deps]):
    """Optimized pipeline that fuses operations to reduce overhead."""

    def __init__(self, bricks: list[NanobrickProtocol]):
        """Initialize fused pipeline.

        Args:
            bricks: List of bricks to fuse
        """
        if not bricks:
            raise ValueError("Need at least one brick")

        self._bricks = bricks
        self._fused_invoke = self._create_fused_invoke()

        # Metadata from first and last bricks
        self.name = f"fused_{bricks[0].name}_to_{bricks[-1].name}"
        self.version = "1.0.0"

    def _create_fused_invoke(self) -> Callable:
        """Create optimized fused invoke function."""

        # For simple transformations, we can optimize by reducing async overhead
        async def fused_invoke(input_data: Any, deps: Any | None = None) -> Any:
            result = input_data

            # Process all bricks in sequence with minimal overhead
            for brick in self._bricks:
                result = await brick.invoke(result, deps=deps)

            return result

        return fused_invoke

    async def invoke(self, input: T_in, *, deps: T_deps = None) -> T_out:
        """Invoke fused pipeline."""
        return await self._fused_invoke(input, deps)

    def invoke_sync(self, input: T_in, *, deps: T_deps = None) -> T_out:
        """Synchronous fused invoke."""
        return asyncio.run(self.invoke(input, deps=deps))

    def __rshift__(self, other: NanobrickProtocol) -> NanobrickProtocol:
        """Extend the fused pipeline."""
        if isinstance(other, FusedPipeline):
            return FusedPipeline(self._bricks + other._bricks)
        else:
            return FusedPipeline(self._bricks + [other])
    
    def __or__(self, other):
        """Backwards compatibility for | operator. DEPRECATED: Use >> instead."""
        import warnings
        warnings.warn(
            "The | operator for nanobrick composition is deprecated. "
            "Use >> instead. This will be removed in v0.3.0.",
            DeprecationWarning,
            stacklevel=2
        )
        return self.__rshift__(other)


class MemoryPool:
    """Memory pool for reducing allocation overhead."""

    def __init__(self, object_factory: Callable[[], T], size: int = 10):
        """Initialize memory pool.

        Args:
            object_factory: Factory function to create pooled objects
            size: Pool size
        """
        self._factory = object_factory
        self._size = size
        self._pool: list[T] = []
        self._in_use: set = set()  # Track objects by id instead of weak references

        # Pre-populate pool
        for _ in range(size):
            self._pool.append(self._factory())

    def acquire(self) -> T:
        """Acquire object from pool."""
        if self._pool:
            obj = self._pool.pop()
        else:
            obj = self._factory()

        self._in_use.add(id(obj))
        return obj

    def release(self, obj: T) -> None:
        """Release object back to pool."""
        obj_id = id(obj)
        if obj_id in self._in_use:
            self._in_use.remove(obj_id)

            if len(self._pool) < self._size:
                # Reset object state if it has a reset method
                if hasattr(obj, "reset"):
                    obj.reset()
                self._pool.append(obj)


# Performance optimization utilities
def with_cache(
    brick: NanobrickProtocol[T_in, T_out, T_deps],
    max_size: int = 128,
    ttl: float | None = None,
) -> NanobrickCached[T_in, T_out, T_deps]:
    """Add caching to a nanobrick."""
    return NanobrickCached(brick, max_size=max_size, ttl=ttl)


def with_batching(
    brick: NanobrickProtocol[T_in, T_out, T_deps],
    batch_size: int = 10,
    timeout: float = 0.1,
) -> NanobrickBatched[T_in, T_out, T_deps]:
    """Add batching to a nanobrick."""
    return NanobrickBatched(brick, batch_size=batch_size, timeout=timeout)


def fuse_pipeline(pipeline: Pipeline | list[NanobrickProtocol]) -> FusedPipeline:
    """Fuse a pipeline for better performance."""
    if isinstance(pipeline, Pipeline):
        bricks = pipeline.bricks
    else:
        bricks = pipeline

    return FusedPipeline(bricks)


@lru_cache(maxsize=1024)
def _memoized_transform(value: str, transform_type: str) -> str:
    """Memoized string transformation for common operations."""
    if transform_type == "upper":
        return value.upper()
    elif transform_type == "lower":
        return value.lower()
    elif transform_type == "strip":
        return value.strip()
    else:
        return value


# Connection pooling for external resources
class ConnectionPool:
    """Connection pool for managing external resources."""

    def __init__(
        self,
        factory: Callable[[], T],
        *,
        min_size: int = 1,
        max_size: int = 10,
        acquire_timeout: float = 5.0,
    ):
        """Initialize connection pool.

        Args:
            factory: Factory function to create connections
            min_size: Minimum pool size
            max_size: Maximum pool size
            acquire_timeout: Timeout for acquiring connection
        """
        self._factory = factory
        self._min_size = min_size
        self._max_size = max_size
        self._acquire_timeout = acquire_timeout
        self._pool: list[T] = []
        self._used: dict[int, T] = {}  # Track by id
        self._created = 0
        self._lock = asyncio.Lock()
        self._not_empty = asyncio.Condition()
        self._closed = False

    async def _create_connection(self) -> T:
        """Create new connection."""
        if asyncio.iscoroutinefunction(self._factory):
            return await self._factory()
        return self._factory()

    async def _ensure_min_connections(self) -> None:
        """Ensure minimum connections exist."""
        while self._created < self._min_size and not self._closed:
            conn = await self._create_connection()
            self._pool.append(conn)
            self._created += 1

    @asynccontextmanager
    async def acquire(self):
        """Acquire connection from pool."""
        if self._closed:
            raise RuntimeError("Pool is closed")

        # Initialize pool if needed
        if self._created == 0:
            async with self._lock:
                await self._ensure_min_connections()

        conn = None
        start_time = time.time()

        try:
            while True:
                async with self._not_empty:
                    # Try to get from pool
                    async with self._lock:
                        if self._pool:
                            conn = self._pool.pop()
                            self._used[id(conn)] = conn
                            break
                        elif self._created < self._max_size:
                            # Create new connection
                            conn = await self._create_connection()
                            self._created += 1
                            self._used[id(conn)] = conn
                            break

                    # Wait for connection with timeout
                    elapsed = time.time() - start_time
                    remaining = self._acquire_timeout - elapsed

                    if remaining <= 0:
                        raise TimeoutError("Acquire timeout")

                    try:
                        await asyncio.wait_for(
                            self._not_empty.wait(), timeout=remaining
                        )
                    except TimeoutError:
                        raise TimeoutError("Acquire timeout") from None

            yield conn

        finally:
            if conn is not None:
                await self.release(conn)

    async def release(self, conn: T) -> None:
        """Release connection back to pool."""
        async with self._lock:
            conn_id = id(conn)
            if conn_id in self._used:
                del self._used[conn_id]
                if len(self._pool) < self._max_size and not self._closed:
                    self._pool.append(conn)
        async with self._not_empty:
            self._not_empty.notify()

    async def close(self) -> None:
        """Close all connections."""
        async with self._lock:
            self._closed = True

            # Close all connections
            all_conns = list(self._pool) + list(self._used.values())
            self._pool.clear()
            self._used.clear()

            for conn in all_conns:
                if hasattr(conn, "close"):
                    if asyncio.iscoroutinefunction(conn.close):
                        await conn.close()
                    else:
                        conn.close()

    def get_stats(self) -> dict[str, int]:
        """Get pool statistics."""
        return {
            "created": self._created,
            "available": len(self._pool),
            "in_use": len(self._used),
            "total": self._created,
        }


# Performance benchmarking
@dataclass
class BenchmarkResult:
    """Result of a performance benchmark."""

    name: str
    total_time: float
    iterations: int
    avg_time: float
    min_time: float
    max_time: float
    ops_per_sec: float
    timestamp: datetime = field(default_factory=datetime.now)


class Benchmark:
    """Performance benchmarking utility."""

    def __init__(self, name: str):
        self.name = name
        self.results: list[float] = []

    async def measure(
        self,
        func: Callable[[], Any],
        iterations: int = 1000,
        warmup: int = 10,
    ) -> BenchmarkResult:
        """Measure function performance.

        Args:
            func: Function to benchmark
            iterations: Number of iterations
            warmup: Number of warmup iterations

        Returns:
            Benchmark results
        """
        # Warmup
        for _ in range(warmup):
            if asyncio.iscoroutinefunction(func):
                await func()
            else:
                func()

        # Measure
        times = []
        start_total = time.perf_counter()

        for _ in range(iterations):
            start = time.perf_counter()
            if asyncio.iscoroutinefunction(func):
                await func()
            else:
                func()
            end = time.perf_counter()
            times.append(end - start)

        end_total = time.perf_counter()
        total_time = end_total - start_total

        return BenchmarkResult(
            name=self.name,
            total_time=total_time,
            iterations=iterations,
            avg_time=sum(times) / len(times),
            min_time=min(times),
            max_time=max(times),
            ops_per_sec=iterations / total_time,
        )

    def compare(self, other: BenchmarkResult) -> dict[str, float]:
        """Compare with another benchmark result."""
        return {
            "speedup": other.avg_time / self.results[-1].avg_time,
            "throughput_ratio": self.results[-1].ops_per_sec / other.ops_per_sec,
        }


# System metrics monitoring
def get_system_metrics() -> dict[str, Any]:
    """Get system-wide performance metrics."""
    try:
        import psutil

        cpu_info = {
            "percent": psutil.cpu_percent(interval=0.1),
            "count": psutil.cpu_count(),
            "freq": psutil.cpu_freq()._asdict() if psutil.cpu_freq() else {},
        }

        memory_info = psutil.virtual_memory()._asdict()

        disk_info = {}
        if psutil.disk_io_counters():
            disk_info = psutil.disk_io_counters()._asdict()

        network_info = {}
        if psutil.net_io_counters():
            network_info = psutil.net_io_counters()._asdict()

        return {
            "cpu": cpu_info,
            "memory": memory_info,
            "disk_io": disk_info,
            "network_io": network_info,
            "timestamp": datetime.now().isoformat(),
        }
    except ImportError:
        return {
            "error": "psutil not installed",
            "timestamp": datetime.now().isoformat(),
        }


# Export performance utilities
__all__ = [
    "CachedBrick",
    "BatchedBrick",
    "FusedPipeline",
    "MemoryPool",
    "ConnectionPool",
    "Benchmark",
    "BenchmarkResult",
    "with_cache",
    "with_batching",
    "fuse_pipeline",
    "get_system_metrics",
]
