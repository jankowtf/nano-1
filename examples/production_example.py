"""Example demonstrating production-ready features."""

import asyncio
import random
from typing import Dict

from nanobricks.production import (
    Bulkhead,
    CircuitBreaker,
    GracefulShutdown,
    HealthCheck,
    with_production_features,
)
from nanobricks.protocol import NanobrickBase


class WeatherService(NanobrickBase[str, Dict[str, float], None]):
    """Mock weather service that can be unreliable."""
    
    def __init__(self, failure_rate: float = 0.1):
        super().__init__(name="weather_service", version="1.0.0")
        self.failure_rate = failure_rate
        self.call_count = 0
    
    async def invoke(self, input: str, *, deps: None = None) -> Dict[str, float]:
        """Get weather for a city."""
        self.call_count += 1
        
        # Simulate network delays
        await asyncio.sleep(random.uniform(0.1, 0.3))
        
        # Simulate failures
        if random.random() < self.failure_rate:
            raise ConnectionError(f"Failed to fetch weather for {input}")
        
        # Return mock weather data
        return {
            "temperature": random.uniform(15, 30),
            "humidity": random.uniform(40, 80),
            "wind_speed": random.uniform(5, 25),
        }


class DataProcessor(NanobrickBase[Dict[str, float], str, None]):
    """Process weather data into a report."""
    
    def __init__(self):
        super().__init__(name="data_processor", version="1.0.0")
    
    async def invoke(
        self, input: Dict[str, float], *, deps: None = None
    ) -> str:
        """Process weather data."""
        # Simulate processing
        await asyncio.sleep(0.05)
        
        return (
            f"Weather Report: "
            f"Temp={input['temperature']:.1f}°C, "
            f"Humidity={input['humidity']:.0f}%, "
            f"Wind={input['wind_speed']:.1f}km/h"
        )


async def circuit_breaker_example():
    """Demonstrate circuit breaker pattern."""
    print("=== Circuit Breaker Example ===\n")
    
    # Create unreliable service
    service = WeatherService(failure_rate=0.5)
    
    # Add circuit breaker with fallback
    def fallback(city: str, deps) -> Dict[str, float]:
        print(f"Using cached data for {city}")
        return {"temperature": 20.0, "humidity": 60.0, "wind_speed": 10.0}
    
    protected_service = CircuitBreaker(
        service,
        failure_threshold=3,
        timeout_seconds=5,
        fallback=fallback,
    )
    
    # Make multiple requests
    cities = ["London", "Paris", "Tokyo", "New York", "Sydney", "Berlin"]
    
    for city in cities:
        try:
            weather = await protected_service.invoke(city)
            print(f"{city}: Got weather data")
        except Exception as e:
            print(f"{city}: Error - {e}")
    
    # Check circuit status
    print(f"\nCircuit state: {protected_service.state}")
    print(f"Total calls: {protected_service.stats.total_calls}")
    print(f"Failures: {protected_service.stats.failure_calls}")
    print()


async def bulkhead_example():
    """Demonstrate bulkhead isolation pattern."""
    print("=== Bulkhead Example ===\n")
    
    # Create service with bulkhead protection
    service = WeatherService(failure_rate=0.1)
    processor = DataProcessor()
    
    # Create pipeline with bulkhead
    pipeline = Bulkhead(service, max_concurrent=2) | processor
    
    # Create many concurrent requests
    cities = [f"City{i}" for i in range(10)]
    
    async def fetch_weather_report(city: str) -> str:
        try:
            return await pipeline.invoke(city)
        except Exception as e:
            return f"Failed to get report for {city}: {e}"
    
    # Start all requests concurrently
    print("Starting 10 concurrent requests (bulkhead limit: 2)...")
    start_time = asyncio.get_event_loop().time()
    
    results = await asyncio.gather(
        *[fetch_weather_report(city) for city in cities]
    )
    
    end_time = asyncio.get_event_loop().time()
    duration = end_time - start_time
    
    # Show results
    print(f"Completed in {duration:.1f}s")
    print(f"Successful reports: {sum(1 for r in results if 'Weather Report' in r)}")
    
    # Show bulkhead stats
    bulkhead = pipeline
    if hasattr(bulkhead, "stats"):
        print(f"Bulkhead stats: {bulkhead.stats}")
    print()


async def health_check_example():
    """Demonstrate health checking."""
    print("=== Health Check Example ===\n")
    
    # Create services with health checks
    weather_service = HealthCheck(WeatherService(failure_rate=0.2))
    processor = HealthCheck(DataProcessor())
    
    # Start background health checks
    await weather_service.start_health_checks()
    await processor.start_health_checks()
    
    # Make some requests
    print("Making requests and monitoring health...")
    
    for i in range(5):
        try:
            weather = await weather_service.invoke(f"City{i}")
            report = await processor.invoke(weather)
            print(f"Request {i+1}: Success")
        except Exception as e:
            print(f"Request {i+1}: Failed - {e}")
        
        # Check health periodically
        if i % 2 == 0:
            weather_health = await weather_service.check_health()
            processor_health = await processor.check_health()
            print(f"  Weather service: {weather_health.status}")
            print(f"  Processor: {processor_health.status}")
    
    # Stop health checks
    await weather_service.stop_health_checks()
    await processor.stop_health_checks()
    print()


async def graceful_shutdown_example():
    """Demonstrate graceful shutdown."""
    print("=== Graceful Shutdown Example ===\n")
    
    shutdown_manager = GracefulShutdown(timeout_seconds=2)
    
    # Create some long-running tasks
    async def background_task(name: str):
        try:
            print(f"{name}: Started")
            while True:
                await asyncio.sleep(1)
                print(f"{name}: Working...")
        except asyncio.CancelledError:
            print(f"{name}: Shutting down gracefully")
            # Cleanup would go here
            raise
    
    # Start tasks
    task1 = asyncio.create_task(background_task("Monitor"))
    task2 = asyncio.create_task(background_task("Reporter"))
    
    shutdown_manager.register_task(task1)
    shutdown_manager.register_task(task2)
    
    # Register cleanup handlers
    async def save_state():
        print("Saving application state...")
        await asyncio.sleep(0.1)
        print("State saved")
    
    def close_connections():
        print("Closing database connections...")
    
    shutdown_manager.register_handler(save_state)
    shutdown_manager.register_handler(close_connections)
    
    # Run for a bit
    print("Application running (will shutdown in 3 seconds)...")
    await asyncio.sleep(3)
    
    # Trigger shutdown
    print("\nTriggering shutdown...")
    await shutdown_manager.shutdown()
    print()


async def integrated_example():
    """Demonstrate all production features together."""
    print("=== Integrated Production Example ===\n")
    
    # Create service with all production features
    weather_service = with_production_features(
        WeatherService(failure_rate=0.15),
        circuit_breaker=True,
        bulkhead=3,
        health_check=True,
        failure_threshold=5,
        timeout_seconds=10,
    )
    
    processor = with_production_features(
        DataProcessor(),
        bulkhead=5,
        health_check=True,
    )
    
    # Create pipeline
    pipeline = weather_service | processor
    
    # Process multiple cities
    cities = ["London", "Paris", "Tokyo", "New York", "Sydney"]
    
    print("Processing weather reports with full production protection...")
    
    async def process_city(city: str) -> str:
        try:
            return await pipeline.invoke(city)
        except Exception as e:
            return f"Error processing {city}: {e}"
    
    # Process all cities
    results = await asyncio.gather(
        *[process_city(city) for city in cities]
    )
    
    # Show results
    for city, result in zip(cities, results):
        print(f"{city}: {result}")
    
    # Show health status
    print("\nHealth Status:")
    if hasattr(weather_service, "is_healthy"):
        print(f"Weather service healthy: {weather_service.is_healthy}")
    if hasattr(processor, "is_healthy"):
        print(f"Processor healthy: {processor.is_healthy}")


async def main():
    """Run all production examples."""
    await circuit_breaker_example()
    await bulkhead_example()
    await health_check_example()
    await graceful_shutdown_example()
    await integrated_example()


if __name__ == "__main__":
    asyncio.run(main())