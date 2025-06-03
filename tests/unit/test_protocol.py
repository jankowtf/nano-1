"""
Unit tests for the core nanobrick protocol.
"""

import asyncio

import pytest

from nanobricks.protocol import NanobrickBase, NanobrickProtocol, Nanobrick


class TestNanobrickProtocol:
    """Test the protocol definition and type checking."""

    def test_protocol_is_runtime_checkable(self):
        """Protocol should be runtime checkable."""

        class FakeNanobrick:
            name = "fake"
            version = "1.0.0"

            async def invoke(self, input, *, deps=None):
                return input

            def invoke_sync(self, input, *, deps=None):
                return input

            def __rshift__(self, other):
                return self
            
            def __or__(self, other):
                return self

        # Should be recognized as implementing the protocol
        assert isinstance(FakeNanobrick(), NanobrickProtocol)


class TestNanobrickBase:
    """Test the base class implementation."""

    @pytest.fixture
    def echo_brick(self):
        """Create a simple echo brick for testing."""

        class EchoNanobrick(NanobrickBase[str, str, None]):
            async def invoke(self, input: str, *, deps: None = None) -> str:
                return input

        return EchoNanobrick()

    async def test_basic_invocation(self, echo_brick):
        """Test basic async invocation."""
        result = await echo_brick.invoke("hello")
        assert result == "hello"

    def test_sync_invocation(self, echo_brick):
        """Test sync wrapper."""
        result = echo_brick.invoke_sync("hello")
        assert result == "hello"

    async def test_sync_invocation_in_async_context_raises(self, echo_brick):
        """Test that invoke_sync raises in async context."""
        with pytest.raises(RuntimeError, match="Cannot call invoke_sync"):
            echo_brick.invoke_sync("hello")

    def test_default_name(self):
        """Test that name defaults to class name."""

        class MyNanobrick(NanobrickBase[str, str, None]):
            async def invoke(self, input: str, *, deps=None) -> str:
                return input

        brick = MyNanobrick()
        assert brick.name == "MyNanobrick"
        assert brick.version == "0.1.0"

    def test_custom_name_and_version(self):
        """Test custom name and version."""

        class MyNanobrick(NanobrickBase[str, str, None]):
            async def invoke(self, input: str, *, deps=None) -> str:
                return input

        brick = MyNanobrick(name="custom", version="2.0.0")
        assert brick.name == "custom"
        assert brick.version == "2.0.0"

    def test_repr_and_str(self, echo_brick):
        """Test string representations."""
        assert repr(echo_brick) == "EchoNanobrick(name='EchoNanobrick', version='0.1.0')"
        assert str(echo_brick) == "EchoNanobrick v0.1.0"


class TestNanobrickSimple:
    """Test the Nanobrick convenience class."""

    def test_simple_brick_no_deps(self):
        """Nanobrick should work without dependencies."""

        class UpperNanobrick(Nanobrick[str, str]):
            async def invoke(self, input: str, *, deps=None) -> str:
                return input.upper()

        brick = UpperNanobrick()
        result = brick.invoke_sync("hello")
        assert result == "HELLO"

    async def test_simple_brick_async(self):
        """Nanobrick should work with async."""

        class AsyncUpperNanobrick(Nanobrick[str, str]):
            async def invoke(self, input: str, *, deps=None) -> str:
                await asyncio.sleep(0.01)  # Simulate async work
                return input.upper()

        brick = AsyncUpperNanobrick()
        result = await brick.invoke("hello")
        assert result == "HELLO"


class TestTypeEnforcement:
    """Test that types are properly defined (runtime enforcement will be added later)."""

    def test_type_annotations_exist(self):
        """Verify that nanobricks have proper type annotations."""

        class TypedNanobrick(NanobrickBase[int, str, None]):
            async def invoke(self, input: int, *, deps=None) -> str:
                return str(input * 2)

        brick = TypedNanobrick()

        # Should work with correct type
        result = brick.invoke_sync(21)
        assert result == "42"

        # Get type hints to verify they exist
        from typing import get_type_hints

        hints = get_type_hints(brick.invoke)
        assert "input" in hints
        assert "return" in hints
