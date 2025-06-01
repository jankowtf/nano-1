"""Advanced example: Multi-agent AI system with nanobricks.

This example demonstrates a complete AI agent system with:
- Multiple specialized agents communicating via A2A
- Web UI for monitoring via AGUI
- External AI API integration via ACP
- Protocol bridging for seamless communication
"""

import asyncio
from typing import Any, Dict, List, Optional
from datetime import datetime
from enum import Enum
import random

from nanobricks import NanobrickBase, NanobrickComposite
from nanobricks.agent import ProtocolBridge, Message
from nanobricks.skills import (
    SkillA2A,
    A2AMessage,
    SkillAGUI,
    UIBuilder,
    ComponentType,
    SkillACP,
    RESTEndpoint,
)


class TaskType(Enum):
    """Types of AI tasks."""
    ANALYSIS = "analysis"
    GENERATION = "generation"
    CLASSIFICATION = "classification"
    SUMMARIZATION = "summarization"


class AnalysisAgent(NanobrickBase[Dict[str, Any], Dict[str, Any], None]):
    """Agent specialized in data analysis."""
    
    def __init__(self):
        """Initialize agent."""
        self.name = "analysis_agent"
        self.version = "1.0.0"
        self.specialization = TaskType.ANALYSIS
    
    async def invoke(self, input: Dict[str, Any], *, deps: None = None) -> Dict[str, Any]:
        """Analyze input data."""
        data = input.get("data", {})
        
        # Simulate analysis
        await asyncio.sleep(0.1)  # Simulate processing time
        
        analysis = {
            "type": "analysis_result",
            "metrics": {
                "complexity": random.uniform(0.3, 0.9),
                "confidence": random.uniform(0.7, 0.95),
                "patterns_found": random.randint(2, 8),
            },
            "insights": [
                "Pattern A detected with high confidence",
                "Anomaly in data segment 3",
                "Strong correlation between features X and Y"
            ],
            "timestamp": datetime.now().isoformat()
        }
        
        return analysis
    
    def invoke_sync(self, input: Dict[str, Any], *, deps: None = None) -> Dict[str, Any]:
        """Sync version."""
        return asyncio.run(self.invoke(input, deps=deps))


class GenerationAgent(NanobrickBase[Dict[str, Any], Dict[str, Any], None]):
    """Agent specialized in content generation."""
    
    def __init__(self):
        """Initialize agent."""
        self.name = "generation_agent"
        self.version = "1.0.0"
        self.specialization = TaskType.GENERATION
    
    async def invoke(self, input: Dict[str, Any], *, deps: None = None) -> Dict[str, Any]:
        """Generate content based on input."""
        prompt = input.get("prompt", "")
        style = input.get("style", "default")
        
        # Simulate generation
        await asyncio.sleep(0.2)  # Simulate processing time
        
        generation = {
            "type": "generation_result",
            "content": f"Generated content based on '{prompt}' in {style} style.",
            "variations": [
                f"Variation 1: {prompt} - formal approach",
                f"Variation 2: {prompt} - creative approach",
                f"Variation 3: {prompt} - technical approach"
            ],
            "metadata": {
                "tokens_used": random.randint(100, 500),
                "generation_time": 0.2,
                "model": "internal-gen-v1"
            },
            "timestamp": datetime.now().isoformat()
        }
        
        return generation
    
    def invoke_sync(self, input: Dict[str, Any], *, deps: None = None) -> Dict[str, Any]:
        """Sync version."""
        return asyncio.run(self.invoke(input, deps=deps))


class CoordinatorAgent(NanobrickBase[Dict[str, Any], Dict[str, Any], None]):
    """Agent that coordinates other agents."""
    
    def __init__(self):
        """Initialize coordinator."""
        self.name = "coordinator_agent"
        self.version = "1.0.0"
        self.task_queue: List[Dict[str, Any]] = []
        self.results_cache: Dict[str, Any] = {}
    
    async def invoke(self, input: Dict[str, Any], *, deps: None = None) -> Dict[str, Any]:
        """Coordinate task execution."""
        task = input.get("task", {})
        task_type = TaskType(task.get("type", "analysis"))
        
        # Add to queue
        task_id = f"task_{len(self.task_queue)}"
        task["id"] = task_id
        task["status"] = "queued"
        self.task_queue.append(task)
        
        # Determine which agent to use
        agent_id = self._select_agent(task_type)
        
        result = {
            "type": "coordination_result",
            "task_id": task_id,
            "assigned_agent": agent_id,
            "status": "dispatched",
            "queue_length": len(self.task_queue),
            "timestamp": datetime.now().isoformat()
        }
        
        return result
    
    def invoke_sync(self, input: Dict[str, Any], *, deps: None = None) -> Dict[str, Any]:
        """Sync version."""
        return asyncio.run(self.invoke(input, deps=deps))
    
    def _select_agent(self, task_type: TaskType) -> str:
        """Select appropriate agent for task."""
        agent_map = {
            TaskType.ANALYSIS: "analysis-agent",
            TaskType.GENERATION: "generation-agent",
            TaskType.CLASSIFICATION: "analysis-agent",
            TaskType.SUMMARIZATION: "generation-agent",
        }
        return agent_map.get(task_type, "analysis-agent")


class AgentMonitorUI:
    """UI for monitoring agent system."""
    
    def __init__(self, agui_skill: SkillAGUI):
        """Initialize monitor."""
        self.skill = agui_skill
        self.agent_statuses: Dict[str, str] = {}
    
    async def build_dashboard(self) -> List[Any]:
        """Build monitoring dashboard."""
        ui = self.skill.create_ui()
        
        # Header
        ui.text("🤖 AI Agent System Monitor", style={
            "fontSize": "28px",
            "fontWeight": "bold",
            "marginBottom": "20px"
        })
        
        # Status grid
        status_components = []
        for agent_id, status in self.agent_statuses.items():
            color = "green" if status == "active" else "red"
            status_components.append(
                ui.container([
                    ui.text(agent_id, style={"fontWeight": "bold"}),
                    ui.text(status, style={"color": color})
                ], style={"border": "1px solid #ccc", "padding": "10px"})
            )
        
        # Control panel
        ui.container([
            ui.text("Task Control", style={"fontSize": "20px", "fontWeight": "bold"}),
            ui.select(["analysis", "generation", "classification", "summarization"], 
                     default="analysis", 
                     id="task_type_select"),
            ui.input("Enter task data...", id="task_input"),
            ui.button("Submit Task", on_click="submit_task"),
            ui.button("View Queue", on_click="view_queue")
        ], style={"marginTop": "20px", "padding": "15px", "background": "#f0f0f0"})
        
        # Results area
        ui.container([], id="results_area", style={
            "marginTop": "20px",
            "minHeight": "200px",
            "border": "1px solid #ddd",
            "padding": "10px"
        })
        
        return ui.build()
    
    async def update_agent_status(self, agent_id: str, status: str):
        """Update agent status in UI."""
        self.agent_statuses[agent_id] = status
        await self.skill.update_ui({
            f"status_{agent_id}": {"content": status, "style": {"color": "green" if status == "active" else "red"}}
        })
    
    async def display_result(self, result: Dict[str, Any]):
        """Display task result in UI."""
        result_text = f"Task Result ({result.get('type', 'unknown')}):\n"
        result_text += f"Status: {result.get('status', 'unknown')}\n"
        result_text += f"Details: {json.dumps(result, indent=2)}"
        
        await self.skill.update_ui({
            "results_area": {"content": result_text}
        })


async def create_agent_system():
    """Create and configure the multi-agent system."""
    print("🚀 Initializing AI Agent System...")
    
    # Create base agents
    coordinator = CoordinatorAgent()
    analyzer = AnalysisAgent()
    generator = GenerationAgent()
    
    # Enhance with A2A communication
    coordinator_a2a = SkillA2A(agent_id="coordinator")
    analyzer_a2a = SkillA2A(agent_id="analysis-agent")
    generator_a2a = SkillA2A(agent_id="generation-agent")
    
    coord_agent = coordinator_a2a.enhance(coordinator)
    analysis_agent = analyzer_a2a.enhance(analyzer)
    gen_agent = generator_a2a.enhance(generator)
    
    # Connect all agents
    await coordinator_a2a.connect()
    await analyzer_a2a.connect()
    await generator_a2a.connect()
    
    # Set up peer connections
    coordinator_a2a.add_peer("analysis-agent")
    coordinator_a2a.add_peer("generation-agent")
    analyzer_a2a.add_peer("coordinator")
    generator_a2a.add_peer("coordinator")
    
    # Set up message handlers
    async def handle_coordinator_messages(msg: A2AMessage):
        """Handle messages to coordinator."""
        print(f"Coordinator received: {msg.content}")
        if msg.content.get("type") == "task_result":
            coordinator.results_cache[msg.content.get("task_id")] = msg.content
    
    async def handle_analysis_messages(msg: A2AMessage):
        """Handle messages to analyzer."""
        print(f"Analyzer received: {msg.content}")
        if msg.content.get("type") == "task_request":
            # Process task
            result = await analyzer.invoke(msg.content)
            result["task_id"] = msg.content.get("task_id")
            # Send result back
            await analysis_agent.send_to("coordinator", result)
    
    async def handle_generation_messages(msg: A2AMessage):
        """Handle messages to generator."""
        print(f"Generator received: {msg.content}")
        if msg.content.get("type") == "task_request":
            # Process task
            result = await generator.invoke(msg.content)
            result["task_id"] = msg.content.get("task_id")
            # Send result back
            await gen_agent.send_to("coordinator", result)
    
    coordinator_a2a.on_message(handle_coordinator_messages)
    analyzer_a2a.on_message(handle_analysis_messages)
    generator_a2a.on_message(handle_generation_messages)
    
    # Add AGUI for coordinator
    agui_skill = SkillAGUI(session_id="agent-monitor", auto_render=False)
    coord_with_ui = agui_skill.enhance(coord_agent)
    
    # Create monitor UI
    monitor = AgentMonitorUI(agui_skill)
    await agui_skill.connect()
    
    # Initialize UI
    await monitor.update_agent_status("coordinator", "active")
    await monitor.update_agent_status("analysis-agent", "active")
    await monitor.update_agent_status("generation-agent", "active")
    
    dashboard = await monitor.build_dashboard()
    await coord_with_ui.render(dashboard)
    
    # Add ACP for external AI integration
    acp_skill = SkillACP(
        base_url="https://api.openai.com",
        auth={"type": "bearer", "token": "demo-key"}
    )
    final_coordinator = acp_skill.enhance(coord_with_ui)
    
    # Register external AI endpoints
    final_coordinator.register_endpoint("gpt4", RESTEndpoint(
        path="/v1/chat/completions",
        method="POST"
    ))
    
    return {
        "coordinator": final_coordinator,
        "analyzer": analysis_agent,
        "generator": gen_agent,
        "monitor": monitor,
        "skills": {
            "coordinator_a2a": coordinator_a2a,
            "analyzer_a2a": analyzer_a2a,
            "generator_a2a": generator_a2a,
            "agui": agui_skill,
            "acp": acp_skill
        }
    }


async def run_agent_system_demo():
    """Run the agent system demo."""
    # Create system
    system = await create_agent_system()
    
    print("\n📊 Agent System Ready!")
    print("Available agents:")
    print("  - Coordinator (with A2A, AGUI, ACP)")
    print("  - Analysis Agent (with A2A)")
    print("  - Generation Agent (with A2A)")
    
    # Example tasks
    tasks = [
        {
            "type": "analysis",
            "data": {"dataset": "customer_feedback", "metrics": ["sentiment", "topics"]}
        },
        {
            "type": "generation",
            "prompt": "Create a summary of Q4 results",
            "style": "executive"
        },
        {
            "type": "classification",
            "data": {"text": "This product exceeded my expectations!", "categories": ["positive", "negative", "neutral"]}
        }
    ]
    
    # Submit tasks
    print("\n📝 Submitting tasks...")
    for i, task_data in enumerate(tasks):
        result = await system["coordinator"].invoke({
            "task": task_data
        })
        print(f"Task {i+1} submitted: {result['task_id']} -> {result['assigned_agent']}")
        
        # Dispatch task to assigned agent
        agent_id = result["assigned_agent"]
        task_request = {
            "type": "task_request",
            "task_id": result["task_id"],
            **task_data
        }
        await system["coordinator"].send_to(agent_id, task_request)
        
        # Update UI
        await system["monitor"].display_result(result)
        
        # Small delay between tasks
        await asyncio.sleep(0.5)
    
    # Wait for results
    print("\n⏳ Processing tasks...")
    await asyncio.sleep(2)
    
    # Display final status
    print("\n✅ Demo Complete!")
    print(f"Tasks in queue: {len(system['coordinator'].wrapped.task_queue)}")
    print(f"Results cached: {len(system['coordinator'].wrapped.results_cache)}")
    
    # Cleanup
    for skill in system["skills"].values():
        if hasattr(skill, "disconnect"):
            await skill.disconnect()


async def main():
    """Run the complete demo."""
    print("=" * 60)
    print("🤖 Nanobricks Multi-Agent AI System Demo")
    print("=" * 60)
    
    await run_agent_system_demo()
    
    print("\n" + "=" * 60)
    print("Demo finished!")


if __name__ == "__main__":
    asyncio.run(main())