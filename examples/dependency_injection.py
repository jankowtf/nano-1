"""
Dependency injection example for nanobricks.

This demonstrates how to pass shared resources like databases,
caches, and loggers through nanobrick pipelines.
"""

import asyncio
from typing import Optional

from nanobricks import NanobrickBase
from nanobricks.dependencies import (
    StandardDeps, 
    MockDatabase, 
    MockCache, 
    MockLogger,
    DependencyContainer
)


# Define nanobricks that use dependencies
class UserLoaderBrick(NanobrickBase[str, dict, StandardDeps]):
    """Loads user data from database."""
    
    async def invoke(self, user_id: str, *, deps: Optional[StandardDeps] = None) -> dict:
        if not deps or "db" not in deps:
            raise ValueError("Database dependency required")
        
        if "logger" in deps:
            deps["logger"].info(f"Loading user {user_id}")
        
        # Query database
        results = await deps["db"].query(
            "SELECT * FROM users WHERE id = ?",
            {"id": user_id}
        )
        
        if not results:
            raise ValueError(f"User {user_id} not found")
        
        return results[0]


class CacheCheckBrick(NanobrickBase[str, Optional[dict], StandardDeps]):
    """Checks cache before loading from database."""
    
    async def invoke(self, user_id: str, *, deps: Optional[StandardDeps] = None) -> Optional[dict]:
        if not deps or "cache" not in deps:
            return None  # No cache available
        
        cache_key = f"user:{user_id}"
        cached_data = await deps["cache"].get(cache_key)
        
        if cached_data and "logger" in deps:
            deps["logger"].debug(f"Cache hit for {cache_key}")
        
        return cached_data


class CacheStoreBrick(NanobrickBase[dict, dict, StandardDeps]):
    """Stores data in cache for future use."""
    
    async def invoke(self, user_data: dict, *, deps: Optional[StandardDeps] = None) -> dict:
        if deps and "cache" in deps:
            cache_key = f"user:{user_data['id']}"
            await deps["cache"].set(cache_key, user_data, ttl=300)  # 5 minute TTL
            
            if "logger" in deps:
                deps["logger"].debug(f"Cached data for {cache_key}")
        
        return user_data


class EnrichUserBrick(NanobrickBase[dict, dict, StandardDeps]):
    """Enriches user data with additional information."""
    
    async def invoke(self, user_data: dict, *, deps: Optional[StandardDeps] = None) -> dict:
        # Add computed fields
        enriched = user_data.copy()
        enriched["full_name"] = f"{user_data.get('first_name', '')} {user_data.get('last_name', '')}".strip()
        
        # Add config-based data if available
        if deps and "config" in deps:
            enriched["tenant"] = deps["config"].get("tenant_name", "default")
        
        if deps and "logger" in deps:
            deps["logger"].info(f"Enriched user {user_data['id']}")
        
        return enriched


# Smart loading with cache
class SmartUserLoader(NanobrickBase[str, dict, StandardDeps]):
    """Loads user with cache support."""
    
    def __init__(self):
        super().__init__(name="smart_user_loader")
        
        # Compose the pipeline
        self.cache_check = CacheCheckBrick(name="cache_check")
        self.db_loader = UserLoaderBrick(name="db_load")
        self.cache_store = CacheStoreBrick(name="cache_store")
        self.enricher = EnrichUserBrick(name="enrich")
    
    async def invoke(self, user_id: str, *, deps: Optional[StandardDeps] = None) -> dict:
        # Check cache first
        cached = await self.cache_check.invoke(user_id, deps=deps)
        if cached:
            # Still enrich cached data
            return await self.enricher.invoke(cached, deps=deps)
        
        # Load from database
        user_data = await self.db_loader.invoke(user_id, deps=deps)
        
        # Store in cache
        await self.cache_store.invoke(user_data, deps=deps)
        
        # Enrich and return
        return await self.enricher.invoke(user_data, deps=deps)


async def main():
    """Demonstrate dependency injection."""
    
    print("=== Dependency Injection Examples ===\n")
    
    # Set up mock dependencies
    mock_db = MockDatabase({
        "SELECT * FROM users WHERE id = ?": [
            {"id": "123", "first_name": "Alice", "last_name": "Smith", "email": "alice@example.com"},
        ]
    })
    mock_cache = MockCache()
    mock_logger = MockLogger()
    
    # Create dependency container
    deps = DependencyContainer(
        db=mock_db,
        cache=mock_cache,
        logger=mock_logger,
        config={"tenant_name": "AcmeCorp"}
    )
    
    # Example 1: Basic dependency usage
    print("1. Basic Dependency Usage")
    print("-" * 30)
    
    loader = UserLoaderBrick(name="loader")
    user_data = await loader.invoke("123", deps=deps.to_dict())
    print(f"  Loaded user: {user_data}")
    
    # Check logger output
    print(f"  Log messages: {len(mock_logger.messages)}")
    for level, msg, _ in mock_logger.messages:
        print(f"    [{level}] {msg}")
    
    # Example 2: Pipeline with dependencies
    print("\n2. Pipeline with Dependencies")
    print("-" * 30)
    
    # Create pipeline - note deps are NOT part of the type signature for composition
    enricher = EnrichUserBrick(name="enricher")
    pipeline = loader | enricher  # This works because both use StandardDeps
    
    # Clear logger
    mock_logger.messages.clear()
    
    result = await pipeline.invoke("123", deps=deps.to_dict())
    print(f"  Pipeline result: {result}")
    print(f"  Log messages: {mock_logger.messages}")
    
    # Example 3: Smart loader with caching
    print("\n3. Smart Loading with Cache")
    print("-" * 30)
    
    smart_loader = SmartUserLoader()
    
    # First call - loads from DB
    mock_logger.messages.clear()
    result1 = await smart_loader.invoke("123", deps=deps.to_dict())
    print(f"  First call (DB): {result1['full_name']}")
    print(f"  DB queries: {len(mock_db.queries)}")
    print(f"  Cache size: {len(mock_cache.data)}")
    
    # Second call - loads from cache
    mock_logger.messages.clear()
    mock_db.queries.clear()
    result2 = await smart_loader.invoke("123", deps=deps.to_dict())
    print(f"\n  Second call (Cache): {result2['full_name']}")
    print(f"  DB queries: {len(mock_db.queries)}")  # Should be 0
    print(f"  Cache hit: {'user:123' in mock_cache.data}")
    
    # Example 4: Dependency override
    print("\n4. Dependency Override")
    print("-" * 30)
    
    # Override specific dependencies
    alt_deps = deps.override(
        config={"tenant_name": "DifferentCorp"},
        logger=MockLogger()  # Fresh logger
    )
    
    result3 = await enricher.invoke(
        {"id": "456", "first_name": "Bob", "last_name": "Jones"},
        deps=alt_deps.to_dict()
    )
    print(f"  Result with override: {result3}")
    print(f"  Original tenant: {deps.get('config')['tenant_name']}")
    print(f"  Override tenant: {result3['tenant']}")
    
    # Example 5: Missing dependencies
    print("\n5. Handling Missing Dependencies")
    print("-" * 30)
    
    # Try without required dependency
    try:
        await loader.invoke("123", deps={})  # No database!
    except ValueError as e:
        print(f"  Error (expected): {e}")
    
    # Cache check handles missing cache gracefully
    result = await smart_loader.cache_check.invoke("123", deps={})
    print(f"  Cache check without cache: {result}")  # Returns None


if __name__ == "__main__":
    asyncio.run(main())