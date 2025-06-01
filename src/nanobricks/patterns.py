"""
Advanced composition patterns for nanobricks.

Provides branching, parallel execution, and fan-out/fan-in patterns.
"""

import asyncio
from collections.abc import Callable, Iterable
from typing import Any, TypeVar, Union

from nanobricks.protocol import NanobrickBase, NanobrickProtocol

T_in = TypeVar("T_in")
T_out = TypeVar("T_out")
T_deps = TypeVar("T_deps")


class Branch(NanobrickBase[T_in, T_out, T_deps]):
    """
    Conditional branching pattern.

    Routes input to different nanobricks based on a condition.
    """

    def __init__(
        self,
        condition: Callable[[T_in], bool],
        true_path: NanobrickProtocol[T_in, T_out, T_deps],
        false_path: NanobrickProtocol[T_in, T_out, T_deps],
        name: str = "Branch",
    ):
        self.name = name
        self.version = "1.0.0"
        self.condition = condition
        self.true_path = true_path
        self.false_path = false_path

    async def invoke(self, input: T_in, *, deps: T_deps = None) -> T_out:
        """Route input based on condition."""
        if self.condition(input):
            return await self.true_path.invoke(input, deps=deps)
        else:
            return await self.false_path.invoke(input, deps=deps)


class Parallel(NanobrickBase[T_in, list[Any], T_deps]):
    """
    Parallel execution pattern.

    Executes multiple nanobricks concurrently and collects results.
    """

    def __init__(
        self, bricks: list[NanobrickProtocol[T_in, Any, T_deps]], name: str = "Parallel"
    ):
        self.name = name
        self.version = "1.0.0"
        self.bricks = bricks

    async def invoke(self, input: T_in, *, deps: T_deps = None) -> list[Any]:
        """Execute all bricks in parallel."""
        tasks = [brick.invoke(input, deps=deps) for brick in self.bricks]
        return await asyncio.gather(*tasks)


class FanOut(NanobrickBase[T_in, dict[str, Any], T_deps]):
    """
    Fan-out pattern.

    Sends input to multiple nanobricks and returns named results.
    """

    def __init__(
        self,
        branches: dict[str, NanobrickProtocol[T_in, Any, T_deps]],
        name: str = "FanOut",
    ):
        self.name = name
        self.version = "1.0.0"
        self.branches = branches

    async def invoke(self, input: T_in, *, deps: T_deps = None) -> dict[str, Any]:
        """Fan out to all branches."""
        tasks = {
            name: brick.invoke(input, deps=deps)
            for name, brick in self.branches.items()
        }

        results = {}
        for name, task in tasks.items():
            results[name] = await task

        return results


class FanIn(NanobrickBase[Union[list[Any], dict[str, Any]], T_out, T_deps]):
    """
    Fan-in pattern.

    Combines results from multiple sources using a merge strategy.
    """

    def __init__(
        self, merger: Callable[[list[Any] | dict[str, Any]], T_out], name: str = "FanIn"
    ):
        self.name = name
        self.version = "1.0.0"
        self.merger = merger

    async def invoke(
        self, input: list[Any] | dict[str, Any], *, deps: T_deps = None
    ) -> T_out:
        """Merge inputs using the merger function."""
        return self.merger(input)


class Pipeline(NanobrickBase[T_in, T_out, T_deps]):
    """
    Sequential pipeline with error recovery.

    Executes nanobricks in sequence with optional error handlers.
    """

    def __init__(
        self,
        steps: list[NanobrickProtocol],
        error_handler: Callable[[Exception, Any], Any] | None = None,
        name: str = "Pipeline",
    ):
        self.name = name
        self.version = "1.0.0"
        self.steps = steps
        self.error_handler = error_handler

    async def invoke(self, input: T_in, *, deps: T_deps = None) -> T_out:
        """Execute pipeline with error recovery."""
        result = input

        for i, step in enumerate(self.steps):
            try:
                result = await step.invoke(result, deps=deps)
            except Exception as e:
                if self.error_handler:
                    result = self.error_handler(e, result)
                else:
                    raise

        return result


class Retry(NanobrickBase[T_in, T_out, T_deps]):
    """
    Retry pattern for error recovery.

    Retries a nanobrick on failure with configurable backoff.
    """

    def __init__(
        self,
        brick: NanobrickProtocol[T_in, T_out, T_deps],
        max_retries: int = 3,
        backoff: float = 1.0,
        backoff_multiplier: float = 2.0,
        name: str = "Retry",
    ):
        self.name = name
        self.version = "1.0.0"
        self.brick = brick
        self.max_retries = max_retries
        self.backoff = backoff
        self.backoff_multiplier = backoff_multiplier

    async def invoke(self, input: T_in, *, deps: T_deps = None) -> T_out:
        """Execute with retry logic."""
        last_error = None
        delay = self.backoff

        for attempt in range(self.max_retries + 1):
            try:
                return await self.brick.invoke(input, deps=deps)
            except Exception as e:
                last_error = e
                if attempt < self.max_retries:
                    await asyncio.sleep(delay)
                    delay *= self.backoff_multiplier

        raise last_error


class Map(NanobrickBase[Iterable[T_in], list[T_out], T_deps]):
    """
    Map pattern for collection processing.

    Applies a nanobrick to each item in a collection.
    """

    def __init__(
        self,
        brick: NanobrickProtocol[T_in, T_out, T_deps],
        parallel: bool = False,
        name: str = "Map",
    ):
        self.name = name
        self.version = "1.0.0"
        self.brick = brick
        self.parallel = parallel

    async def invoke(
        self, input: Iterable[T_in], *, deps: T_deps = None
    ) -> list[T_out]:
        """Map brick over collection."""
        if self.parallel:
            tasks = [self.brick.invoke(item, deps=deps) for item in input]
            return await asyncio.gather(*tasks)
        else:
            results = []
            for item in input:
                result = await self.brick.invoke(item, deps=deps)
                results.append(result)
            return results


class Reduce(NanobrickBase[Iterable[T_in], T_out, T_deps]):
    """
    Reduce pattern for aggregation.

    Reduces a collection to a single value using a nanobrick.
    """

    def __init__(
        self,
        brick: NanobrickProtocol[tuple[T_out, T_in], T_out, T_deps],
        initial: T_out,
        name: str = "Reduce",
    ):
        self.name = name
        self.version = "1.0.0"
        self.brick = brick
        self.initial = initial

    async def invoke(self, input: Iterable[T_in], *, deps: T_deps = None) -> T_out:
        """Reduce collection using brick."""
        accumulator = self.initial

        for item in input:
            accumulator = await self.brick.invoke((accumulator, item), deps=deps)

        return accumulator


class Switch(NanobrickBase[T_in, T_out, T_deps]):
    """
    Switch pattern for multi-way branching.

    Routes input to different nanobricks based on a selector.
    """

    def __init__(
        self,
        selector: Callable[[T_in], str],
        cases: dict[str, NanobrickProtocol[T_in, T_out, T_deps]],
        default: NanobrickProtocol[T_in, T_out, T_deps] | None = None,
        name: str = "Switch",
    ):
        self.name = name
        self.version = "1.0.0"
        self.selector = selector
        self.cases = cases
        self.default = default

    async def invoke(self, input: T_in, *, deps: T_deps = None) -> T_out:
        """Route based on selector."""
        key = self.selector(input)

        if key in self.cases:
            return await self.cases[key].invoke(input, deps=deps)
        elif self.default:
            return await self.default.invoke(input, deps=deps)
        else:
            raise ValueError(f"No handler for case '{key}' and no default provided")


class Cache(NanobrickBase[T_in, T_out, T_deps]):
    """
    Caching pattern for performance.

    Caches results of a nanobrick based on input.
    """

    def __init__(
        self,
        brick: NanobrickProtocol[T_in, T_out, T_deps],
        key_func: Callable[[T_in], str] = str,
        ttl: float | None = None,
        name: str = "Cache",
    ):
        self.name = name
        self.version = "1.0.0"
        self.brick = brick
        self.key_func = key_func
        self.ttl = ttl
        self._cache: dict[str, tuple[T_out, float]] = {}

    async def invoke(self, input: T_in, *, deps: T_deps = None) -> T_out:
        """Execute with caching."""
        import time

        key = self.key_func(input)

        # Check cache
        if key in self._cache:
            result, timestamp = self._cache[key]
            if self.ttl is None or (time.time() - timestamp) < self.ttl:
                return result

        # Execute and cache
        result = await self.brick.invoke(input, deps=deps)
        self._cache[key] = (result, time.time())

        return result

    def clear_cache(self):
        """Clear the cache."""
        self._cache.clear()
