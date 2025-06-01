"""Registry management for Nanobricks skills.

This module provides lazy loading and plugin discovery for skills.
"""

import importlib
import importlib.util
import sys
from pathlib import Path

from nanobricks.skill import Skill, _registry


class LazySkillLoader:
    """Lazy loader for skills to avoid importing heavy dependencies."""

    def __init__(self):
        self._loaded: set[str] = set()
        self._builtin_modules = {
            "logging": "nanobricks.skills.logging",
            "api": "nanobricks.skills.api",
            "cli": "nanobricks.skills.cli",
            "observability": "nanobricks.skills.observability",
            "ui": "nanobricks.skills.ui",
            "persistence": "nanobricks.skills.persistence",
        }

    def load_builtin(self, name: str) -> bool:
        """Load a built-in skill module.

        Args:
            name: The skill name

        Returns:
            True if loaded successfully
        """
        if name in self._loaded:
            return True

        if name not in self._builtin_modules:
            return False

        try:
            module_name = self._builtin_modules[name]
            importlib.import_module(module_name)
            self._loaded.add(name)
            return True
        except ImportError:
            return False

    def load_from_path(self, path: Path) -> int:
        """Load skills from a directory.

        Args:
            path: Directory containing skill modules

        Returns:
            Number of skills loaded
        """
        count = 0

        if not path.exists() or not path.is_dir():
            return count

        for file_path in path.glob("*.py"):
            if file_path.name.startswith("_"):
                continue

            try:
                # Create module name
                module_name = f"nanobricks_ext_{file_path.stem}"

                # Load module
                spec = importlib.util.spec_from_file_location(module_name, file_path)
                if spec and spec.loader:
                    module = importlib.util.module_from_spec(spec)
                    sys.modules[module_name] = module
                    spec.loader.exec_module(module)
                    count += 1
            except Exception:
                # Skip modules that fail to load
                pass

        return count

    def ensure_loaded(self, name: str) -> None:
        """Ensure a skill is loaded.

        Args:
            name: The skill name

        Raises:
            KeyError: If skill cannot be loaded
        """
        # First check if already registered
        try:
            _registry.get(name)
            return
        except KeyError:
            pass

        # Try to load built-in
        if self.load_builtin(name):
            return

        # If still not found, raise error
        raise KeyError(f"Skill '{name}' not found")


# Global lazy loader
_loader = LazySkillLoader()


def get_skill(name: str) -> type[Skill]:
    """Get a skill class, loading it if necessary.

    Args:
        name: The skill name

    Returns:
        The skill class
    """
    _loader.ensure_loaded(name)
    return _registry.get(name)


def create_skill(name: str, config: dict[str, any] | None = None) -> Skill:
    """Create a skill instance, loading it if necessary.

    Args:
        name: The skill name
        config: Optional configuration

    Returns:
        A skill instance
    """
    _loader.ensure_loaded(name)
    return _registry.create(name, config)


def list_available_skills() -> list[str]:
    """List all available skills (loaded and unloaded).

    Returns:
        List of skill names
    """
    # Get already loaded
    available = set(_registry.list())

    # Add built-in that can be loaded
    available.update(_loader._builtin_modules.keys())

    return sorted(list(available))


def load_skills_from_path(path: str | Path) -> int:
    """Load skills from a directory.

    Args:
        path: Directory path containing skill modules

    Returns:
        Number of skills loaded
    """
    return _loader.load_from_path(Path(path))


# Re-export for convenience
__all__ = [
    "get_skill",
    "create_skill",
    "list_available_skills",
    "load_skills_from_path",
]
