"""Tests for AI integration features."""

import asyncio

import pytest

from nanobricks import NanobrickBase
from nanobricks.adaptive import AdaptiveBrick
from nanobricks.adaptive.policies import ThresholdPolicy
from nanobricks.agent import Agent, MessageType, create_agent
from nanobricks.skills import (
    MCPToolConfig,
    SkillAI,
    SkillMCP,
    create_ai_skill,
    create_mcp_server,
)


class SampleNanobrick(NanobrickBase[str, str, None]):
    """Sample brick for AI integration tests."""

    async def invoke(self, input: str, *, deps: None = None) -> str:
        return f"processed: {input}"


class TestAISkill:
    """Test AI reasoning skill."""

    def test_create_ai_skill(self):
        """Test creating AI skill."""
        skill = create_ai_skill(
            max_cost_per_invoke=0.05,
            enable_reasoning_trace=True,
            enable_memory=True,
        )

        assert isinstance(skill, SkillAI)
        assert skill.max_cost_per_invoke == 0.05
        assert skill.enable_reasoning_trace
        assert skill.enable_memory

    @pytest.mark.asyncio
    async def test_ai_enhancement(self):
        """Test AI enhancement of brick."""
        skill = create_ai_skill()
        brick = SampleBrick()

        # Enhance with AI
        ai_brick = brick.with_skill(skill)

        # Test invocation
        result = await ai_brick.invoke("test input")
        assert "processed:" in result

    def test_cost_tracking(self):
        """Test AI cost tracking."""
        skill = create_ai_skill(max_cost_per_invoke=0.10)

        # Initial cost should be zero
        report = skill.get_cost_report()
        assert report["total_cost"] == 0.0
        assert report["cost_limit"] == 0.10
        assert report["cost_remaining"] == 0.10

    def test_model_configuration(self):
        """Test model configuration."""
        skill = SkillAI(
            default_model="gpt-4o-mini",
            enable_reasoning_trace=False,
        )

        assert skill.default_model == "gpt-4o-mini"
        assert not skill.enable_reasoning_trace
        assert len(skill.models) > 0


class TestMCPIntegration:
    """Test MCP server integration."""

    def test_create_mcp_server(self):
        """Test creating MCP server."""
        brick1 = SampleBrick(name="test1")
        brick2 = SampleBrick(name="test2")

        skill = create_mcp_server(
            bricks=[brick1, brick2],
            server_name="test-server",
        )

        assert isinstance(skill, SkillMCP)
        assert skill.server_name == "test-server"
        assert len(skill._tools) == 2

    def test_tool_configuration(self):
        """Test MCP tool configuration."""
        brick = SampleBrick(name="calculator")
        config = MCPToolConfig(
            name="calc",
            description="Performs calculations",
            include_in_prompt=True,
            example_inputs=[{"input": "2 + 2"}],
        )

        skill = SkillMCP()
        skill.expose_tool(brick, config)

        assert "calc" in skill._tools
        assert skill._tools["calc"][1].description == "Performs calculations"

    @pytest.mark.asyncio
    async def test_mcp_client(self):
        """Test MCP client functionality."""
        from nanobricks.skills.mcp import MCPClient

        brick = SampleBrick(name="test_tool")
        skill = create_mcp_server([brick])
        client = MCPClient(skill)

        # List tools
        tools = await client.list_tools()
        assert len(tools) == 1
        assert tools[0]["name"] == "test_tool"

        # Invoke tool
        result = await client.invoke_tool("test_tool", {"input": "hello"})
        assert result == "processed: hello"

    def test_prompt_generation(self):
        """Test prompt generation for MCP tools."""
        brick = SampleBrick(name="analyzer")
        config = MCPToolConfig(
            include_in_prompt=True,
            example_inputs=[{"text": "analyze this"}],
        )

        skill = SkillMCP()
        skill.expose_tool(brick, config)

        prompts = skill.generate_prompts()
        assert len(prompts) == 1
        assert "analyzer" in prompts[0]["name"]
        assert "template" in prompts[0]


class TestAgentCommunication:
    """Test agent communication."""

    @pytest.mark.asyncio
    async def test_create_agent(self):
        """Test agent creation."""
        brick = SampleBrick()
        agent = create_agent(brick, name="Test Agent")

        assert isinstance(agent, Agent)
        assert agent.name == "Test Agent"
        assert agent.brick == brick
        assert "brick:SampleBrick" in agent.capabilities

        # Cleanup
        await agent.shutdown()

    @pytest.mark.asyncio
    async def test_agent_messaging(self):
        """Test agent-to-agent messaging."""
        brick1 = SampleBrick(name="agent1")
        brick2 = SampleBrick(name="agent2")

        agent1 = create_agent(brick1)
        agent2 = create_agent(brick2)

        # Wait for registration
        await asyncio.sleep(0.1)

        # Send message
        msg_id = await agent1.send_message(
            to_agent=agent2.id,
            message_type=MessageType.REQUEST,
            content={"test": "data"},
        )

        assert msg_id is not None

        # Receive message
        messages = await agent2.receive_messages(timeout=1.0)
        assert len(messages) == 1
        assert messages[0].content == {"test": "data"}

        # Cleanup
        await agent1.shutdown()
        await agent2.shutdown()

    @pytest.mark.asyncio
    async def test_agent_discovery(self):
        """Test agent discovery."""
        agent1 = Agent(id="a1", name="Agent 1", capabilities=["process"])
        agent2 = Agent(id="a2", name="Agent 2", capabilities=["analyze"])

        # Wait for registration
        await asyncio.sleep(0.1)

        # Discover all agents
        discovered = await agent1.discover_agents()
        assert len(discovered) >= 2

        # Discover by capability
        analyzers = await agent1.discover_agents(capability="analyze")
        assert any(a["id"] == "a2" for a in analyzers)

        # Cleanup
        await agent1.shutdown()
        await agent2.shutdown()

    @pytest.mark.asyncio
    async def test_request_processing(self):
        """Test request processing between agents."""
        brick = SampleBrick()
        processor = create_agent(brick, name="Processor")
        requester = Agent(id="req", name="Requester")

        # Start handler
        handler_task = asyncio.create_task(processor.handle_requests())

        # Wait for setup
        await asyncio.sleep(0.1)

        try:
            # Request processing
            result = await requester.request_processing(
                target_agent=processor.id,
                input="test data",
                timeout=2.0,
            )

            assert result == "processed: test data"

        finally:
            # Cleanup
            handler_task.cancel()
            await processor.shutdown()
            await requester.shutdown()


class TestAdaptiveBehavior:
    """Test adaptive behavior."""

    def test_create_adaptive_brick(self):
        """Test creating adaptive brick."""
        brick = SampleBrick()
        policy = ThresholdPolicy()
        adaptive = AdaptiveBrick(
            brick,
            policy,
            window_size=50,
        )

        assert isinstance(adaptive, AdaptiveBrick)
        assert adaptive.wrapped == brick
        assert adaptive.window_size == 50

    @pytest.mark.asyncio
    async def test_performance_tracking(self):
        """Test performance metrics tracking."""
        brick = SampleBrick()
        policy = ThresholdPolicy(latency_threshold_ms=100)
        adaptive = AdaptiveBrick(brick, policy, window_size=10)

        # Run multiple invocations
        for i in range(5):
            await adaptive.invoke(f"test{i}")

        # Check metrics
        summary = adaptive.get_metrics_summary()
        assert summary["total_invocations"] == 5
        assert summary["success_rate"] == 1.0
        assert "avg_latency_ms" in summary

    @pytest.mark.asyncio
    async def test_error_recovery(self):
        """Test automatic error recovery."""

        class ErrorNanobrick(NanobrickBase[str, str, None]):
            def __init__(self):
                super().__init__(name="error_brick")
                self.call_count = 0

            async def invoke(self, input: str, *, deps: None = None) -> str:
                self.call_count += 1
                if self.call_count == 1:
                    raise ValueError("First call fails")
                return f"recovered: {input}"

        brick = ErrorNanobrick()
        policy = ThresholdPolicy()
        adaptive = AdaptiveBrick(
            brick,
            policy,
            enable_auto_recovery=True,
        )

        # Add a custom recovery strategy for ValueError
        async def retry_once(adapter, input, error, deps):
            if isinstance(error, ValueError) and adapter.wrapped.call_count == 1:
                # Just retry once
                return await adapter.wrapped.invoke(input, deps=deps)
            return None

        adaptive.add_recovery_strategy(retry_once)

        # Should recover on retry
        result = await adaptive.invoke("test")
        assert result == "recovered: test"
        assert brick.call_count == 2

    def test_adaptation_policies(self):
        """Test different adaptation policies."""
        from nanobricks.adaptive.policies import (
            GradientPolicy,
            MLPolicy,
            RuleBasedPolicy,
        )

        # Test gradient policy
        gradient = GradientPolicy(
            learning_rate=0.05,
            target_latency_ms=50,
        )
        assert gradient.learning_rate == 0.05

        # Test rule-based policy
        rules = RuleBasedPolicy()
        assert len(rules.rules) > 0  # Has default rules

        # Test ML policy
        ml = MLPolicy()
        assert ml.model is None  # No model loaded by default
