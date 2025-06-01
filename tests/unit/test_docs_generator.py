"""Tests for documentation generator."""

import tempfile
from pathlib import Path

from nanobricks import NanobrickBase
from nanobricks.docs import DocumentationGenerator


class SampleNanobrick(NanobrickBase[str, str, None]):
    """A sample brick for testing.

    This brick processes strings by adding a prefix.

    Example:
        >>> brick = SampleBrick()
        >>> result = await brick.invoke("hello")
        >>> print(result)
        Sample: hello
    """

    def __init__(self, prefix: str = "Sample"):
        """Initialize sample brick.

        Args:
            prefix: Prefix to add to input
        """
        super().__init__(name="sample", version="1.0.0")
        self.prefix = prefix

    async def invoke(self, input: str, *, deps: None = None) -> str:
        """Process input string.

        Args:
            input: Input string to process
            deps: No dependencies required

        Returns:
            String with prefix added
        """
        return f"{self.prefix}: {input}"


class AnotherNanobrick(NanobrickBase[int, int, None]):
    """Another test brick that doubles numbers."""

    async def invoke(self, input: int, *, deps: None = None) -> int:
        """Double the input.

        Args:
            input: Number to double
            deps: No dependencies

        Returns:
            Doubled number
        """
        return input * 2


class TestDocumentationGenerator:
    """Test documentation generator."""

    def test_document_brick(self):
        """Test documenting a single brick."""
        with tempfile.TemporaryDirectory() as tmpdir:
            generator = DocumentationGenerator(Path(tmpdir))

            doc = generator.document_brick(SampleBrick)

            # Check content
            assert "# SampleBrick" in doc
            assert "A sample brick for testing" in doc
            assert "## Type Signature" in doc
            assert "Input**: `str`" in doc
            assert "Output**: `str`" in doc
            assert "## Constructor" in doc
            assert "## Methods" in doc
            assert "### invoke" in doc
            assert "## Examples" in doc
            assert ">>> brick = SampleBrick()" in doc
            assert "## Composition" in doc

    def test_extract_examples(self):
        """Test example extraction."""
        generator = DocumentationGenerator()

        examples = generator._extract_examples(SampleBrick)

        assert len(examples) == 1
        assert ">>> brick = SampleBrick()" in examples[0]
        assert ">>> result = await brick.invoke" in examples[0]
        assert "Sample: hello" in examples[0]

    def test_generate_index(self):
        """Test index generation."""
        with tempfile.TemporaryDirectory() as tmpdir:
            generator = DocumentationGenerator(Path(tmpdir))

            index = generator.generate_index([SampleBrick, AnotherBrick])

            assert "# Nanobricks Documentation" in index
            assert "## Available Bricks" in index
            assert "SampleBrick" in index
            assert "AnotherBrick" in index
            assert "sample brick for testing" in index
            assert "doubles numbers" in index

    def test_generate_composition_diagram(self):
        """Test composition diagram generation."""
        generator = DocumentationGenerator()

        # Single brick
        diagram = generator.generate_composition_diagram(SampleBrick())
        assert "Single brick" in diagram

        # Mock pipeline
        class MockPipeline:
            def __init__(self):
                self.bricks = [SampleBrick(), AnotherBrick()]

        pipeline = MockPipeline()
        diagram = generator.generate_composition_diagram(pipeline)

        assert "Pipeline Composition:" in diagram
        assert "SampleBrick" in diagram
        assert "AnotherBrick" in diagram
        assert "│" in diagram
        assert "▼" in diagram

    def test_write_docs(self):
        """Test writing documentation files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir)
            generator = DocumentationGenerator(output_dir)

            generator.write_docs([SampleBrick, AnotherBrick])

            # Check files created
            assert (output_dir / "index.md").exists()
            assert (output_dir / "samplebrick.md").exists()
            assert (output_dir / "anotherbrick.md").exists()

            # Check index content
            index_content = (output_dir / "index.md").read_text()
            assert "SampleBrick" in index_content
            assert "AnotherBrick" in index_content

            # Check individual docs
            sample_doc = (output_dir / "samplebrick.md").read_text()
            assert "# SampleBrick" in sample_doc
            assert "A sample brick for testing" in sample_doc
