#!/bin/bash
# Script to set up a new project using Nanobricks

PROJECT_NAME=$1
NANOBRICKS_PATH="/Users/jankothyson/Code/kaosmaps/nano/nano-1"

if [ -z "$PROJECT_NAME" ]; then
    echo "Usage: ./new-project-setup.sh <project-name>"
    exit 1
fi

echo "🚀 Creating new Nanobricks project: $PROJECT_NAME"

# Create project directory
mkdir -p "$PROJECT_NAME"
cd "$PROJECT_NAME"

# Create project structure
mkdir -p src/$PROJECT_NAME tests docs

# Create pyproject.toml
cat > pyproject.toml << EOF
[project]
name = "$PROJECT_NAME"
version = "0.1.0"
description = "A project built with Nanobricks"
requires-python = ">=3.13"
dependencies = [
    # Nanobricks - choose one:
    # For active development (editable):
    "nanobricks @ file://$NANOBRICKS_PATH",
    
    # For stable local:
    # "nanobricks @ file://$NANOBRICKS_PATH/dist/nanobricks-0.1.0-py3-none-any.whl",
    
    # Your other dependencies here
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0",
    "pytest-asyncio>=0.23",
    "pytest-cov>=5.0",
    "ruff>=0.3.0",
    "mypy>=1.9",
]

[build-system]
requires = ["setuptools>=61.0", "wheel"]
build-backend = "setuptools.build_meta"

[tool.ruff]
target-version = "py313"
line-length = 88

[tool.mypy]
python_version = "3.13"
strict = true

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]
EOF

# Create .gitignore
cat > .gitignore << 'EOF'
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
.venv/
venv/
ENV/
.env
.coverage
htmlcov/
.pytest_cache/
.mypy_cache/
.ruff_cache/
dist/
build/
*.egg-info/
.DS_Store
EOF

# Create README.md
cat > README.md << EOF
# $PROJECT_NAME

A project built with [Nanobricks](https://github.com/yourusername/nanobricks).

## Setup

\`\`\`bash
# Create virtual environment
python3.13 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -e .
pip install -e ".[dev]"  # For development
\`\`\`

## Usage

\`\`\`python
from nanobricks import NanobrickSimple

class MyBrick(NanobrickSimple[str, str]):
    async def invoke(self, input: str) -> str:
        return f"Processed: {input}"
\`\`\`

## Testing

\`\`\`bash
pytest
\`\`\`
EOF

# Create a simple example brick
cat > src/$PROJECT_NAME/__init__.py << EOF
"""$PROJECT_NAME - Built with Nanobricks."""

from nanobricks import NanobrickSimple, Pipeline

__version__ = "0.1.0"


class GreetingBrick(NanobrickSimple[str, str]):
    """A simple greeting brick."""
    
    async def invoke(self, input: str) -> str:
        return f"Hello, {input}!"


class UppercaseBrick(NanobrickSimple[str, str]):
    """Converts text to uppercase."""
    
    async def invoke(self, input: str) -> str:
        return input.upper()


# Example pipeline
greeting_pipeline = GreetingBrick() | UppercaseBrick()


__all__ = ["GreetingBrick", "UppercaseBrick", "greeting_pipeline"]
EOF

# Create a main module
cat > src/$PROJECT_NAME/__main__.py << EOF
"""Main entry point."""

import asyncio
from $PROJECT_NAME import greeting_pipeline


async def main():
    result = await greeting_pipeline.invoke("world")
    print(result)  # "HELLO, WORLD!"


if __name__ == "__main__":
    asyncio.run(main())
EOF

# Create a test file
cat > tests/test_basic.py << EOF
"""Basic tests."""

import pytest
from $PROJECT_NAME import GreetingBrick, UppercaseBrick, greeting_pipeline


@pytest.mark.asyncio
async def test_greeting_brick():
    brick = GreetingBrick()
    result = await brick.invoke("Alice")
    assert result == "Hello, Alice!"


@pytest.mark.asyncio
async def test_uppercase_brick():
    brick = UppercaseBrick()
    result = await brick.invoke("hello world")
    assert result == "HELLO WORLD"


@pytest.mark.asyncio
async def test_pipeline():
    result = await greeting_pipeline.invoke("test")
    assert result == "HELLO, TEST!"
EOF

# Create conftest.py
cat > tests/conftest.py << EOF
"""Test configuration."""

import pytest


@pytest.fixture
def anyio_backend():
    return "asyncio"
EOF

# Create setup script
cat > setup.sh << 'EOF'
#!/bin/bash
# Quick setup script

echo "Setting up development environment..."

# Create virtual environment
python3.13 -m venv .venv
source .venv/bin/activate

# Upgrade pip
pip install --upgrade pip

# Install package and dev dependencies
pip install -e .
pip install -e ".[dev]"

echo "✅ Setup complete!"
echo "Run 'source .venv/bin/activate' to activate the environment"
EOF

chmod +x setup.sh

# Final message
echo "✅ Project created successfully!"
echo ""
echo "Next steps:"
echo "1. cd $PROJECT_NAME"
echo "2. ./setup.sh"
echo "3. source .venv/bin/activate"
echo "4. python -m $PROJECT_NAME  # Run the example"
echo "5. pytest                   # Run tests"
echo ""
echo "Happy building with Nanobricks! 🧱"