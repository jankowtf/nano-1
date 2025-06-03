"""
Composition utilities for nanobricks.

This module provides the CompositeBrick class and other composition patterns.
"""

from typing import Any, TypeVar, cast, Type, get_type_hints

from beartype import beartype

from nanobricks.protocol import NanobrickBase, NanobrickProtocol
from nanobricks.typing import (
    TypeMismatchError,
    check_type_compatibility,
    suggest_adapter,
)

T_in = TypeVar("T_in")
T_mid = TypeVar("T_mid")
T_out = TypeVar("T_out")
T_deps = TypeVar("T_deps")


class NanobrickComposite(NanobrickBase[T_in, T_out, T_deps]):
    """
    A composite nanobrick that chains two bricks together.

    The output of the first brick becomes the input of the second.
    This enables pipeline-style composition with the | operator.
    """

    def __init__(
        self,
        first: NanobrickProtocol[T_in, T_mid, T_deps],
        second: NanobrickProtocol[T_mid, T_out, T_deps],
    ):
        """
        Create a composite brick from two bricks.

        Args:
            first: The first brick in the pipeline
            second: The second brick in the pipeline
        """
        super().__init__(name=f"{first.name}>>{second.name}", version="composite")
        self.first = first
        self.second = second

        # Enhanced type checking with better error messages
        self._validate_type_compatibility()

    def _validate_type_compatibility(self) -> None:
        """Validate type compatibility between bricks with helpful error messages."""
        try:
            # Try to get type hints from the invoke method
            first_hints = get_type_hints(self.first.invoke)
            second_hints = get_type_hints(self.second.invoke)

            # Get return type of first and input type of second
            first_output = first_hints.get("return", Any)
            second_input = second_hints.get("input", Any)

            # Check compatibility
            if not check_type_compatibility(first_output, second_input):
                suggestion = suggest_adapter(first_output, second_input)
                raise TypeMismatchError(
                    left_brick=self.first.name,
                    right_brick=self.second.name,
                    output_type=first_output,
                    expected_type=second_input,
                    suggestion=suggestion,
                )
        except (AttributeError, TypeError):
            # If we can't get type hints, skip validation
            # This maintains backwards compatibility
            pass

    @beartype
    async def invoke(self, input: T_in, *, deps: T_deps | None = None) -> T_out:
        """
        Execute the pipeline: first brick then second brick.

        Args:
            input: Input to the first brick
            deps: Dependencies passed to both bricks

        Returns:
            Output from the second brick

        Raises:
            Exception: If either brick fails, the exception propagates (fail-fast)
        """
        # Run first brick
        intermediate = await self.first.invoke(input, deps=deps)
        # Run second brick with the output of the first
        result = await self.second.invoke(intermediate, deps=deps)
        return result

    def __repr__(self) -> str:
        """String representation showing the pipeline."""
        return f"NanobrickComposite({self.first!r} >> {self.second!r})"

    def __str__(self) -> str:
        """Human-readable string showing the pipeline."""
        return f"{self.first.name} >> {self.second.name}"


class Pipeline(NanobrickBase[T_in, T_out, T_deps]):
    """
    A pipeline of multiple nanobricks chained together.

    This is a convenience class for creating longer pipelines.
    """

    def __init__(self, *bricks: NanobrickProtocol[Any, Any, T_deps]):
        """
        Create a pipeline from multiple bricks.

        Args:
            *bricks: The bricks to chain together in order
        """
        if len(bricks) < 2:
            raise ValueError("Pipeline requires at least 2 bricks")

        # Build name from all brick names
        names = [brick.name for brick in bricks]
        super().__init__(name=" >> ".join(names), version="pipeline")
        self.bricks = bricks

    @beartype
    async def invoke(self, input: T_in, *, deps: T_deps | None = None) -> T_out:
        """
        Execute all bricks in the pipeline sequentially.

        Args:
            input: Input to the first brick
            deps: Dependencies passed to all bricks

        Returns:
            Output from the last brick
        """
        result: Any = input
        for brick in self.bricks:
            result = await brick.invoke(result, deps=deps)
        return cast(T_out, result)

    def __repr__(self) -> str:
        """String representation showing all bricks."""
        brick_reprs = [repr(brick) for brick in self.bricks]
        return f"Pipeline({', '.join(brick_reprs)})"
