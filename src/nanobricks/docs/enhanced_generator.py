"""Enhanced documentation generator for nanobricks."""

import ast
import importlib
import importlib.util
import inspect
import json
import re
import sys
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import (
    Any,
    Union,
    get_args,
    get_origin,
    get_type_hints,
)


@dataclass(order=True)
class BrickInfo:
    """Information about a nanobrick."""

    name: str
    module: str
    class_obj: type
    docstring: str
    input_type: str
    output_type: str
    deps_type: str
    constructor_params: list[dict[str, Any]]
    methods: list[dict[str, Any]]
    examples: list[str]
    skills: list[str]
    source_file: Path | None = None
    line_number: int | None = None
    is_validator: bool = False
    is_transformer: bool = False
    is_pipeline: bool = False
    composition_info: dict[str, Any] | None = None
    version: str = "0.1.0"


@dataclass
class ExampleInfo:
    """Information about a code example."""

    code: str
    description: str | None = None
    output: str | None = None
    async_example: bool = False


class EnhancedDocumentationGenerator:
    """Enhanced documentation generator with advanced features."""

    def __init__(
        self,
        output_dir: Path = Path("docs/api"),
        format: str = "markdown",
        include_source: bool = True,
        include_diagrams: bool = True,
        extract_from_tests: bool = True,
    ):
        """Initialize enhanced documentation generator.

        Args:
            output_dir: Output directory for documentation
            format: Output format (markdown, html, json)
            include_source: Include source code references
            include_diagrams: Generate composition diagrams
            extract_from_tests: Extract examples from test files
        """
        self.output_dir = output_dir
        self.format = format
        self.include_source = include_source
        self.include_diagrams = include_diagrams
        self.extract_from_tests = extract_from_tests
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Cache for discovered bricks
        self._brick_cache: dict[str, BrickInfo] = {}

    def discover_bricks(self, search_paths: list[Path]) -> list[BrickInfo]:
        """Discover all nanobricks in given paths.

        Args:
            search_paths: List of paths to search for nanobricks

        Returns:
            List of discovered brick information
        """
        bricks = []

        for path in search_paths:
            if path.is_file() and path.suffix == ".py":
                bricks.extend(self._discover_in_file(path))
            elif path.is_dir():
                for py_file in path.rglob("*.py"):
                    if not any(part.startswith(".") for part in py_file.parts):
                        bricks.extend(self._discover_in_file(py_file))

        # Cache discovered bricks
        for brick in bricks:
            self._brick_cache[f"{brick.module}.{brick.name}"] = brick

        return bricks

    def _discover_in_file(self, file_path: Path) -> list[BrickInfo]:
        """Discover nanobricks in a Python file."""
        bricks = []

        try:
            # Parse AST
            with open(file_path) as f:
                tree = ast.parse(f.read(), filename=str(file_path))

            # Find all classes
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    # Check if it's a nanobrick
                    if self._is_nanobrick_class(node):
                        # Load the module to get class object
                        module_name = self._get_module_name(file_path)
                        class_obj = self._load_class(file_path, module_name, node.name)

                        if class_obj:
                            info = self._extract_brick_info(
                                class_obj,
                                source_file=file_path,
                                line_number=node.lineno,
                            )
                            bricks.append(info)

        except Exception as e:
            print(f"Error processing {file_path}: {e}")

        return bricks

    def _is_nanobrick_class(self, node: ast.ClassDef) -> bool:
        """Check if AST node is a nanobrick class."""
        # Check base classes
        for base in node.bases:
            base_str = ast.unparse(base) if hasattr(ast, "unparse") else str(base)
            if "NanobrickBase" in base_str or "NanobrickProtocol" in base_str:
                return True
            if "SimpleBrick" in base_str or "ValidatorBase" in base_str:
                return True
            if "TransformerBase" in base_str:
                return True
        return False

    def _get_module_name(self, file_path: Path) -> str:
        """Get module name from file path."""
        # Try to determine module name from path
        parts = file_path.with_suffix("").parts

        # Find src or package root
        for i, part in enumerate(parts):
            if part == "src" and i < len(parts) - 1:
                return ".".join(parts[i + 1 :])
            elif part in ["nanobricks", "examples", "tests"]:
                return ".".join(parts[i:])

        return file_path.stem

    def _load_class(
        self, file_path: Path, module_name: str, class_name: str
    ) -> type | None:
        """Load a class from a file."""
        try:
            spec = importlib.util.spec_from_file_location(module_name, file_path)
            if spec and spec.loader:
                module = importlib.util.module_from_spec(spec)
                sys.modules[module_name] = module
                spec.loader.exec_module(module)
                return getattr(module, class_name, None)
        except Exception as e:
            print(f"Error loading {class_name} from {file_path}: {e}")
        return None

    def _extract_brick_info(
        self,
        brick_class: type,
        source_file: Path | None = None,
        line_number: int | None = None,
    ) -> BrickInfo:
        """Extract comprehensive information about a brick."""
        name = brick_class.__name__
        module = brick_class.__module__
        docstring = inspect.getdoc(brick_class) or "No description available."

        # Get version if available
        version = "0.1.0"
        if hasattr(brick_class, "version"):
            version = brick_class.version
        elif hasattr(brick_class, "__version__"):
            version = brick_class.__version__

        # Get type information
        input_type, output_type, deps_type = self._extract_type_info(brick_class)

        # Get constructor parameters
        constructor_params = self._extract_constructor_params(brick_class)

        # Get methods
        methods = self._extract_methods(brick_class)

        # Extract examples
        examples = self._extract_enhanced_examples(brick_class)

        # Get skills
        skills = self._get_supported_skills(brick_class)

        # Check brick type
        is_validator = self._is_validator(brick_class)
        is_transformer = self._is_transformer(brick_class)
        is_pipeline = self._is_pipeline(brick_class)

        # Get composition info
        composition_info = self._extract_composition_info(brick_class)

        return BrickInfo(
            name=name,
            module=module,
            class_obj=brick_class,
            docstring=docstring,
            version=version,
            input_type=input_type,
            output_type=output_type,
            deps_type=deps_type,
            constructor_params=constructor_params,
            methods=methods,
            examples=examples,
            skills=skills,
            source_file=source_file,
            line_number=line_number,
            is_validator=is_validator,
            is_transformer=is_transformer,
            is_pipeline=is_pipeline,
            composition_info=composition_info,
        )

    def _extract_type_info(self, brick_class: type) -> tuple[str, str, str]:
        """Extract type information from a brick class."""
        input_type = "Any"
        output_type = "Any"
        deps_type = "None"

        try:
            # Try to get from invoke method
            hints = get_type_hints(brick_class.invoke)
            input_type = self._format_type(hints.get("input", Any))
            output_type = self._format_type(hints.get("return", Any))

            # Get deps type from method signature
            sig = inspect.signature(brick_class.invoke)
            if "deps" in sig.parameters:
                param = sig.parameters["deps"]
                if param.annotation != inspect.Parameter.empty:
                    deps_type = self._format_type(param.annotation)
        except:
            pass

        # Try to get from class type parameters
        if hasattr(brick_class, "__orig_bases__"):
            for base in brick_class.__orig_bases__:
                if hasattr(base, "__args__") and len(base.__args__) >= 2:
                    input_type = self._format_type(base.__args__[0])
                    output_type = self._format_type(base.__args__[1])
                    if len(base.__args__) >= 3:
                        deps_type = self._format_type(base.__args__[2])
                    break

        return input_type, output_type, deps_type

    def _format_type(self, type_obj: Any) -> str:
        """Format type object to readable string."""
        if type_obj is None or type_obj == type(None):
            return "None"

        # Handle Any
        if type_obj is Any:
            return "Any"

        # Handle basic types
        if type_obj in (str, int, float, bool, list, dict, tuple, set):
            return type_obj.__name__

        # Handle Optional
        origin = get_origin(type_obj)
        if origin is Union:
            args = get_args(type_obj)
            if len(args) == 2 and type(None) in args:
                other_type = args[0] if args[1] is type(None) else args[1]
                return f"Optional[{self._format_type(other_type)}]"
            else:
                return f"Union[{', '.join(self._format_type(arg) for arg in args)}]"

        # Handle List, Dict, etc.
        if origin in (list, list):
            args = get_args(type_obj)
            if args:
                return f"List[{self._format_type(args[0])}]"
            return "List"

        if origin in (dict, dict):
            args = get_args(type_obj)
            if len(args) >= 2:
                return (
                    f"Dict[{self._format_type(args[0])}, {self._format_type(args[1])}]"
                )
            return "Dict"

        # Handle custom types
        if hasattr(type_obj, "__name__"):
            return type_obj.__name__

        # Fallback to string representation
        type_str = str(type_obj)
        type_str = type_str.replace("<class '", "").replace("'>", "")
        type_str = type_str.replace("typing.", "")
        return type_str

    def _extract_constructor_params(self, brick_class: type) -> list[dict[str, Any]]:
        """Extract constructor parameters."""
        params = []

        try:
            sig = inspect.signature(brick_class.__init__)
            for name, param in sig.parameters.items():
                if name in ("self", "cls"):
                    continue

                param_info = {
                    "name": name,
                    "type": "Any",
                    "default": None,
                    "required": param.default == inspect.Parameter.empty,
                    "description": "",
                }

                # Get type
                if param.annotation != inspect.Parameter.empty:
                    param_info["type"] = self._format_type(param.annotation)

                # Get default
                if param.default != inspect.Parameter.empty:
                    param_info["default"] = repr(param.default)

                # Extract description from docstring
                init_doc = inspect.getdoc(brick_class.__init__)
                if init_doc:
                    # Look for parameter description
                    pattern = rf"{name}:\s*(.+?)(?:\n|$)"
                    match = re.search(pattern, init_doc, re.MULTILINE)
                    if match:
                        param_info["description"] = match.group(1).strip()

                params.append(param_info)

        except Exception:
            pass

        return params

    def _extract_methods(self, brick_class: type) -> list[dict[str, Any]]:
        """Extract public methods from brick class."""
        methods = []

        # Get all methods
        for name, method in inspect.getmembers(brick_class, inspect.isfunction):
            # Skip private methods and special methods
            if name.startswith("_") or name in ("invoke", "invoke_sync"):
                continue

            method_info = {
                "name": name,
                "signature": "",
                "docstring": inspect.getdoc(method) or "",
                "async": inspect.iscoroutinefunction(method),
            }

            # Get signature
            try:
                sig = inspect.signature(method)
                method_info["signature"] = str(sig)
            except:
                pass

            methods.append(method_info)

        return methods

    def _extract_enhanced_examples(self, brick_class: type) -> list[str]:
        """Extract examples with better parsing."""
        examples = []

        # Extract from class docstring
        docstring = inspect.getdoc(brick_class)
        if docstring:
            examples.extend(self._parse_docstring_examples(docstring))

        # Extract from invoke method docstring
        invoke_doc = inspect.getdoc(brick_class.invoke)
        if invoke_doc:
            examples.extend(self._parse_docstring_examples(invoke_doc))

        # Extract from test files if enabled
        if self.extract_from_tests:
            test_examples = self._extract_test_examples(brick_class)
            examples.extend(test_examples)

        return examples

    def _parse_docstring_examples(self, docstring: str) -> list[str]:
        """Parse examples from docstring."""
        examples = []

        # Look for Example: or Examples: sections
        example_pattern = r"(?:Example|Examples):\s*\n((?:(?:>>>|\.\.\.).*\n?)+)"
        matches = re.findall(example_pattern, docstring, re.MULTILINE | re.IGNORECASE)

        for match in matches:
            examples.append(match.strip())

        # Also look for code blocks after Example:
        lines = docstring.split("\n")
        in_example = False
        current_example = []

        for i, line in enumerate(lines):
            if re.match(r"\s*(?:Example|Examples):", line, re.IGNORECASE):
                in_example = True
                continue

            if in_example:
                # Check if we're in a code block
                if line.strip().startswith("```"):
                    # Start or end of code block
                    if current_example:
                        examples.append("\n".join(current_example))
                        current_example = []
                        in_example = False
                elif line.strip() and not line[0].isspace() and ":" in line:
                    # Likely a new section
                    if current_example:
                        examples.append("\n".join(current_example))
                        current_example = []
                    in_example = False
                elif line.strip():
                    current_example.append(line)

        if current_example:
            examples.append("\n".join(current_example))

        return examples

    def _extract_test_examples(self, brick_class: type) -> list[str]:
        """Extract examples from test files."""
        examples = []

        # TODO: Implement test file parsing
        # This would look for test files that test this brick
        # and extract relevant test cases as examples

        return examples

    def _get_supported_skills(self, brick_class: type) -> list[str]:
        """Get list of supported skills."""
        skills = []

        # Check for skill decorator
        if hasattr(brick_class, "__skills__"):
            skills.extend(brick_class.__skills__)

        # Check for with_skill method
        if hasattr(brick_class, "with_skill"):
            skills.append("Dynamic Skills")

        # Check for specific skill methods
        skill_methods = {
            "start_server": "API",
            "create_cli": "CLI",
            "enable_logging": "Logging",
            "enable_tracing": "Observability",
            "to_docker": "Docker",
            "to_kubernetes": "Kubernetes",
        }

        for method, skill in skill_methods.items():
            if hasattr(brick_class, method):
                skills.append(skill)

        return list(set(skills))  # Remove duplicates

    def _is_validator(self, brick_class: type) -> bool:
        """Check if brick is a validator."""
        # Check base classes
        for base in inspect.getmro(brick_class):
            if base.__name__ == "ValidatorBase":
                return True

        # Check if it has validate method
        return hasattr(brick_class, "validate")

    def _is_transformer(self, brick_class: type) -> bool:
        """Check if brick is a transformer."""
        # Check base classes
        for base in inspect.getmro(brick_class):
            if base.__name__ == "TransformerBase":
                return True

        # Check if it has transform method
        return hasattr(brick_class, "transform")

    def _is_pipeline(self, brick_class: type) -> bool:
        """Check if brick is a pipeline."""
        # Check if it has bricks attribute
        return hasattr(brick_class, "bricks") or "Pipeline" in brick_class.__name__

    def _extract_composition_info(self, brick_class: type) -> dict[str, Any] | None:
        """Extract information about brick composition."""
        info = {}

        # Check if it's composable
        if hasattr(brick_class, "__or__"):
            info["composable"] = True
            info["compose_method"] = "pipe_operator"

        # Check if it's a pipeline
        if hasattr(brick_class, "bricks"):
            info["type"] = "pipeline"
            try:
                # Get brick count if possible
                instance = brick_class()
                if hasattr(instance, "bricks"):
                    info["brick_count"] = len(instance.bricks)
            except:
                pass

        return info if info else None

    def generate_markdown_docs(self, bricks: list[BrickInfo]) -> dict[str, str]:
        """Generate markdown documentation for bricks."""
        docs = {}

        # Generate index
        docs["index.md"] = self._generate_markdown_index(bricks)

        # Generate individual brick docs
        for brick in bricks:
            filename = f"{brick.name.lower()}.md"
            docs[filename] = self._generate_markdown_brick(brick)

        # Generate category pages
        categories = self._categorize_bricks(bricks)
        for category, category_bricks in categories.items():
            filename = f"{category.lower()}.md"
            docs[filename] = self._generate_markdown_category(category, category_bricks)

        return docs

    def _generate_markdown_index(self, bricks: list[BrickInfo]) -> str:
        """Generate markdown index page."""
        md = "# Nanobricks API Documentation\n\n"
        md += "Welcome to the Nanobricks API documentation. "
        md += "This documentation is automatically generated from the source code.\n\n"

        # Stats
        md += "## Overview\n\n"
        md += f"- **Total Bricks**: {len(bricks)}\n"

        validators = sum(1 for b in bricks if b.is_validator)
        transformers = sum(1 for b in bricks if b.is_transformer)
        pipelines = sum(1 for b in bricks if b.is_pipeline)

        md += f"- **Validators**: {validators}\n"
        md += f"- **Transformers**: {transformers}\n"
        md += f"- **Pipelines**: {pipelines}\n"
        md += f"- **Other**: {len(bricks) - validators - transformers - pipelines}\n\n"

        # Quick links
        md += "## Quick Links\n\n"
        md += "- [Validators](validators.md) - Input validation bricks\n"
        md += "- [Transformers](transformers.md) - Data transformation bricks\n"
        md += "- [Pipelines](pipelines.md) - Multi-stage processing pipelines\n"
        md += "- [Skills](skills.md) - Available skills and enhancements\n\n"

        # All bricks by module
        md += "## All Bricks by Module\n\n"

        by_module = defaultdict(list)
        for brick in bricks:
            by_module[brick.module].append(brick)

        for module in sorted(by_module.keys()):
            md += f"### {module}\n\n"
            for brick in sorted(by_module[module], key=lambda b: b.name):
                desc = brick.docstring.split("\n")[0]
                md += f"- [{brick.name}]({brick.name.lower()}.md) - {desc}\n"
            md += "\n"

        return md

    def _generate_markdown_brick(self, brick: BrickInfo) -> str:
        """Generate markdown documentation for a single brick."""
        md = f"# {brick.name}\n\n"

        # Module path and version
        md += f"`{brick.module}.{brick.name}` v{brick.version}\n\n"

        # Source link
        if self.include_source and brick.source_file:
            rel_path = (
                brick.source_file.relative_to(Path.cwd())
                if brick.source_file.is_absolute()
                else brick.source_file
            )
            md += f"[View Source]({rel_path}#L{brick.line_number})\n\n"

        # Description
        md += f"{brick.docstring}\n\n"

        # Type badge
        if brick.is_validator:
            md += "![Validator](https://img.shields.io/badge/Type-Validator-blue)\n"
        elif brick.is_transformer:
            md += (
                "![Transformer](https://img.shields.io/badge/Type-Transformer-green)\n"
            )
        elif brick.is_pipeline:
            md += "![Pipeline](https://img.shields.io/badge/Type-Pipeline-purple)\n"
        md += "\n"

        # Type signature
        md += "## Type Signature\n\n"
        md += f"```python\n{brick.name}[{brick.input_type}, {brick.output_type}, {brick.deps_type}]\n```\n\n"

        md += f"- **Input**: `{brick.input_type}`\n"
        md += f"- **Output**: `{brick.output_type}`\n"
        md += f"- **Dependencies**: `{brick.deps_type}`\n\n"

        # Constructor
        if brick.constructor_params:
            md += "## Constructor\n\n"
            md += f"```python\n{brick.name}(\n"
            for param in brick.constructor_params:
                if param["required"]:
                    md += f"    {param['name']}: {param['type']},\n"
                else:
                    md += (
                        f"    {param['name']}: {param['type']} = {param['default']},\n"
                    )
            md += ")\n```\n\n"

            # Parameter descriptions
            md += "### Parameters\n\n"
            for param in brick.constructor_params:
                req = "required" if param["required"] else "optional"
                md += f"- **{param['name']}** (`{param['type']}`, {req})"
                if param.get("description"):
                    md += f" - {param['description']}"
                if not param["required"] and param["default"]:
                    md += f" (default: `{param['default']}`)"
                md += "\n"
            md += "\n"

        # Methods
        md += "## Methods\n\n"

        # Invoke method
        md += "### invoke\n\n"
        md += "```python\n"
        md += f"async def invoke(input: {brick.input_type}, *, deps: {brick.deps_type} = None) -> {brick.output_type}\n"
        md += "```\n\n"
        md += "Process input asynchronously.\n\n"

        # Invoke sync
        md += "### invoke_sync\n\n"
        md += "```python\n"
        md += f"def invoke_sync(input: {brick.input_type}, *, deps: {brick.deps_type} = None) -> {brick.output_type}\n"
        md += "```\n\n"
        md += "Process input synchronously (wrapper around async invoke).\n\n"

        # Additional methods
        if brick.methods:
            for method in brick.methods:
                async_prefix = "async " if method["async"] else ""
                md += f"### {method['name']}\n\n"
                md += f"```python\n{async_prefix}def {method['name']}{method['signature']}\n```\n\n"
                if method["docstring"]:
                    md += f"{method['docstring']}\n\n"

        # Examples
        if brick.examples:
            md += "## Examples\n\n"
            for i, example in enumerate(brick.examples, 1):
                if len(brick.examples) > 1:
                    md += f"### Example {i}\n\n"
                md += "```python\n"
                md += example
                md += "\n```\n\n"

        # Skills
        if brick.skills:
            md += "## Supported Skills\n\n"
            for skill in brick.skills:
                md += f"- {skill}\n"
            md += "\n"

        # Composition
        if brick.composition_info:
            md += "## Composition\n\n"
            md += "This brick supports composition using the pipe operator (`|`):\n\n"
            md += "```python\n"
            md += f"pipeline = {brick.name}() | OtherBrick()\n"
            md += "result = await pipeline.invoke(input)\n"
            md += "```\n\n"

        # See also
        md += "## See Also\n\n"
        if brick.is_validator:
            md += "- [Validators](validators.md) - Other validation bricks\n"
        elif brick.is_transformer:
            md += "- [Transformers](transformers.md) - Other transformation bricks\n"
        elif brick.is_pipeline:
            md += "- [Pipelines](pipelines.md) - Other pipeline bricks\n"
        md += "- [Index](index.md) - Return to main documentation\n"

        return md

    def _categorize_bricks(self, bricks: list[BrickInfo]) -> dict[str, list[BrickInfo]]:
        """Categorize bricks by type."""
        categories = defaultdict(list)

        for brick in bricks:
            if brick.is_validator:
                categories["validators"].append(brick)
            elif brick.is_transformer:
                categories["transformers"].append(brick)
            elif brick.is_pipeline:
                categories["pipelines"].append(brick)
            else:
                categories["core"].append(brick)

        return dict(categories)

    def _generate_markdown_category(
        self, category: str, bricks: list[BrickInfo]
    ) -> str:
        """Generate category page."""
        md = f"# {category.title()}\n\n"

        if category == "validators":
            md += "Validator bricks ensure data meets specific criteria. "
            md += "They return the input unchanged if valid, or raise a ValueError if invalid.\n\n"
        elif category == "transformers":
            md += "Transformer bricks convert data from one format or structure to another. "
            md += "They are type-safe and composable.\n\n"
        elif category == "pipelines":
            md += "Pipeline bricks combine multiple bricks into complex processing workflows.\n\n"

        # List bricks
        for brick in sorted(bricks, key=lambda b: b.name):
            md += f"## [{brick.name}]({brick.name.lower()}.md)\n\n"
            md += f"{brick.docstring.split(chr(10))[0]}\n\n"
            md += f"- **Input**: `{brick.input_type}`\n"
            md += f"- **Output**: `{brick.output_type}`\n\n"

        return md

    def generate_composition_diagram(self, pipeline: Any) -> str:
        """Generate a visual composition diagram."""
        diagram = "```mermaid\ngraph TD\n"

        if hasattr(pipeline, "bricks"):
            bricks = pipeline.bricks

            diagram += "    Input[Input Data]\n"

            for i, brick in enumerate(bricks):
                brick_id = f"B{i}"
                brick_name = brick.__class__.__name__

                if i == 0:
                    diagram += f"    Input --> {brick_id}[{brick_name}]\n"
                else:
                    prev_id = f"B{i - 1}"
                    diagram += f"    {prev_id} --> {brick_id}[{brick_name}]\n"

                if i == len(bricks) - 1:
                    diagram += f"    {brick_id} --> Output[Output Data]\n"

            diagram += "```\n"
        else:
            # Single brick
            diagram += "    Input[Input Data]\n"
            diagram += f"    Input --> Brick[{pipeline.__class__.__name__}]\n"
            diagram += "    Brick --> Output[Output Data]\n"
            diagram += "```\n"

        return diagram

    def generate_html_docs(self, bricks: list[BrickInfo]) -> dict[str, str]:
        """Generate HTML documentation."""
        # TODO: Implement HTML generation
        # This would use a template engine like Jinja2
        # to generate styled HTML documentation
        return {}

    def generate_json_docs(self, bricks: list[BrickInfo]) -> str:
        """Generate JSON documentation for programmatic access."""
        data = {"version": "1.0", "total_bricks": len(bricks), "bricks": []}

        for brick in bricks:
            brick_data = {
                "name": brick.name,
                "module": brick.module,
                "version": brick.version,
                "description": brick.docstring,
                "type_signature": {
                    "input": brick.input_type,
                    "output": brick.output_type,
                    "dependencies": brick.deps_type,
                },
                "constructor_params": brick.constructor_params,
                "methods": brick.methods,
                "examples": brick.examples,
                "skills": brick.skills,
                "categories": [],
            }

            if brick.is_validator:
                brick_data["categories"].append("validator")
            if brick.is_transformer:
                brick_data["categories"].append("transformer")
            if brick.is_pipeline:
                brick_data["categories"].append("pipeline")

            data["bricks"].append(brick_data)

        return json.dumps(data, indent=2)

    def write_documentation(self, bricks: list[BrickInfo]):
        """Write documentation to output directory."""
        if self.format == "markdown":
            docs = self.generate_markdown_docs(bricks)
            for filename, content in docs.items():
                (self.output_dir / filename).write_text(content)

        elif self.format == "html":
            docs = self.generate_html_docs(bricks)
            for filename, content in docs.items():
                (self.output_dir / filename).write_text(content)

        elif self.format == "json":
            json_doc = self.generate_json_docs(bricks)
            (self.output_dir / "nanobricks-api.json").write_text(json_doc)

        print(f"Documentation generated in {self.output_dir}")
        print(f"Format: {self.format}")
        print(f"Total bricks documented: {len(bricks)}")


def generate_docs(
    search_paths: list[Path] | None = None,
    output_dir: Path = Path("docs/api"),
    format: str = "markdown",
    include_source: bool = True,
    include_diagrams: bool = True,
    extract_from_tests: bool = False,
):
    """Generate documentation for nanobricks.

    Args:
        search_paths: Paths to search for nanobricks
        output_dir: Output directory
        format: Output format (markdown, html, json)
        include_source: Include source code references
        include_diagrams: Generate composition diagrams
        extract_from_tests: Extract examples from test files
    """
    if search_paths is None:
        # Default to src directory
        search_paths = [Path("src")]

    generator = EnhancedDocumentationGenerator(
        output_dir=output_dir,
        format=format,
        include_source=include_source,
        include_diagrams=include_diagrams,
        extract_from_tests=extract_from_tests,
    )

    # Discover bricks
    bricks = generator.discover_bricks(search_paths)

    if bricks:
        # Generate documentation
        generator.write_documentation(bricks)
    else:
        print("No nanobricks found to document")
