"""
Pytest configuration and shared fixtures for Nanobricks tests.
"""

from pathlib import Path
from typing import Any

import pytest

# Remove custom event_loop fixture - pytest-asyncio provides it automatically


@pytest.fixture
def sample_data() -> dict[str, Any]:
    """Sample data for testing transformations."""
    return {
        "name": "test",
        "value": 42,
        "items": ["a", "b", "c"],
        "nested": {"key": "value"},
    }


@pytest.fixture
def temp_config_file(tmp_path: Path) -> Path:
    """Create a temporary TOML config file."""
    config_file = tmp_path / "nanobrick.toml"
    config_file.write_text(
        """
[metadata]
name = "test-brick"
version = "1.0.0"

[skills]
logging = { enabled = true, level = "DEBUG" }
api = { enabled = false }

[features]
strict_mode = true
    """
    )
    return config_file


@pytest.fixture
def mock_deps() -> dict[str, Any]:
    """Mock dependencies for testing."""

    class MockDB:
        async def query(self, sql: str):
            return [{"id": 1, "name": "test"}]

    class MockCache:
        def __init__(self):
            self.data = {}

        async def get(self, key: str):
            return self.data.get(key)

        async def set(self, key: str, value: Any):
            self.data[key] = value

    return {"db": MockDB(), "cache": MockCache(), "config": {"debug": True}}


# Pytest configuration
def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line(
        "markers", "slow: marks tests as slow (deselect with '-m \"not slow\"')"
    )
    config.addinivalue_line("markers", "integration: marks tests as integration tests")
    config.addinivalue_line("markers", "unit: marks tests as unit tests")
