"""Tests for the configuration system."""

import os
import tempfile
from pathlib import Path

import pytest

from nanobricks.config import (
    Config,
    ConfigError,
    ConfigLoader,
    add_config_search_path,
    clear_config_cache,
    get_default_config,
    load_config,
)


class TestConfig:
    """Test the Config container."""

    def test_init(self):
        """Test basic initialization."""
        data = {"key": "value", "nested": {"inner": 42}}
        config = Config(data)
        assert config._data == data

    def test_dot_access(self):
        """Test dot notation access."""
        config = Config(
            {"name": "test", "database": {"host": "localhost", "port": 5432}}
        )

        assert config.name == "test"
        assert config.database.host == "localhost"
        assert config.database.port == 5432

    def test_dict_access(self):
        """Test dictionary-style access."""
        config = Config({"key": "value"})
        assert config["key"] == "value"

    def test_get_method(self):
        """Test safe get with default."""
        config = Config({"exists": "yes"})
        assert config.get("exists") == "yes"
        assert config.get("missing", "default") == "default"

    def test_missing_attribute(self):
        """Test accessing missing attribute."""
        config = Config({})
        with pytest.raises(AttributeError):
            _ = config.missing

    def test_to_dict(self):
        """Test conversion back to dict."""
        data = {"a": 1, "b": {"c": 2}}
        config = Config(data)
        assert config.to_dict() == data

    def test_freeze(self):
        """Test configuration freezing."""
        config = Config({"mutable": "yes"})
        config.mutable = "changed"
        assert config.mutable == "changed"

        config.freeze()
        with pytest.raises(ConfigError):
            config.mutable = "no"

    def test_repr(self):
        """Test string representation."""
        config = Config({"key": "value"})
        assert repr(config) == "Config({'key': 'value'})"


class TestConfigLoader:
    """Test the ConfigLoader."""

    def test_init(self):
        """Test loader initialization."""
        loader = ConfigLoader()
        assert len(loader.search_paths) > 0
        assert Path("nanobrick.toml") in loader.search_paths

    def test_custom_search_paths(self):
        """Test custom search paths."""
        custom_paths = [Path("custom.toml")]
        loader = ConfigLoader(search_paths=custom_paths)
        assert loader.search_paths == custom_paths

    def test_add_search_path(self):
        """Test adding search paths."""
        loader = ConfigLoader()
        new_path = Path("new.toml")
        loader.add_search_path(new_path)
        assert new_path in loader.search_paths
        assert loader.search_paths[0] == new_path

    def test_find_config_file(self):
        """Test config file discovery."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            config_file = tmppath / "nanobrick.toml"
            config_file.write_text("# test config")

            loader = ConfigLoader()
            found = loader.find_config_file(tmppath)
            assert found.resolve() == config_file.resolve()

    def test_find_config_file_parent(self):
        """Test finding config in parent directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            subdir = tmppath / "subdir"
            subdir.mkdir()

            config_file = tmppath / "nanobrick.toml"
            config_file.write_text("# test config")

            loader = ConfigLoader()
            found = loader.find_config_file(subdir)
            assert found.resolve() == config_file.resolve()

    def test_load_file(self):
        """Test loading TOML file."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".toml", delete=False) as f:
            f.write('[test]\nkey = "value"')
            f.flush()

            try:
                loader = ConfigLoader()
                data = loader.load_file(Path(f.name))
                assert data == {"test": {"key": "value"}}
            finally:
                os.unlink(f.name)

    def test_load_pyproject_toml(self):
        """Test loading from pyproject.toml."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".toml", delete=False) as f:
            f.write('[tool.nanobricks]\nkey = "value"')
            f.flush()

            try:
                loader = ConfigLoader()
                # Rename to pyproject.toml for testing
                pyproject_path = Path(f.name).parent / "pyproject.toml"
                Path(f.name).rename(pyproject_path)

                data = loader.load_file(pyproject_path)
                assert data == {"key": "value"}
            finally:
                pyproject_path.unlink()

    def test_load_with_environment(self):
        """Test loading with environment overrides."""
        config_data = """
[database]
host = "localhost"
port = 5432

[environments.production]
[environments.production.database]
host = "prod.example.com"
port = 5433
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".toml", delete=False) as f:
            f.write(config_data)
            f.flush()

            try:
                loader = ConfigLoader()
                config = loader.load(Path(f.name), environment="production")

                assert config.database.host == "prod.example.com"
                assert config.database.port == 5433
            finally:
                os.unlink(f.name)

    def test_load_with_overrides(self):
        """Test loading with manual overrides."""
        config_data = """
[app]
name = "test"
debug = false
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".toml", delete=False) as f:
            f.write(config_data)
            f.flush()

            try:
                loader = ConfigLoader()
                config = loader.load(Path(f.name), overrides={"app": {"debug": True}})

                assert config.app.name == "test"
                assert config.app.debug is True
            finally:
                os.unlink(f.name)

    def test_deep_merge(self):
        """Test deep dictionary merging."""
        loader = ConfigLoader()
        base = {"a": 1, "b": {"c": 2, "d": 3}, "e": [1, 2, 3]}
        updates = {"a": 10, "b": {"c": 20, "f": 4}, "g": 5}

        result = loader._deep_merge(base, updates)

        assert result == {
            "a": 10,
            "b": {"c": 20, "d": 3, "f": 4},
            "e": [1, 2, 3],
            "g": 5,
        }

    def test_caching(self):
        """Test configuration caching."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".toml", delete=False) as f:
            f.write("[test]\nvalue = 1")
            f.flush()

            try:
                loader = ConfigLoader()
                config1 = loader.load(Path(f.name))
                config2 = loader.load(Path(f.name))

                # Should be the same object
                assert config1 is config2

                # Clear cache
                loader.clear_cache()
                config3 = loader.load(Path(f.name))

                # Should be different object
                assert config1 is not config3
            finally:
                os.unlink(f.name)


class TestGlobalFunctions:
    """Test global configuration functions."""

    def test_load_config(self):
        """Test global load_config function."""
        # Should work without config file
        config = load_config()
        assert isinstance(config, Config)

    def test_load_config_with_env(self):
        """Test loading with environment variable."""
        original_env = os.environ.get("NANOBRICKS_ENV")
        try:
            os.environ["NANOBRICKS_ENV"] = "test"
            config = load_config()
            # Just verify it doesn't crash
            assert isinstance(config, Config)
        finally:
            if original_env:
                os.environ["NANOBRICKS_ENV"] = original_env
            else:
                os.environ.pop("NANOBRICKS_ENV", None)

    def test_get_default_config(self):
        """Test getting cached default config."""
        config1 = get_default_config()
        config2 = get_default_config()
        assert config1 is config2  # Should be cached

    def test_add_config_search_path(self):
        """Test adding global search path."""
        # Clear any existing state
        clear_config_cache()

        # Add a custom path
        add_config_search_path("custom/path.toml")

        # Verify it was added (indirectly through the loader)
        from nanobricks.config import _loader

        assert Path("custom/path.toml") in _loader.search_paths
