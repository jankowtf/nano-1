"""Templates for project scaffolding."""

# Additional skill templates
SKILL_API_TEMPLATE = '''"""API skill for {name}."""

from typing import Any, Dict
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from nanobricks import skill
from {module_name} import {class_name}


class {class_name}Request(BaseModel):
    """Request model for {class_name} API."""
    data: str


class {class_name}Response(BaseModel):
    """Response model for {class_name} API."""
    result: str
    status: str = "success"


# Create FastAPI app
app = FastAPI(
    title="{title} API",
    description="{description}",
    version="0.1.0"
)

# Create brick instance
brick = {class_name}()


@app.post("/process", response_model={class_name}Response)
async def process(request: {class_name}Request):
    """Process data with {class_name}."""
    try:
        result = await brick.invoke(request.data)
        return {class_name}Response(result=result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {{"status": "healthy", "service": "{name}"}}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
'''

SKILL_CLI_TEMPLATE = '''"""CLI interface for {name}."""

import asyncio
import json
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table

from {module_name} import {class_name}

console = Console()
app = typer.Typer(help="{description}")

# Global brick instance
brick = {class_name}()


@app.command()
def process(
    input: str = typer.Argument(..., help="Input to process"),
    output_format: str = typer.Option("text", "--format", "-f", help="Output format (text/json)"),
):
    """Process input with {class_name}."""
    try:
        # Run async function
        result = asyncio.run(brick.invoke(input))
        
        if output_format == "json":
            console.print_json({{"input": input, "output": result}})
        else:
            console.print(f"[green]Result:[/] {{result}}")
            
    except Exception as e:
        console.print(f"[red]Error:[/] {{e}}")
        raise typer.Exit(1)


@app.command()
def batch(
    file: Path = typer.Argument(..., help="Input file (one item per line)"),
    output: Optional[Path] = typer.Option(None, "--output", "-o", help="Output file"),
):
    """Process multiple inputs from file."""
    if not file.exists():
        console.print(f"[red]Error:[/] File {{file}} not found")
        raise typer.Exit(1)
    
    inputs = file.read_text().strip().split("\\n")
    results = []
    
    with console.status(f"Processing {{len(inputs)}} items..."):
        for i, input_text in enumerate(inputs, 1):
            try:
                result = asyncio.run(brick.invoke(input_text))
                results.append({{"input": input_text, "output": result, "status": "success"}})
            except Exception as e:
                results.append({{"input": input_text, "error": str(e), "status": "failed"}})
            
            console.print(f"Processed {{i}}/{{len(inputs)}}")
    
    # Output results
    if output:
        output.write_text(json.dumps(results, indent=2))
        console.print(f"[green]✓[/] Results saved to {{output}}")
    else:
        # Display table
        table = Table(title="Processing Results")
        table.add_column("Input", style="cyan")
        table.add_column("Output", style="green")
        table.add_column("Status", style="yellow")
        
        for result in results:
            table.add_row(
                result["input"],
                result.get("output", result.get("error", "")),
                result["status"]
            )
        
        console.print(table)


@app.command()
def info():
    """Show information about the brick."""
    console.print(f"[bold]{{brick.name}}[/] v{{brick.version}}")
    console.print(f"Description: {description}")
    console.print(f"Type: {{type(brick).__name__}}")
    
    # Show example
    console.print("\\n[bold]Example:[/]")
    console.print("  nanobrick process 'hello world'")


if __name__ == "__main__":
    app()
'''

ADVANCED_BRICK_TEMPLATE = '''"""Advanced nanobrick implementation with multiple features."""

from typing import Any, Dict, List, Optional, TypedDict
import logging

from nanobricks import NanobrickBase, skill, Pipeline
from nanobricks.validators import TypeValidator, RangeValidator
from nanobricks.transformers import TextNormalizer


class {class_name}Config(TypedDict):
    """Configuration for {class_name}."""
    max_length: int
    min_length: int
    normalize: bool
    validate_strict: bool


class {class_name}Deps(TypedDict, total=False):
    """Dependencies for {class_name}."""
    logger: logging.Logger
    cache: Dict[str, Any]
    config: {class_name}Config


@skill("logging", level="INFO")
class {class_name}(NanobrickBase[str, Dict[str, Any], {class_name}Deps]):
    """
    Advanced implementation of {name}.
    
    Features:
    - Input validation
    - Text normalization
    - Caching support
    - Configurable behavior
    - Logging integration
    
    Example:
        >>> config = {{"max_length": 100, "min_length": 1, "normalize": True, "validate_strict": True}}
        >>> deps = {{"config": config}}
        >>> brick = {class_name}()
        >>> result = await brick.invoke("Hello World!", deps=deps)
        >>> print(result)
        {{'input': 'Hello World!', 'processed': 'hello world', 'length': 11, 'cached': False}}
    """
    
    def __init__(
        self,
        *,
        default_config: Optional[{class_name}Config] = None,
        enable_cache: bool = True,
        name: str = "{name}",
        version: str = "0.1.0"
    ):
        """Initialize {class_name}.
        
        Args:
            default_config: Default configuration
            enable_cache: Enable caching
            name: Brick name
            version: Brick version
        """
        super().__init__(name=name, version=version)
        
        self.default_config = default_config or {{
            "max_length": 1000,
            "min_length": 1,
            "normalize": True,
            "validate_strict": False
        }}
        self.enable_cache = enable_cache
        
        # Create internal pipeline
        self._create_pipeline()
    
    def _create_pipeline(self):
        """Create internal processing pipeline."""
        # Validators
        self.type_validator = TypeValidator(expected_type=str)
        self.length_validator = RangeValidator(
            min_value=self.default_config["min_length"],
            max_value=self.default_config["max_length"],
            value_extractor=len
        )
        
        # Transformers
        self.normalizer = TextNormalizer(
            lowercase=True,
            remove_extra_spaces=True
        )
        
        # Compose pipeline
        self.validation_pipeline = Pipeline(
            self.type_validator,
            self.length_validator
        )
    
    async def invoke(
        self, 
        input: str, 
        *, 
        deps: Optional[{class_name}Deps] = None
    ) -> Dict[str, Any]:
        """Process input with advanced features.
        
        Args:
            input: Input string to process
            deps: Optional dependencies
            
        Returns:
            Dictionary with processing results
        """
        # Get config and logger
        config = (deps or {{}}).get("config", self.default_config)
        logger = (deps or {{}}).get("logger")
        cache = (deps or {{}}).get("cache", {{}}) if self.enable_cache else {{}}
        
        # Log start
        if logger:
            logger.info(f"Processing input of length {{len(input)}}")
        
        # Check cache
        cache_key = f"{{self.name}}:{{input}}"
        if cache_key in cache:
            if logger:
                logger.debug(f"Cache hit for key: {{cache_key}}")
            cached_result = cache[cache_key]
            cached_result["cached"] = True
            return cached_result
        
        # Validate input
        if config["validate_strict"]:
            await self.validation_pipeline.invoke(input)
        
        # Process
        processed = input
        if config["normalize"]:
            processed = await self.normalizer.invoke(input)
        
        # Create result
        result = {{
            "input": input,
            "processed": processed,
            "length": len(processed),
            "cached": False,
            "config": {{
                "normalized": config["normalize"],
                "validated": config["validate_strict"]
            }}
        }}
        
        # Cache result
        if self.enable_cache:
            cache[cache_key] = result.copy()
            if logger:
                logger.debug(f"Cached result for key: {{cache_key}}")
        
        return result
    
    def clear_cache(self, deps: Optional[{class_name}Deps] = None):
        """Clear the cache."""
        if deps and "cache" in deps:
            deps["cache"].clear()
'''

DOCKERFILE_TEMPLATE = """FROM python:3.13-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \\
    gcc \\
    && rm -rf /var/lib/apt/lists/*

# Copy project files
COPY pyproject.toml README.md ./
COPY src/ ./src/

# Install package
RUN pip install --no-cache-dir -e .

# Create non-root user
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

# Default command (override as needed)
CMD ["python", "-m", "{module_name}"]
"""

DOCKER_COMPOSE_TEMPLATE = """version: '3.8'

services:
  {name}:
    build: .
    image: {name}:latest
    ports:
      - "8000:8000"
    environment:
      - LOG_LEVEL=INFO
      - ENV=development
    volumes:
      - ./config:/app/config:ro
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s

  # Add additional services as needed
  # redis:
  #   image: redis:7-alpine
  #   ports:
  #     - "6379:6379"
"""

MAKEFILE_TEMPLATE = """# {title} Makefile

.PHONY: help install dev test lint format clean build docker run

help: ## Show this help message
\t@echo 'Usage: make [target]'
\t@echo ''
\t@echo 'Targets:'
\t@awk 'BEGIN {{FS = ":.*?## "}} /^[a-zA-Z_-]+:.*?## / {{printf "  \\033[36m%-15s\\033[0m %s\\n", $$1, $$2}}' $(MAKEFILE_LIST)

install: ## Install package
\tpip install -e .

dev: ## Install with dev dependencies
\tpip install -e ".[dev]"

test: ## Run tests
\tpytest tests/ -v

test-cov: ## Run tests with coverage
\tpytest tests/ --cov=src --cov-report=html --cov-report=term

lint: ## Run linters
\truff check src tests
\tmypy src

format: ## Format code
\tblack src tests
\truff check --fix src tests

clean: ## Clean build artifacts
\trm -rf build dist *.egg-info
\tfind . -type d -name __pycache__ -exec rm -rf {{}} +
\tfind . -type f -name "*.pyc" -delete

build: clean ## Build package
\tpython -m build

docker: ## Build Docker image
\tdocker build -t {name}:latest .

run: ## Run the application
\tpython -m {module_name}

# Development helpers
watch: ## Watch for changes and run tests
\twatchmedo shell-command -p "*.py" -c "clear && make test" -R -D .

serve-docs: ## Serve documentation
\tmkdocs serve

publish: build ## Publish to PyPI
\ttwine upload dist/*
"""

GITHUB_WORKFLOW_TEMPLATE = """name: CI

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main ]

jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: ['3.13']
    
    steps:
    - uses: actions/checkout@v4
    
    - name: Set up Python ${{{{ matrix.python-version }}}}
      uses: actions/setup-python@v4
      with:
        python-version: ${{{{ matrix.python-version }}}}
    
    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install -e ".[dev]"
    
    - name: Lint with ruff
      run: |
        ruff check src tests
    
    - name: Type check with mypy
      run: |
        mypy src
    
    - name: Test with pytest
      run: |
        pytest tests/ --cov=src --cov-report=xml
    
    - name: Upload coverage
      uses: codecov/codecov-action@v3
      with:
        file: ./coverage.xml
"""

PRE_COMMIT_CONFIG = """repos:
  - repo: https://github.com/psf/black
    rev: 24.3.0
    hooks:
      - id: black
        language_version: python3.13

  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.3.0
    hooks:
      - id: ruff
        args: [--fix]

  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v1.8.0
    hooks:
      - id: mypy
        additional_dependencies: [types-all]
        args: [--strict]
"""
