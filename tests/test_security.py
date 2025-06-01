"""Tests for security features."""

import asyncio

import pytest

from nanobricks.security import (
    AuditLogger,
    EncryptionBrick,
    InputSanitizer,
    Permission,
    PermissionGuard,
    RateLimiter,
    SecurityContext,
    secure_nanobrick,
)
from nanobricks.skill import NanobrickBase


class EchoNanobrick(NanobrickBase[str, str, None]):
    """Simple brick that echoes input."""

    def __init__(self):
        super().__init__(name="echo", version="1.0.0")

    async def invoke(self, input: str, *, deps: None = None) -> str:
        return input


class TestInputSanitizer:
    """Test input sanitization."""

    @pytest.mark.asyncio
    async def test_html_escape(self):
        """Test HTML escaping."""
        brick = InputSanitizer(EchoNanobrick())

        # Test HTML special chars
        result = await brick.invoke('<script>alert("xss")</script>')
        assert result == "&lt;script&gt;alert(&quot;xss&quot;)&lt;/script&gt;"

        # Test single quotes
        result = await brick.invoke("It's a test")
        assert result == "It&#x27;s a test"

    @pytest.mark.asyncio
    async def test_sql_escape(self):
        """Test SQL escaping."""
        # Test with SQL escaping only (no HTML escaping)
        brick = InputSanitizer(EchoNanobrick(), html_escape=False)

        # Test SQL injection attempt
        result = await brick.invoke("'; DROP TABLE users; --")
        assert result == "''; DROP TABLE users; --"

        # Test backslash escaping
        result = await brick.invoke("path\\to\\file")
        assert result == "path\\\\to\\\\file"

    @pytest.mark.asyncio
    async def test_max_length(self):
        """Test max length enforcement."""
        brick = InputSanitizer(EchoNanobrick(), max_length=10)

        result = await brick.invoke("This is a very long string")
        assert result == "This is a "
        assert len(result) == 10

    @pytest.mark.asyncio
    async def test_allowed_chars(self):
        """Test allowed character filtering."""
        brick = InputSanitizer(
            EchoNanobrick(),
            allowed_chars="abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ ",
            html_escape=False,
        )

        result = await brick.invoke("Hello123 World!")
        assert result == "Hello World"

    @pytest.mark.asyncio
    async def test_nested_sanitization(self):
        """Test sanitization of nested structures."""

        class DictNanobrick(NanobrickBase[dict, dict, None]):
            def __init__(self):
                super().__init__(name="dict", version="1.0.0")

            async def invoke(self, input: dict, *, deps: None = None) -> dict:
                return input

        brick = InputSanitizer(DictNanobrick())

        result = await brick.invoke(
            {
                "name": "<b>Test</b>",
                "items": ["<script>", "normal"],
                "nested": {"value": "It's nested"},
            }
        )

        assert result["name"] == "&lt;b&gt;Test&lt;/b&gt;"
        assert result["items"][0] == "&lt;script&gt;"
        assert result["nested"]["value"] == "It&#x27;s nested"

    @pytest.mark.asyncio
    async def test_custom_sanitizer(self):
        """Test custom sanitization function."""

        def uppercase_sanitizer(value):
            return value.upper() if isinstance(value, str) else value

        brick = InputSanitizer(
            EchoNanobrick(),
            html_escape=False,
            custom_sanitizer=uppercase_sanitizer,
        )

        result = await brick.invoke("hello world")
        assert result == "HELLO WORLD"


class TestRateLimiter:
    """Test rate limiting."""

    @pytest.mark.asyncio
    async def test_basic_rate_limit(self):
        """Test basic rate limiting."""
        brick = RateLimiter(EchoNanobrick(), max_requests=2, window_seconds=1)

        # First two requests should succeed
        assert await brick.invoke("test1") == "test1"
        assert await brick.invoke("test2") == "test2"

        # Third request should fail
        with pytest.raises(ValueError, match="Rate limit exceeded"):
            await brick.invoke("test3")

        # Wait for window to reset
        await asyncio.sleep(1.1)

        # Should work again
        assert await brick.invoke("test4") == "test4"

    @pytest.mark.asyncio
    async def test_burst_limit(self):
        """Test burst limiting."""
        brick = RateLimiter(
            EchoNanobrick(),
            max_requests=10,
            window_seconds=10,
            burst_size=2,
        )

        # Burst limit should kick in
        assert await brick.invoke("test1") == "test1"
        assert await brick.invoke("test2") == "test2"

        with pytest.raises(ValueError, match="Rate limit exceeded"):
            await brick.invoke("test3")

    @pytest.mark.asyncio
    async def test_key_based_limiting(self):
        """Test per-key rate limiting."""

        def extract_user(input, deps):
            return input.split(":")[0] if ":" in input else "default"

        brick = RateLimiter(
            EchoNanobrick(),
            max_requests=1,
            window_seconds=1,
            key_func=extract_user,
        )

        # Different users should have separate limits
        assert await brick.invoke("user1:test") == "user1:test"
        assert await brick.invoke("user2:test") == "user2:test"

        # Same user hits limit
        with pytest.raises(ValueError):
            await brick.invoke("user1:test2")


class TestPermissionGuard:
    """Test permission-based access control."""

    @pytest.mark.asyncio
    async def test_permission_check(self):
        """Test basic permission checking."""
        brick = PermissionGuard(
            EchoNanobrick(),
            required_permissions={Permission.READ, Permission.EXECUTE},
        )

        # No permissions - should fail
        with pytest.raises(PermissionError):
            await brick.invoke("test", deps={})

        # Partial permissions - should fail
        context = SecurityContext(permissions={Permission.READ})
        with pytest.raises(PermissionError):
            await brick.invoke("test", deps={"security_context": context})

        # All permissions - should succeed
        context = SecurityContext(permissions={Permission.READ, Permission.EXECUTE})
        result = await brick.invoke("test", deps={"security_context": context})
        assert result == "test"

    @pytest.mark.asyncio
    async def test_admin_bypass(self):
        """Test admin permission bypasses other checks."""
        brick = PermissionGuard(
            EchoNanobrick(),
            required_permissions={Permission.READ, Permission.WRITE},
        )

        context = SecurityContext(permissions={Permission.ADMIN})
        result = await brick.invoke("test", deps={"security_context": context})
        assert result == "test"

    @pytest.mark.asyncio
    async def test_role_check(self):
        """Test role-based access control."""
        brick = PermissionGuard(
            EchoNanobrick(),
            required_roles={"developer", "tester"},
        )

        # No roles - should fail
        context = SecurityContext()
        with pytest.raises(PermissionError):
            await brick.invoke("test", deps={"security_context": context})

        # Has required roles - should succeed
        context = SecurityContext(roles={"developer", "tester", "user"})
        result = await brick.invoke("test", deps={"security_context": context})
        assert result == "test"

    @pytest.mark.asyncio
    async def test_any_permission_mode(self):
        """Test any_permission mode."""
        brick = PermissionGuard(
            EchoNanobrick(),
            required_permissions={Permission.READ, Permission.WRITE},
            any_permission=True,
        )

        # Has one of the permissions - should succeed
        context = SecurityContext(permissions={Permission.READ})
        result = await brick.invoke("test", deps={"security_context": context})
        assert result == "test"

    @pytest.mark.asyncio
    async def test_custom_context_extractor(self):
        """Test custom security context extraction."""

        def extract_from_input(input, deps):
            # Extract user from input format "user:message"
            if ":" in input:
                user, _ = input.split(":", 1)
                return SecurityContext(
                    user_id=user,
                    permissions={Permission.EXECUTE},
                )
            return SecurityContext()

        brick = PermissionGuard(
            EchoNanobrick(),
            required_permissions={Permission.EXECUTE},
            context_extractor=extract_from_input,
        )

        # Should extract context from input
        result = await brick.invoke("alice:hello")
        assert result == "alice:hello"

        # No user in input - should fail
        with pytest.raises(PermissionError):
            await brick.invoke("hello")


class TestEncryptionBrick:
    """Test encryption/decryption."""

    @pytest.mark.asyncio
    async def test_output_encryption(self):
        """Test encrypting output."""
        key = b"SfW-52R7F8Xz1A7vNcqjfQHgV8hcZn8AlFxLlLJgfcg="  # Fixed key for testing
        brick = EncryptionBrick(EchoNanobrick(), key=key)

        result = await brick.invoke("secret message")
        assert result != "secret message"  # Should be encrypted
        assert isinstance(result, str)

        # Decrypt to verify
        decrypt_brick = EncryptionBrick(
            EchoNanobrick(),
            key=key,
            encrypt_output=False,
            decrypt_input=True,
        )
        decrypted = await decrypt_brick.invoke(result)
        assert decrypted == "secret message"

    @pytest.mark.asyncio
    async def test_field_encryption(self):
        """Test selective field encryption."""

        class DictNanobrick(NanobrickBase[dict, dict, None]):
            def __init__(self):
                super().__init__(name="dict", version="1.0.0")

            async def invoke(self, input: dict, *, deps: None = None) -> dict:
                return input

        key = b"SfW-52R7F8Xz1A7vNcqjfQHgV8hcZn8AlFxLlLJgfcg="
        brick = EncryptionBrick(
            DictNanobrick(),
            key=key,
            fields_to_encrypt=["password", "ssn"],
        )

        result = await brick.invoke(
            {
                "username": "alice",
                "password": "secret123",
                "ssn": "123-45-6789",
                "public": "visible",
            }
        )

        # Specified fields should be encrypted
        assert result["password"] != "secret123"
        assert result["ssn"] != "123-45-6789"
        # Other fields should not be encrypted
        assert result["username"] == "alice"
        assert result["public"] == "visible"

    @pytest.mark.asyncio
    async def test_input_decryption(self):
        """Test decrypting input."""
        key = b"SfW-52R7F8Xz1A7vNcqjfQHgV8hcZn8AlFxLlLJgfcg="

        # First encrypt
        encrypt_brick = EncryptionBrick(
            EchoNanobrick(),
            key=key,
            encrypt_input=True,
            encrypt_output=False,
        )

        # Then decrypt
        decrypt_brick = EncryptionBrick(
            EchoNanobrick(),
            key=key,
            decrypt_input=True,
            encrypt_output=False,
        )

        # Should handle encryption/decryption transparently
        encrypted = await encrypt_brick.invoke("test")
        assert encrypted != "test"  # Input was encrypted

        decrypted = await decrypt_brick.invoke(encrypted)
        assert decrypted == "test"  # Was decrypted back


class TestAuditLogger:
    """Test audit logging."""

    @pytest.mark.asyncio
    async def test_success_logging(self):
        """Test logging successful operations."""
        brick = AuditLogger(EchoNanobrick())

        result = await brick.invoke("test")
        assert result == "test"

        # Check audit log
        entries = brick.get_audit_log()
        assert len(entries) == 1

        entry = entries[0]
        assert entry.brick_name == "echo"
        assert entry.action == "invoke"
        assert entry.success is True
        assert entry.error is None
        assert entry.duration_ms > 0

    @pytest.mark.asyncio
    async def test_failure_logging(self):
        """Test logging failed operations."""

        class FailingNanobrick(NanobrickBase[str, str, None]):
            def __init__(self):
                super().__init__(name="failing", version="1.0.0")

            async def invoke(self, input: str, *, deps: None = None) -> str:
                raise ValueError("Intentional failure")

        brick = AuditLogger(FailingNanobrick())

        with pytest.raises(ValueError):
            await brick.invoke("test")

        # Check audit log
        entries = brick.get_audit_log()
        assert len(entries) == 1

        entry = entries[0]
        assert entry.success is False
        assert entry.error == "Intentional failure"
        assert entry.output_hash is None

    @pytest.mark.asyncio
    async def test_user_tracking(self):
        """Test tracking user in audit log."""

        def extract_context(input, deps):
            if deps and "user" in deps:
                return SecurityContext(user_id=deps["user"])
            return SecurityContext()

        brick = AuditLogger(EchoNanobrick(), context_extractor=extract_context)

        await brick.invoke("test1", deps={"user": "alice"})
        await brick.invoke("test2", deps={"user": "bob"})
        await brick.invoke("test3")  # No user

        # Check filtering by user
        alice_entries = brick.get_audit_log(user_id="alice")
        assert len(alice_entries) == 1
        assert alice_entries[0].user_id == "alice"

        bob_entries = brick.get_audit_log(user_id="bob")
        assert len(bob_entries) == 1

        all_entries = brick.get_audit_log()
        assert len(all_entries) == 3

    @pytest.mark.asyncio
    async def test_sensitive_data_hashing(self):
        """Test that sensitive data is hashed."""
        brick = AuditLogger(
            EchoNanobrick(),
            log_input=True,
            log_output=True,
            hash_sensitive_data=True,
        )

        await brick.invoke("sensitive-password-123")

        entries = brick.get_audit_log()
        entry = entries[0]

        # Should be hashed, not plaintext
        assert entry.input_hash != "sensitive-password-123"
        assert len(entry.input_hash) == 16  # Truncated SHA256
        assert entry.output_hash != "sensitive-password-123"

    @pytest.mark.asyncio
    async def test_audit_handler(self):
        """Test custom audit handler."""
        handled_entries = []

        def handler(entry):
            handled_entries.append(entry)

        brick = AuditLogger(EchoNanobrick(), audit_handler=handler)

        await brick.invoke("test")

        # Handler should have been called
        assert len(handled_entries) == 1
        assert handled_entries[0].success is True


class TestSecureNanobrick:
    """Test the secure_nanobrick helper."""

    @pytest.mark.asyncio
    async def test_layered_security(self):
        """Test applying multiple security layers."""
        base_brick = EchoNanobrick()

        secure_brick = secure_nanobrick(
            base_brick,
            sanitize=True,
            rate_limit=10,
            permissions={Permission.EXECUTE},
            audit=True,
        )

        # Should handle sanitization
        context = SecurityContext(permissions={Permission.EXECUTE})
        result = await secure_brick.invoke(
            "<script>test</script>",
            deps={"security_context": context},
        )
        assert "&lt;script&gt;" in result

        # Check audit log exists
        audit_layer = secure_brick
        while hasattr(audit_layer, "brick"):
            if isinstance(audit_layer, AuditLogger):
                break
            audit_layer = audit_layer.brick

        if isinstance(audit_layer, AuditLogger):
            entries = audit_layer.get_audit_log()
            assert len(entries) == 1

    @pytest.mark.asyncio
    async def test_security_composition(self):
        """Test that security wrappers compose properly."""
        brick = EchoNanobrick()

        # Apply security in steps
        brick = InputSanitizer(brick)
        brick = RateLimiter(brick, max_requests=10)
        brick = AuditLogger(brick)

        # Should work through all layers
        result = await brick.invoke("<b>hello</b>")
        assert result == "&lt;b&gt;hello&lt;/b&gt;"

        # Verify composition
        assert "AuditLogger" in brick.name
        assert "RateLimiter" in brick.name
        assert "InputSanitizer" in brick.name
