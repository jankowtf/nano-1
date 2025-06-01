"""Example demonstrating performance optimization features."""

import asyncio
import time
from typing import Any

from nanobricks.performance import (
    Benchmark,
    ConnectionPool,
    FusedPipeline,
    get_system_metrics,
    with_cache,
)
from nanobricks.protocol import NanobrickBase


# Example bricks for demonstration
class FibonacciBrick(NanobrickBase[int, int, None]):
    """Computes Fibonacci numbers (intentionally slow for demo)."""
    
    def __init__(self):
        super().__init__(name="fibonacci", version="1.0.0")
    
    async def invoke(self, input: int, *, deps: None = None) -> int:
        if input <= 1:
            return input
        
        # Intentionally inefficient for demo
        a, b = 0, 1
        for _ in range(input):
            a, b = b, a + b
        
        # Simulate some work
        await asyncio.sleep(0.01)
        return a


class DatabaseBrick(NanobrickBase[str, dict[str, Any], dict[str, Any]]):
    """Simulates database queries."""
    
    def __init__(self):
        super().__init__(name="database", version="1.0.0")
        self.query_count = 0
    
    async def invoke(
        self, query: str, *, deps: dict[str, Any] = None
    ) -> dict[str, Any]:
        self.query_count += 1
        conn = deps.get("connection") if deps else None
        
        # Simulate database query
        await asyncio.sleep(0.05)
        
        return {
            "query": query,
            "results": [{"id": i, "value": f"row_{i}"} for i in range(5)],
            "connection": conn.get("id") if conn else None,
            "query_count": self.query_count,
        }


class TransformBrick(NanobrickBase[Any, Any, None]):
    """Simple transformation brick."""
    
    def __init__(self, transform_fn):
        super().__init__(name="transform", version="1.0.0")
        self.transform = transform_fn
    
    async def invoke(self, input: Any, *, deps: None = None) -> Any:
        _ = deps  # Unused
        return self.transform(input)


async def demo_caching():
    """Demonstrate caching benefits."""
    print("\n=== Caching Demo ===")
    
    # Create a slow Fibonacci brick
    fib_brick = FibonacciBrick()
    
    # Add caching
    cached_fib = with_cache(fib_brick, max_size=100, ttl=60)
    
    # Benchmark without cache
    print("\nWithout cache:")
    for n in [10, 20, 10, 20, 10]:  # Repeated values
        start = time.time()
        result = await fib_brick.invoke(n)
        duration = time.time() - start
        print(f"  fib({n}) = {result}, time: {duration:.3f}s")
    
    # Benchmark with cache
    print("\nWith cache:")
    for n in [10, 20, 10, 20, 10]:  # Same repeated values
        start = time.time()
        result = await cached_fib.invoke(n)
        duration = time.time() - start
        print(f"  fib({n}) = {result}, time: {duration:.3f}s")
    
    # Show cache statistics
    cache_info = cached_fib.cache_info()
    print(f"\nCache stats: {cache_info}")


async def demo_connection_pooling():
    """Demonstrate connection pooling."""
    print("\n=== Connection Pooling Demo ===")
    
    # Mock database connection factory
    conn_id = 0
    
    async def create_connection():
        nonlocal conn_id
        conn_id += 1
        await asyncio.sleep(0.1)  # Simulate connection overhead
        return {"id": conn_id, "connected": True}
    
    # Create connection pool
    pool = ConnectionPool(
        create_connection,
        min_size=2,
        max_size=5,
        acquire_timeout=5.0
    )
    
    # Database brick
    db_brick = DatabaseBrick()
    
    # Execute multiple queries
    print("\nExecuting queries with connection pool:")
    
    async def execute_query(query_id: int):
        async with pool.acquire() as conn:
            result = await db_brick.invoke(
                f"SELECT * FROM table_{query_id}",
                deps={"connection": conn}
            )
            print(
                f"  Query {query_id}: connection={result['connection']}, "
                f"count={result['query_count']}"
            )
    
    # Run queries concurrently
    await asyncio.gather(*[execute_query(i) for i in range(8)])
    
    # Show pool statistics
    stats = pool.get_stats()
    print(f"\nPool stats: {stats}")
    
    # Cleanup
    await pool.close()


async def demo_pipeline_fusion():
    """Demonstrate pipeline fusion optimization."""
    print("\n=== Pipeline Fusion Demo ===")
    
    # Create a series of transformation bricks
    upper_brick = TransformBrick(lambda x: x.upper())
    strip_brick = TransformBrick(lambda x: x.strip())
    reverse_brick = TransformBrick(lambda x: x[::-1])
    
    # Regular pipeline
    print("\nRegular pipeline:")
    start = time.time()
    for _ in range(1000):
        result = await upper_brick.invoke("  hello world  ")
        result = await strip_brick.invoke(result)
        result = await reverse_brick.invoke(result)
    regular_time = time.time() - start
    print(f"  Result: {result}")
    print(f"  Time for 1000 iterations: {regular_time:.3f}s")
    
    # Fused pipeline
    fused = FusedPipeline([upper_brick, strip_brick, reverse_brick])
    
    print("\nFused pipeline:")
    start = time.time()
    for _ in range(1000):
        result = await fused.invoke("  hello world  ")
    fused_time = time.time() - start
    print(f"  Result: {result}")
    print(f"  Time for 1000 iterations: {fused_time:.3f}s")
    print(f"  Speedup: {regular_time / fused_time:.2f}x")


async def demo_benchmarking():
    """Demonstrate benchmarking utilities."""
    print("\n=== Benchmarking Demo ===")
    
    # Create bricks to benchmark
    fib_brick = FibonacciBrick()
    cached_fib = with_cache(fib_brick)
    
    # Benchmark uncached
    benchmark = Benchmark("fibonacci_uncached")
    result1 = await benchmark.measure(
        lambda: fib_brick.invoke(15),
        iterations=50,
        warmup=5
    )
    
    print("\nUncached Fibonacci(15):")
    print(f"  Total time: {result1.total_time:.3f}s")
    print(f"  Avg time: {result1.avg_time * 1000:.3f}ms")
    print(
        f"  Min/Max: {result1.min_time * 1000:.3f}ms / "
        f"{result1.max_time * 1000:.3f}ms"
    )
    print(f"  Ops/sec: {result1.ops_per_sec:.2f}")
    
    # Pre-warm cache
    await cached_fib.invoke(15)
    
    # Benchmark cached
    benchmark2 = Benchmark("fibonacci_cached")
    result2 = await benchmark2.measure(
        lambda: cached_fib.invoke(15),
        iterations=50,
        warmup=5
    )
    
    print("\nCached Fibonacci(15):")
    print(f"  Total time: {result2.total_time:.3f}s")
    print(f"  Avg time: {result2.avg_time * 1000:.3f}ms")
    print(
        f"  Min/Max: {result2.min_time * 1000:.3f}ms / "
        f"{result2.max_time * 1000:.3f}ms"
    )
    print(f"  Ops/sec: {result2.ops_per_sec:.2f}")
    
    print(f"\nSpeedup from caching: {result1.avg_time / result2.avg_time:.2f}x")


async def demo_system_metrics():
    """Demonstrate system metrics monitoring."""
    print("\n=== System Metrics Demo ===")
    
    metrics = get_system_metrics()
    
    if "error" not in metrics:
        print("\nCurrent system metrics:")
        print(f"  CPU: {metrics['cpu']['percent']}% ({metrics['cpu']['count']} cores)")
        print(f"  Memory: {metrics['memory']['percent']:.1f}% used")
        
        if metrics['disk_io']:
            disk_gb = metrics['disk_io'].get('read_bytes', 0) / 1e9
            print(f"  Disk I/O: {disk_gb:.2f} GB read")
        
        if metrics['network_io']:
            net_mb = metrics['network_io'].get('bytes_sent', 0) / 1e6
            print(f"  Network: {net_mb:.2f} MB sent")
    else:
        print(f"\nSystem metrics error: {metrics['error']}")


async def main():
    """Run all performance demos."""
    print("Nanobricks Performance Optimization Examples")
    print("=" * 50)
    
    await demo_caching()
    await demo_connection_pooling()
    await demo_pipeline_fusion()
    await demo_benchmarking()
    await demo_system_metrics()
    
    print("\n" + "=" * 50)
    print("Performance optimization demos completed!")


if __name__ == "__main__":
    asyncio.run(main())