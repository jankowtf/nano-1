"""
Executable Contract for Nanobrick Protocol
This file serves as both documentation and validation.
"""

from typing import Protocol, TypeVar, Generic, runtime_checkable
from abc import ABC, abstractmethod
import asyncio
import inspect

T_in = TypeVar("T_in")
T_out = TypeVar("T_out")
T_deps = TypeVar("T_deps")


@runtime_checkable
class NanobrickContract(Protocol[T_in, T_out, T_deps]):
    """
    The core contract that all Nanobricks must fulfill.
    This is an executable specification.
    """
    
    @abstractmethod
    async def invoke(self, input: T_in, *, deps: T_deps = None) -> T_out:
        """Process input asynchronously."""
        ...
    
    @abstractmethod
    def invoke_sync(self, input: T_in, *, deps: T_deps = None) -> T_out:
        """Process input synchronously."""
        ...
    
    @abstractmethod
    def __rshift__(self, other: "NanobrickContract") -> "NanobrickContract":
        """Compose with another nanobrick using >> operator."""
        ...


class ContractValidator:
    """Validates that a class fulfills the Nanobrick contract."""
    
    @staticmethod
    def validate(cls) -> tuple[bool, list[str]]:
        """
        Validate a class against the contract.
        Returns (is_valid, list_of_issues).
        """
        issues = []
        
        # Check for required methods
        required_methods = ['invoke', 'invoke_sync', '__rshift__']
        for method_name in required_methods:
            if not hasattr(cls, method_name):
                issues.append(f"Missing required method: {method_name}")
                continue
            
            method = getattr(cls, method_name)
            
            # Check invoke is async
            if method_name == 'invoke' and not inspect.iscoroutinefunction(method):
                issues.append("invoke method must be async")
            
            # Check invoke_sync is not async
            if method_name == 'invoke_sync' and inspect.iscoroutinefunction(method):
                issues.append("invoke_sync method must not be async")
        
        # Check if it's a Protocol instance
        if not isinstance(cls, type):
            instance = cls
            if not isinstance(instance, NanobrickContract):
                issues.append("Does not implement NanobrickContract protocol")
        
        return len(issues) == 0, issues


# Example usage for AI agents:
def example_validation():
    """
    COPY-PASTE-MODIFY: How to validate your nanobrick
    """
    from my_module import MyNanobrick
    
    is_valid, issues = ContractValidator.validate(MyNanobrick)
    
    if is_valid:
        print("✅ Contract fulfilled!")
    else:
        print("❌ Contract violations:")
        for issue in issues:
            print(f"  - {issue}")


# Test fixtures for contract compliance
class ValidNanobrick(Generic[T_in, T_out]):
    """Example of a contract-compliant nanobrick."""
    
    async def invoke(self, input: T_in, *, deps=None) -> T_out:
        return input  # type: ignore
    
    def invoke_sync(self, input: T_in, *, deps=None) -> T_out:
        return asyncio.run(self.invoke(input, deps=deps))
    
    def __rshift__(self, other):
        return other  # Simplified composition


class InvalidNanobrick:
    """Example of a non-compliant nanobrick (for testing)."""
    
    def invoke(self, input):  # Not async!
        return input


if __name__ == "__main__":
    # Self-test the contract
    print("Testing contract validator...")
    
    # Test valid nanobrick
    is_valid, issues = ContractValidator.validate(ValidNanobrick)
    assert is_valid, f"ValidNanobrick should be valid: {issues}"
    
    # Test invalid nanobrick
    is_valid, issues = ContractValidator.validate(InvalidNanobrick)
    assert not is_valid, "InvalidNanobrick should be invalid"
    assert "invoke method must be async" in issues[0]
    
    print("✅ Contract validator working correctly!")