"""Project scaffolding for nanobricks."""

import shutil
from pathlib import Path

import typer
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.prompt import Confirm, Prompt
from rich.table import Table

from .scaffold_enhanced import (
    BrickType,
    SkillType,
    create_enhanced_project,
    init_git_repo,
    install_dependencies,
)

console = Console()

# Project templates
PYPROJECT_TEMPLATE = """[project]
name = "{name}"
version = "0.1.0"
description = "{description}"
authors = [{{name = "{author}", email = "{email}"}}]
readme = "README.md"
license = {{text = "MIT"}}
requires-python = ">=3.11"
dependencies = [
    "nanobricks>=0.1.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0.0",
    "pytest-asyncio>=0.23.0",
    "pytest-cov>=4.0.0",
    "black>=24.0.0",
    "ruff>=0.3.0",
    "mypy>=1.0.0",
]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.pytest.ini_options]
testpaths = ["tests"]
asyncio_mode = "auto"

[tool.ruff]
target-version = "py311"
line-length = 88

[tool.black]
line-length = 88
target-version = ["py311"]

[tool.mypy]
python_version = "3.11"
strict = true
"""

NANOBRICK_TOML_TEMPLATE = """[nanobrick]
name = "{name}"
version = "0.1.0"
description = "{description}"

[skills]
# Enable skills for your nanobrick
# logging = true
# api = true
# cli = true

[features]
# Feature flags
# async_only = false
# strict_types = true

[dependencies]
# External dependencies
# redis = "optional"
# postgres = "optional"
"""

README_TEMPLATE = """# {title}

{description}

## Installation

```bash
pip install {name}
```

## Usage

```python
from {module_name} import {class_name}

# Create instance
brick = {class_name}()

# Use it
result = await brick.invoke("input")
print(result)
```

## Development

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Format code
black src tests
ruff check --fix src tests

# Type check
mypy src
```

## License

MIT
"""

INIT_TEMPLATE = '''"""
{title}

{description}
"""

from .core import {class_name}

__version__ = "0.1.0"
__all__ = ["{class_name}"]
'''

CORE_TEMPLATE = '''"""Core implementation of {name}."""

from typing import Optional, TypeVar

from nanobricks import NanobrickBase

T_in = TypeVar("T_in")
T_out = TypeVar("T_out")
T_deps = TypeVar("T_deps")


class {class_name}(NanobrickBase[str, str, None]):
    """
    {description}
    
    Example:
        >>> brick = {class_name}()
        >>> result = await brick.invoke("hello")
        >>> print(result)
        {name_upper}: hello processed
    """
    
    def __init__(
        self,
        *,
        prefix: str = "{name_upper}",
        name: str = "{name}",
        version: str = "0.1.0"
    ):
        """Initialize {class_name}.
        
        Args:
            prefix: Prefix to add to output
            name: Brick name
            version: Brick version
        """
        super().__init__(name=name, version=version)
        self.prefix = prefix
    
    async def invoke(self, input: str, *, deps: None = None) -> str:
        """Process input string.
        
        Args:
            input: Input string to process
            deps: No dependencies required
            
        Returns:
            Processed string with prefix
        """
        # TODO: Implement your logic here
        return f"{{self.prefix}}: {{input}} processed"
'''

TEST_TEMPLATE = '''"""Tests for {name}."""

import pytest

from {module_name} import {class_name}


class Test{class_name}:
    """Test suite for {class_name}."""
    
    @pytest.fixture
    def brick(self):
        """Create test brick."""
        return {class_name}()
    
    @pytest.mark.asyncio
    async def test_basic_usage(self, brick):
        """Test basic functionality."""
        result = await brick.invoke("hello")
        assert result == "{name_upper}: hello processed"
    
    @pytest.mark.asyncio
    async def test_custom_prefix(self):
        """Test with custom prefix."""
        brick = {class_name}(prefix="CUSTOM")
        result = await brick.invoke("world")
        assert result == "CUSTOM: world processed"
    
    def test_sync_usage(self, brick):
        """Test synchronous usage."""
        result = brick.invoke_sync("sync")
        assert result == "{name_upper}: sync processed"
'''

VSCODE_SETTINGS = """{
    "python.testing.pytestEnabled": true,
    "python.testing.unittestEnabled": false,
    "python.linting.enabled": true,
    "python.linting.ruffEnabled": true,
    "python.formatting.provider": "black",
    "editor.formatOnSave": true,
    "python.analysis.typeCheckingMode": "strict",
    "[python]": {
        "editor.defaultFormatter": "ms-python.black-formatter",
        "editor.formatOnSave": true,
        "editor.codeActionsOnSave": {
            "source.fixAll": true,
            "source.organizeImports": true
        }
    }
}
"""

GITIGNORE_TEMPLATE = """# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
env/
venv/
.venv/
pip-log.txt
pip-delete-this-directory.txt
.pytest_cache/
.coverage
coverage.xml
*.cover
.hypothesis/
.mypy_cache/
.ruff_cache/
dist/
build/
*.egg-info/

# IDE
.vscode/
.idea/
*.swp
*.swo
*~

# OS
.DS_Store
Thumbs.db

# Project
.env
.envrc
"""


def to_class_name(name: str) -> str:
    """Convert kebab-case to PascalCase."""
    return "".join(word.capitalize() for word in name.split("-"))


def to_module_name(name: str) -> str:
    """Convert kebab-case to snake_case."""
    return name.replace("-", "_")


def create_project(
    name: str,
    description: str = "",
    author: str = "",
    email: str = "",
    output_dir: Path | None = None,
) -> Path:
    """Create a new nanobrick project.

    Args:
        name: Project name (kebab-case)
        description: Project description
        author: Author name
        email: Author email
        output_dir: Output directory (defaults to current)

    Returns:
        Path to created project
    """
    # Prepare names
    class_name = to_class_name(name)
    module_name = to_module_name(name)
    title = " ".join(word.capitalize() for word in name.split("-"))

    # Create project directory
    project_dir = (output_dir or Path.cwd()) / name
    if project_dir.exists():
        if not Confirm.ask(f"[yellow]Directory {project_dir} exists. Overwrite?[/]"):
            raise typer.Abort()
        shutil.rmtree(project_dir)

    project_dir.mkdir(parents=True)

    # Create directory structure
    src_dir = project_dir / "src" / module_name
    src_dir.mkdir(parents=True)

    tests_dir = project_dir / "tests"
    tests_dir.mkdir()

    vscode_dir = project_dir / ".vscode"
    vscode_dir.mkdir()

    # Write files
    context = {
        "name": name,
        "name_upper": name.upper().replace("-", "_"),
        "module_name": module_name,
        "class_name": class_name,
        "title": title,
        "description": description or f"A nanobrick for {title.lower()}",
        "author": author,
        "email": email,
    }

    # Project files
    (project_dir / "pyproject.toml").write_text(PYPROJECT_TEMPLATE.format(**context))
    (project_dir / "nanobrick.toml").write_text(
        NANOBRICK_TOML_TEMPLATE.format(**context)
    )
    (project_dir / "README.md").write_text(README_TEMPLATE.format(**context))
    (project_dir / ".gitignore").write_text(GITIGNORE_TEMPLATE)

    # Source files
    (src_dir / "__init__.py").write_text(INIT_TEMPLATE.format(**context))
    (src_dir / "core.py").write_text(CORE_TEMPLATE.format(**context))

    # Test files
    (tests_dir / "__init__.py").write_text("")
    (tests_dir / f"test_{module_name}.py").write_text(TEST_TEMPLATE.format(**context))

    # VS Code settings
    (vscode_dir / "settings.json").write_text(VSCODE_SETTINGS)

    return project_dir


app = typer.Typer(help="Nanobrick project scaffolding")


@app.command()
def new(
    name: str = typer.Argument(..., help="Project name (kebab-case)"),
    brick_type: BrickType = typer.Option(
        BrickType.SIMPLE, "--type", "-t", help="Type of nanobrick to create"
    ),
    skills: list[SkillType] | None = typer.Option(
        None, "--skill", "-s", help="Skills to include (can be used multiple times)"
    ),
    description: str | None = typer.Option(
        None, "--description", "-d", help="Project description"
    ),
    author: str | None = typer.Option(None, "--author", "-a", help="Author name"),
    email: str | None = typer.Option(None, "--email", "-e", help="Author email"),
    output_dir: Path | None = typer.Option(
        None, "--output", "-o", help="Output directory"
    ),
    docker: bool = typer.Option(False, "--docker", help="Include Docker files"),
    ci: bool = typer.Option(False, "--ci", help="Include CI/CD configuration"),
    examples: bool = typer.Option(
        True, "--examples/--no-examples", help="Include example files"
    ),
    git: bool = typer.Option(True, "--git/--no-git", help="Initialize git repository"),
    install: bool = typer.Option(
        False, "--install", help="Install dependencies after creation"
    ),
    interactive: bool = typer.Option(
        True, "--interactive/--no-interactive", "-i/-I", help="Interactive mode"
    ),
):
    """Create a new nanobrick project with enhanced features."""
    console.print(f"[bold blue]🧱 Creating nanobrick: {name}[/]")

    # Interactive mode
    if interactive:
        # Show brick types
        if not brick_type or brick_type == BrickType.SIMPLE:
            table = Table(title="Available Brick Types")
            table.add_column("Type", style="cyan")
            table.add_column("Description", style="green")

            table.add_row("simple", "Basic nanobrick with minimal structure")
            table.add_row("validator", "Input validation nanobrick")
            table.add_row("transformer", "Data transformation nanobrick")
            table.add_row(
                "advanced", "Full-featured nanobrick with caching, config, etc."
            )
            table.add_row("pipeline", "Multi-stage processing pipeline")

            console.print(table)

            brick_type_str = Prompt.ask(
                "Select brick type",
                choices=["simple", "validator", "transformer", "advanced", "pipeline"],
                default="simple",
            )
            brick_type = BrickType(brick_type_str)

        # Select skills
        if not skills:
            console.print("\n[bold]Available Skills:[/]")
            console.print("  • api - REST API with FastAPI")
            console.print("  • cli - Command-line interface with Typer")
            console.print("  • logging - Enhanced logging integration")
            console.print("  • observability - Metrics and tracing")
            console.print("  • docker - Docker deployment support")
            console.print("  • kubernetes - Kubernetes deployment")

            selected_skills = []
            if Confirm.ask("Add API skill?", default=False):
                selected_skills.append(SkillType.API)
            if Confirm.ask("Add CLI skill?", default=False):
                selected_skills.append(SkillType.CLI)
            if Confirm.ask("Add logging skill?", default=True):
                selected_skills.append(SkillType.LOGGING)

            skills = selected_skills or None

        # Other options
        if not description:
            description = Prompt.ask(
                "Description", default=f"A {brick_type.value} nanobrick for {name}"
            )
        if not author:
            author = Prompt.ask("Author name", default="")
        if not email:
            email = Prompt.ask("Author email", default="")

        if docker is False:
            docker = Confirm.ask("Include Docker files?", default=False)
        if ci is False:
            ci = Confirm.ask("Include CI/CD configuration?", default=False)
        if install is False:
            install = Confirm.ask("Install dependencies?", default=True)

    # Create project with progress
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        # Create project
        task = progress.add_task("Creating project structure...", total=None)

        try:
            project_dir = create_enhanced_project(
                name=name,
                brick_type=brick_type,
                skills=skills or [],
                description=description or "",
                author=author or "",
                email=email or "",
                output_dir=output_dir,
                include_docker=docker,
                include_ci=ci,
                include_examples=examples,
            )
            progress.update(task, completed=True)

            # Initialize git
            if git:
                progress.add_task("Initializing git repository...", total=None)
                if init_git_repo(project_dir):
                    console.print("[green]✓[/] Initialized git repository")
                else:
                    console.print("[yellow]⚠[/]  Could not initialize git repository")

            # Install dependencies
            if install:
                progress.add_task("Installing dependencies...", total=None)
                if install_dependencies(project_dir):
                    console.print("[green]✓[/] Installed dependencies")
                else:
                    console.print("[yellow]⚠[/]  Could not install dependencies")

        except Exception as e:
            console.print(f"[red]Error:[/] {e}")
            raise typer.Exit(1)

    # Success message
    console.print(
        f"\n[green]✅ Created {brick_type.value} nanobrick at:[/] {project_dir}"
    )

    # Show project structure
    console.print("\n[bold]Project Structure:[/]")
    console.print(f"  {name}/")
    console.print(f"  ├── src/{to_module_name(name)}/")
    console.print("  │   ├── __init__.py")
    console.print("  │   └── core.py")

    if skills:
        for skill in skills:
            if skill == SkillType.API:
                console.print("  │   └── api/")
            elif skill == SkillType.CLI:
                console.print("  │   └── cli/")

    console.print("  ├── tests/")
    console.print("  ├── pyproject.toml")
    console.print("  ├── nanobrick.toml")
    console.print("  ├── README.md")
    console.print("  └── Makefile")

    # Next steps
    console.print("\n[bold]Next Steps:[/]")
    console.print(f"  cd {project_dir.name}")

    if not install:
        console.print('  pip install -e ".[dev]"')

    console.print("  make test")

    if SkillType.API in (skills or []):
        console.print(f"  python -m {to_module_name(name)}.api.main")

    if SkillType.CLI in (skills or []):
        console.print(f"  python -m {to_module_name(name)}.cli.main --help")

    console.print("\n[dim]Run 'make help' to see all available commands[/]")


@app.command()
def list_templates():
    """List available project templates and options."""
    console.print("[bold blue]🧱 Nanobrick Project Templates[/]\n")

    # Brick types
    console.print("[bold]Brick Types:[/]")
    types_table = Table(show_header=True, header_style="bold cyan")
    types_table.add_column("Type", style="green")
    types_table.add_column("Description")
    types_table.add_column("Use Case", style="dim")

    types_table.add_row(
        "simple",
        "Basic nanobrick with minimal structure",
        "Quick prototypes, simple transformations",
    )
    types_table.add_row(
        "validator",
        "Input validation nanobrick",
        "Data validation, input checking, contracts",
    )
    types_table.add_row(
        "transformer",
        "Data transformation nanobrick",
        "Data conversion, formatting, processing",
    )
    types_table.add_row(
        "advanced",
        "Full-featured with caching, config, logging",
        "Production services, complex logic",
    )
    types_table.add_row(
        "pipeline", "Multi-stage processing pipeline", "Workflows, ETL, data pipelines"
    )

    console.print(types_table)

    # Skills
    console.print("\n[bold]Available Skills:[/]")
    skills_table = Table(show_header=True, header_style="bold cyan")
    skills_table.add_column("Skill", style="green")
    skills_table.add_column("Description")
    skills_table.add_column("Adds", style="dim")

    skills_table.add_row(
        "api", "REST API with FastAPI", "FastAPI app, endpoints, models"
    )
    skills_table.add_row(
        "cli", "Command-line interface", "Typer CLI, commands, batch processing"
    )
    skills_table.add_row(
        "logging", "Enhanced logging", "Structured logs, log levels, formatting"
    )
    skills_table.add_row(
        "observability", "Metrics and tracing", "OpenTelemetry, metrics, traces"
    )
    skills_table.add_row(
        "docker", "Container support", "Dockerfile, docker-compose.yml"
    )
    skills_table.add_row("kubernetes", "K8s deployment", "Manifests, Helm charts")

    console.print(skills_table)

    # Additional options
    console.print("\n[bold]Additional Options:[/]")
    console.print("  • [green]--docker[/] - Include Docker configuration")
    console.print("  • [green]--ci[/] - Add GitHub Actions CI/CD")
    console.print("  • [green]--examples[/] - Include usage examples")
    console.print("  • [green]--git[/] - Initialize git repository")
    console.print("  • [green]--install[/] - Install dependencies")

    # Example commands
    console.print("\n[bold]Example Commands:[/]")
    console.print("  # Simple nanobrick")
    console.print("  [dim]nanobrick new my-brick[/]")
    console.print("\n  # Validator with CLI")
    console.print("  [dim]nanobrick new my-validator --type validator --skill cli[/]")
    console.print("\n  # Advanced brick with full stack")
    console.print(
        "  [dim]nanobrick new my-service --type advanced --skill api --skill cli --docker --ci[/]"
    )
    console.print("\n  # Pipeline with examples")
    console.print("  [dim]nanobrick new my-pipeline --type pipeline --examples[/]")


@app.command()
def add_skill(
    skill: str = typer.Argument(..., help="Skill to add (api, cli, logging, etc.)"),
    path: Path = typer.Option(Path.cwd(), "--path", "-p", help="Project path"),
):
    """Add a skill to existing project."""
    # Find nanobrick.toml
    toml_path = path / "nanobrick.toml"
    if not toml_path.exists():
        toml_path = path.parent / "nanobrick.toml"
        if not toml_path.exists():
            console.print("[red]Error:[/] No nanobrick.toml found")
            raise typer.Exit(1)

    # TODO: Implement skill addition
    console.print(f"[yellow]Adding skill '{skill}' - not yet implemented[/]")


if __name__ == "__main__":
    app()
