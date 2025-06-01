"""
Unit tests for dependency injection functionality.
"""

from nanobricks import NanobrickBase, NanobrickSimple
from nanobricks.dependencies import (
    DependencyContainer,
    MockCache,
    MockDatabase,
    MockLogger,
    StandardDeps,
)


class TestDependencyContainer:
    """Test the DependencyContainer class."""

    def test_basic_operations(self):
        """Test basic get/set operations."""
        container = DependencyContainer(foo="bar", num=42)

        assert container.get("foo") == "bar"
        assert container.get("num") == 42
        assert container.get("missing") is None
        assert container.get("missing", "default") == "default"

    def test_update_and_override(self):
        """Test updating and overriding dependencies."""
        container = DependencyContainer(a=1, b=2)

        # Update modifies in place
        container.update(b=3, c=4)
        assert container.get("a") == 1
        assert container.get("b") == 3
        assert container.get("c") == 4

        # Override creates new container
        new_container = container.override(b=5, d=6)
        assert container.get("b") == 3  # Original unchanged
        assert new_container.get("b") == 5  # New value
        assert new_container.get("d") == 6

    def test_dictionary_interface(self):
        """Test dictionary-like access."""
        container = DependencyContainer(key="value")

        assert container["key"] == "value"
        assert "key" in container
        assert "missing" not in container

        # Test to_dict
        d = container.to_dict()
        assert d == {"key": "value"}
        assert d is not container._deps  # Should be a copy

    def test_repr(self):
        """Test string representation."""
        container = DependencyContainer(db="database", cache="cache")
        repr_str = repr(container)
        assert "DependencyContainer" in repr_str
        assert "db" in repr_str
        assert "cache" in repr_str


class TestMockImplementations:
    """Test the mock implementations."""

    async def test_mock_database(self):
        """Test MockDatabase functionality."""
        db = MockDatabase({"SELECT * FROM users": [{"id": 1, "name": "Alice"}]})

        result = await db.query("SELECT * FROM users")
        assert result == [{"id": 1, "name": "Alice"}]
        assert len(db.queries) == 1
        assert db.queries[0] == ("SELECT * FROM users", None)

        # Test with params
        await db.execute("INSERT INTO users", {"name": "Bob"})
        assert len(db.queries) == 2

    async def test_mock_cache(self):
        """Test MockCache functionality."""
        cache = MockCache()

        # Test get/set/delete
        assert await cache.get("key") is None

        await cache.set("key", "value")
        assert await cache.get("key") == "value"

        await cache.delete("key")
        assert await cache.get("key") is None

    def test_mock_logger(self):
        """Test MockLogger functionality."""
        logger = MockLogger()

        logger.info("test message", extra="data")
        logger.error("error message")

        assert len(logger.messages) == 2
        assert logger.messages[0] == ("INFO", "test message", {"extra": "data"})
        assert logger.messages[1] == ("ERROR", "error message", {})


class TestDependencyInjection:
    """Test dependency injection with nanobricks."""

    async def test_brick_with_deps(self):
        """Test a nanobrick that uses dependencies."""

        class DepNanobrick(NanobrickBase[str, str, StandardDeps]):
            async def invoke(self, input: str, *, deps=None) -> str:
                if deps and "logger" in deps:
                    deps["logger"].info(f"Processing: {input}")

                if deps and "config" in deps:
                    prefix = deps["config"].get("prefix", "")
                    return f"{prefix}{input}"

                return input

        brick = DepNanobrick()
        logger = MockLogger()

        # Without deps
        result = await brick.invoke("test")
        assert result == "test"

        # With deps
        deps: StandardDeps = {"logger": logger, "config": {"prefix": ">>> "}}
        result = await brick.invoke("test", deps=deps)
        assert result == ">>> test"
        assert len(logger.messages) == 1
        assert logger.messages[0][1] == "Processing: test"

    async def test_pipeline_deps_propagation(self):
        """Test that deps propagate through pipelines."""
        logs = []

        class LogNanobrick(NanobrickSimple[str, str]):
            def __init__(self, name: str):
                super().__init__(name=name)

            async def invoke(self, input: str, *, deps=None) -> str:
                if deps and "logger" in deps:
                    deps["logger"].info(f"{self.name}: {input}")
                logs.append((self.name, deps is not None))
                return input

        brick1 = LogBrick("first")
        brick2 = LogBrick("second")
        pipeline = brick1 | brick2

        logger = MockLogger()
        deps = {"logger": logger}

        result = await pipeline.invoke("test", deps=deps)
        assert result == "test"
        assert len(logs) == 2
        assert logs[0] == ("first", True)
        assert logs[1] == ("second", True)
        assert len(logger.messages) == 2

    async def test_deps_not_required(self):
        """Test that deps are optional."""

        class OptionalDepNanobrick(NanobrickBase[int, int, StandardDeps]):
            async def invoke(self, input: int, *, deps=None) -> int:
                multiplier = 1
                if deps and "config" in deps:
                    multiplier = deps["config"].get("multiplier", 1)
                return input * multiplier

        brick = OptionalDepNanobrick()

        # Works without deps
        result = await brick.invoke(5)
        assert result == 5

        # Works with deps
        result = await brick.invoke(5, deps={"config": {"multiplier": 3}})
        assert result == 15

    async def test_different_dep_types(self):
        """Test bricks can have different dependency types."""
        from typing import TypedDict

        class CustomDeps(TypedDict):
            api_key: str
            timeout: int

        class CustomBrick(NanobrickBase[str, str, CustomDeps]):
            async def invoke(self, input: str, *, deps=None) -> str:
                if deps:
                    return f"{input} (timeout={deps['timeout']})"
                return input

        brick = CustomBrick()
        custom_deps: CustomDeps = {"api_key": "secret", "timeout": 30}

        result = await brick.invoke("test", deps=custom_deps)
        assert result == "test (timeout=30)"
