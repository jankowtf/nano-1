"""Examples demonstrating AI reasoning features with nanobricks."""

import asyncio
from typing import Any, Dict, List

from nanobricks import NanobrickBase
from nanobricks.agent import (
    AIMessage,
    AIRequest,
    AIResponse,
    ChainOfThought,
    CostTracker,
    MemoryManager,
    MemoryType,
    MessageRole,
    ModelCapability,
    ModelInfo,
    ModelSelector,
    ReasoningTracer,
    TaskAnalyzer,
    TaskComplexity,
)


class ReasoningProcessor(NanobrickBase[Dict[str, Any], Dict[str, Any], None]):
    """A nanobrick that processes requests with reasoning traces."""
    
    def __init__(self):
        """Initialize processor."""
        self.name = "reasoning_processor"
        self.version = "1.0.0"
        self.tracer = ReasoningTracer()
        self.memory = MemoryManager()
        self.cost_tracker = CostTracker()
    
    async def invoke(self, input: Dict[str, Any], *, deps: None = None) -> Dict[str, Any]:
        """Process input with reasoning."""
        problem = input.get("problem", "")
        
        # Start reasoning trace
        trace = self.tracer.start_trace(problem)
        
        # Add to working memory
        self.memory.working.add(
            self.memory.remember(
                f"Current problem: {problem}",
                memory_type=MemoryType.WORKING
            )
        )
        
        # Reasoning steps
        trace.observe("Analyzing the problem statement")
        trace.hypothesize("This might require multi-step reasoning")
        trace.analyze("Breaking down into sub-problems")
        
        # Search relevant memories
        relevant = self.memory.search(problem[:20])
        if relevant:
            trace.observe(f"Found {len(relevant)} relevant memories")
        
        # Conclude
        trace.conclude("Problem analyzed and ready for processing", 0.85)
        
        return {
            "problem": problem,
            "trace_id": trace.id,
            "reasoning_steps": len(trace.steps),
            "confidence": trace.confidence,
            "memory_context": self.memory.get_context()
        }
    
    def invoke_sync(self, input: Dict[str, Any], *, deps: None = None) -> Dict[str, Any]:
        """Sync version."""
        return asyncio.run(self.invoke(input, deps=deps))


async def example_basic_reasoning():
    """Example: Basic reasoning trace."""
    print("\n=== Basic Reasoning Example ===")
    
    processor = ReasoningProcessor()
    
    # Process a problem
    result = await processor.invoke({
        "problem": "How can we optimize database queries for better performance?"
    })
    
    print(f"Trace ID: {result['trace_id']}")
    print(f"Steps taken: {result['reasoning_steps']}")
    print(f"Confidence: {result['confidence']:.0%}")
    
    # Get the trace
    trace = processor.tracer.get_trace(result['trace_id'])
    print("\nReasoning steps:")
    for i, step in enumerate(trace.steps, 1):
        print(f"{i}. [{step.type.value}] {step.content}")


async def example_chain_of_thought():
    """Example: Chain of thought reasoning."""
    print("\n=== Chain of Thought Example ===")
    
    # Format a CoT prompt
    problem = "Calculate the total cost if we have 3 items at $12.50 each with 8% tax"
    
    prompt = ChainOfThought.format_cot_prompt(
        problem,
        examples=[
            ("What is 2 items at $10 each?", "2 × $10 = $20 total"),
            ("Add 5% tax to $100", "$100 × 0.05 = $5 tax, total = $105")
        ]
    )
    
    print("Generated prompt:")
    print(prompt)
    
    # Simulate AI response
    ai_response = """
    Let me solve this step by step:
    
    1. First, I'll calculate the base cost: 3 items × $12.50 = $37.50
    
    2. Next, I'll calculate the tax amount: $37.50 × 0.08 = $3.00
    
    3. Finally, I'll add the tax to get the total: $37.50 + $3.00 = $40.50
    
    Therefore, the total cost is $40.50.
    """
    
    # Extract reasoning trace
    trace = ChainOfThought.create_trace_from_text(problem, ai_response)
    
    print(f"\nExtracted {len(trace.steps)} reasoning steps")
    print("\nReasoning trace as markdown:")
    print(trace.to_markdown())


async def example_memory_management():
    """Example: Memory management for AI agents."""
    print("\n=== Memory Management Example ===")
    
    memory = MemoryManager(
        short_term_size=50,
        long_term_size=500,
        working_capacity=5
    )
    
    # Add various memories
    memory.remember(
        "User prefers concise answers",
        importance=0.9,
        memory_type=MemoryType.LONG_TERM,
        tags={"preference", "user"}
    )
    
    memory.remember(
        "Previous query was about Python",
        importance=0.6,
        memory_type=MemoryType.SHORT_TERM,
        tags={"context", "python"}
    )
    
    memory.remember(
        "User is working on a web application",
        importance=0.8,
        memory_type=MemoryType.SHORT_TERM,
        tags={"project", "web"}
    )
    
    # Working memory for current task
    memory.remember(
        "Current task: Explain async/await",
        importance=1.0,
        memory_type=MemoryType.WORKING
    )
    
    # Search memories
    python_memories = memory.search("Python")
    print(f"Found {len(python_memories)} Python-related memories")
    
    # Consolidate important short-term to long-term
    consolidated = memory.consolidate(threshold=0.7)
    print(f"Consolidated {consolidated} memories to long-term")
    
    # Get context
    context = memory.get_context()
    print("\nCurrent memory context:")
    print(f"- Working memory: {context['working_memory']}")
    print(f"- Short-term memories: {context['short_term_count']}")
    print(f"- Long-term memories: {context['long_term_count']}")
    
    # Create episodic memory
    episode = memory.create_episode(
        "Helped user with Python async programming",
        python_memories
    )
    print(f"\nCreated episode: {episode.content['description']}")


async def example_model_selection():
    """Example: Intelligent model selection."""
    print("\n=== Model Selection Example ===")
    
    # Define available models
    models = [
        ModelInfo(
            id="fast-chat",
            name="Fast Chat Model",
            provider="provider1",
            capabilities={ModelCapability.CHAT},
            context_window=4096,
            cost_per_1k_input=0.0005,
            cost_per_1k_output=0.001,
        ),
        ModelInfo(
            id="smart-coder",
            name="Smart Coding Model",
            provider="provider2",
            capabilities={ModelCapability.CHAT, ModelCapability.CODE_GENERATION},
            context_window=16384,
            cost_per_1k_input=0.01,
            cost_per_1k_output=0.02,
        ),
        ModelInfo(
            id="reasoning-pro",
            name="Advanced Reasoning Model",
            provider="provider3",
            capabilities={
                ModelCapability.CHAT,
                ModelCapability.REASONING,
                ModelCapability.FUNCTION_CALLING
            },
            context_window=128000,
            cost_per_1k_input=0.03,
            cost_per_1k_output=0.06,
        ),
    ]
    
    selector = ModelSelector(models)
    
    # Example 1: Simple chat
    print("\n1. Simple chat request:")
    simple_request = AIRequest(messages=[
        AIMessage(MessageRole.USER, "Hello, how are you?")
    ])
    
    requirements = TaskAnalyzer.analyze_request(simple_request)
    selected = selector.select_model(requirements)
    print(f"   Selected: {selected.name}")
    print(f"   Reason: {requirements.complexity.value} task")
    
    # Example 2: Code generation
    print("\n2. Code generation request:")
    code_request = AIRequest(messages=[
        AIMessage(MessageRole.USER, "Write a Python function to sort a list")
    ])
    
    requirements = TaskAnalyzer.analyze_request(code_request)
    selected = selector.select_model(requirements)
    print(f"   Selected: {selected.name}")
    print(f"   Capabilities: {[c.value for c in selected.capabilities]}")
    
    # Example 3: Complex reasoning
    print("\n3. Complex reasoning request:")
    reasoning_request = AIRequest(messages=[
        AIMessage(MessageRole.SYSTEM, "You are a helpful assistant"),
        AIMessage(MessageRole.USER, "Analyze the economic impacts of AI step by step"),
        AIMessage(MessageRole.ASSISTANT, "I'll analyze this systematically..."),
        AIMessage(MessageRole.USER, "Continue with specific examples")
    ])
    
    requirements = TaskAnalyzer.analyze_request(reasoning_request)
    requirements.cost_sensitivity = 0.2  # Prioritize quality
    
    # Get rankings
    rankings = selector.rank_models(requirements)
    print(f"   Model rankings:")
    for i, score in enumerate(rankings, 1):
        print(f"   {i}. {score.model.name} (score: {score.overall_score:.3f})")
        for reason in score.reasons[:2]:
            print(f"      - {reason}")


async def example_cost_tracking():
    """Example: Track AI usage costs."""
    print("\n=== Cost Tracking Example ===")
    
    tracker = CostTracker()
    
    # Define a model
    model = ModelInfo(
        id="gpt-4",
        name="GPT-4",
        provider="openai",
        capabilities={ModelCapability.CHAT, ModelCapability.REASONING},
        context_window=8192,
        cost_per_1k_input=0.03,
        cost_per_1k_output=0.06
    )
    
    # Simulate multiple responses
    responses = [
        AIResponse(
            content="First response",
            usage={"prompt_tokens": 150, "completion_tokens": 200, "total_tokens": 350}
        ),
        AIResponse(
            content="Second response",
            usage={"prompt_tokens": 300, "completion_tokens": 450, "total_tokens": 750}
        ),
        AIResponse(
            content="Third response",
            usage={"prompt_tokens": 500, "completion_tokens": 800, "total_tokens": 1300}
        ),
    ]
    
    # Track each response
    for response in responses:
        tracker.track_response(response, model)
    
    # Get summary
    summary = tracker.get_summary()
    print(f"Total requests: {summary['request_count']}")
    print(f"Total cost: ${summary['total_cost']:.4f}")
    
    print("\nUsage by model:")
    for model_id, usage in summary['usage_by_model'].items():
        print(f"  {model_id}:")
        print(f"    - Prompt tokens: {usage['prompt_tokens']:,}")
        print(f"    - Completion tokens: {usage['completion_tokens']:,}")
        print(f"    - Total tokens: {usage['total_tokens']:,}")


async def example_integrated_ai_reasoning():
    """Example: Integrated AI reasoning system."""
    print("\n=== Integrated AI Reasoning System ===")
    
    class AIReasoningSystem(NanobrickBase[AIRequest, Dict[str, Any], None]):
        """Complete AI reasoning system."""
        
        def __init__(self):
            self.name = "ai_reasoning_system"
            self.version = "1.0.0"
            self.memory = MemoryManager()
            self.tracer = ReasoningTracer()
            self.cost_tracker = CostTracker()
            self.model_selector = ModelSelector([
                ModelInfo(
                    id="fast",
                    name="Fast Model",
                    provider="test",
                    capabilities={ModelCapability.CHAT},
                    context_window=4096,
                    cost_per_1k_input=0.001,
                    cost_per_1k_output=0.002
                ),
                ModelInfo(
                    id="smart",
                    name="Smart Model",
                    provider="test",
                    capabilities={ModelCapability.CHAT, ModelCapability.REASONING},
                    context_window=32768,
                    cost_per_1k_input=0.01,
                    cost_per_1k_output=0.02
                )
            ])
        
        async def invoke(self, input: AIRequest, *, deps: None = None) -> Dict[str, Any]:
            """Process AI request with full reasoning."""
            # Analyze task
            requirements = TaskAnalyzer.analyze_request(input)
            
            # Add to working memory
            self.memory.remember(
                f"Processing: {input.messages[-1].content[:50]}...",
                memory_type=MemoryType.WORKING
            )
            
            # Select model
            model = self.model_selector.select_model(requirements, input)
            
            # Start reasoning trace
            trace = self.tracer.start_trace(
                f"AI Request: {requirements.domain.value} task"
            )
            
            trace.observe(f"Selected model: {model.name}")
            trace.analyze(f"Complexity: {requirements.complexity.value}")
            
            # Search relevant memories
            if input.messages:
                query = input.messages[-1].content[:30]
                memories = self.memory.search(query)
                if memories:
                    trace.observe(f"Found {len(memories)} relevant memories")
            
            # Simulate response
            response = AIResponse(
                content="Simulated AI response based on reasoning",
                model=model.id,
                usage={
                    "prompt_tokens": len(str(input.messages)) * 2,
                    "completion_tokens": 150,
                    "total_tokens": len(str(input.messages)) * 2 + 150
                }
            )
            
            # Track cost
            self.cost_tracker.track_response(response, model)
            
            # Complete reasoning
            trace.conclude(
                f"Successfully processed {requirements.domain.value} request",
                0.9
            )
            
            # Store in memory
            self.memory.remember(
                f"Completed: {response.content[:50]}...",
                importance=0.7,
                memory_type=MemoryType.SHORT_TERM,
                tags={requirements.domain.value, model.id}
            )
            
            return {
                "response": response.content,
                "model_used": model.name,
                "reasoning_trace": trace.get_summary(),
                "cost": self.cost_tracker.total_cost,
                "memory_stats": self.memory.get_context()
            }
        
        def invoke_sync(self, input: AIRequest, *, deps: None = None) -> Dict[str, Any]:
            return asyncio.run(self.invoke(input, deps=deps))
    
    # Use the system
    system = AIReasoningSystem()
    
    # Process different requests
    requests = [
        AIRequest(messages=[
            AIMessage(MessageRole.USER, "What's the weather like?")
        ]),
        AIRequest(messages=[
            AIMessage(MessageRole.USER, "Explain quantum computing step by step")
        ]),
        AIRequest(messages=[
            AIMessage(MessageRole.USER, "Write a function to calculate fibonacci")
        ])
    ]
    
    for i, request in enumerate(requests, 1):
        print(f"\nRequest {i}: {request.messages[0].content}")
        result = await system.invoke(request)
        
        print(f"Model: {result['model_used']}")
        print(f"Cost so far: ${result['cost']:.4f}")
        print(f"Reasoning steps: {result['reasoning_trace']['step_count']}")
        print(f"Memories: ST={result['memory_stats']['short_term_count']}, "
              f"LT={result['memory_stats']['long_term_count']}")


async def main():
    """Run all examples."""
    print("=== Nanobricks AI Reasoning Examples ===")
    
    await example_basic_reasoning()
    await example_chain_of_thought()
    await example_memory_management()
    await example_model_selection()
    await example_cost_tracking()
    await example_integrated_ai_reasoning()
    
    print("\n=== Examples Complete ===")


if __name__ == "__main__":
    asyncio.run(main())