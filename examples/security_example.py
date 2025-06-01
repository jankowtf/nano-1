"""Example demonstrating security features for nanobricks."""

import asyncio
from typing import Dict

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


class UserService(NanobrickBase[Dict[str, str], Dict[str, str], Dict[str, SecurityContext]]):
    """Mock user service that requires authentication."""
    
    name = "user_service"
    version = "1.0.0"
    
    async def invoke(
        self,
        input: Dict[str, str],
        *,
        deps: Dict[str, SecurityContext] = None,
    ) -> Dict[str, str]:
        """Process user request."""
        action = input.get("action", "unknown")
        
        if action == "get_profile":
            return {
                "username": input.get("username", "unknown"),
                "email": "user@example.com",
                "role": "user",
            }
        elif action == "update_profile":
            return {
                "status": "updated",
                "username": input.get("username", "unknown"),
            }
        elif action == "delete_account":
            return {"status": "deleted"}
        else:
            raise ValueError(f"Unknown action: {action}")


async def basic_security_example():
    """Demonstrate basic security features."""
    print("=== Basic Security Example ===\n")
    
    # Create base service
    service = UserService()
    
    # Add input sanitization
    safe_service = InputSanitizer(service, max_length=100)
    
    # Test with potentially malicious input
    result = await safe_service.invoke({
        "action": "get_profile",
        "username": "<script>alert('xss')</script>",
    })
    print(f"Sanitized result: {result}")
    print(f"Username was sanitized: {result['username']}\n")


async def rate_limiting_example():
    """Demonstrate rate limiting."""
    print("=== Rate Limiting Example ===\n")
    
    service = UserService()
    
    # Add rate limiting: 3 requests per 5 seconds
    limited_service = RateLimiter(
        service,
        max_requests=3,
        window_seconds=5,
    )
    
    # Make requests
    for i in range(5):
        try:
            result = await limited_service.invoke({
                "action": "get_profile",
                "username": f"user{i}",
            })
            print(f"Request {i+1}: Success")
        except ValueError as e:
            print(f"Request {i+1}: {e}")
    
    print()


async def permission_example():
    """Demonstrate permission-based access control."""
    print("=== Permission Example ===\n")
    
    service = UserService()
    
    # Different endpoints require different permissions
    read_service = PermissionGuard(
        service,
        required_permissions={Permission.READ},
    )
    
    write_service = PermissionGuard(
        service,
        required_permissions={Permission.WRITE},
    )
    
    delete_service = PermissionGuard(
        service,
        required_permissions={Permission.DELETE, Permission.ADMIN},
    )
    
    # Test with different permission sets
    contexts = {
        "reader": SecurityContext(
            user_id="alice",
            permissions={Permission.READ},
        ),
        "writer": SecurityContext(
            user_id="bob",
            permissions={Permission.READ, Permission.WRITE},
        ),
        "admin": SecurityContext(
            user_id="charlie",
            permissions={Permission.ADMIN},
        ),
    }
    
    # Reader can only read
    try:
        result = await read_service.invoke(
            {"action": "get_profile", "username": "alice"},
            deps={"security_context": contexts["reader"]},
        )
        print("Reader: ✓ Can read profiles")
    except PermissionError:
        print("Reader: ✗ Cannot read profiles")
    
    try:
        await write_service.invoke(
            {"action": "update_profile", "username": "alice"},
            deps={"security_context": contexts["reader"]},
        )
        print("Reader: ✓ Can write profiles")
    except PermissionError:
        print("Reader: ✗ Cannot write profiles")
    
    # Admin can do everything
    try:
        await delete_service.invoke(
            {"action": "delete_account"},
            deps={"security_context": contexts["admin"]},
        )
        print("Admin: ✓ Can delete accounts")
    except PermissionError:
        print("Admin: ✗ Cannot delete accounts")
    
    print()


async def encryption_example():
    """Demonstrate encryption of sensitive data."""
    print("=== Encryption Example ===\n")
    
    service = UserService()
    
    # Encrypt sensitive fields
    encrypted_service = EncryptionBrick(
        service,
        fields_to_encrypt=["email", "password"],
    )
    
    # Process request with sensitive data
    result = await encrypted_service.invoke({
        "action": "get_profile",
        "username": "alice",
    })
    
    print(f"Encrypted result: {result}")
    print(f"Email is encrypted: {result['email'][:20]}...")
    print()


async def audit_logging_example():
    """Demonstrate audit logging."""
    print("=== Audit Logging Example ===\n")
    
    service = UserService()
    
    # Add comprehensive audit logging
    audited_service = AuditLogger(
        service,
        log_input=True,
        log_output=False,  # Don't log output for privacy
        hash_sensitive_data=True,
    )
    
    # Make some requests
    users = ["alice", "bob", "charlie"]
    for user in users:
        await audited_service.invoke({
            "action": "get_profile",
            "username": user,
        })
    
    # Check audit log
    entries = audited_service.get_audit_log()
    print(f"Total audit entries: {len(entries)}")
    
    for entry in entries:
        print(f"- {entry.timestamp}: {entry.action} "
              f"(duration: {entry.duration_ms:.2f}ms, "
              f"success: {entry.success})")
    
    print()


async def layered_security_example():
    """Demonstrate multiple security layers."""
    print("=== Layered Security Example ===\n")
    
    service = UserService()
    
    # Apply multiple security layers at once
    secure_service = secure_nanobrick(
        service,
        sanitize=True,
        rate_limit=10,
        permissions={Permission.READ},
        encrypt=True,
        audit=True,
    )
    
    # Use the secure service
    context = SecurityContext(
        user_id="alice",
        permissions={Permission.READ},
    )
    
    try:
        result = await secure_service.invoke(
            {
                "action": "get_profile",
                "username": "<b>alice</b>",  # Will be sanitized
            },
            deps={"security_context": context},
        )
        print("✓ Request succeeded with all security checks")
        print(f"Result type: {type(result)}")
    except Exception as e:
        print(f"✗ Request failed: {e}")
    
    print()


async def main():
    """Run all security examples."""
    await basic_security_example()
    await rate_limiting_example()
    await permission_example()
    await encryption_example()
    await audit_logging_example()
    await layered_security_example()


if __name__ == "__main__":
    asyncio.run(main())