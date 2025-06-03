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


class RateLimiter(NanobrickProtocol[T_in, T_out, T_deps]):
    """Rate limits requests to a nanobrick."""

    def __init__(
        self,
        brick: NanobrickProtocol[T_in, T_out, T_deps],
        *,
        max_requests: int = 100,
        window_seconds: int = 60,
        burst_size: int | None = None,
        key_func: Callable[[T_in, T_deps], str] | None = None,
    ):
        self.brick = brick
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.burst_size = burst_size or max_requests
        self.key_func = key_func or (lambda *_: "default")
        self._requests: dict[str, list[float]] = defaultdict(list)
        self._lock = asyncio.Lock()
        self.name = f"RateLimiter[{brick.name}]"
        self.version = brick.version

    async def _is_allowed(self, key: str) -> bool:
        """Check if request is allowed under rate limit."""
        async with self._lock:
            now = time.time()
            window_start = now - self.window_seconds

            # Clean old requests
            self._requests[key] = [
                ts for ts in self._requests[key] if ts > window_start
            ]

            # Check rate limit
            if len(self._requests[key]) >= self.max_requests:
                return False

            # Check burst limit
            if self.burst_size < self.max_requests:
                recent_start = now - (self.window_seconds / 10)  # 10% of window
                recent_requests = sum(
                    1 for ts in self._requests[key] if ts > recent_start
                )
                if recent_requests >= self.burst_size:
                    return False

            # Record request
            self._requests[key].append(now)
            return True

    async def invoke(self, input: T_in, *, deps: T_deps = None) -> T_out:
        """Check rate limit then invoke the wrapped brick."""
        key = self.key_func(input, deps)

        if not await self._is_allowed(key):
            raise ValueError(f"Rate limit exceeded for key: {key}")

        return await self.brick.invoke(input, deps=deps)

    def invoke_sync(self, input: T_in, *, deps: T_deps = None) -> T_out:
        """Synchronous version of invoke."""
        return asyncio.run(self.invoke(input, deps=deps))

    def __rshift__(self, other: "NanobrickProtocol") -> "NanobrickProtocol":
        """Compose with another brick."""
        from nanobricks.composition import Pipeline

        return Pipeline(self, other)


class PermissionGuard(NanobrickProtocol[T_in, T_out, T_deps]):
    """Guards a nanobrick with permission checks."""

    def __init__(
        self,
        brick: NanobrickProtocol[T_in, T_out, T_deps],
        *,
        required_permissions: set[Permission] | None = None,
        required_roles: set[str] | None = None,
        any_permission: bool = False,  # If True, any permission satisfies
        context_extractor: Callable[[T_in, T_deps], SecurityContext] | None = None,
    ):
        self.brick = brick
        self.required_permissions = required_permissions or set()
        self.required_roles = required_roles or set()
        self.any_permission = any_permission
        self.context_extractor = context_extractor
        self.name = f"PermissionGuard[{brick.name}]"
        self.version = brick.version

    def _extract_context(self, input: T_in, deps: T_deps) -> SecurityContext:
        """Extract security context from input and deps."""
        if self.context_extractor:
            return self.context_extractor(input, deps)

        # Default: look for context in deps
        if isinstance(deps, dict) and "security_context" in deps:
            return deps["security_context"]

        return SecurityContext()

    def _check_permissions(self, context: SecurityContext) -> bool:
        """Check if context has required permissions."""
        if not self.required_permissions:
            return True

        if Permission.ADMIN in context.permissions:
            return True

        if self.any_permission:
            return bool(self.required_permissions & context.permissions)
        else:
            return self.required_permissions <= context.permissions

    def _check_roles(self, context: SecurityContext) -> bool:
        """Check if context has required roles."""
        if not self.required_roles:
            return True

        return bool(self.required_roles & context.roles)

    async def invoke(self, input: T_in, *, deps: T_deps = None) -> T_out:
        """Check permissions then invoke the wrapped brick."""
        context = self._extract_context(input, deps)

        if not self._check_permissions(context):
            raise PermissionError(
                f"Missing required permissions: {self.required_permissions}"
            )

        if not self._check_roles(context):
            raise PermissionError(f"Missing required roles: {self.required_roles}")

        return await self.brick.invoke(input, deps=deps)

    def invoke_sync(self, input: T_in, *, deps: T_deps = None) -> T_out:
        """Synchronous version of invoke."""
        return asyncio.run(self.invoke(input, deps=deps))

    def __rshift__(self, other: "NanobrickProtocol") -> "NanobrickProtocol":
        """Compose with another brick."""
        from nanobricks.composition import Pipeline

        return Pipeline(self, other)


class EncryptionBrick(NanobrickProtocol[T_in, T_out, T_deps]):
    """Encrypts/decrypts data passing through a nanobrick."""

    def __init__(
        self,
        brick: NanobrickProtocol[T_in, T_out, T_deps],
        *,
        key: bytes | None = None,
        password: str | None = None,
        salt: bytes | None = None,
        encrypt_input: bool = False,
        decrypt_input: bool = False,
        encrypt_output: bool = True,
        decrypt_output: bool = False,
        fields_to_encrypt: list[str] | None = None,
    ):
        self.brick = brick
        self.encrypt_input = encrypt_input
        self.decrypt_input = decrypt_input
        self.encrypt_output = encrypt_output
        self.decrypt_output = decrypt_output
        self.fields_to_encrypt = fields_to_encrypt
        self.name = f"EncryptionBrick[{brick.name}]"
        self.version = brick.version

        # Generate or derive encryption key
        if key:
            self._fernet = Fernet(key)
        elif password:
            salt = salt or b"nanobricks-salt"  # Use provided or default salt
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=salt,
                iterations=100000,
            )
            key = kdf.derive(password.encode())
            self._fernet = Fernet(Fernet.generate_key())
        else:
            self._fernet = Fernet(Fernet.generate_key())

    def _encrypt_value(self, value: Any) -> Any:
        """Encrypt a value."""
        if isinstance(value, str):
            return self._fernet.encrypt(value.encode()).decode()
        elif isinstance(value, bytes):
            return self._fernet.encrypt(value)
        elif isinstance(value, dict) and self.fields_to_encrypt:
            result = value.copy()
            for field in self.fields_to_encrypt:
                if field in result:
                    result[field] = self._encrypt_value(result[field])
            return result
        else:
            return value

    def _decrypt_value(self, value: Any) -> Any:
        """Decrypt a value."""
        if isinstance(value, str):
            try:
                return self._fernet.decrypt(value.encode()).decode()
            except Exception:
                return value  # Not encrypted or invalid
        elif isinstance(value, bytes):
            try:
                return self._fernet.decrypt(value)
            except Exception:
                return value
        elif isinstance(value, dict) and self.fields_to_encrypt:
            result = value.copy()
            for field in self.fields_to_encrypt:
                if field in result:
                    result[field] = self._decrypt_value(result[field])
            return result
        else:
            return value

    async def invoke(self, input: T_in, *, deps: T_deps = None) -> T_out:
        """Process input/output with encryption as configured."""
        # Process input
        if self.decrypt_input:
            input = self._decrypt_value(input)
        elif self.encrypt_input:
            input = self._encrypt_value(input)

        # Invoke wrapped brick
        result = await self.brick.invoke(input, deps=deps)

        # Process output
        if self.decrypt_output:
            result = self._decrypt_value(result)
        elif self.encrypt_output:
            result = self._encrypt_value(result)

        return result

    def invoke_sync(self, input: T_in, *, deps: T_deps = None) -> T_out:
        """Synchronous version of invoke."""
        return asyncio.run(self.invoke(input, deps=deps))

    def __rshift__(self, other: "NanobrickProtocol") -> "NanobrickProtocol":
        """Compose with another brick."""
        from nanobricks.composition import Pipeline

        return Pipeline(self, other)


@dataclass
class AuditEntry:
    """Audit log entry."""

    timestamp: datetime
    brick_name: str
    user_id: str | None
    action: str
    input_hash: str
    output_hash: str | None
    duration_ms: float
    success: bool
    error: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


class AuditLogger(NanobrickProtocol[T_in, T_out, T_deps]):
    """Logs all operations for security auditing."""

    def __init__(
        self,
        brick: NanobrickProtocol[T_in, T_out, T_deps],
        *,
        log_input: bool = True,
        log_output: bool = False,
        hash_sensitive_data: bool = True,
        context_extractor: Callable[[T_in, T_deps], SecurityContext] | None = None,
        audit_handler: Callable[[AuditEntry], None] | None = None,
    ):
        self.brick = brick
        self.log_input = log_input
        self.log_output = log_output
        self.hash_sensitive_data = hash_sensitive_data
        self.context_extractor = context_extractor
        self.audit_handler = audit_handler
        self._entries: list[AuditEntry] = []
        self.name = f"AuditLogger[{brick.name}]"
        self.version = brick.version

    def _hash_value(self, value: Any) -> str:
        """Hash a value for audit logging."""
        if self.hash_sensitive_data:
            value_str = str(value)
            return hashlib.sha256(value_str.encode()).hexdigest()[:16]
        else:
            return str(value)[:100]  # Truncate for safety

    def _extract_user_id(self, input: T_in, deps: T_deps) -> str | None:
        """Extract user ID from context."""
        if self.context_extractor:
            context = self.context_extractor(input, deps)
            return context.user_id
        elif isinstance(deps, dict) and "security_context" in deps:
            return deps["security_context"].user_id
        return None

    async def invoke(self, input: T_in, *, deps: T_deps = None) -> T_out:
        """Log operation and invoke the wrapped brick."""
        start_time = time.time()
        user_id = self._extract_user_id(input, deps)
        input_hash = self._hash_value(input) if self.log_input else "N/A"

        try:
            result = await self.brick.invoke(input, deps=deps)
            duration_ms = (time.time() - start_time) * 1000
            output_hash = self._hash_value(result) if self.log_output else None

            entry = AuditEntry(
                timestamp=datetime.now(),
                brick_name=self.brick.name,
                user_id=user_id,
                action="invoke",
                input_hash=input_hash,
                output_hash=output_hash,
                duration_ms=duration_ms,
                success=True,
            )

            self._entries.append(entry)
            if self.audit_handler:
                self.audit_handler(entry)

            return result

        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000

            entry = AuditEntry(
                timestamp=datetime.now(),
                brick_name=self.brick.name,
                user_id=user_id,
                action="invoke",
                input_hash=input_hash,
                output_hash=None,
                duration_ms=duration_ms,
                success=False,
                error=str(e),
            )

            self._entries.append(entry)
            if self.audit_handler:
                self.audit_handler(entry)

            raise

    def invoke_sync(self, input: T_in, *, deps: T_deps = None) -> T_out:
        """Synchronous version of invoke."""
        return asyncio.run(self.invoke(input, deps=deps))

    def __rshift__(self, other: "NanobrickProtocol") -> "NanobrickProtocol":
        """Compose with another brick."""
        from nanobricks.composition import Pipeline

        return Pipeline(self, other)

    def get_audit_log(
        self,
        *,
        user_id: str | None = None,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        success_only: bool = False,
    ) -> list[AuditEntry]:
        """Get filtered audit log entries."""
        entries = self._entries

        if user_id:
            entries = [e for e in entries if e.user_id == user_id]

        if start_time:
            entries = [e for e in entries if e.timestamp >= start_time]

        if end_time:
            entries = [e for e in entries if e.timestamp <= end_time]

        if success_only:
            entries = [e for e in entries if e.success]

        return entries


def secure_nanobrick(
    brick: NanobrickProtocol[T_in, T_out, T_deps],
    *,
    sanitize: bool = True,
    rate_limit: int | None = None,
    permissions: set[Permission] | None = None,
    encrypt: bool = False,
    audit: bool = True,
    encryption_key: bytes | None = None,
) -> NanobrickProtocol[T_in, T_out, T_deps]:
    """Apply multiple security layers to a nanobrick."""
    result = brick

    if sanitize:
        result = InputSanitizer(result)

    if rate_limit:
        result = RateLimiter(result, max_requests=rate_limit)

    if permissions:
        result = PermissionGuard(result, required_permissions=permissions)

    if encrypt:
        result = EncryptionBrick(result, key=encryption_key)

    if audit:
        result = AuditLogger(result)

    return result
