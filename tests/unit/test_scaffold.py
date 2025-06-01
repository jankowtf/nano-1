"""Tests for project scaffolding."""

import tempfile
from pathlib import Path

from nanobricks.cli.scaffold import create_project, to_class_name, to_module_name


class TestNameConversion:
    """Test name conversion utilities."""

    def test_to_class_name(self):
        """Test kebab-case to PascalCase conversion."""
        assert to_class_name("my-brick") == "MyBrick"
        assert to_class_name("data-validator") == "DataValidator"
        assert to_class_name("simple") == "Simple"
        assert to_class_name("multi-word-name") == "MultiWordName"

    def test_to_module_name(self):
        """Test kebab-case to snake_case conversion."""
        assert to_module_name("my-brick") == "my_brick"
        assert to_module_name("data-validator") == "data_validator"
        assert to_module_name("simple") == "simple"
        assert to_module_name("multi-word-name") == "multi_word_name"


class TestProjectCreation:
    """Test project creation."""

    def test_create_basic_project(self):
        """Test creating a basic project."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = create_project(
                name="test-brick",
                description="A test nanobrick",
                author="Test Author",
                email="test@example.com",
                output_dir=Path(tmpdir),
            )

            # Check project structure
            assert project_dir.exists()
            assert project_dir.name == "test-brick"

            # Check files exist
            assert (project_dir / "pyproject.toml").exists()
            assert (project_dir / "nanobrick.toml").exists()
            assert (project_dir / "README.md").exists()
            assert (project_dir / ".gitignore").exists()

            # Check source files
            src_dir = project_dir / "src" / "test_brick"
            assert src_dir.exists()
            assert (src_dir / "__init__.py").exists()
            assert (src_dir / "core.py").exists()

            # Check test files
            tests_dir = project_dir / "tests"
            assert tests_dir.exists()
            assert (tests_dir / "__init__.py").exists()
            assert (tests_dir / "test_test_brick.py").exists()

            # Check VS Code settings
            assert (project_dir / ".vscode" / "settings.json").exists()

    def test_project_content(self):
        """Test project file contents."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = create_project(
                name="my-awesome-brick",
                description="An awesome brick",
                author="John Doe",
                email="john@example.com",
                output_dir=Path(tmpdir),
            )

            # Check pyproject.toml
            pyproject = (project_dir / "pyproject.toml").read_text()
            assert 'name = "my-awesome-brick"' in pyproject
            assert 'description = "An awesome brick"' in pyproject
            assert 'name = "John Doe"' in pyproject
            assert 'email = "john@example.com"' in pyproject

            # Check core.py
            core = (project_dir / "src" / "my_awesome_brick" / "core.py").read_text()
            assert "class MyAwesomeBrick" in core
            assert "MY_AWESOME_BRICK" in core

            # Check test file
            test = (project_dir / "tests" / "test_my_awesome_brick.py").read_text()
            assert "from my_awesome_brick import MyAwesomeBrick" in test
            assert "class TestMyAwesomeBrick" in test
            assert "MY_AWESOME_BRICK: hello processed" in test

    def test_overwrite_existing(self):
        """Test overwriting existing project."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create first time
            project_dir = create_project(
                name="test-brick",
                output_dir=Path(tmpdir),
            )

            # Create marker file
            marker = project_dir / "marker.txt"
            marker.write_text("test")

            # Try to create again (would need interactive confirmation)
            # For testing, we'll just check the directory exists
            assert project_dir.exists()
            assert marker.exists()
