#!/usr/bin/env python3
"""
Dependency Injection Example - Using the deps Parameter

This example shows how to use the deps parameter to inject shared resources,
configuration, and services into your nanobricks.
"""

import asyncio
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from datetime import datetime
from nanobricks import Nanobrick


# Example 1: Shared Database Connection
class DatabaseQueryBrick(Nanobrick[str, List[Dict[str, Any]]]):
    """Executes database queries using injected connection."""
    
    name = "database_query"
    version = "1.0.0"
    
    async def invoke(self, query: str, *, deps: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        if not deps or "db" not in deps:
            raise ValueError("Database connection required in deps['db']")
        
        db = deps["db"]
        # In real code, this would execute the query
        print(f"Executing query on {db.name}: {query}")
        
        # Mock result
        return [
            {"id": 1, "name": "Alice", "score": 95},
            {"id": 2, "name": "Bob", "score": 87}
        ]


# Example 2: Configuration Injection
@dataclass
class ProcessingConfig:
    min_score: int = 80
    max_results: int = 10
    include_metadata: bool = True


class DataProcessor(Nanobrick[List[Dict[str, Any]], List[Dict[str, Any]]]):
    """Processes data based on injected configuration."""
    
    name = "data_processor"
    version = "1.0.0"
    
    async def invoke(
        self, 
        data: List[Dict[str, Any]], 
        *, 
        deps: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        # Get config from deps, with defaults
        config = ProcessingConfig()
        if deps and "config" in deps:
            config = deps["config"]
        
        # Filter based on config
        filtered = [
            item for item in data 
            if item.get("score", 0) >= config.min_score
        ][:config.max_results]
        
        # Add metadata if configured
        if config.include_metadata:
            for item in filtered:
                item["processed_at"] = datetime.now().isoformat()
                item["min_score_threshold"] = config.min_score
        
        return filtered


# Example 3: Service Injection
class EmailService:
    """Mock email service."""
    def __init__(self, smtp_host: str):
        self.smtp_host = smtp_host
    
    async def send(self, to: str, subject: str, body: str):
        print(f"[{self.smtp_host}] Sending email to {to}: {subject}")
        return True


class NotificationBrick(Nanobrick[Dict[str, Any], bool]):
    """Sends notifications using injected services."""
    
    name = "notification_sender"
    version = "1.0.0"
    
    async def invoke(
        self, 
        notification: Dict[str, Any], 
        *, 
        deps: Optional[Dict[str, Any]] = None
    ) -> bool:
        if not deps:
            raise ValueError("Dependencies required")
        
        # Get required services
        email_service = deps.get("email_service")
        logger = deps.get("logger")
        
        if not email_service:
            raise ValueError("Email service required in deps")
        
        # Log if logger available
        if logger:
            logger.info(f"Sending notification to {notification['to']}")
        
        # Send notification
        success = await email_service.send(
            to=notification["to"],
            subject=notification["subject"],
            body=notification["body"]
        )
        
        if logger:
            logger.info(f"Notification sent: {success}")
        
        return success


# Example 4: Pipeline with Shared Dependencies
class Pipeline(Nanobrick[str, bool]):
    """A pipeline that uses dependency injection throughout."""
    
    name = "notification_pipeline"
    version = "1.0.0"
    
    def __init__(self):
        self.query_brick = DatabaseQueryBrick()
        self.processor = DataProcessor()
        self.notifier = NotificationBrick()
    
    async def invoke(self, query: str, *, deps: Optional[Dict[str, Any]] = None) -> bool:
        # Pass deps to all stages
        data = await self.query_brick.invoke(query, deps=deps)
        processed = await self.processor.invoke(data, deps=deps)
        
        # Create notification from processed data
        if processed:
            notification = {
                "to": "admin@example.com",
                "subject": f"Query returned {len(processed)} results",
                "body": f"Top result: {processed[0]['name']} with score {processed[0]['score']}"
            }
            return await self.notifier.invoke(notification, deps=deps)
        
        return False


# Example 5: Mock implementations for testing
class MockDatabase:
    """Mock database for testing."""
    def __init__(self, name: str):
        self.name = name


class MockLogger:
    """Mock logger for testing."""
    def info(self, message: str):
        print(f"[LOG] {message}")


async def main():
    # Create shared dependencies
    deps = {
        "db": MockDatabase("production_db"),
        "config": ProcessingConfig(
            min_score=90,
            max_results=5,
            include_metadata=True
        ),
        "email_service": EmailService("smtp.example.com"),
        "logger": MockLogger()
    }
    
    # Example 1: Individual brick with deps
    print("=== Example 1: Database Query ===")
    query_brick = DatabaseQueryBrick()
    results = await query_brick.invoke("SELECT * FROM users", deps=deps)
    print(f"Query returned {len(results)} results")
    print()
    
    # Example 2: Pipeline with deps
    print("=== Example 2: Full Pipeline ===")
    pipeline = Pipeline()
    success = await pipeline.invoke("SELECT * FROM high_scores", deps=deps)
    print(f"Pipeline completed: {success}")
    print()
    
    # Example 3: Different configs for different environments
    print("=== Example 3: Environment-Specific Config ===")
    dev_deps = {
        **deps,  # Copy all deps
        "config": ProcessingConfig(
            min_score=0,  # Lower threshold for dev
            max_results=100,
            include_metadata=True
        ),
        "db": MockDatabase("dev_db")
    }
    
    dev_results = await query_brick.invoke("SELECT * FROM test_users", deps=dev_deps)
    print("Dev query executed")
    print()
    
    # Example 4: Partial dependencies (error handling)
    print("=== Example 4: Missing Dependencies ===")
    try:
        await query_brick.invoke("SELECT * FROM users", deps={})  # Missing db
    except ValueError as e:
        print(f"Error caught: {e}")


# Best practices for dependency injection
async def dependency_injection_patterns():
    """Demonstrates various dependency injection patterns."""
    
    # Pattern 1: Factory functions for dependencies
    def create_deps(env: str) -> Dict[str, Any]:
        """Create environment-specific dependencies."""
        if env == "production":
            return {
                "db": MockDatabase("prod_db"),
                "config": ProcessingConfig(min_score=80),
                "email_service": EmailService("smtp.prod.com")
            }
        else:
            return {
                "db": MockDatabase("dev_db"),
                "config": ProcessingConfig(min_score=0),
                "email_service": EmailService("smtp.dev.com")
            }
    
    # Pattern 2: Dependency container class
    class DependencyContainer:
        """Manages all application dependencies."""
        def __init__(self, env: str):
            self.env = env
            self._db = None
            self._email = None
        
        @property
        def db(self):
            if not self._db:
                self._db = MockDatabase(f"{self.env}_db")
            return self._db
        
        @property
        def email_service(self):
            if not self._email:
                self._email = EmailService(f"smtp.{self.env}.com")
            return self._email
        
        def as_dict(self) -> Dict[str, Any]:
            return {
                "db": self.db,
                "email_service": self.email_service,
                "config": ProcessingConfig()
            }
    
    # Use the patterns
    prod_deps = create_deps("production")
    container = DependencyContainer("staging")
    staging_deps = container.as_dict()


if __name__ == "__main__":
    asyncio.run(main())