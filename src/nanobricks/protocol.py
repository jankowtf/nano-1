"""
Core Nanobrick protocol and base classes.

This module defines the fundamental interfaces and base implementations
that all nanobricks must follow.
"""

import asyncio
from abc import ABC, abstractmethod
from typing import Any, Generic, Protocol, TypeVar, runtime_checkable

from beartype import beartype

# Type variables for input, output, and dependencies
T_in = TypeVar("T_in")
T_out = TypeVar("T_out")
T_deps = TypeVar("T_deps")


@runtime_checkable
class NanobrickProtocol(Protocol, Generic[T_in, T_out, T_deps]):
    """
    Protocol defining the interface that all nanobricks must implement.

    This is used for static type checking and allows duck typing of nanobricks.
    """

    # Required attributes
    name: str
    version: str

    async def invoke(self, input: T_in, *, deps: T_deps | None = None) -> T_out:
        """
        Asynchronously process input and return output.

        Args:
            input: The input data to process
            deps: Optional dependencies needed for processing

        Returns:
            The processed output
        """
        ...

    def invoke_sync(self, input: T_in, *, deps: T_deps | None = None) -> T_out:
        """
        Synchronously process input and return output.

        This is a convenience wrapper around the async invoke method.

        Args:
            input: The input data to process
            deps: Optional dependencies needed for processing

        Returns:
            The processed output
        """
        ...

    def __or__(
        self, other: "NanobrickProtocol[T_out, Any, T_deps]"
    ) -> "NanobrickProtocol[T_in, Any, T_deps]":
        """
        Compose this nanobrick with another using the pipe operator.

        Args:
            other: The nanobrick to compose with

        Returns:
            A new composite nanobrick
        """
        ...


class NanobrickBase(ABC, Generic[T_in, T_out, T_deps]):
    """
    Abstract base class for all nanobricks.

    This provides runtime enforcement of the protocol and common functionality.
    All concrete nanobricks should inherit from this class.
    """

    def __init__(self, name: str | None = None, version: str = "0.1.0"):
        """
        Initialize a nanobrick.

        Args:
            name: The name of the nanobrick (defaults to class name)
            version: The version of the nanobrick
        """
        self.name = name or self.__class__.__name__
        self.version = version

    @abstractmethod
    @beartype
    async def invoke(self, input: T_in, *, deps: T_deps | None = None) -> T_out:
        """
        Asynchronously process input and return output.

        This must be implemented by all concrete nanobricks.

        Args:
            input: The input data to process
            deps: Optional dependencies needed for processing

        Returns:
            The processed output
        """
        pass

    @beartype
    def invoke_sync(self, input: T_in, *, deps: T_deps | None = None) -> T_out:
        """
        Synchronously process input and return output.

        This is automatically provided as a wrapper around invoke().

        Args:
            input: The input data to process
            deps: Optional dependencies needed for processing

        Returns:
            The processed output
        """
        # Create new event loop if none exists, otherwise use existing
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            # No loop is running, so we can use asyncio.run
            return asyncio.run(self.invoke(input, deps=deps))
        else:
            # Loop is already running, we need to handle this differently
            raise RuntimeError(
                "Cannot call invoke_sync from within an async context. "
                "Use 'await invoke()' instead."
            )

    def __or__(
        self, other: "NanobrickProtocol[T_out, Any, T_deps]"
    ) -> "NanobrickProtocol[T_in, Any, T_deps]":
        """
        Compose this nanobrick with another using the pipe operator.

        Creates a pipeline where the output of this brick becomes the input of the next.

        Args:
            other: The nanobrick to compose with

        Returns:
            A new composite nanobrick that runs both in sequence
        """
        # Import here to avoid circular dependency
        from nanobricks.composition import NanobrickComposite

        return NanobrickComposite(self, other)

    def __repr__(self) -> str:
        """String representation of the nanobrick."""
        return (
            f"{self.__class__.__name__}(name='{self.name}', version='{self.version}')"
        )

    def __str__(self) -> str:
        """Human-readable string representation."""
        return f"{self.name} v{self.version}"


class NanobrickSimple(NanobrickBase[T_in, T_out, None]):
    """
    A simplified base class for nanobricks that don't need dependencies.

    This is a convenience class for the common case where no deps are needed.
    """

    @abstractmethod
    @beartype
    async def invoke(self, input: T_in, *, deps: None = None) -> T_out:
        """Process input without dependencies."""
        pass
