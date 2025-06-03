"""Documentation generator for nanobricks."""

import inspect
from pathlib import Path
from typing import Any, get_type_hints

from nanobricks import NanobrickProtocol


class DocumentationGenerator:
    """Generate documentation for nanobricks."""

    def __init__(self, output_dir: Path = Path("docs")):
        """Initialize documentation generator.

        Args:
            output_dir: Output directory for documentation
        """
        self.output_dir = output_dir
        self.output_dir.mkdir(exist_ok=True)

    def document_brick(self, brick_class: type[NanobrickProtocol]) -> str:
        """Generate documentation for a single brick.

        Args:
            brick_class: Nanobrick class to document

        Returns:
            Markdown documentation
        """
        # Get class info
        name = brick_class.__name__
        module = brick_class.__module__
        docstring = inspect.getdoc(brick_class) or "No description available."

        # Get type hints
        try:
            hints = get_type_hints(brick_class.invoke)
            input_type = self._format_type(hints.get("input", "Any"))
            return_type = self._format_type(hints.get("return", "Any"))
        except:
            input_type = "Any"
            return_type = "Any"

        # Start documentation
        doc = f"# {name}\n\n"
        doc += f"`{module}.{name}`\n\n"
        doc += f"{docstring}\n\n"

        # Type information
        doc += "## Type Signature\n\n"
        doc += f"- **Input**: `{input_type}`\n"
        doc += f"- **Output**: `{return_type}`\n"
        doc += f"- **Dependencies**: `{self._get_deps_type(brick_class)}`\n\n"

        # Constructor
        init_doc = inspect.getdoc(brick_class.__init__)
        if init_doc:
            doc += "## Constructor\n\n"
            doc += f"```python\n{name}(...)\n```\n\n"
            doc += f"{init_doc}\n\n"

        # Methods
        doc += "## Methods\n\n"

        # Document invoke method
        invoke_doc = inspect.getdoc(brick_class.invoke)
        if invoke_doc:
            doc += "### invoke\n\n"
            doc += f"```python\nasync def invoke(input: {input_type}, *, deps=None) -> {return_type}\n```\n\n"
            doc += f"{invoke_doc}\n\n"

        # Document invoke_sync if available
        if hasattr(brick_class, "invoke_sync"):
            sync_doc = inspect.getdoc(brick_class.invoke_sync)
            if sync_doc:
                doc += "### invoke_sync\n\n"
                doc += f"```python\ndef invoke_sync(input: {input_type}, *, deps=None) -> {return_type}\n```\n\n"
                doc += f"{sync_doc}\n\n"

        # Usage examples
        examples = self._extract_examples(brick_class)
        if examples:
            doc += "## Examples\n\n"
            for example in examples:
                doc += f"```python\n{example}\n```\n\n"

        # Skills
        skills = self._get_supported_skills(brick_class)
        if skills:
            doc += "## Supported Skills\n\n"
            for skill in skills:
                doc += f"- {skill}\n"
            doc += "\n"

        # Composition
        doc += "## Composition\n\n"
        doc += (
            "This brick can be composed with other bricks using the pipe operator:\n\n"
        )
        doc += f"```python\npipeline = {name}() >> OtherBrick()\nresult = await pipeline.invoke(input)\n```\n\n"

        return doc

    def _format_type(self, type_obj: Any) -> str:
        """Format type object to readable string."""
        if type_obj is None:
            return "None"

        # Handle common types
        if type_obj == str:
            return "str"
        elif type_obj == int:
            return "int"
        elif type_obj == float:
            return "float"
        elif type_obj == bool:
            return "bool"
        elif type_obj == list:
            return "list"
        elif type_obj == dict:
            return "dict"
        elif type_obj == type(None):
            return "None"

        # Handle generic types
        type_str = str(type_obj)

        # Clean up common patterns
        type_str = type_str.replace("<class '", "").replace("'>", "")
        type_str = type_str.replace("typing.", "")
        type_str = type_str.replace("NoneType", "None")

        return type_str

    def _get_deps_type(self, brick_class: type) -> str:
        """Extract dependencies type from class."""
        # Try to get from type parameters
        if hasattr(brick_class, "__orig_bases__"):
            for base in brick_class.__orig_bases__:
                if hasattr(base, "__args__") and len(base.__args__) >= 3:
                    return self._format_type(base.__args__[2])
        return "None"

    def _extract_examples(self, brick_class: type) -> list[str]:
        """Extract examples from docstring."""
        docstring = inspect.getdoc(brick_class)
        if not docstring:
            return []

        examples = []
        in_example = False
        current_example = []

        for line in docstring.split("\n"):
            if "Example:" in line or ">>>" in line:
                in_example = True
                if ">>>" in line:
                    current_example.append(line.strip())
            elif in_example:
                if line.strip() == "":
                    if current_example:
                        examples.append("\n".join(current_example))
                        current_example = []
                    in_example = False
                else:
                    current_example.append(line.strip())

        if current_example:
            examples.append("\n".join(current_example))

        return examples

    def _get_supported_skills(self, brick_class: type) -> list[str]:
        """Get list of supported skills."""
        skills = []

        # Check for skill methods
        if hasattr(brick_class, "with_skill"):
            skills.append("Skill Framework")

        # Check for specific skill support
        skill_checks = {
            "with_logging": "Logging",
            "with_api": "API",
            "with_cli": "CLI",
            "with_observability": "Observability",
            "with_deployment": "Deployment",
        }

        for method, skill_name in skill_checks.items():
            if hasattr(brick_class, method):
                skills.append(skill_name)

        return skills

    def generate_index(self, bricks: list[type[NanobrickProtocol]]) -> str:
        """Generate index page for documentation.

        Args:
            bricks: List of nanobrick classes

        Returns:
            Markdown index page
        """
        doc = "# Nanobricks Documentation\n\n"
        doc += "## Available Bricks\n\n"

        # Group by module
        by_module: dict[str, list[type]] = {}
        for brick in bricks:
            module = brick.__module__
            if module not in by_module:
                by_module[module] = []
            by_module[module].append(brick)

        # Generate index
        for module, module_bricks in sorted(by_module.items()):
            doc += f"### {module}\n\n"
            for brick in sorted(module_bricks, key=lambda b: b.__name__):
                desc = (inspect.getdoc(brick) or "").split("\n")[0]
                doc += f"- [{brick.__name__}]({brick.__name__.lower()}.md) - {desc}\n"
            doc += "\n"

        return doc

    def generate_composition_diagram(self, pipeline: NanobrickProtocol) -> str:
        """Generate ASCII diagram of pipeline composition.

        Args:
            pipeline: Pipeline to diagram

        Returns:
            ASCII diagram
        """
        # Simple ASCII representation
        if hasattr(pipeline, "bricks"):
            bricks = pipeline.bricks
            diagram = "Pipeline Composition:\n\n"

            for i, brick in enumerate(bricks):
                name = brick.__class__.__name__
                if i == 0:
                    diagram += "┌─────────────┐\n"
                    diagram += f"│ {name:^11} │\n"
                    diagram += "└──────┬──────┘\n"
                elif i == len(bricks) - 1:
                    diagram += "       │\n"
                    diagram += "       ▼\n"
                    diagram += "┌─────────────┐\n"
                    diagram += f"│ {name:^11} │\n"
                    diagram += "└─────────────┘\n"
                else:
                    diagram += "       │\n"
                    diagram += "       ▼\n"
                    diagram += "┌─────────────┐\n"
                    diagram += f"│ {name:^11} │\n"
                    diagram += "└──────┬──────┘\n"

            return diagram

        return "Single brick (no composition)"

    def write_docs(self, bricks: list[type[NanobrickProtocol]]):
        """Write documentation files.

        Args:
            bricks: List of nanobrick classes to document
        """
        # Generate index
        index = self.generate_index(bricks)
        (self.output_dir / "index.md").write_text(index)

        # Generate individual brick docs
        for brick in bricks:
            doc = self.document_brick(brick)
            filename = f"{brick.__name__.lower()}.md"
            (self.output_dir / filename).write_text(doc)

        print(f"Documentation generated in {self.output_dir}")


def generate_docs(
    module_path: Path | None = None,
    output_dir: Path = Path("docs/api"),
    recursive: bool = True,
) -> None:
    """Generate documentation for all nanobricks in a module.

    Args:
        module_path: Path to module to document
        output_dir: Output directory
        recursive: Recursively find nanobricks
    """
    import importlib

    generator = DocumentationGenerator(output_dir)
    bricks = []

    # Find all nanobrick classes
    if module_path:
        # Import module
        spec = importlib.util.spec_from_file_location("module", module_path)
        if spec and spec.loader:
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)

            # Find nanobricks
            for name, obj in inspect.getmembers(module):
                if (
                    inspect.isclass(obj)
                    and issubclass(obj, NanobrickProtocol)
                    and obj is not NanobrickProtocol
                ):
                    bricks.append(obj)

    # Generate documentation
    if bricks:
        generator.write_docs(bricks)
    else:
        print("No nanobricks found to document")
