"""Base transformer class for data transformation nanobricks."""

from abc import ABC, abstractmethod
from typing import TypeVar

from nanobricks import NanobrickBase

T_in = TypeVar("T_in")
T_out = TypeVar("T_out")
T_deps = TypeVar("T_deps")


class TransformerBrick(NanobrickBase[T_in, T_out, T_deps], ABC):
    """Base class for transformer nanobricks.

    Transformers are nanobricks that convert input data from one form to another.
    They should be pure functions with no side effects.
    """

    def __init__(self, name: str = None):
        """Initialize transformer with optional custom name."""
        self.name = name or self.__class__.__name__
        self.version = "1.0.0"

    @abstractmethod
    async def transform(self, input: T_in) -> T_out:
        """Transform input data to output format.

        Args:
            input: Data to transform

        Returns:
            Transformed data
        """
        pass

    async def invoke(self, input: T_in, *, deps: T_deps = None) -> T_out:
        """Invoke the transformer.

        Args:
            input: Data to transform
            deps: Optional dependencies (unused in base transformers)

        Returns:
            Transformed data
        """
        return await self.transform(input)

    def invoke_sync(self, input: T_in, *, deps: T_deps = None) -> T_out:
        """Synchronous version of invoke.

        Args:
            input: Data to transform
            deps: Optional dependencies (unused in base transformers)

        Returns:
            Transformed data
        """
        import asyncio

        loop = asyncio.new_event_loop()
        try:
            return loop.run_until_complete(self.invoke(input, deps=deps))
        finally:
            loop.close()


class TransformerBase(NanobrickBase[T_in, T_out, None], ABC):
    """Alternative base class for transformers with async transform method.

    This base class is for transformers that don't need dependencies.
    """

    def __init__(self, name: str = "transformer", version: str = "1.0.0"):
        """Initialize transformer.

        Args:
            name: Transformer name
            version: Transformer version
        """
        self.name = name
        self.version = version

    async def invoke(self, input: T_in, *, deps: None = None) -> T_out:
        """Invoke the transformer.

        Args:
            input: Data to transform
            deps: Not used

        Returns:
            Transformed data
        """
        return await self.transform(input)

    @abstractmethod
    async def transform(self, input: T_in) -> T_out:
        """Transform the input.

        Override this method to implement transformation logic.

        Args:
            input: Input to transform

        Returns:
            Transformed output
        """
        pass
