"""
Unit tests for nanobrick composition functionality.
"""

import pytest

from nanobricks import NanobrickComposite, NanobrickBase, Pipeline, Nanobrick


class TestCompositeBrick:
    """Test the CompositeBrick class for two-brick composition."""

    @pytest.fixture
    def echo_brick(self):
        """A brick that returns its input unchanged."""

        class EchoNanobrick(Nanobrick[str, str]):
            async def invoke(self, input: str, *, deps=None) -> str:
                return input

        return EchoNanobrick(name="echo")

    @pytest.fixture
    def upper_brick(self):
        """A brick that converts input to uppercase."""

        class UpperNanobrick(Nanobrick[str, str]):
            async def invoke(self, input: str, *, deps=None) -> str:
                return input.upper()

        return UpperNanobrick(name="upper")

    @pytest.fixture
    def reverse_brick(self):
        """A brick that reverses its input."""

        class ReverseBrick(Nanobrick[str, str]):
            async def invoke(self, input: str, *, deps=None) -> str:
                return input[::-1]

        return ReverseBrick(name="reverse")

    async def test_basic_composition(self, echo_brick, upper_brick):
        """Test basic pipe operator composition."""
        # Create composite using pipe operator
        pipeline = echo_brick | upper_brick

        # Test async invocation
        result = await pipeline.invoke("hello")
        assert result == "HELLO"

        # Verify it's a NanobrickComposite
        assert isinstance(pipeline, NanobrickComposite)
        assert pipeline.name == "echo>>upper"

    def test_sync_composition(self, echo_brick, upper_brick):
        """Test sync invocation of composite."""
        pipeline = echo_brick | upper_brick

        result = pipeline.invoke_sync("hello world")
        assert result == "HELLO WORLD"

    async def test_three_brick_composition(
        self, echo_brick, upper_brick, reverse_brick
    ):
        """Test chaining three bricks together."""
        # Chain three bricks: echo | upper | reverse
        pipeline = echo_brick | upper_brick | reverse_brick

        result = await pipeline.invoke("hello")
        assert result == "OLLEH"  # "hello" -> "HELLO" -> "OLLEH"

        # Verify nested composition
        assert isinstance(pipeline, NanobrickComposite)
        assert isinstance(pipeline.first, NanobrickComposite)
        assert pipeline.name == "echo>>upper>>reverse"

    async def test_error_propagation(self, echo_brick):
        """Test that errors propagate through the pipeline (fail-fast)."""

        class ErrorNanobrick(Nanobrick[str, str]):
            async def invoke(self, input: str, *, deps=None) -> str:
                raise ValueError("Test error")

        error_brick = ErrorNanobrick(name="error")
        pipeline = echo_brick | error_brick

        # Error should propagate
        with pytest.raises(ValueError, match="Test error"):
            await pipeline.invoke("test")

    def test_composite_repr_and_str(self, echo_brick, upper_brick):
        """Test string representations of composite."""
        pipeline = echo_brick | upper_brick

        assert str(pipeline) == "echo >> upper"
        assert "NanobrickComposite" in repr(pipeline)
        assert "echo" in repr(pipeline)
        assert "upper" in repr(pipeline)


class TestPipeline:
    """Test the Pipeline class for multi-brick composition."""

    @pytest.fixture
    def bricks(self):
        """Create a set of test bricks."""

        class AddNanobrick(Nanobrick[int, int]):
            def __init__(self, amount: int, **kwargs):
                super().__init__(**kwargs)
                self.amount = amount

            async def invoke(self, input: int, *, deps=None) -> int:
                return input + self.amount

        return [
            AddNanobrick(1, name="add1"),
            AddNanobrick(2, name="add2"),
            AddNanobrick(3, name="add3"),
        ]

    async def test_pipeline_creation(self, bricks):
        """Test creating a pipeline from multiple bricks."""
        pipeline = Pipeline(*bricks)

        assert pipeline.name == "add1 >> add2 >> add3"
        assert len(pipeline.bricks) == 3

        # Test execution: 10 + 1 + 2 + 3 = 16
        result = await pipeline.invoke(10)
        assert result == 16

    def test_pipeline_requires_min_bricks(self):
        """Test that Pipeline requires at least 2 bricks."""

        class DummyBrick(Nanobrick[int, int]):
            async def invoke(self, input: int, *, deps=None) -> int:
                return input

        # Should fail with only one brick
        with pytest.raises(ValueError, match="at least 2 bricks"):
            Pipeline(DummyBrick())

    async def test_pipeline_error_propagation(self, bricks):
        """Test error propagation in pipeline."""

        class ErrorNanobrick(Nanobrick[int, int]):
            async def invoke(self, input: int, *, deps=None) -> int:
                raise RuntimeError("Pipeline error")

        # Add error brick in the middle
        pipeline = Pipeline(bricks[0], ErrorNanobrick(name="error"), bricks[2])

        with pytest.raises(RuntimeError, match="Pipeline error"):
            await pipeline.invoke(5)


class TestCompositionWithDependencies:
    """Test composition with dependency injection."""

    async def test_deps_passed_through_composition(self):
        """Test that dependencies are passed to all bricks in composition."""
        deps_seen = []

        class DepsBrick(NanobrickBase[str, str, dict]):
            def __init__(self, id: str):
                super().__init__(name=f"deps_{id}")
                self.id = id

            async def invoke(self, input: str, *, deps=None) -> str:
                deps_seen.append((self.id, deps))
                return f"{input}_{self.id}"

        brick1 = DepsBrick("1")
        brick2 = DepsBrick("2")
        pipeline = brick1 | brick2

        test_deps = {"key": "value"}
        result = await pipeline.invoke("test", deps=test_deps)

        # Check result
        assert result == "test_1_2"

        # Verify both bricks received the same deps
        assert len(deps_seen) == 2
        assert deps_seen[0] == ("1", test_deps)
        assert deps_seen[1] == ("2", test_deps)


class TestAdvancedComposition:
    """Test advanced composition scenarios."""

    async def test_different_types_composition(self):
        """Test composing bricks with different input/output types."""

        class StringToIntBrick(Nanobrick[str, int]):
            async def invoke(self, input: str, *, deps=None) -> int:
                return len(input)

        class IntToFloatBrick(Nanobrick[int, float]):
            async def invoke(self, input: int, *, deps=None) -> float:
                return float(input) * 1.5

        str_to_int = StringToIntBrick(name="strlen")
        int_to_float = IntToFloatBrick(name="multiply")

        pipeline = str_to_int | int_to_float

        result = await pipeline.invoke("hello")  # len("hello") = 5, 5 * 1.5 = 7.5
        assert result == 7.5

    async def test_reusable_pipelines(self):
        """Test that pipelines can be reused multiple times."""

        class CounterBrick(Nanobrick[int, int]):
            def __init__(self):
                super().__init__(name="counter")
                self.count = 0

            async def invoke(self, input: int, *, deps=None) -> int:
                self.count += 1
                return input + self.count

        brick1 = CounterBrick()
        brick2 = CounterBrick()
        pipeline = brick1 | brick2

        # Use pipeline multiple times
        result1 = await pipeline.invoke(0)  # 0 + 1 + 1 = 2
        result2 = await pipeline.invoke(0)  # 0 + 2 + 2 = 4
        result3 = await pipeline.invoke(0)  # 0 + 3 + 3 = 6

        assert result1 == 2
        assert result2 == 4
        assert result3 == 6
