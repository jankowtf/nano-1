"""Configuration system for Nanobricks.

Provides TOML-based configuration with environment-specific overrides
and a discovery chain for finding configuration files.
"""

import os
import tomllib
from functools import lru_cache
from pathlib import Path
from typing import Any


class ConfigError(Exception):
    """Raised when configuration loading fails."""

    pass


class Config:
    """Configuration container with dot-notation access."""

    def __init__(self, data: dict[str, Any]):
        self._data = data
        self._frozen = False

    def __getattr__(self, key: str) -> Any:
        """Enable dot notation access to config values."""
        if key.startswith("_"):
            return super().__getattribute__(key)

        if key not in self._data:
            raise AttributeError(f"Config has no attribute '{key}'")

        value = self._data[key]
        if isinstance(value, dict):
            return Config(value)
        return value

    def __getitem__(self, key: str) -> Any:
        """Enable dictionary-style access."""
        return self._data[key]

    def get(self, key: str, default: Any = None) -> Any:
        """Safe get with default value."""
        return self._data.get(key, default)

    def to_dict(self) -> dict[str, Any]:
        """Convert back to dictionary."""
        return self._data.copy()

    def freeze(self) -> None:
        """Make configuration immutable."""
        self._frozen = True

    def __setattr__(self, key: str, value: Any) -> None:
        """Prevent modification after freezing."""
        if key.startswith("_"):
            super().__setattr__(key, value)
        elif getattr(self, "_frozen", False):
            raise ConfigError("Cannot modify frozen configuration")
        else:
            self._data[key] = value

    def __repr__(self) -> str:
        return f"Config({self._data})"


class ConfigLoader:
    """Loads configuration from TOML files with environment support."""

    DEFAULT_SEARCH_PATHS = [
        Path("nanobrick.toml"),
        Path("pyproject.toml"),
        Path(".nanobrick/config.toml"),
    ]

    def __init__(self, search_paths: list[Path] | None = None):
        self.search_paths = search_paths or self.DEFAULT_SEARCH_PATHS.copy()
        self._cache: dict[str, Config] = {}

    def add_search_path(self, path: Path) -> None:
        """Add a path to the configuration search list."""
        if path not in self.search_paths:
            self.search_paths.insert(0, path)

    def find_config_file(self, start_dir: Path | None = None) -> Path | None:
        """Find the first available config file in the search chain."""
        start_dir = start_dir or Path.cwd()

        # Walk up directory tree
        current = start_dir.resolve()
        while current != current.parent:
            for search_path in self.search_paths:
                config_path = current / search_path
                if config_path.exists():
                    return config_path
            current = current.parent

        # Check home directory
        home = Path.home()
        for search_path in self.search_paths:
            config_path = home / ".nanobricks" / search_path.name
            if config_path.exists():
                return config_path

        return None

    def load_file(self, path: Path) -> dict[str, Any]:
        """Load a TOML file."""
        try:
            with open(path, "rb") as f:
                data = tomllib.load(f)

            # Extract nanobricks section if in pyproject.toml
            if path.name == "pyproject.toml":
                return data.get("tool", {}).get("nanobricks", {})

            return data
        except Exception as e:
            raise ConfigError(f"Failed to load config from {path}: {e}")

    def load(
        self,
        config_file: Path | None = None,
        environment: str | None = None,
        overrides: dict[str, Any] | None = None,
    ) -> Config:
        """Load configuration with environment-specific overrides.

        Args:
            config_file: Explicit config file path
            environment: Environment name (dev, prod, test, etc.)
            overrides: Dictionary of values to override

        Returns:
            Loaded configuration object
        """
        # Determine environment
        env = environment or os.getenv("NANOBRICKS_ENV", "development")

        # Check cache
        cache_key = f"{config_file}:{env}"
        if cache_key in self._cache and not overrides:
            return self._cache[cache_key]

        # Find config file
        if config_file:
            path = Path(config_file)
            if not path.exists():
                raise ConfigError(f"Config file not found: {path}")
        else:
            path = self.find_config_file()
            if not path:
                # Return empty config if no file found
                config = Config({})
                if not overrides:
                    self._cache[cache_key] = config
                return config

        # Load base config
        data = self.load_file(path)

        # Apply environment-specific config
        env_data = data.get("environments", {}).get(env, {})
        merged_data = self._deep_merge(data, env_data)

        # Remove environments section from final config
        merged_data.pop("environments", None)

        # Apply overrides
        if overrides:
            merged_data = self._deep_merge(merged_data, overrides)

        # Create config object
        config = Config(merged_data)

        # Cache if no overrides
        if not overrides:
            self._cache[cache_key] = config

        return config

    def _deep_merge(
        self, base: dict[str, Any], updates: dict[str, Any]
    ) -> dict[str, Any]:
        """Deep merge two dictionaries."""
        result = base.copy()

        for key, value in updates.items():
            if (
                key in result
                and isinstance(result[key], dict)
                and isinstance(value, dict)
            ):
                result[key] = self._deep_merge(result[key], value)
            else:
                result[key] = value

        return result

    def clear_cache(self) -> None:
        """Clear the configuration cache."""
        self._cache.clear()


# Global loader instance
_loader = ConfigLoader()


def load_config(
    config_file: str | Path | None = None,
    environment: str | None = None,
    overrides: dict[str, Any] | None = None,
) -> Config:
    """Load configuration using the global loader.

    Args:
        config_file: Path to config file (optional)
        environment: Environment name (optional)
        overrides: Values to override (optional)

    Returns:
        Configuration object
    """
    if isinstance(config_file, str):
        config_file = Path(config_file)

    return _loader.load(config_file, environment, overrides)


@lru_cache(maxsize=1)
def get_default_config() -> Config:
    """Get the default configuration (cached)."""
    return load_config()


def add_config_search_path(path: str | Path) -> None:
    """Add a path to the global config search list."""
    _loader.add_search_path(Path(path))


def clear_config_cache() -> None:
    """Clear all cached configurations."""
    _loader.clear_cache()
    get_default_config.cache_clear()
