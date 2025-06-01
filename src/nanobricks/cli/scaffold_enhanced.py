"""Enhanced project scaffolding for nanobricks."""

import shutil
import subprocess
from enum import Enum
from pathlib import Path

from rich.console import Console

from .templates import (
    ADVANCED_BRICK_TEMPLATE,
    DOCKER_COMPOSE_TEMPLATE,
    DOCKERFILE_TEMPLATE,
    GITHUB_WORKFLOW_TEMPLATE,
    MAKEFILE_TEMPLATE,
    PRE_COMMIT_CONFIG,
    SKILL_API_TEMPLATE,
    SKILL_CLI_TEMPLATE,
)

console = Console()


class BrickType(str, Enum):
    """Types of nanobricks to scaffold."""

    SIMPLE = "simple"
    VALIDATOR = "validator"
    TRANSFORMER = "transformer"
    ADVANCED = "advanced"
    PIPELINE = "pipeline"


class SkillType(str, Enum):
    """Available skills."""

    API = "api"
    CLI = "cli"
    LOGGING = "logging"
    OBSERVABILITY = "observability"
    DOCKER = "docker"
    KUBERNETES = "kubernetes"


# Enhanced templates
VALIDATOR_TEMPLATE = '''"""Validator nanobrick for {name}."""

from typing import Any, Optional

from nanobricks.validators.base import ValidatorBase


class {class_name}(ValidatorBase[Any]):
    """
    Validates {description}.
    
    Example:
        >>> validator = {class_name}()
        >>> result = await validator.invoke("valid input")
        >>> print(result)  # Returns input unchanged if valid
    """
    
    def __init__(
        self,
        *,
        strict: bool = True,
        custom_error: Optional[str] = None,
        name: str = "{name}",
        version: str = "0.1.0"
    ):
        """Initialize {class_name}.
        
        Args:
            strict: Use strict validation
            custom_error: Custom error message
            name: Validator name
            version: Validator version
        """
        super().__init__(name=name, version=version)
        self.strict = strict
        self.custom_error = custom_error
    
    async def validate(self, input: Any) -> Any:
        """Validate input.
        
        Args:
            input: Input to validate
            
        Returns:
            Input unchanged if valid
            
        Raises:
            ValueError: If validation fails
        """
        # TODO: Implement validation logic
        if not self._is_valid(input):
            error_msg = self.custom_error or f"Validation failed for {{input}}"
            raise ValueError(error_msg)
        
        return input
    
    def _is_valid(self, input: Any) -> bool:
        """Check if input is valid.
        
        Args:
            input: Input to check
            
        Returns:
            True if valid, False otherwise
        """
        # TODO: Implement validation logic
        return True
'''

TRANSFORMER_TEMPLATE = '''"""Transformer nanobrick for {name}."""

from typing import TypeVar

from nanobricks.transformers.base import TransformerBase

T_in = TypeVar("T_in")
T_out = TypeVar("T_out")


class {class_name}(TransformerBase[T_in, T_out]):
    """
    Transforms {description}.
    
    Example:
        >>> transformer = {class_name}()
        >>> result = await transformer.invoke(input_data)
        >>> print(result)  # Transformed output
    """
    
    def __init__(
        self,
        *,
        option1: str = "default",
        option2: bool = True,
        name: str = "{name}",
        version: str = "0.1.0"
    ):
        """Initialize {class_name}.
        
        Args:
            option1: Configuration option 1
            option2: Configuration option 2
            name: Transformer name
            version: Transformer version
        """
        super().__init__(name=name, version=version)
        self.option1 = option1
        self.option2 = option2
    
    async def transform(self, input: T_in) -> T_out:
        """Transform input to output.
        
        Args:
            input: Input data
            
        Returns:
            Transformed output
        """
        # TODO: Implement transformation logic
        # This is a placeholder that returns input unchanged
        return input  # type: ignore
'''

PIPELINE_TEMPLATE = '''"""Pipeline implementation for {name}."""

from typing import Dict, Any, Optional

from nanobricks import Pipeline, SimpleBrick
from nanobricks.validators import TypeValidator
from nanobricks.transformers import TextNormalizer


class InputValidator(SimpleBrick[Dict[str, Any], Dict[str, Any]]):
    """Validates pipeline input."""
    
    async def invoke(self, input: Dict[str, Any], *, deps=None) -> Dict[str, Any]:
        """Validate input structure."""
        required_fields = ["data", "type"]
        for field in required_fields:
            if field not in input:
                raise ValueError(f"Missing required field: {{field}}")
        return input


class DataProcessor(SimpleBrick[Dict[str, Any], Dict[str, Any]]):
    """Processes data in the pipeline."""
    
    async def invoke(self, input: Dict[str, Any], *, deps=None) -> Dict[str, Any]:
        """Process the data."""
        # TODO: Implement processing logic
        result = input.copy()
        result["processed"] = True
        result["timestamp"] = __import__("datetime").datetime.now().isoformat()
        return result


class OutputFormatter(SimpleBrick[Dict[str, Any], str]):
    """Formats pipeline output."""
    
    async def invoke(self, input: Dict[str, Any], *, deps=None) -> str:
        """Format output as string."""
        import json
        return json.dumps(input, indent=2)


def create_{module_name}_pipeline() -> Pipeline:
    """Create the {name} pipeline.
    
    Returns:
        Configured pipeline ready to use
    """
    return Pipeline(
        InputValidator(name="input_validator"),
        DataProcessor(name="data_processor"),
        OutputFormatter(name="output_formatter"),
        name="{name}_pipeline"
    )


# Convenience instance
{module_name}_pipeline = create_{module_name}_pipeline()
'''

EXAMPLE_USAGE_TEMPLATE = '''"""Example usage of {name}."""

import asyncio
from typing import Dict, Any

from {module_name} import {class_name}


async def basic_example():
    """Basic usage example."""
    print("=== Basic Example ===")
    
    # Create instance
    brick = {class_name}()
    
    # Process some data
    result = await brick.invoke("Hello, World!")
    print(f"Result: {{result}}")


async def advanced_example():
    """Advanced usage with configuration."""
    print("\\n=== Advanced Example ===")
    
    # Create with custom config
    brick = {class_name}(prefix="CUSTOM")
    
    # Process multiple items
    items = ["apple", "banana", "cherry"]
    for item in items:
        result = await brick.invoke(item)
        print(f"{{item}} -> {{result}}")


async def pipeline_example():
    """Example using in a pipeline."""
    print("\\n=== Pipeline Example ===")
    
    from nanobricks import Pipeline, SimpleBrick
    
    class UpperCaseBrick(SimpleBrick[str, str]):
        async def invoke(self, input: str, *, deps=None) -> str:
            return input.upper()
    
    # Create pipeline
    pipeline = Pipeline(
        {class_name}(),
        UpperCaseBrick(),
        name="example_pipeline"
    )
    
    # Process through pipeline
    result = await pipeline.invoke("test input")
    print(f"Pipeline result: {{result}}")


async def dependency_example():
    """Example with dependencies."""
    print("\\n=== Dependency Example ===")
    
    # Create brick
    brick = {class_name}()
    
    # Define dependencies
    deps = {{
        "logger": __import__("logging").getLogger(__name__),
        "config": {{"max_retries": 3, "timeout": 30}}
    }}
    
    # Process with dependencies
    result = await brick.invoke("data with deps", deps=deps)
    print(f"Result with deps: {{result}}")


async def main():
    """Run all examples."""
    print(f"\\n🚀 {class_name} Examples\\n")
    
    await basic_example()
    await advanced_example()
    await pipeline_example()
    await dependency_example()
    
    print("\\n✅ All examples complete!\\n")


if __name__ == "__main__":
    asyncio.run(main())
'''


def create_enhanced_project(
    name: str,
    brick_type: BrickType,
    skills: list[SkillType],
    description: str = "",
    author: str = "",
    email: str = "",
    output_dir: Path | None = None,
    include_docker: bool = False,
    include_ci: bool = False,
    include_examples: bool = True,
) -> Path:
    """Create an enhanced nanobrick project.

    Args:
        name: Project name (kebab-case)
        brick_type: Type of nanobrick to create
        skills: List of skills to include
        description: Project description
        author: Author name
        email: Author email
        output_dir: Output directory
        include_docker: Include Docker files
        include_ci: Include CI/CD configuration
        include_examples: Include example files

    Returns:
        Path to created project
    """
    from .scaffold import (
        CORE_TEMPLATE,
        GITIGNORE_TEMPLATE,
        INIT_TEMPLATE,
        NANOBRICK_TOML_TEMPLATE,
        PYPROJECT_TEMPLATE,
        README_TEMPLATE,
        TEST_TEMPLATE,
        VSCODE_SETTINGS,
        to_class_name,
        to_module_name,
    )

    # Prepare names and context
    class_name = to_class_name(name)
    module_name = to_module_name(name)
    title = " ".join(word.capitalize() for word in name.split("-"))

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

    # Create project directory
    project_dir = (output_dir or Path.cwd()) / name
    if project_dir.exists():
        shutil.rmtree(project_dir)

    project_dir.mkdir(parents=True)

    # Create directory structure
    src_dir = project_dir / "src" / module_name
    src_dir.mkdir(parents=True)

    tests_dir = project_dir / "tests"
    tests_dir.mkdir()

    # Add skill directories
    if SkillType.API in skills:
        (src_dir / "api").mkdir()
    if SkillType.CLI in skills:
        (src_dir / "cli").mkdir()

    # Create examples directory
    if include_examples:
        examples_dir = project_dir / "examples"
        examples_dir.mkdir()

    # VS Code settings
    vscode_dir = project_dir / ".vscode"
    vscode_dir.mkdir()
    (vscode_dir / "settings.json").write_text(VSCODE_SETTINGS)

    # Project files
    (project_dir / "pyproject.toml").write_text(PYPROJECT_TEMPLATE.format(**context))
    (project_dir / "README.md").write_text(README_TEMPLATE.format(**context))
    (project_dir / ".gitignore").write_text(GITIGNORE_TEMPLATE)
    (project_dir / "Makefile").write_text(MAKEFILE_TEMPLATE.format(**context))

    # Enhanced nanobrick.toml with skills
    toml_content = NANOBRICK_TOML_TEMPLATE.format(**context)
    if skills:
        skill_section = "\n[skills]\n"
        for skill in skills:
            skill_section += f"{skill.value} = true\n"
        toml_content = toml_content.replace("[skills]\n# Enable skills", skill_section)
    (project_dir / "nanobrick.toml").write_text(toml_content)

    # Source files - choose template based on type
    (src_dir / "__init__.py").write_text(INIT_TEMPLATE.format(**context))

    if brick_type == BrickType.SIMPLE:
        (src_dir / "core.py").write_text(CORE_TEMPLATE.format(**context))
    elif brick_type == BrickType.VALIDATOR:
        (src_dir / "core.py").write_text(VALIDATOR_TEMPLATE.format(**context))
    elif brick_type == BrickType.TRANSFORMER:
        (src_dir / "core.py").write_text(TRANSFORMER_TEMPLATE.format(**context))
    elif brick_type == BrickType.ADVANCED:
        (src_dir / "core.py").write_text(ADVANCED_BRICK_TEMPLATE.format(**context))
    elif brick_type == BrickType.PIPELINE:
        (src_dir / "core.py").write_text(PIPELINE_TEMPLATE.format(**context))

    # Add skill files
    if SkillType.API in skills:
        (src_dir / "api" / "__init__.py").write_text("")
        (src_dir / "api" / "main.py").write_text(SKILL_API_TEMPLATE.format(**context))

    if SkillType.CLI in skills:
        (src_dir / "cli" / "__init__.py").write_text("")
        (src_dir / "cli" / "main.py").write_text(SKILL_CLI_TEMPLATE.format(**context))

    # Test files
    (tests_dir / "__init__.py").write_text("")
    (tests_dir / f"test_{module_name}.py").write_text(TEST_TEMPLATE.format(**context))

    # Example files
    if include_examples:
        (examples_dir / "basic_usage.py").write_text(
            EXAMPLE_USAGE_TEMPLATE.format(**context)
        )

    # Docker files
    if include_docker:
        (project_dir / "Dockerfile").write_text(DOCKERFILE_TEMPLATE.format(**context))
        (project_dir / "docker-compose.yml").write_text(
            DOCKER_COMPOSE_TEMPLATE.format(**context)
        )
        (project_dir / ".dockerignore").write_text(GITIGNORE_TEMPLATE)

    # CI/CD files
    if include_ci:
        github_dir = project_dir / ".github" / "workflows"
        github_dir.mkdir(parents=True)
        (github_dir / "ci.yml").write_text(GITHUB_WORKFLOW_TEMPLATE)
        (project_dir / ".pre-commit-config.yaml").write_text(PRE_COMMIT_CONFIG)

    return project_dir


def init_git_repo(project_dir: Path):
    """Initialize git repository."""
    try:
        subprocess.run(
            ["git", "init"], cwd=project_dir, check=True, capture_output=True
        )
        subprocess.run(
            ["git", "add", "."], cwd=project_dir, check=True, capture_output=True
        )
        subprocess.run(
            ["git", "commit", "-m", "Initial commit"],
            cwd=project_dir,
            check=True,
            capture_output=True,
        )
        return True
    except subprocess.CalledProcessError:
        return False


def install_dependencies(project_dir: Path, dev: bool = True):
    """Install project dependencies."""
    try:
        cmd = ["pip", "install", "-e", ".[dev]" if dev else "."]
        subprocess.run(cmd, cwd=project_dir, check=True, capture_output=True)
        return True
    except subprocess.CalledProcessError:
        return False
