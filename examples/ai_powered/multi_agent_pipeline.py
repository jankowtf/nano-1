"""Example of a multi-agent pipeline using nanobricks."""

import asyncio
from typing import Any, Dict, List

from nanobricks import NanobrickBase
from nanobricks.agent import Agent, create_agent
from nanobricks.adaptive import create_adaptive_brick
from nanobricks.adaptive.policies import ThresholdPolicy


class DataAnalyzer(NanobrickBase[Dict[str, Any], Dict[str, Any], None]):
    """Analyzes data and extracts insights."""
    
    async def invoke(
        self, input: Dict[str, Any], *, deps: None = None
    ) -> Dict[str, Any]:
        """Analyze data."""
        # Simulate analysis
        await asyncio.sleep(0.1)
        
        return {
            "original": input,
            "insights": {
                "total_fields": len(input),
                "has_nulls": any(v is None for v in input.values()),
                "field_types": {k: type(v).__name__ for k, v in input.items()},
            },
            "recommendations": [
                "Consider adding validation",
                "Check for missing required fields",
            ],
        }


class DataEnricher(NanobrickBase[Dict[str, Any], Dict[str, Any], None]):
    """Enriches data with additional information."""
    
    async def invoke(
        self, input: Dict[str, Any], *, deps: None = None
    ) -> Dict[str, Any]:
        """Enrich data."""
        # Simulate enrichment
        await asyncio.sleep(0.05)
        
        enriched = input.copy()
        
        # Add metadata
        enriched["_metadata"] = {
            "enriched_at": "2024-01-01T12:00:00Z",
            "enrichment_version": "1.0",
            "quality_score": 0.85,
        }
        
        # Add computed fields
        if "insights" in enriched:
            enriched["insights"]["quality_assessment"] = "good"
        
        return enriched


class DataValidator(NanobrickBase[Dict[str, Any], Dict[str, Any], None]):
    """Validates data against rules."""
    
    async def invoke(
        self, input: Dict[str, Any], *, deps: None = None
    ) -> Dict[str, Any]:
        """Validate data."""
        errors = []
        warnings = []
        
        # Check required fields
        required = ["original", "insights", "_metadata"]
        for field in required:
            if field not in input:
                errors.append(f"Missing required field: {field}")
        
        # Check data quality
        if input.get("_metadata", {}).get("quality_score", 0) < 0.5:
            warnings.append("Low quality score")
        
        return {
            "data": input,
            "validation": {
                "valid": len(errors) == 0,
                "errors": errors,
                "warnings": warnings,
            },
        }


async def multi_agent_demo():
    """Demonstrate multi-agent pipeline."""
    print("Multi-Agent Pipeline Demo")
    print("=" * 50)
    
    # Create nanobricks
    analyzer = DataAnalyzer(name="analyzer")
    enricher = DataEnricher(name="enricher")
    validator = DataValidator(name="validator")
    
    # Make them adaptive
    adaptive_analyzer = create_adaptive_brick(
        analyzer,
        policy=ThresholdPolicy(latency_threshold_ms=200),
    )
    
    adaptive_enricher = create_adaptive_brick(
        enricher,
        policy=ThresholdPolicy(latency_threshold_ms=100),
    )
    
    # Create agents
    print("\n1. Creating Agents:")
    
    analyzer_agent = create_agent(
        adaptive_analyzer,
        name="Data Analysis Agent",
        capabilities=["analysis", "insights"],
    )
    print(f"   - {analyzer_agent.name} (ID: {analyzer_agent.id})")
    
    enricher_agent = create_agent(
        adaptive_enricher,
        name="Data Enrichment Agent",
        capabilities=["enrichment", "metadata"],
    )
    print(f"   - {enricher_agent.name} (ID: {enricher_agent.id})")
    
    validator_agent = create_agent(
        validator,
        name="Data Validation Agent",
        capabilities=["validation", "quality-check"],
    )
    print(f"   - {validator_agent.name} (ID: {validator_agent.id})")
    
    # Start request handlers
    handler_tasks = [
        asyncio.create_task(analyzer_agent.handle_requests()),
        asyncio.create_task(enricher_agent.handle_requests()),
        asyncio.create_task(validator_agent.handle_requests()),
    ]
    
    # Wait for agents to register
    await asyncio.sleep(0.5)
    
    # Discover agents
    print("\n2. Agent Discovery:")
    discovered = await analyzer_agent.discover_agents()
    for agent in discovered:
        print(f"   - {agent['name']}: {agent['capabilities']}")
    
    # Create coordinator agent
    class CoordinatorBrick(NanobrickBase[Dict[str, Any], Dict[str, Any], None]):
        """Coordinates the multi-agent pipeline."""
        
        def __init__(self, agents: Dict[str, str]):
            super().__init__(name="coordinator", version="1.0.0")
            self.agents = agents  # role -> agent_id mapping
        
        async def invoke(
            self, input: Dict[str, Any], *, deps: None = None
        ) -> Dict[str, Any]:
            """Coordinate pipeline execution."""
            # This brick doesn't process data itself
            # It just coordinates other agents
            return input
    
    coordinator_brick = CoordinatorBrick({
        "analyzer": analyzer_agent.id,
        "enricher": enricher_agent.id,
        "validator": validator_agent.id,
    })
    
    coordinator = create_agent(
        coordinator_brick,
        name="Pipeline Coordinator",
        capabilities=["coordination", "orchestration"],
    )
    
    # Test data
    test_data = [
        {"user_id": 123, "name": "Alice", "score": 85},
        {"user_id": 456, "name": "Bob", "age": 30},
        {"product": "Widget", "price": 29.99, "quantity": 100},
    ]
    
    print("\n3. Processing Data Through Multi-Agent Pipeline:")
    
    for i, data in enumerate(test_data, 1):
        print(f"\n   Test {i}: {data}")
        
        try:
            # Step 1: Analysis
            print("   → Sending to Analyzer Agent...")
            analysis_result = await coordinator.request_processing(
                analyzer_agent.id, data, timeout=5.0
            )
            print(f"   ← Analysis complete: {len(analysis_result.get('insights', {}))} insights")
            
            # Step 2: Enrichment
            print("   → Sending to Enricher Agent...")
            enriched_result = await coordinator.request_processing(
                enricher_agent.id, analysis_result, timeout=5.0
            )
            print(f"   ← Enrichment complete: quality_score = {enriched_result.get('_metadata', {}).get('quality_score', 0)}")
            
            # Step 3: Validation
            print("   → Sending to Validator Agent...")
            validated_result = await coordinator.request_processing(
                validator_agent.id, enriched_result, timeout=5.0
            )
            
            validation = validated_result.get("validation", {})
            print(f"   ← Validation complete: valid = {validation.get('valid')}")
            
            if validation.get("errors"):
                print(f"      Errors: {validation['errors']}")
            if validation.get("warnings"):
                print(f"      Warnings: {validation['warnings']}")
            
        except Exception as e:
            print(f"   ✗ Pipeline failed: {e}")
    
    # Show adaptive performance
    print("\n4. Adaptive Performance Metrics:")
    
    print(f"\n   Analyzer Agent:")
    analyzer_metrics = adaptive_analyzer.get_metrics_summary()
    print(f"   - Invocations: {analyzer_metrics.get('total_invocations', 0)}")
    print(f"   - Success Rate: {analyzer_metrics.get('success_rate', 0):.2%}")
    print(f"   - Avg Latency: {analyzer_metrics.get('avg_latency_ms', 0):.1f}ms")
    
    print(f"\n   Enricher Agent:")
    enricher_metrics = adaptive_enricher.get_metrics_summary()
    print(f"   - Invocations: {enricher_metrics.get('total_invocations', 0)}")
    print(f"   - Success Rate: {enricher_metrics.get('success_rate', 0):.2%}")
    print(f"   - Avg Latency: {enricher_metrics.get('avg_latency_ms', 0):.1f}ms")
    
    # Broadcast shutdown
    print("\n5. Shutting down agents...")
    await coordinator.broadcast("shutdown", {"reason": "demo complete"})
    
    # Cancel handler tasks
    for task in handler_tasks:
        task.cancel()
    
    # Shutdown agents
    await analyzer_agent.shutdown()
    await enricher_agent.shutdown()
    await validator_agent.shutdown()
    await coordinator.shutdown()
    
    print("\nMulti-agent pipeline demo complete!")


if __name__ == "__main__":
    asyncio.run(multi_agent_demo())