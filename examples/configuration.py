"""Example of using the Nanobricks configuration system."""

import asyncio
from typing import Dict, Any

from nanobricks.protocol import NanobrickBase
from nanobricks.config import load_config, get_default_config, Config
from nanobricks.dependencies import StandardDeps


class ConfigurableBrick(NanobrickBase[str, str, StandardDeps]):
    """A brick that uses configuration."""
    
    def __init__(self, name: str = "configurable", config: Config = None):
        self.name = name
        self.version = "1.0.0"
        self.config = config or get_default_config()
    
    async def invoke(self, input: str, *, deps: StandardDeps = None) -> str:
        # Use configuration values
        log_level = self.config.get("logging", {}).get("level", "INFO")
        
        if deps and deps.get("logger"):
            deps["logger"].info(
                f"Processing with log level: {log_level}"
            )
        
        # Access nested config with dot notation
        if hasattr(self.config, "features"):
            if self.config.features.get("enable_caching", False):
                result = f"[CACHED] {input}"
            else:
                result = input
        else:
            result = input
        
        return result


class DatabaseBrick(NanobrickBase[Dict[str, Any], bool, StandardDeps]):
    """A brick that uses database configuration."""
    
    def __init__(self, config: Config = None):
        self.name = "database"
        self.version = "1.0.0"
        self.config = config or get_default_config()
    
    async def invoke(self, input: Dict[str, Any], *, deps: StandardDeps = None) -> bool:
        # Get database configuration
        db_config = self.config.get("database", {})
        db_url = db_config.get("url", "sqlite:///default.db")
        pool_size = db_config.get("pool_size", 5)
        
        if deps and deps.get("logger"):
            deps["logger"].info(
                f"Connecting to {db_url} with pool size {pool_size}"
            )
        
        # Simulate database operation
        return True


async def main():
    """Demonstrate configuration usage."""
    
    # Example 1: Load default configuration
    print("=== Default Configuration ===")
    config = load_config()
    print(f"Project name: {config.get('project', {}).get('name', 'unknown')}")
    print(f"Log level: {config.get('logging', {}).get('level', 'INFO')}")
    print()
    
    # Example 2: Load with environment override
    print("=== Production Configuration ===")
    prod_config = load_config(environment="production")
    print(f"Database URL: {prod_config.get('database', {}).get('url', 'not set')}")
    print(f"API port: {prod_config.get('api', {}).get('port', 8000)}")
    print()
    
    # Example 3: Load with manual overrides
    print("=== Custom Override Configuration ===")
    custom_config = load_config(
        overrides={
            "logging": {"level": "DEBUG"},
            "features": {"enable_telemetry": True}
        }
    )
    print(f"Log level: {custom_config.get('logging', {}).get('level', 'INFO')}")
    print(f"Telemetry: {custom_config.get('features', {}).get('enable_telemetry', False)}")
    print()
    
    # Example 4: Use configuration in bricks
    print("=== Using Configuration in Bricks ===")
    
    # Create bricks with default config
    configurable = ConfigurableBrick()
    db_brick = DatabaseBrick()
    
    # Create a pipeline
    pipeline = configurable | db_brick
    
    # Mock logger
    from nanobricks.dependencies import MockLogger
    logger = MockLogger()
    deps: StandardDeps = {"logger": logger}
    
    # Run the pipeline
    result = await pipeline.invoke("test data", deps=deps)
    print(f"Pipeline result: {result}")
    print(f"Logger messages: {logger.messages}")
    print()
    
    # Example 5: Brick with custom config
    print("=== Custom Configuration for Brick ===")
    test_config = Config({
        "logging": {"level": "DEBUG"},
        "features": {"enable_caching": True}
    })
    
    custom_brick = ConfigurableBrick(config=test_config)
    result = await custom_brick.invoke("test input", deps=deps)
    print(f"Result with caching: {result}")


def demonstrate_config_api():
    """Show various configuration API features."""
    print("\n=== Configuration API Demo ===")
    
    # Create a config object
    config = Config({
        "app": {
            "name": "demo",
            "version": "1.0.0",
            "settings": {
                "debug": True,
                "timeout": 30
            }
        },
        "features": ["auth", "api", "cache"]
    })
    
    # Dot notation access
    print(f"App name: {config.app.name}")
    print(f"Debug mode: {config.app.settings.debug}")
    
    # Dictionary access
    print(f"Features: {config['features']}")
    
    # Safe get with default
    print(f"Missing key: {config.get('missing', 'default value')}")
    
    # Convert back to dict
    data = config.to_dict()
    print(f"As dict: {type(data)}")
    
    # Freeze configuration
    config.freeze()
    try:
        config.app.name = "changed"  # This will raise an error
    except Exception as e:
        print(f"Error when modifying frozen config: {e}")


if __name__ == "__main__":
    # Run async examples
    asyncio.run(main())
    
    # Run sync examples
    demonstrate_config_api()