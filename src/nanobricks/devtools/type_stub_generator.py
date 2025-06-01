"""Type stub generator for nanobricks."""

import ast
import inspect
from pathlib import Path
from typing import Any, get_type_hints


class TypeStubGenerator:
    """Generate type stubs (.pyi files) for nanobricks."""

    def __init__(
        self,
        include_private: bool = False,
        include_docstrings: bool = True,
        use_generic_base: bool = True,
    ):
        """Initialize type stub generator.

        Args:
            include_private: Whether to include private methods
            include_docstrings: Whether to include docstrings
            use_generic_base: Whether to use generic base classes
        """
        self.include_private = include_private
        self.include_docstrings = include_docstrings
        self.use_generic_base = use_generic_base

    def generate_stub_for_brick(self, brick_class: type) -> str:
        """Generate type stub for a single brick class.

        Args:
            brick_class: Brick class to generate stub for

        Returns:
            Type stub content
        """
        lines = []

        # Imports
        imports = self._collect_imports(brick_class)
        if imports:
            lines.extend(imports)
            lines.append("")

        # Class definition
        class_def = self._generate_class_definition(brick_class)
        lines.append(class_def)

        # Class docstring
        if self.include_docstrings:
            docstring = inspect.getdoc(brick_class)
            if docstring:
                lines.append(f'    """{docstring}"""')

        # Class variables
        class_vars = self._generate_class_variables(brick_class)
        if class_vars:
            lines.extend(f"    {var}" for var in class_vars)
            lines.append("")

        # Methods
        methods = self._generate_methods(brick_class)
        for method in methods:
            lines.extend(f"    {line}" for line in method.split("\n"))
            lines.append("")

        return "\n".join(lines)

    def generate_stub_for_module(self, module_path: Path) -> str:
        """Generate type stub for a module.

        Args:
            module_path: Path to Python module

        Returns:
            Type stub content
        """
        lines = []

        # Parse module
        with open(module_path) as f:
            tree = ast.parse(f.read())

        # Module docstring
        docstring = ast.get_docstring(tree)
        if docstring and self.include_docstrings:
            lines.append(f'"""{docstring}"""')
            lines.append("")

        # Imports
        imports = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.append(ast.unparse(node))
            elif isinstance(node, ast.ImportFrom):
                imports.append(ast.unparse(node))

        if imports:
            lines.extend(sorted(set(imports)))
            lines.append("")

        # Classes
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                # Try to load the class
                module_name = module_path.stem
                try:
                    # Import module dynamically
                    import importlib.util

                    spec = importlib.util.spec_from_file_location(
                        module_name, module_path
                    )
                    if spec and spec.loader:
                        module = importlib.util.module_from_spec(spec)
                        spec.loader.exec_module(module)

                        # Get class
                        if hasattr(module, node.name):
                            cls = getattr(module, node.name)
                            if self._is_nanobrick(cls):
                                stub = self.generate_stub_for_brick(cls)
                                lines.append(stub)
                                lines.append("")
                except Exception:
                    # Fallback to AST-based generation
                    stub = self._generate_stub_from_ast(node)
                    lines.append(stub)
                    lines.append("")

        # Functions
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.col_offset == 0:
                func_stub = self._generate_function_stub_from_ast(node)
                lines.append(func_stub)
                lines.append("")

        # Constants
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign) and node.col_offset == 0:
                for target in node.targets:
                    if isinstance(target, ast.Name) and target.id.isupper():
                        lines.append(f"{target.id}: Any")

        return "\n".join(lines).strip()

    def _collect_imports(self, brick_class: type) -> list[str]:
        """Collect necessary imports for a brick class."""
        imports = set()

        # Standard imports
        imports.add("from typing import Any, Optional, TypeVar")

        # Base class imports
        if self.use_generic_base:
            imports.add("from nanobricks import NanobrickProtocol")

        # Check for specific type requirements
        try:
            hints = get_type_hints(brick_class)

            # Add imports based on type hints
            for hint in hints.values():
                hint_str = str(hint)
                if "pandas" in hint_str:
                    imports.add("import pandas as pd")
                if "numpy" in hint_str:
                    imports.add("import numpy as np")
                if "Dict" in hint_str or "dict" in hint_str:
                    imports.add("from typing import Dict")
                if "List" in hint_str or "list" in hint_str:
                    imports.add("from typing import List")
        except:
            pass

        return sorted(list(imports))

    def _generate_class_definition(self, brick_class: type) -> str:
        """Generate class definition line."""
        bases = []

        # Get base classes
        for base in brick_class.__bases__:
            if base.__name__ != "object":
                if self.use_generic_base and hasattr(base, "__args__"):
                    # Generic base with type parameters
                    type_params = self._extract_type_parameters(brick_class)
                    if type_params:
                        bases.append(f"{base.__name__}{type_params}")
                    else:
                        bases.append(base.__name__)
                else:
                    bases.append(base.__name__)

        if not bases:
            bases = ["object"]

        return f"class {brick_class.__name__}({', '.join(bases)}):"

    def _extract_type_parameters(self, brick_class: type) -> str:
        """Extract type parameters from a generic class."""
        if hasattr(brick_class, "__orig_bases__"):
            for base in brick_class.__orig_bases__:
                if hasattr(base, "__args__"):
                    args = []
                    for arg in base.__args__:
                        if hasattr(arg, "__name__"):
                            args.append(arg.__name__)
                        else:
                            args.append(str(arg).replace("typing.", ""))

                    if args:
                        return f"[{', '.join(args)}]"

        return ""

    def _generate_class_variables(self, brick_class: type) -> list[str]:
        """Generate class variable declarations."""
        vars = []

        # Standard nanobrick attributes
        if hasattr(brick_class, "name"):
            vars.append(f"name: str = {repr(brick_class.name)}")

        if hasattr(brick_class, "version"):
            vars.append(f"version: str = {repr(brick_class.version)}")

        # Other class variables
        for name, value in inspect.getmembers(brick_class):
            if (
                not name.startswith("_")
                and not inspect.ismethod(value)
                and not inspect.isfunction(value)
                and name not in ("name", "version")
            ):
                # Try to get type annotation
                if (
                    hasattr(brick_class, "__annotations__")
                    and name in brick_class.__annotations__
                ):
                    type_str = self._format_type(brick_class.__annotations__[name])
                    vars.append(f"{name}: {type_str}")
                else:
                    vars.append(f"{name}: Any")

        return vars

    def _generate_methods(self, brick_class: type) -> list[str]:
        """Generate method stubs."""
        methods = []

        # Get all methods
        for name, method in inspect.getmembers(brick_class, inspect.ismethod):
            if not self.include_private and name.startswith("_") and name != "__init__":
                continue

            # Skip inherited methods unless overridden
            if name in ("__hash__", "__eq__", "__repr__", "__str__"):
                continue

            method_stub = self._generate_method_stub(name, method)
            if method_stub:
                methods.append(method_stub)

        # Ensure key methods are present
        if not any("__init__" in m for m in methods):
            methods.insert(0, "def __init__(self) -> None: ...")

        if not any("invoke" in m for m in methods):
            methods.append(
                "async def invoke(self, input: Any, *, deps: Any = None) -> Any: ..."
            )

        if not any("invoke_sync" in m for m in methods):
            methods.append(
                "def invoke_sync(self, input: Any, *, deps: Any = None) -> Any: ..."
            )

        return methods

    def _generate_method_stub(self, name: str, method: Any) -> str | None:
        """Generate stub for a single method."""
        try:
            sig = inspect.signature(method)

            # Build parameter list
            params = []
            for param_name, param in sig.parameters.items():
                if param_name == "self":
                    params.append("self")
                    continue

                # Parameter with type annotation
                if param.annotation != inspect.Parameter.empty:
                    type_str = self._format_type(param.annotation)
                else:
                    type_str = "Any"

                # Default value
                if param.default != inspect.Parameter.empty:
                    if param.default is None:
                        params.append(f"{param_name}: {type_str} = None")
                    elif isinstance(param.default, (str, int, float, bool)):
                        params.append(
                            f"{param_name}: {type_str} = {repr(param.default)}"
                        )
                    else:
                        params.append(f"{param_name}: {type_str} = ...")
                else:
                    params.append(f"{param_name}: {type_str}")

            # Return type
            if sig.return_annotation != inspect.Signature.empty:
                return_type = self._format_type(sig.return_annotation)
            else:
                return_type = "Any"

            # Check if async
            if inspect.iscoroutinefunction(method):
                prefix = "async def"
            else:
                prefix = "def"

            # Build method stub
            stub = f"{prefix} {name}({', '.join(params)}) -> {return_type}:"

            # Add docstring
            if self.include_docstrings:
                docstring = inspect.getdoc(method)
                if docstring:
                    stub += f'\n    """{docstring}"""'
                    stub += "\n    ..."
                else:
                    stub += " ..."
            else:
                stub += " ..."

            return stub

        except:
            # Fallback for problematic methods
            return f"def {name}(self, *args: Any, **kwargs: Any) -> Any: ..."

    def _format_type(self, type_obj: Any) -> str:
        """Format type annotation for stub."""
        if type_obj is None:
            return "None"

        if hasattr(type_obj, "__name__"):
            return type_obj.__name__

        type_str = str(type_obj)

        # Clean up common patterns
        type_str = type_str.replace("typing.", "")
        type_str = type_str.replace("<class ", "").replace(">", "")
        type_str = type_str.replace("'", "")

        return type_str

    def _is_nanobrick(self, cls: type) -> bool:
        """Check if a class is a nanobrick."""
        # Check if it inherits from NanobrickProtocol or has invoke method
        return hasattr(cls, "invoke") or any(
            base.__name__ in ("NanobrickProtocol", "NanobrickBase")
            for base in inspect.getmro(cls)
        )

    def _generate_stub_from_ast(self, node: ast.ClassDef) -> str:
        """Generate stub from AST node (fallback)."""
        lines = []

        # Class definition
        bases = []
        for base in node.bases:
            bases.append(ast.unparse(base))

        if not bases:
            bases = ["object"]

        lines.append(f"class {node.name}({', '.join(bases)}):")

        # Docstring
        docstring = ast.get_docstring(node)
        if docstring and self.include_docstrings:
            lines.append(f'    """{docstring}"""')

        # Methods
        has_content = False
        for item in node.body:
            if isinstance(item, ast.FunctionDef):
                method_stub = self._generate_function_stub_from_ast(item)
                lines.append(f"    {method_stub}")
                has_content = True

        if not has_content:
            lines.append("    ...")

        return "\n".join(lines)

    def _generate_function_stub_from_ast(self, node: ast.FunctionDef) -> str:
        """Generate function stub from AST node."""
        # Build parameter list
        params = []
        for arg in node.args.args:
            params.append(arg.arg)

        # Check if async
        if isinstance(node, ast.AsyncFunctionDef):
            prefix = "async def"
        else:
            prefix = "def"

        # Build stub
        stub = f"{prefix} {node.name}({', '.join(params)}) -> Any:"

        # Add docstring
        docstring = ast.get_docstring(node)
        if docstring and self.include_docstrings:
            stub += f'\n    """{docstring}"""'
            stub += "\n    ..."
        else:
            stub += " ..."

        return stub

    def generate_stubs_for_package(
        self, package_path: Path, output_dir: Path | None = None
    ) -> dict[Path, str]:
        """Generate stubs for an entire package.

        Args:
            package_path: Path to package directory
            output_dir: Output directory for stubs (defaults to package path)

        Returns:
            Dictionary mapping stub paths to content
        """
        if output_dir is None:
            output_dir = package_path

        stubs = {}

        # Process all Python files
        for py_file in package_path.rglob("*.py"):
            if py_file.name.startswith("_") and py_file.name != "__init__.py":
                continue

            # Generate stub
            try:
                stub_content = self.generate_stub_for_module(py_file)

                # Calculate stub path
                relative_path = py_file.relative_to(package_path)
                stub_path = output_dir / relative_path.with_suffix(".pyi")

                stubs[stub_path] = stub_content
            except Exception as e:
                print(f"Error generating stub for {py_file}: {e}")

        return stubs

    def write_stubs(self, stubs: dict[Path, str]):
        """Write stubs to disk.

        Args:
            stubs: Dictionary mapping paths to stub content
        """
        for path, content in stubs.items():
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content)


def generate_type_stubs(
    source: Path, output_dir: Path | None = None, **kwargs
) -> dict[Path, str]:
    """Convenience function to generate type stubs.

    Args:
        source: Source file or directory
        output_dir: Output directory for stubs
        **kwargs: Additional arguments for TypeStubGenerator

    Returns:
        Dictionary mapping stub paths to content
    """
    generator = TypeStubGenerator(**kwargs)

    if source.is_file():
        content = generator.generate_stub_for_module(source)
        stub_path = source.with_suffix(".pyi")
        if output_dir:
            stub_path = output_dir / source.name.replace(".py", ".pyi")
        return {stub_path: content}
    else:
        return generator.generate_stubs_for_package(source, output_dir)
