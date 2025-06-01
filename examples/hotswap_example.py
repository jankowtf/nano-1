"""
Example demonstrating hot-swapping capabilities.

Shows zero-downtime updates, gradual rollouts, and canary deployments.
"""

import asyncio
import random
from typing import Dict, Any

from nanobricks.protocol import NanobrickBase
from nanobricks.hotswap import (
    SwappablePipeline, SwapStrategy, CanaryController
)


# Example nanobricks with different behaviors

class DataProcessor(NanobrickBase[Dict[str, Any], Dict[str, Any], None]):
    """Process data with a specific algorithm version."""
    
    def __init__(self, version: str, algorithm: str):
        self.name = f"DataProcessor[{algorithm}]"
        self.version = version
        self.algorithm = algorithm
        self._processed_count = 0
        self._error_count = 0
    
    async def invoke(self, input: Dict[str, Any], *, deps: None = None) -> Dict[str, Any]:
        self._processed_count += 1
        
        # Simulate processing
        await asyncio.sleep(0.01)
        
        data = input.get("data", [])
        
        if self.algorithm == "v1":
            # Simple sum
            result = sum(data)
        elif self.algorithm == "v2":
            # Average
            result = sum(data) / len(data) if data else 0
        elif self.algorithm == "v3":
            # Median
            sorted_data = sorted(data)
            n = len(sorted_data)
            if n == 0:
                result = 0
            elif n % 2 == 0:
                result = (sorted_data[n//2 - 1] + sorted_data[n//2]) / 2
            else:
                result = sorted_data[n//2]
        elif self.algorithm == "buggy":
            # Buggy version that fails sometimes
            if random.random() < 0.3:
                self._error_count += 1
                raise ValueError("Processing error")
            result = sum(data)
        else:
            result = 0
        
        return {
            **input,
            "result": result,
            "processor": f"{self.algorithm}@{self.version}",
            "stats": {
                "processed": self._processed_count,
                "errors": self._error_count
            }
        }


class DataValidator(NanobrickBase[Dict[str, Any], Dict[str, Any], None]):
    """Validate data before processing."""
    
    def __init__(self, strict: bool = False):
        self.name = f"DataValidator[{'strict' if strict else 'lenient'}]"
        self.version = "1.0.0"
        self.strict = strict
    
    async def invoke(self, input: Dict[str, Any], *, deps: None = None) -> Dict[str, Any]:
        data = input.get("data", [])
        
        if self.strict:
            # Strict validation
            if not data:
                raise ValueError("Data cannot be empty")
            if not all(isinstance(x, (int, float)) for x in data):
                raise ValueError("All data must be numeric")
            if len(data) > 100:
                raise ValueError("Too many data points")
        else:
            # Lenient validation - just ensure it's a list
            if not isinstance(data, list):
                input["data"] = []
        
        return {**input, "validated": True}


async def example_immediate_swap():
    """Example: Immediate hot-swap during operation."""
    print("\n=== Immediate Hot-Swap Example ===")
    
    # Create initial pipeline
    pipeline = SwappablePipeline([
        DataValidator(strict=False),
        DataProcessor("1.0", "v1")  # Sum algorithm
    ])
    
    print("Initial pipeline: Validator[lenient] -> Processor[v1]")
    
    # Simulate continuous processing
    async def process_continuously():
        for i in range(10):
            data = {"data": [random.randint(1, 10) for _ in range(5)]}
            try:
                result = await pipeline.invoke(data)
                print(f"  Request {i}: {result['result']} (by {result['processor']})")
            except Exception as e:
                print(f"  Request {i}: Error - {e}")
            await asyncio.sleep(0.1)
    
    # Start processing
    task = asyncio.create_task(process_continuously())
    
    # After 0.3 seconds, hot-swap the processor
    await asyncio.sleep(0.3)
    print("\n>> Hot-swapping processor from v1 to v2...")
    
    new_processor = DataProcessor("2.0", "v2")  # Average algorithm
    success = await pipeline.swap(1, new_processor, SwapStrategy.IMMEDIATE)
    print(f">> Swap {'succeeded' if success else 'failed'}!")
    
    # Continue processing
    await task
    
    # Show final status
    status = pipeline.get_status()
    print(f"\nFinal status: {status['components'][1]['current_brick']}")


async def example_gradual_rollout():
    """Example: Gradual rollout with monitoring."""
    print("\n=== Gradual Rollout Example ===")
    
    # Create pipeline
    pipeline = SwappablePipeline([
        DataValidator(strict=False),
        DataProcessor("1.0", "v1")  # Sum algorithm
    ])
    
    print("Starting with Processor[v1] (sum algorithm)")
    
    # Prepare new version
    new_processor = DataProcessor("3.0", "v3")  # Median algorithm
    
    # Start gradual rollout at 20%
    print("\n>> Starting gradual rollout of v3 at 20%...")
    await pipeline.swap(1, new_processor, SwapStrategy.GRADUAL, 20.0)
    
    # Process requests and show distribution
    v1_count = 0
    v3_count = 0
    
    for i in range(50):
        data = {"data": [i, i+1, i+2, i+3, i+4]}  # Predictable data
        result = await pipeline.invoke(data)
        
        if "v1" in result["processor"]:
            v1_count += 1
        else:
            v3_count += 1
    
    print(f"Distribution: v1={v1_count}, v3={v3_count} ({v3_count/50*100:.0f}% on v3)")
    
    # Increase rollout
    print("\n>> Increasing rollout to 50%...")
    await pipeline.adjust_rollout(1, 50.0)
    
    v1_count = 0
    v3_count = 0
    
    for i in range(50):
        data = {"data": [i, i+1, i+2, i+3, i+4]}
        result = await pipeline.invoke(data)
        
        if "v1" in result["processor"]:
            v1_count += 1
        else:
            v3_count += 1
    
    print(f"Distribution: v1={v1_count}, v3={v3_count} ({v3_count/50*100:.0f}% on v3)")
    
    # Complete the rollout
    print("\n>> Completing rollout to 100%...")
    await pipeline.complete_swap(1)
    
    # Verify all traffic goes to v3
    result = await pipeline.invoke({"data": [1, 2, 3, 4, 5]})
    print(f"Final processor: {result['processor']}")


async def example_canary_deployment():
    """Example: Canary deployment with automatic promotion/rollback."""
    print("\n=== Canary Deployment Example ===")
    
    # Scenario 1: Successful canary
    print("\nScenario 1: Deploying stable v2")
    
    pipeline = SwappablePipeline([
        DataValidator(strict=False),
        DataProcessor("1.0", "v1")
    ])
    
    controller = CanaryController(
        pipeline,
        position=1,
        success_threshold=0.8,
        sample_size=20,
        rollout_increments=[5, 25, 50, 100]
    )
    
    # Deploy v2 as canary
    new_processor = DataProcessor("2.0", "v2")
    
    async def monitor_success(result):
        # Monitor function - v2 is stable
        return "error" not in str(result)
    
    await controller.start_canary(new_processor, monitor_success)
    print("Started canary deployment of v2 at 5%")
    
    # Simulate traffic
    for i in range(100):
        data = {"data": [random.randint(1, 10) for _ in range(5)]}
        try:
            result = await pipeline.invoke(data)
            controller.record_result(True)
            
            # Show progress
            if i % 20 == 19:
                status = pipeline.get_status()
                rollout = status["components"][1]["rollout_percent"]
                print(f"  After {i+1} requests: {rollout}% on v2")
        except:
            controller.record_result(False)
        
        await asyncio.sleep(0.02)
    
    # Scenario 2: Failed canary
    print("\n\nScenario 2: Deploying buggy version")
    
    pipeline2 = SwappablePipeline([
        DataValidator(strict=False),
        DataProcessor("1.0", "v1")
    ])
    
    controller2 = CanaryController(
        pipeline2,
        position=1,
        success_threshold=0.8,
        sample_size=20
    )
    
    # Deploy buggy version
    buggy_processor = DataProcessor("buggy", "buggy")
    await controller2.start_canary(buggy_processor, monitor_success)
    print("Started canary deployment of buggy version at 5%")
    
    # Simulate traffic
    successes = 0
    failures = 0
    
    for i in range(30):
        data = {"data": [random.randint(1, 10) for _ in range(5)]}
        try:
            result = await pipeline2.invoke(data)
            controller2.record_result(True)
            successes += 1
        except:
            controller2.record_result(False)
            failures += 1
        
        await asyncio.sleep(0.02)
    
    print(f"  Results: {successes} successes, {failures} failures")
    
    # Check if rollback happened
    await asyncio.sleep(1.5)  # Wait for controller to process
    status = pipeline2.get_status()
    if status["components"][1]["new_brick"] is None:
        print("  ✓ Canary automatically rolled back due to high error rate!")
    else:
        print("  ✗ Canary still active")


async def example_blue_green_deployment():
    """Example: Blue-green deployment pattern."""
    print("\n=== Blue-Green Deployment Example ===")
    
    # Create pipeline
    pipeline = SwappablePipeline([
        DataValidator(strict=False),
        DataProcessor("1.0", "v1")  # Blue
    ])
    
    print("Blue environment: Processor[v1]")
    
    # Prepare green environment
    green_processor = DataProcessor("2.0", "v2")
    
    # Stage green environment (0% traffic)
    print("\n>> Staging green environment (v2) with 0% traffic...")
    await pipeline.swap(1, green_processor, SwapStrategy.BLUE_GREEN)
    
    # Run validation tests on green
    print(">> Running validation tests on green environment...")
    test_data = [
        {"data": [1, 2, 3, 4, 5]},
        {"data": [10, 20, 30]},
        {"data": []}
    ]
    
    all_passed = True
    for test in test_data:
        try:
            # Directly test the new processor
            result = await green_processor.invoke(test)
            print(f"  Test passed: {test['data']} -> {result.get('result', 'N/A')}")
        except Exception as e:
            print(f"  Test failed: {test['data']} -> {e}")
            all_passed = False
    
    if all_passed:
        print("\n>> All tests passed! Switching to green...")
        await pipeline.complete_swap(1)
        print(">> Blue-green swap completed!")
    else:
        print("\n>> Tests failed! Rolling back...")
        await pipeline.rollback(1)
        print(">> Rollback completed!")
    
    # Verify final state
    result = await pipeline.invoke({"data": [1, 2, 3]})
    print(f"\nFinal processor: {result['processor']}")


async def example_monitoring_and_history():
    """Example: Monitoring swaps and viewing history."""
    print("\n=== Monitoring and History Example ===")
    
    # Create pipeline
    pipeline = SwappablePipeline([
        DataValidator(strict=False),
        DataProcessor("1.0", "v1")
    ])
    
    # Perform multiple swaps
    versions = [
        ("2.0", "v2", SwapStrategy.IMMEDIATE),
        ("3.0", "v3", SwapStrategy.GRADUAL),
        ("1.1", "v1", SwapStrategy.CANARY)  # Rollback to v1
    ]
    
    print("Performing multiple swaps...")
    for version, algorithm, strategy in versions:
        processor = DataProcessor(version, algorithm)
        success = await pipeline.swap(1, processor, strategy, 30.0)
        print(f"  Swap to {algorithm}@{version} ({strategy.value}): {'✓' if success else '✗'}")
        await asyncio.sleep(0.1)
    
    # Show history
    print("\nSwap History:")
    history = pipeline.get_history()
    for record in history:
        status = "✓" if record.success else "✗"
        print(f"  {status} {record.timestamp.strftime('%H:%M:%S')} - "
              f"{record.old_brick} -> {record.new_brick} "
              f"({record.strategy.value} @ {record.rollout_percent}%)")
    
    # Show metrics
    print("\nPipeline Metrics:")
    status = pipeline.get_status()
    metrics = status["metrics"]
    for key, value in metrics.items():
        print(f"  {key}: {value}")
    
    # Show current configuration
    print("\nCurrent Configuration:")
    for i, component in enumerate(status["components"]):
        print(f"  Position {i}: {component['current_brick']}")
        if component['new_brick']:
            print(f"    -> Swapping to: {component['new_brick']} "
                  f"({component['rollout_percent']}%)")


async def main():
    """Run all hot-swap examples."""
    await example_immediate_swap()
    await example_gradual_rollout()
    await example_canary_deployment()
    await example_blue_green_deployment()
    await example_monitoring_and_history()


if __name__ == "__main__":
    asyncio.run(main())