"""Demonstration of nanobrick scaffolding features.

This example shows the various project templates and options available
through the nanobrick CLI scaffolding system.
"""

import os
import tempfile
from pathlib import Path

# Direct imports for demonstration (in real usage, you'd use the CLI)
from nanobricks.cli.scaffold import create_project, to_module_name
from nanobricks.cli.scaffold_enhanced import (
    BrickType,
    SkillType,
    create_enhanced_project,
)


def print_section(title: str):
    """Print a section header."""
    print(f"\n{'=' * 60}")
    print(f"{title}")
    print('=' * 60)


def show_project_structure(project_dir: Path, max_depth: int = 3):
    """Display project directory structure."""
    print(f"\nProject structure for {project_dir.name}:")
    
    for root, dirs, files in os.walk(project_dir):
        level = root.replace(str(project_dir), '').count(os.sep)
        if level > max_depth:
            continue
        indent = '  ' * level
        print(f"{indent}{os.path.basename(root)}/")
        subindent = '  ' * (level + 1)
        for file in files[:5]:  # Limit files shown
            print(f"{subindent}{file}")
        if len(files) > 5:
            print(f"{subindent}... and {len(files) - 5} more files")


def demo_simple_brick():
    """Demonstrate creating a simple nanobrick."""
    print_section("DEMO 1: Simple Nanobrick")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        project = create_project(
            name="hello-world",
            description="A simple hello world nanobrick",
            author="Demo User",
            email="demo@example.com",
            output_dir=Path(tmpdir),
        )
        
        show_project_structure(project)
        
        # Show core implementation
        core_file = project / "src" / "hello_world" / "core.py"
        print(f"\nCore implementation preview:")
        print("─" * 40)
        lines = core_file.read_text().split('\n')[:15]
        for line in lines:
            print(line)
        print("...")


def demo_validator_brick():
    """Demonstrate creating a validator nanobrick."""
    print_section("DEMO 2: Validator Nanobrick with CLI")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        project = create_enhanced_project(
            name="email-validator",
            brick_type=BrickType.VALIDATOR,
            skills=[SkillType.CLI],
            description="Email validation nanobrick",
            author="Demo User",
            email="demo@example.com",
            output_dir=Path(tmpdir),
        )
        
        show_project_structure(project)
        
        # Show validator specific features
        print("\nValidator features:")
        print("- Inherits from ValidatorBase")
        print("- Returns input unchanged if valid")
        print("- Raises ValueError on validation failure")
        print("- Includes CLI for batch validation")


def demo_transformer_brick():
    """Demonstrate creating a transformer nanobrick."""
    print_section("DEMO 3: Transformer Nanobrick")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        project = create_enhanced_project(
            name="json-transformer",
            brick_type=BrickType.TRANSFORMER,
            skills=[],
            description="JSON data transformation",
            author="Demo User",
            email="demo@example.com",
            output_dir=Path(tmpdir),
        )
        
        show_project_structure(project)
        
        print("\nTransformer features:")
        print("- Inherits from TransformerBase")
        print("- Type-safe input/output transformation")
        print("- Composable with other transformers")


def demo_advanced_brick():
    """Demonstrate creating an advanced nanobrick with multiple skills."""
    print_section("DEMO 4: Advanced Nanobrick with Full Stack")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        project = create_enhanced_project(
            name="data-processor",
            brick_type=BrickType.ADVANCED,
            skills=[SkillType.API, SkillType.CLI, SkillType.LOGGING],
            description="Advanced data processing service",
            author="Demo User",
            email="demo@example.com",
            output_dir=Path(tmpdir),
            include_docker=True,
            include_ci=True,
            include_examples=True,
        )
        
        show_project_structure(project)
        
        print("\nAdvanced features included:")
        print("✓ Caching support")
        print("✓ Configuration management")
        print("✓ Dependency injection")
        print("✓ Internal pipeline")
        print("✓ FastAPI REST endpoints")
        print("✓ Typer CLI commands")
        print("✓ Structured logging")
        print("✓ Docker deployment")
        print("✓ GitHub Actions CI/CD")
        print("✓ Usage examples")


def demo_pipeline_brick():
    """Demonstrate creating a pipeline nanobrick."""
    print_section("DEMO 5: Pipeline Nanobrick")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        project = create_enhanced_project(
            name="etl-pipeline",
            brick_type=BrickType.PIPELINE,
            skills=[SkillType.CLI, SkillType.OBSERVABILITY],
            description="ETL pipeline for data processing",
            author="Demo User",
            email="demo@example.com",
            output_dir=Path(tmpdir),
            include_examples=True,
        )
        
        # Show pipeline components
        core_file = project / "src" / "etl_pipeline" / "core.py"
        content = core_file.read_text()
        
        print("\nPipeline components:")
        import re
        classes = re.findall(r'^class (\w+)\(', content, re.MULTILINE)
        for cls in classes:
            if "Brick" in cls:
                print(f"  • {cls}")
        
        print("\nPipeline features:")
        print("- Multi-stage processing")
        print("- Input validation stage")
        print("- Data processing stage")
        print("- Output formatting stage")
        print("- CLI for pipeline execution")
        print("- OpenTelemetry observability")


def show_cli_commands():
    """Show example CLI commands."""
    print_section("CLI USAGE EXAMPLES")
    
    print("\n1. List available templates:")
    print("   $ nanobrick new list-templates")
    
    print("\n2. Interactive mode (default):")
    print("   $ nanobrick new my-awesome-brick")
    
    print("\n3. Create specific brick types:")
    print("   # Simple brick")
    print("   $ nanobrick new my-brick")
    
    print("\n   # Validator")
    print("   $ nanobrick new my-validator --type validator --skill cli")
    
    print("\n   # Transformer")
    print("   $ nanobrick new my-transformer --type transformer")
    
    print("\n   # Advanced service")
    print("   $ nanobrick new my-service \\")
    print("       --type advanced \\")
    print("       --skill api \\")
    print("       --skill cli \\")
    print("       --skill logging \\")
    print("       --docker \\")
    print("       --ci \\")
    print("       --install")
    
    print("\n   # Pipeline")
    print("   $ nanobrick new my-pipeline \\")
    print("       --type pipeline \\")
    print("       --skill observability \\")
    print("       --examples")
    
    print("\n4. Non-interactive mode:")
    print("   $ nanobrick new my-brick \\")
    print("       --description 'My awesome nanobrick' \\")
    print("       --author 'Your Name' \\")
    print("       --email 'you@example.com' \\")
    print("       --no-interactive")


def show_generated_files():
    """Show what files are generated for each brick type."""
    print_section("GENERATED FILES BY BRICK TYPE")
    
    print("\n[Simple Brick]")
    print("  src/<name>/")
    print("    __init__.py        # Package initialization")
    print("    core.py           # Basic implementation")
    print("  tests/")
    print("    test_<name>.py    # Unit tests")
    print("  pyproject.toml      # Project metadata")
    print("  nanobrick.toml      # Nanobrick config")
    print("  README.md           # Documentation")
    print("  Makefile            # Common tasks")
    
    print("\n[Validator Brick]")
    print("  + All simple files")
    print("  + Validator-specific implementation in core.py")
    print("  + Validation logic template")
    
    print("\n[Transformer Brick]")
    print("  + All simple files")
    print("  + Transformer-specific implementation")
    print("  + Type-safe transformation template")
    
    print("\n[Advanced Brick]")
    print("  + All simple files")
    print("  + Caching and configuration")
    print("  + Internal pipeline")
    print("  + Dependency injection")
    
    print("\n[Pipeline Brick]")
    print("  + All simple files")
    print("  + Multiple stage classes")
    print("  + Pipeline factory function")
    print("  + Convenience instance")
    
    print("\n[With Skills]")
    print("  --skill api:")
    print("    src/<name>/api/")
    print("      main.py         # FastAPI application")
    print("  --skill cli:")
    print("    src/<name>/cli/")
    print("      main.py         # Typer CLI")
    print("  --skill logging:")
    print("    + Logging configuration in core.py")
    print("  --skill observability:")
    print("    + OpenTelemetry integration")
    
    print("\n[With Options]")
    print("  --docker:")
    print("    Dockerfile        # Container image")
    print("    docker-compose.yml # Compose config")
    print("  --ci:")
    print("    .github/workflows/")
    print("      ci.yml          # GitHub Actions")
    print("    .pre-commit-config.yaml")
    print("  --examples:")
    print("    examples/")
    print("      basic_usage.py  # Usage examples")


def main():
    """Run all demonstrations."""
    print("🧱 Nanobrick Scaffolding System Demo")
    print("=" * 60)
    print("This demo shows the different project templates available")
    print("and how to use the scaffolding CLI.")
    
    # Run demos
    demo_simple_brick()
    demo_validator_brick()
    demo_transformer_brick()
    demo_advanced_brick()
    demo_pipeline_brick()
    
    # Show usage
    show_cli_commands()
    show_generated_files()
    
    print_section("SUMMARY")
    print("\nThe nanobrick scaffolding system provides:")
    print("✓ 5 brick types (simple, validator, transformer, advanced, pipeline)")
    print("✓ 6 skills (api, cli, logging, observability, docker, kubernetes)")
    print("✓ Docker and CI/CD integration")
    print("✓ Interactive and non-interactive modes")
    print("✓ Complete project structure with tests")
    print("✓ VS Code configuration")
    print("✓ Makefile for common tasks")
    
    print("\nGet started:")
    print("1. Install nanobricks: pip install -e .")
    print("2. Run: nanobrick new --help")
    print("3. Create your first brick: nanobrick new my-awesome-brick")
    
    print("\n✅ Demo complete!")


if __name__ == "__main__":
    main()