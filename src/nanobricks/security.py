"""Security features for production nanobricks."""

import asyncio
import hashlib
import time
from collections import defaultdict
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

from nanobricks.protocol import NanobrickProtocol, T_deps, T_in, T_out


class Permission(str, Enum):
    """Standard permissions for nanobricks."""

    READ = "read"
    WRITE = "write"
    EXECUTE = "execute"
    DELETE = "delete"
    ADMIN = "admin"


@dataclass
class SecurityContext:
    """Security context for requests."""

    user_id: str | None = None
    permissions: set[Permission] = field(default_factory=set)
    roles: set[str] = field(default_factory=set)
    metadata: dict[str, Any] = field(default_factory=dict)


class InputSanitizer(NanobrickProtocol[T_in, T_in, T_deps]):
    """Sanitizes input to prevent injection attacks."""

    def __init__(
        self,
        brick: NanobrickProtocol[T_in, T_out, T_deps],
        *,
        html_escape: bool = True,
        sql_escape: bool = True,
        max_length: int | None = None,
        allowed_chars: str | None = None,
        custom_sanitizer: Callable[[Any], Any] | None = None,
    ):
        self.brick = brick
        self.html_escape = html_escape
        self.sql_escape = sql_escape
        self.max_length = max_length
        self.allowed_chars = allowed_chars
        self.custom_sanitizer = custom_sanitizer
        self.name = f"InputSanitizer[{brick.name}]"
        self.version = brick.version

    def _sanitize_string(self, value: str) -> str:
        """Sanitize a string value."""
        if self.max_length and len(value) > self.max_length:
            value = value[: self.max_length]

        if self.allowed_chars:
            value = "".join(c for c in value if c in self.allowed_chars)

        if self.html_escape:
            value = (
                value.replace("&", "&amp;")
                .replace("<", "&lt;")
                .replace(">", "&gt;")
                .replace('"', "&quot;")
                .replace("'", "&#x27;")
            )

        if self.sql_escape:
            value = value.replace("'", "''").replace("\\", "\\\\")

        if self.custom_sanitizer:
            value = self.custom_sanitizer(value)

        return value

    def _sanitize_value(self, value: Any) -> Any:
        """Recursively sanitize values."""
        if isinstance(value, str):
            return self._sanitize_string(value)
        elif isinstance(value, dict):
            return {k: self._sanitize_value(v) for k, v in value.items()}
        elif isinstance(value, list):
            return [self._sanitize_value(v) for v in value]
        elif isinstance(value, tuple):
            return tuple(self._sanitize_value(v) for v in value)
        else:
            return value

    async def invoke(self, input: T_in, *, deps: T_deps = None) -> T_out:
        """Sanitize input then invoke the wrapped brick."""
        sanitized_input = self._sanitize_value(input)
        return await self.brick.invoke(sanitized_input, deps=deps)

    def invoke_sync(self, input: T_in, *, deps: T_deps = None) -> T_out:
        """Synchronous version of invoke."""
        return asyncio.run(self.invoke(input, deps=deps))

    def __rshift__(self, other: "NanobrickProtocol") -> "NanobrickProtocol":
        """Compose with another brick."""
        from nanobricks.composition import Pipeline

        return Pipeline(self, other)
    def __or__(self, other):
        """Backwards compatibility for | operator. DEPRECATED: Use >> instead."""
        import warnings
        warnings.warn(
            "The | operator for nanobrick composition is deprecated. "
            "Use >> instead. This will be removed in v0.3.0.",
            DeprecationWarning,
            stacklevel=2
        )
        return self.__rshift__(other)
