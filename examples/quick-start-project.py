#!/usr/bin/env python3
"""
Quick example of using Nanobricks in a new project.

First, install Nanobricks in your project:
    pip install -e /path/to/nanobricks

Or in your pyproject.toml:
    dependencies = [
        "nanobricks @ file:///path/to/nanobricks",
    ]
"""

import asyncio
from typing import TypedDict

from nanobricks import NanobrickSimple, Pipeline, NanobrickBase
from nanobricks.validators import EmailValidator, LengthValidator
from nanobricks.transformers import JSONParser, SnakeCaseTransformer
from nanobricks.skills import with_skill


# Example 1: Simple Data Processing Pipeline
class UserData(TypedDict):
    name: str
    email: str
    age: int


class ValidateUser(NanobrickBase[dict, UserData, None]):
    """Validates and types user data."""
    
    async def invoke(self, input: dict, *, deps=None) -> UserData:
        # In real app, would use Pydantic or similar
        if not all(k in input for k in ['name', 'email', 'age']):
            raise ValueError("Missing required fields")
        
        return UserData(
            name=input['name'],
            email=input['email'],
            age=input['age']
        )


class EnrichUser(NanobrickBase[UserData, UserData, None]):
    """Enriches user data with additional info."""
    
    async def invoke(self, input: UserData, *, deps=None) -> UserData:
        # Add computed fields
        input['username'] = input['email'].split('@')[0]
        input['is_adult'] = input['age'] >= 18
        return input


# Example 2: Using Built-in Components
async def example_validation_pipeline():
    """Example using built-in validators."""
    
    # Create pipeline with validators
    pipeline = (
        JSONParser() |  # Parse JSON string
        ValidateUser() |  # Custom validation
        EnrichUser()  # Enrich data
    )
    
    # Add logging skill
    logged_pipeline = with_skill(pipeline, "logging")
    
    # Test data
    json_data = '{"name": "Alice", "email": "alice@example.com", "age": 25}'
    
    result = await logged_pipeline.invoke(json_data)
    print("Processed user:", result)
    return result


# Example 3: Building a Microservice Component
class APIRequest(TypedDict):
    method: str
    path: str
    body: dict | None


class APIResponse(TypedDict):
    status: int
    data: dict


class RateLimiter(NanobrickSimple[APIRequest, APIRequest]):
    """Simple rate limiter brick."""
    
    def __init__(self, max_requests: int = 10):
        super().__init__(name="rate_limiter")
        self.max_requests = max_requests
        self.requests = []
    
    async def invoke(self, input: APIRequest) -> APIRequest:
        # Simple rate limiting logic
        import time
        now = time.time()
        
        # Clean old requests
        self.requests = [t for t in self.requests if now - t < 60]
        
        if len(self.requests) >= self.max_requests:
            raise Exception("Rate limit exceeded")
        
        self.requests.append(now)
        return input


class APIHandler(NanobrickBase[APIRequest, APIResponse, None]):
    """Handles API requests."""
    
    async def invoke(self, input: APIRequest, *, deps=None) -> APIResponse:
        # Simulate API handling
        if input['path'] == '/users' and input['method'] == 'GET':
            return APIResponse(
                status=200,
                data={"users": ["alice", "bob"]}
            )
        
        return APIResponse(
            status=404,
            data={"error": "Not found"}
        )


# Example 4: Real-world Use Case
async def build_api_service():
    """Build a simple API service with Nanobricks."""
    
    # Create service pipeline
    service = (
        RateLimiter(max_requests=100) |
        APIHandler()
    )
    
    # Add production features
    from nanobricks.production import CircuitBreaker
    from nanobricks.security import InputSanitizer
    
    # Wrap with production features
    production_service = CircuitBreaker(
        InputSanitizer(service),
        failure_threshold=5,
        timeout_seconds=30
    )
    
    # Test request
    request = APIRequest(
        method="GET",
        path="/users",
        body=None
    )
    
    response = await production_service.invoke(request)
    print("API Response:", response)
    return response


# Example 5: Using in Your Own Package Structure
def create_my_package_structure():
    """
    Suggested structure for your package using Nanobricks:
    
    my-package/
    ├── pyproject.toml
    ├── src/
    │   └── my_package/
    │       ├── __init__.py
    │       ├── bricks/          # Your custom nanobricks
    │       │   ├── __init__.py
    │       │   ├── processors.py
    │       │   └── validators.py
    │       ├── pipelines/       # Composed pipelines
    │       │   ├── __init__.py
    │       │   └── user_pipeline.py
    │       └── main.py
    └── tests/
    """
    pass


# Run examples
async def main():
    print("=== Nanobricks Quick Start Examples ===\n")
    
    print("1. Validation Pipeline:")
    await example_validation_pipeline()
    
    print("\n2. API Service:")
    await build_api_service()
    
    print("\n✅ All examples completed!")
    print("\nTo use in your project:")
    print("1. Install Nanobricks as shown at the top of this file")
    print("2. Import what you need: from nanobricks import ...")
    print("3. Build your bricks and compose them!")


if __name__ == "__main__":
    asyncio.run(main())