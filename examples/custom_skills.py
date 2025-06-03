"""Example demonstrating the skill framework."""

import asyncio

from nanobricks import (
    NanobrickEnhanced,
    Nanobrick,
    Skill,
    register_skill,
    skill,
)

# First, let's create some example skills


@register_skill("timing")
class TimingSkill(Skill[any, any, any]):
    """Adds timing information to brick invocations."""

    def _create_enhanced_brick(self, brick):
        import time

        class TimingEnhanced(NanobrickEnhanced):
            async def invoke(self, input, *, deps=None):
                start = time.time()
                result = await self._wrapped.invoke(input, deps=deps)
                elapsed = time.time() - start
                print(f"⏱️  {self._wrapped.name} took {elapsed:.3f}s")
                return result

        return TimingEnhanced(brick, self)


@register_skill("retry")
class RetrySkill(Skill[any, any, any]):
    """Adds retry logic to brick invocations."""

    def _create_enhanced_brick(self, brick):
        max_retries = self.config.get("max_retries", 3)

        class RetryEnhanced(NanobrickEnhanced):
            async def invoke(self, input, *, deps=None):
                last_error = None
                for attempt in range(max_retries):
                    try:
                        return await self._wrapped.invoke(input, deps=deps)
                    except Exception as e:
                        last_error = e
                        if attempt < max_retries - 1:
                            print(
                                f"🔄 Retry {attempt + 1}/{max_retries} after error: {e}"
                            )

                raise last_error

        return RetryEnhanced(brick, self)


@register_skill("cache")
class CacheSkill(Skill[any, any, any]):
    """Adds simple caching to brick invocations."""

    def _create_enhanced_brick(self, brick):
        cache = {}

        class CacheEnhanced(NanobrickEnhanced):
            async def invoke(self, input, *, deps=None):
                # Simple cache key based on input string representation
                cache_key = str(input)

                if cache_key in cache:
                    print(f"💾 Cache hit for: {cache_key}")
                    return cache[cache_key]

                result = await self._wrapped.invoke(input, deps=deps)
                cache[cache_key] = result
                print(f"💾 Cached result for: {cache_key}")
                return result

        return CacheEnhanced(brick, self)


# Now let's create some example bricks


class SlowProcessorBrick(Nanobrick[str, str]):
    """A brick that simulates slow processing."""

    async def invoke(self, input: str, *, deps=None) -> str:
        # Simulate slow processing
        await asyncio.sleep(0.5)
        return f"Processed: {input.upper()}"


class UnreliableBrick(Nanobrick[int, int]):
    """A brick that randomly fails."""

    def __init__(self):
        super().__init__()
        self._count = 0

    async def invoke(self, input: int, *, deps=None) -> int:
        self._count += 1
        # Fail on first two attempts
        if self._count % 3 != 0:
            raise ValueError(f"Random failure on attempt {self._count}")
        return input * 2


class DataTransformerBrick(Nanobrick[dict, dict]):
    """A brick that transforms data."""

    async def invoke(self, input: dict, *, deps=None) -> dict:
        # Simulate some data transformation
        await asyncio.sleep(0.1)
        return {
            **input,
            "transformed": True,
            "keys": list(input.keys()),
            "values_sum": sum(v for v in input.values() if isinstance(v, (int, float))),
        }


async def main():
    """Demonstrate skill usage."""

    print("=== Skill Framework Demo ===\n")

    # Example 1: Add timing to a slow processor
    print("1. Timing Skill:")
    slow_brick = SlowProcessorBrick()
    timed_brick = slow_brick.with_skill("timing")

    result = await timed_brick.invoke("hello world")
    print(f"Result: {result}\n")

    # Example 2: Add retry logic to an unreliable brick
    print("2. Retry Skill:")
    unreliable = UnreliableBrick()
    reliable = unreliable.with_skill("retry", max_retries=3)

    try:
        result = await reliable.invoke(42)
        print(f"Result: {result}\n")
    except Exception as e:
        print(f"Failed after retries: {e}\n")

    # Example 3: Add caching to expensive operations
    print("3. Cache Skill:")
    transformer = DataTransformerBrick()
    cached_transformer = transformer.with_skill("cache").with_skill("timing")

    # First call - will be slow
    data1 = {"a": 1, "b": 2, "c": 3}
    result1 = await cached_transformer.invoke(data1)
    print(f"First result: {result1}")

    # Second call with same data - will be fast (cached)
    result2 = await cached_transformer.invoke(data1)
    print(f"Second result: {result2}")

    # Third call with different data - will be slow again
    data2 = {"x": 10, "y": 20}
    result3 = await cached_transformer.invoke(data2)
    print(f"Third result: {result3}\n")

    # Example 4: Chain multiple skills
    print("4. Chaining Skills:")

    # Create a brick with multiple enhancements
    enhanced_processor = (
        SlowProcessorBrick()
        .with_skill("cache")
        .with_skill("timing")
        .with_skill("retry", max_retries=2)
    )

    # Process some data
    for word in ["hello", "world", "hello"]:  # Note: "hello" appears twice
        result = await enhanced_processor.invoke(word)
        print(f"'{word}' -> '{result}'")

    print("\n")

    # Example 5: Using the @skill decorator
    print("5. Decorator Style:")

    @skill("timing")
    @skill("cache")
    class SmartBrick(Nanobrick[str, int]):
        """A brick decorated with skills."""

        async def invoke(self, input: str, *, deps=None) -> int:
            # Simulate some work
            await asyncio.sleep(0.2)
            return len(input)

    smart = SmartBrick()

    # Test it
    for text in ["short", "longer text", "short"]:  # "short" appears twice
        length = await smart.invoke(text)
        print(f"Length of '{text}': {length}")

    print("\n=== Demo Complete ===")


if __name__ == "__main__":
    asyncio.run(main())
