"""Tests for AI reasoning components."""

from datetime import datetime, timedelta
from unittest.mock import Mock

import pytest

from nanobricks.agent import (
    AIMessage,
    AIRequest,
    AIResponse,
    ChainOfThought,
    CostTracker,
    Memory,
    MemoryManager,
    MemoryType,
    MessageRole,
    ModelCapability,
    ModelInfo,
    ModelScore,
    ModelSelector,
    ReasoningStep,
    ReasoningStepType,
    ReasoningTrace,
    ReasoningTracer,
    SimpleMemoryStore,
    TaskAnalyzer,
    TaskComplexity,
    TaskDomain,
    TaskRequirements,
    TokenUsage,
    WorkingMemory,
)


class TestAIInterface:
    """Test AI interface components."""

    def test_ai_message_creation(self):
        """Test creating AI messages."""
        msg = AIMessage(
            role=MessageRole.USER, content="Hello AI", metadata={"source": "test"}
        )

        assert msg.role == MessageRole.USER
        assert msg.content == "Hello AI"
        assert msg.metadata["source"] == "test"

        # Test to_dict
        data = msg.to_dict()
        assert data["role"] == "user"
        assert data["content"] == "Hello AI"

    def test_ai_request(self):
        """Test AI request functionality."""
        request = AIRequest(messages=[])

        # Add messages
        request.add_message(MessageRole.SYSTEM, "You are helpful")
        request.add_message(MessageRole.USER, "Hello")

        assert len(request.messages) == 2
        assert request.messages[0].role == MessageRole.SYSTEM
        assert request.messages[1].role == MessageRole.USER

        # Test conversation text
        text = request.get_conversation_text()
        assert "system: You are helpful" in text
        assert "user: Hello" in text

    def test_model_info(self):
        """Test model information."""
        model = ModelInfo(
            id="gpt-4",
            name="GPT-4",
            provider="openai",
            capabilities={ModelCapability.CHAT, ModelCapability.REASONING},
            context_window=8192,
            cost_per_1k_input=0.03,
            cost_per_1k_output=0.06,
        )

        assert model.supports_chat
        assert model.supports_reasoning
        assert not model.supports_vision

    def test_cost_tracker(self):
        """Test cost tracking."""
        tracker = CostTracker()

        # Create model
        model = ModelInfo(
            id="test-model",
            name="Test Model",
            provider="test",
            capabilities={ModelCapability.CHAT},
            context_window=4096,
            cost_per_1k_input=0.01,
            cost_per_1k_output=0.02,
        )

        # Track response
        response = AIResponse(
            content="Test response",
            usage={"prompt_tokens": 100, "completion_tokens": 50, "total_tokens": 150},
        )

        tracker.track_response(response, model)

        # Check tracking
        assert tracker.request_count == 1
        assert tracker.total_cost == pytest.approx(
            0.002
        )  # (100/1000)*0.01 + (50/1000)*0.02

        summary = tracker.get_summary()
        assert summary["request_count"] == 1
        assert summary["total_cost"] == pytest.approx(0.002)


class TestReasoning:
    """Test reasoning trace components."""

    def test_reasoning_step(self):
        """Test reasoning step creation."""
        step = ReasoningStep(
            type=ReasoningStepType.OBSERVATION,
            content="The data shows a pattern",
            confidence=0.8,
        )

        step.add_evidence("Supporting data point 1")
        step.add_alternative("Could be random variation")

        assert step.type == ReasoningStepType.OBSERVATION
        assert len(step.evidence) == 1
        assert len(step.alternatives) == 1

    def test_reasoning_trace(self):
        """Test reasoning trace functionality."""
        trace = ReasoningTrace(problem="Solve X")

        # Add steps
        obs = trace.observe("Initial observation", 0.9)
        hyp = trace.hypothesize("Possible solution", 0.7)
        analysis = trace.analyze("Detailed analysis", 0.85)

        assert len(trace.steps) == 3
        assert trace.steps[0].type == ReasoningStepType.OBSERVATION
        assert trace.steps[1].type == ReasoningStepType.HYPOTHESIS
        assert trace.steps[2].type == ReasoningStepType.ANALYSIS

        # Test confidence range
        min_conf, max_conf = trace.get_confidence_range()
        assert min_conf == 0.7
        assert max_conf == 0.9

        # Test conclusion
        trace.conclude("Final answer", 0.95)
        assert trace.conclusion == "Final answer"
        assert trace.confidence == 0.95
        assert trace.completed is not None

    def test_reasoning_tracer(self):
        """Test reasoning tracer."""
        tracer = ReasoningTracer()

        # Start trace
        trace1 = tracer.start_trace("Problem 1")
        assert tracer.get_active_trace() == trace1

        # Start another trace
        trace2 = tracer.start_trace("Problem 2")
        assert tracer.get_active_trace() == trace2

        # List traces
        traces = tracer.list_traces()
        assert len(traces) == 2

        # Get specific trace
        retrieved = tracer.get_trace(trace1.id)
        assert retrieved == trace1

    def test_chain_of_thought(self):
        """Test chain of thought utilities."""
        # Test prompt formatting
        prompt = ChainOfThought.format_cot_prompt(
            "What is 2+2?", [("What is 1+1?", "1+1=2")]
        )

        assert "What is 2+2?" in prompt
        assert "1+1=2" in prompt
        assert "step by step" in prompt

        # Test step extraction
        text = """
        1. First, I observe the numbers
        2. Then, I add them together
        3. Finally, I get the result
        """

        steps = ChainOfThought.extract_steps_from_text(text)
        assert len(steps) == 3
        assert "observe" in steps[0]
        assert "add" in steps[1]
        assert "result" in steps[2]


class TestMemory:
    """Test memory management components."""

    def test_memory_creation(self):
        """Test memory creation and relevance."""
        memory = Memory(
            content="Important fact", type=MemoryType.LONG_TERM, importance=0.8
        )

        memory.add_tag("fact")
        memory.add_tag("important")

        assert memory.has_tag("fact")
        assert memory.has_tag("important")
        assert not memory.has_tag("trivial")

        # Test relevance
        relevance = memory.get_relevance()
        assert 0.0 <= relevance <= 1.0

        # Access should increase count
        memory.access()
        assert memory.access_count == 1

    def test_simple_memory_store(self):
        """Test simple memory store."""
        store = SimpleMemoryStore(max_size=3)

        # Store memories
        mem1 = Memory(content="Fact 1", tags={"test"})
        mem2 = Memory(content="Fact 2", tags={"test"})
        mem3 = Memory(content="Important fact", tags={"important"})

        store.store(mem1)
        store.store(mem2)
        store.store(mem3)

        # Retrieve
        retrieved = store.retrieve(mem1.id)
        assert retrieved == mem1
        assert retrieved.access_count == 1

        # Search
        results = store.search("fact")
        assert len(results) == 3

        results = store.search("important")
        assert len(results) == 1
        assert results[0] == mem3

        # Test eviction
        mem4 = Memory(content="Fact 4")
        store.store(mem4)
        assert len(store.memories) == 3

    def test_working_memory(self):
        """Test working memory."""
        wm = WorkingMemory(capacity=3)

        # Add memories
        mem1 = Memory(content="Current task", importance=0.9)
        mem2 = Memory(content="Context info", importance=0.5)
        mem3 = Memory(content="Previous result", importance=0.7)

        wm.add(mem1)
        wm.add(mem2)
        wm.add(mem3)

        # Check capacity
        mem4 = Memory(content="New info", importance=0.3)
        wm.add(mem4)  # Should not be added (lower priority)

        assert len(wm.get_all()) == 3
        assert not wm.contains(mem4.id)

        # Test context
        context = wm.to_context()
        assert "Current task" in context
        assert "Context info" in context

    def test_memory_manager(self):
        """Test memory manager."""
        manager = MemoryManager(
            short_term_size=10, long_term_size=100, working_capacity=5
        )

        # Remember different types
        st_mem = manager.remember("Short term fact", memory_type=MemoryType.SHORT_TERM)
        lt_mem = manager.remember(
            "Long term knowledge", memory_type=MemoryType.LONG_TERM
        )
        ep_mem = manager.remember("Episode event", memory_type=MemoryType.EPISODIC)

        # Recall
        assert manager.recall(st_mem.id) == st_mem
        assert manager.recall(lt_mem.id) == lt_mem
        assert manager.recall(ep_mem.id) == ep_mem

        # Search
        results = manager.search("fact")
        assert len(results) == 1
        assert results[0] == st_mem

        # Consolidation
        st_mem.importance = 0.9
        consolidated = manager.consolidate(threshold=0.8)
        assert consolidated == 1

        # Should now be in long-term
        assert st_mem.id not in manager.short_term.memories
        assert st_mem.id in manager.long_term.memories


class TestModelSelection:
    """Test model selection components."""

    def test_task_requirements(self):
        """Test task requirements."""
        req = TaskRequirements(
            complexity=TaskComplexity.COMPLEX,
            domain=TaskDomain.CODING,
            capabilities_needed={ModelCapability.CODE_GENERATION},
        )

        assert not req.requires_vision()
        assert not req.requires_functions()
        assert req.requires_reasoning()  # Complex tasks need reasoning

    def test_model_selector(self):
        """Test model selection."""
        # Create test models
        models = [
            ModelInfo(
                id="small",
                name="Small Model",
                provider="test",
                capabilities={ModelCapability.CHAT},
                context_window=4096,
                cost_per_1k_input=0.001,
                cost_per_1k_output=0.002,
            ),
            ModelInfo(
                id="medium",
                name="Medium Model",
                provider="test",
                capabilities={ModelCapability.CHAT, ModelCapability.CODE_GENERATION},
                context_window=16384,
                cost_per_1k_input=0.01,
                cost_per_1k_output=0.02,
            ),
            ModelInfo(
                id="large",
                name="Large Model",
                provider="test",
                capabilities={
                    ModelCapability.CHAT,
                    ModelCapability.CODE_GENERATION,
                    ModelCapability.REASONING,
                },
                context_window=100000,
                cost_per_1k_input=0.03,
                cost_per_1k_output=0.06,
            ),
        ]

        selector = ModelSelector(models)

        # Test simple task
        simple_req = TaskRequirements(
            complexity=TaskComplexity.SIMPLE, cost_sensitivity=0.8
        )
        selected = selector.select_model(simple_req)
        assert selected.id == "small"  # Cheapest for simple tasks

        # Test coding task
        coding_req = TaskRequirements(
            complexity=TaskComplexity.MODERATE,
            domain=TaskDomain.CODING,
            capabilities_needed={ModelCapability.CODE_GENERATION},
        )
        selected = selector.select_model(coding_req)
        assert selected.id in ["medium", "large"]  # Both support code generation

        # Test complex reasoning task
        complex_req = TaskRequirements(
            complexity=TaskComplexity.EXPERT,
            capabilities_needed={ModelCapability.REASONING},
            cost_sensitivity=0.2,  # Quality over cost
        )
        selected = selector.select_model(complex_req)
        assert selected.id == "large"  # Only one with reasoning

    def test_task_analyzer(self):
        """Test task analysis."""
        # Simple request
        simple_request = AIRequest(
            messages=[AIMessage(MessageRole.USER, "Hello, how are you?")]
        )

        req = TaskAnalyzer.analyze_request(simple_request)
        assert req.complexity == TaskComplexity.SIMPLE

        # Code request
        code_request = AIRequest(
            messages=[
                AIMessage(MessageRole.USER, "Write a function def calculate_sum(a, b):")
            ]
        )

        req = TaskAnalyzer.analyze_request(code_request)
        assert req.domain == TaskDomain.CODING
        assert ModelCapability.CODE_GENERATION in req.capabilities_needed

        # Reasoning request
        reasoning_request = AIRequest(
            messages=[
                AIMessage(
                    MessageRole.USER, "Think step by step about why the sky is blue"
                )
            ]
        )

        req = TaskAnalyzer.analyze_request(reasoning_request)
        assert ModelCapability.REASONING in req.capabilities_needed
        assert req.reasoning_depth > 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
