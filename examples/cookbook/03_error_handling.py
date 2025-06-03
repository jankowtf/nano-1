#!/usr/bin/env python3
"""
Error Handling Patterns - Exceptions vs Validation Results

This example demonstrates two main approaches to error handling in nanobricks:
1. Exception-based (fail fast)
2. Result-based (explicit error handling)
"""

import asyncio
from typing import Optional, Union, List, Dict, Any
from dataclasses import dataclass
from enum import Enum
from nanobricks import Nanobrick


# Approach 1: Exception-Based Error Handling
class StrictParser(Nanobrick[str, Dict[str, Any]]):
    """Parser that raises exceptions on invalid input."""
    
    name = "strict_parser"
    version = "1.0.0"
    
    async def invoke(self, input: str, *, deps=None) -> Dict[str, Any]:
        if not input:
            raise ValueError("Empty input is not allowed")
        
        if not input.strip().startswith("{"):
            raise ValueError("Input must be valid JSON starting with '{'")
        
        try:
            # In real code, use json.loads
            if input == "{}":
                return {}
            elif "error" in input:
                raise ValueError("Input contains error field")
            else:
                return {"parsed": True, "content": input}
        except Exception as e:
            # Re-raise with context
            raise ValueError(f"Failed to parse input: {str(e)}") from e


# Approach 2: Result-Based Error Handling
@dataclass
class ValidationResult:
    """Result of validation with success/failure info."""
    is_valid: bool
    data: Optional[Dict[str, Any]] = None
    errors: List[str] = None
    warnings: List[str] = None
    
    def __post_init__(self):
        if self.errors is None:
            self.errors = []
        if self.warnings is None:
            self.warnings = []


class SafeParser(Nanobrick[str, ValidationResult]):
    """Parser that returns validation results instead of raising."""
    
    name = "safe_parser"
    version = "1.0.0"
    
    async def invoke(self, input: str, *, deps=None) -> ValidationResult:
        errors = []
        warnings = []
        
        if not input:
            errors.append("Empty input is not allowed")
            return ValidationResult(is_valid=False, errors=errors)
        
        if not input.strip().startswith("{"):
            warnings.append("Input should ideally start with '{'")
        
        try:
            # Simulate parsing
            if input == "{}":
                warnings.append("Empty object provided")
                return ValidationResult(
                    is_valid=True,
                    data={},
                    warnings=warnings
                )
            elif "error" in input:
                errors.append("Input contains error field")
                return ValidationResult(is_valid=False, errors=errors)
            else:
                return ValidationResult(
                    is_valid=True,
                    data={"parsed": True, "content": input},
                    warnings=warnings
                )
        except Exception as e:
            errors.append(f"Unexpected error: {str(e)}")
            return ValidationResult(is_valid=False, errors=errors)


# Hybrid Approach: Configurable Error Handling
class ErrorMode(Enum):
    STRICT = "strict"      # Raise exceptions
    SAFE = "safe"          # Return results
    WARN = "warn"          # Log warnings but continue


class ConfigurableParser(Nanobrick[str, Union[Dict[str, Any], ValidationResult]]):
    """Parser with configurable error handling mode."""
    
    name = "configurable_parser"
    version = "1.0.0"
    
    def __init__(self, error_mode: ErrorMode = ErrorMode.SAFE):
        self.error_mode = error_mode
    
    async def invoke(
        self, 
        input: str, 
        *, 
        deps=None
    ) -> Union[Dict[str, Any], ValidationResult]:
        logger = deps.get("logger") if deps else None
        
        # Validation logic
        errors = []
        warnings = []
        
        if not input:
            error = "Empty input is not allowed"
            if self.error_mode == ErrorMode.STRICT:
                raise ValueError(error)
            else:
                errors.append(error)
        
        # Process based on mode
        if self.error_mode == ErrorMode.STRICT:
            # Exception mode - fail fast
            try:
                return {"parsed": True, "content": input}
            except Exception as e:
                raise ValueError(f"Parse error: {str(e)}") from e
                
        elif self.error_mode == ErrorMode.SAFE:
            # Result mode - capture all errors
            if errors:
                return ValidationResult(is_valid=False, errors=errors)
            else:
                return ValidationResult(
                    is_valid=True,
                    data={"parsed": True, "content": input},
                    warnings=warnings
                )
                
        else:  # WARN mode
            # Log warnings but return data
            if logger and warnings:
                for warning in warnings:
                    logger.warning(warning)
            return {"parsed": True, "content": input, "had_warnings": bool(warnings)}


# Error Recovery with Fallbacks
class ResilientProcessor(Nanobrick[str, Dict[str, Any]]):
    """Processor with built-in error recovery."""
    
    name = "resilient_processor"
    version = "1.0.0"
    
    def __init__(self):
        self.strict_parser = StrictParser()
        self.safe_parser = SafeParser()
    
    async def invoke(self, input: str, *, deps=None) -> Dict[str, Any]:
        # Try strict parsing first
        try:
            return await self.strict_parser.invoke(input, deps=deps)
        except ValueError as e:
            # Fall back to safe parsing
            if deps and "logger" in deps:
                deps["logger"].warning(f"Strict parse failed: {e}, trying safe mode")
            
            result = await self.safe_parser.invoke(input, deps=deps)
            
            if result.is_valid:
                return result.data
            else:
                # Last resort - return error info
                return {
                    "parsed": False,
                    "errors": result.errors,
                    "original_input": input
                }


# Pipeline with Error Boundaries
class ErrorBoundaryPipeline(Nanobrick[List[str], Dict[str, Any]]):
    """Pipeline that handles errors at each stage."""
    
    name = "error_boundary_pipeline"
    version = "1.0.0"
    
    def __init__(self):
        self.parser = ConfigurableParser(ErrorMode.SAFE)
    
    async def invoke(self, inputs: List[str], *, deps=None) -> Dict[str, Any]:
        results = {
            "successful": [],
            "failed": [],
            "total": len(inputs)
        }
        
        for idx, input_str in enumerate(inputs):
            try:
                result = await self.parser.invoke(input_str, deps=deps)
                
                if isinstance(result, ValidationResult):
                    if result.is_valid:
                        results["successful"].append({
                            "index": idx,
                            "data": result.data
                        })
                    else:
                        results["failed"].append({
                            "index": idx,
                            "input": input_str,
                            "errors": result.errors
                        })
                else:
                    results["successful"].append({
                        "index": idx,
                        "data": result
                    })
                    
            except Exception as e:
                # Catch any unexpected errors
                results["failed"].append({
                    "index": idx,
                    "input": input_str,
                    "errors": [f"Unexpected error: {str(e)}"]
                })
        
        results["success_rate"] = len(results["successful"]) / results["total"]
        return results


# Custom exception types for better error handling
class BrickException(Exception):
    """Base exception for nanobrick errors."""
    pass


class ValidationException(BrickException):
    """Raised when input validation fails."""
    def __init__(self, message: str, field: Optional[str] = None):
        super().__init__(message)
        self.field = field


class DependencyException(BrickException):
    """Raised when required dependencies are missing."""
    def __init__(self, missing_deps: List[str]):
        super().__init__(f"Missing required dependencies: {', '.join(missing_deps)}")
        self.missing_deps = missing_deps


class TypedErrorBrick(Nanobrick[Dict[str, Any], Dict[str, Any]]):
    """Brick that uses typed exceptions."""
    
    name = "typed_error_brick"
    version = "1.0.0"
    
    async def invoke(self, input: Dict[str, Any], *, deps=None) -> Dict[str, Any]:
        # Check dependencies
        if not deps or "validator" not in deps:
            raise DependencyException(["validator"])
        
        # Validate required fields
        if "id" not in input:
            raise ValidationException("Missing required field", field="id")
        
        if not isinstance(input.get("id"), int):
            raise ValidationException("ID must be an integer", field="id")
        
        # Process if valid
        return {
            "processed": True,
            "id": input["id"],
            "validated_by": deps["validator"].name
        }


async def main():
    print("=== Error Handling Examples ===\n")
    
    # Example 1: Exception-based handling
    print("1. Exception-based (Strict) Handling:")
    strict_parser = StrictParser()
    
    try:
        result = await strict_parser.invoke("{valid json}")
        print(f"Success: {result}")
    except ValueError as e:
        print(f"Error caught: {e}")
    
    try:
        result = await strict_parser.invoke("")  # Will raise
    except ValueError as e:
        print(f"Error caught: {e}")
    print()
    
    # Example 2: Result-based handling
    print("2. Result-based (Safe) Handling:")
    safe_parser = SafeParser()
    
    result1 = await safe_parser.invoke("{valid json}")
    print(f"Valid input: {result1}")
    
    result2 = await safe_parser.invoke("")
    print(f"Invalid input: {result2}")
    print()
    
    # Example 3: Pipeline with error boundaries
    print("3. Pipeline with Error Boundaries:")
    pipeline = ErrorBoundaryPipeline()
    
    inputs = [
        "{valid}",
        "",  # Invalid
        "{another valid}",
        "error in input",  # Will fail
        "{}"  # Valid but empty
    ]
    
    results = await pipeline.invoke(inputs)
    print(f"Processed {results['total']} items:")
    print(f"- Successful: {len(results['successful'])}")
    print(f"- Failed: {len(results['failed'])}")
    print(f"- Success rate: {results['success_rate']:.1%}")
    
    if results['failed']:
        print("\nFailed items:")
        for failed in results['failed']:
            print(f"  - Item {failed['index']}: {failed['errors']}")
    print()
    
    # Example 4: Typed exceptions
    print("4. Typed Exceptions:")
    typed_brick = TypedErrorBrick()
    
    # Mock validator
    class MockValidator:
        name = "mock_validator"
    
    try:
        # Missing dependency
        await typed_brick.invoke({"id": 123}, deps={})
    except DependencyException as e:
        print(f"Dependency error: {e}")
        print(f"Missing: {e.missing_deps}")
    
    try:
        # Invalid input
        await typed_brick.invoke(
            {"name": "test"},  # Missing id
            deps={"validator": MockValidator()}
        )
    except ValidationException as e:
        print(f"Validation error: {e}")
        print(f"Field: {e.field}")


if __name__ == "__main__":
    asyncio.run(main())