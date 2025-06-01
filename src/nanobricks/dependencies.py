"""
Dependency injection utilities for nanobricks.

This module provides helpers for managing dependencies that flow through
nanobrick pipelines, such as database connections, caches, and configurations.
"""

from dataclasses import dataclass
from typing import Any, Protocol, TypedDict


# Example dependency protocols
class Database(Protocol):
    """Protocol for database dependencies."""

    async def query(self, sql: str, params: dict | None = None) -> list:
        """Execute a query and return results."""
        ...

    async def execute(self, sql: str, params: dict | None = None) -> None:
        """Execute a command without returning results."""
        ...


class Cache(Protocol):
    """Protocol for cache dependencies."""

    async def get(self, key: str) -> Any | None:
        """Get a value from cache."""
        ...

    async def set(self, key: str, value: Any, ttl: int | None = None) -> None:
        """Set a value in cache with optional TTL."""
        ...

    async def delete(self, key: str) -> None:
        """Delete a value from cache."""
        ...


class Logger(Protocol):
    """Protocol for logger dependencies."""

    def debug(self, message: str, **kwargs: Any) -> None:
        """Log debug message."""
        ...

    def info(self, message: str, **kwargs: Any) -> None:
        """Log info message."""
        ...

    def warning(self, message: str, **kwargs: Any) -> None:
        """Log warning message."""
        ...

    def error(self, message: str, **kwargs: Any) -> None:
        """Log error message."""
        ...


# Common dependency containers
class StandardDeps(TypedDict, total=False):
    """Standard dependencies that many nanobricks might use."""

    db: Database
    cache: Cache
    logger: Logger
    config: dict


class WebDeps(StandardDeps):
    """Dependencies for web-related nanobricks."""

    session: dict  # User session data
    request_id: str  # Request tracking ID
    user_id: str | None  # Authenticated user ID


class DataProcessingDeps(StandardDeps):
    """Dependencies for data processing nanobricks."""

    batch_id: str  # Batch processing ID
    checkpoint_dir: str  # Directory for checkpoints
    max_retries: int  # Maximum retry attempts


# Dependency management utilities
@dataclass
class DependencyContainer:
    """Container for managing dependencies with override support."""

    _deps: dict

    def __init__(self, **kwargs: Any):
        """Initialize with keyword arguments as dependencies."""
        self._deps = kwargs

    def get(self, key: str, default: Any = None) -> Any:
        """Get a dependency by key."""
        return self._deps.get(key, default)

    def set(self, key: str, value: Any) -> None:
        """Set a dependency."""
        self._deps[key] = value

    def update(self, **kwargs: Any) -> None:
        """Update multiple dependencies."""
        self._deps.update(kwargs)

    def override(self, **kwargs: Any) -> "DependencyContainer":
        """Create a new container with overridden values."""
        new_deps = self._deps.copy()
        new_deps.update(kwargs)
        return DependencyContainer(**new_deps)

    def to_dict(self) -> dict:
        """Convert to plain dictionary."""
        return self._deps.copy()

    def __getitem__(self, key: str) -> Any:
        """Dictionary-style access."""
        return self._deps[key]

    def __contains__(self, key: str) -> bool:
        """Check if dependency exists."""
        return key in self._deps

    def __repr__(self) -> str:
        """String representation."""
        keys = list(self._deps.keys())
        return f"DependencyContainer({', '.join(keys)})"


# Mock implementations for testing
class MockDatabase:
    """Mock database for testing."""

    def __init__(self, data: dict | None = None):
        self.data = data or {}
        self.queries: list = []

    async def query(self, sql: str, params: dict | None = None) -> list:
        """Mock query execution."""
        self.queries.append((sql, params))
        return self.data.get(sql, [])

    async def execute(self, sql: str, params: dict | None = None) -> None:
        """Mock command execution."""
        self.queries.append((sql, params))


class MockCache:
    """Mock cache for testing."""

    def __init__(self):
        self.data: dict = {}

    async def get(self, key: str) -> Any | None:
        """Get from mock cache."""
        return self.data.get(key)

    async def set(self, key: str, value: Any, ttl: int | None = None) -> None:
        """Set in mock cache."""
        self.data[key] = value

    async def delete(self, key: str) -> None:
        """Delete from mock cache."""
        self.data.pop(key, None)


class MockLogger:
    """Mock logger for testing."""

    def __init__(self):
        self.messages: list = []

    def debug(self, message: str, **kwargs: Any) -> None:
        """Log debug."""
        self.messages.append(("DEBUG", message, kwargs))

    def info(self, message: str, **kwargs: Any) -> None:
        """Log info."""
        self.messages.append(("INFO", message, kwargs))

    def warning(self, message: str, **kwargs: Any) -> None:
        """Log warning."""
        self.messages.append(("WARNING", message, kwargs))

    def error(self, message: str, **kwargs: Any) -> None:
        """Log error."""
        self.messages.append(("ERROR", message, kwargs))
