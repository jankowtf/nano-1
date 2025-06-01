"""Examples demonstrating multi-protocol AI integration with nanobricks."""

import asyncio
from typing import Any, Dict
import json

from nanobricks import NanobrickBase
from nanobricks.agent import (
    ProtocolType,
    ProtocolConfig,
    ProtocolBridge,
    ProtocolRegistry,
    Message,
)
from nanobricks.skills import (
    SkillA2A,
    A2AMessage,
    SkillAGUI,
    UIBuilder,
    SkillACP,
    RESTEndpoint,
)


class AIProcessor(NanobrickBase[Dict[str, Any], Dict[str, Any], None]):
    """Example AI processor nanobrick."""
    
    def __init__(self):
        """Initialize processor."""
        self.name = "ai_processor"
        self.version = "1.0.0"
    
    async def invoke(self, input: Dict[str, Any], *, deps: None = None) -> Dict[str, Any]:
        """Process AI request."""
        # Simulate AI processing
        action = input.get("action", "unknown")
        data = input.get("data", {})
        
        result = {
            "action": action,
            "status": "processed",
            "response": f"Processed {action} with data: {data}",
            "timestamp": asyncio.get_event_loop().time()
        }
        
        return result
    
    def invoke_sync(self, input: Dict[str, Any], *, deps: None = None) -> Dict[str, Any]:
        """Sync version."""
        return asyncio.run(self.invoke(input, deps=deps))


async def example_a2a_communication():
    """Example: Agent-to-Agent communication."""
    print("\n=== A2A Communication Example ===")
    
    # Create two AI processors
    processor1 = AIProcessor()
    processor2 = AIProcessor()
    
    # Enhance with A2A skill
    a2a_skill1 = SkillA2A(agent_id="agent-1")
    a2a_skill2 = SkillA2A(agent_id="agent-2")
    
    agent1 = a2a_skill1.enhance(processor1)
    agent2 = a2a_skill2.enhance(processor2)
    
    # Connect agents
    await a2a_skill1.connect()
    await a2a_skill2.connect()
    
    # Add each other as peers
    a2a_skill1.add_peer("agent-2")
    a2a_skill2.add_peer("agent-1")
    
    # Set up message handler for agent2
    messages_received = []
    
    def handle_message(msg: A2AMessage):
        print(f"Agent-2 received: {msg.content}")
        messages_received.append(msg)
    
    a2a_skill2.on_message(handle_message)
    
    # Agent1 sends message to Agent2
    await agent1.send_to("agent-2", {
        "action": "analyze",
        "data": {"text": "Hello from Agent 1"}
    })
    
    # Process normally
    result = await agent1.invoke({
        "action": "process",
        "data": {"value": 42}
    })
    print(f"Agent-1 result: {result}")
    
    # Broadcast to all peers
    await agent1.broadcast({
        "action": "status",
        "data": {"status": "active", "load": 0.75}
    })
    
    # Clean up
    await a2a_skill1.disconnect()
    await a2a_skill2.disconnect()


async def example_agui_interface():
    """Example: Agent GUI interface."""
    print("\n=== AGUI Interface Example ===")
    
    # Create AI processor
    processor = AIProcessor()
    
    # Enhance with AGUI skill
    agui_skill = SkillAGUI(session_id="demo-session", auto_render=False)
    ui_processor = agui_skill.enhance(processor)
    
    # Connect to UI system (mock)
    await agui_skill.connect()
    
    # Build UI
    ui = (agui_skill.create_ui()
        .text("AI Control Panel", style={"fontSize": "24px", "fontWeight": "bold"})
        .input("prompt_input", placeholder="Enter your AI prompt...")
        .select(["GPT-4", "Claude", "PaLM"], default="Claude")
        .button("Process", on_click="process_handler")
        .container([], id="results_container")
        .build())
    
    # Render UI
    await ui_processor.render(ui)
    print("UI rendered with components:", [comp.type.value for comp in ui])
    
    # Simulate user interaction
    await agui_skill.update_ui({
        "prompt_input": "Analyze this text for sentiment",
        "model_select": "Claude"
    })
    
    # Process with UI feedback
    result = await ui_processor.invoke({
        "action": "analyze",
        "data": {"prompt": "Analyze this text for sentiment"}
    })
    
    # Update UI with results
    await agui_skill.update_ui({
        "results_container": {"content": json.dumps(result, indent=2)}
    })
    
    # Show dialog
    response = await ui_processor.show_dialog(
        "Processing Complete",
        "Would you like to save the results?",
        ["Save", "Discard", "Continue"]
    )
    print(f"User selected: {response}")
    
    # Clean up
    await agui_skill.disconnect()


async def example_acp_rest_api():
    """Example: REST API integration."""
    print("\n=== ACP REST API Example ===")
    
    # Create AI processor
    processor = AIProcessor()
    
    # Enhance with ACP skill
    acp_skill = SkillACP(
        base_url="https://api.example.com",
        auth={"type": "bearer", "token": "demo-token"}
    )
    api_processor = acp_skill.enhance(processor)
    
    # Register endpoints
    api_processor.register_endpoint("chat", RESTEndpoint(
        path="/v1/chat/completions",
        method="POST",
        headers={"Content-Type": "application/json"}
    ))
    
    api_processor.register_endpoint("models", RESTEndpoint(
        path="/v1/models",
        method="GET"
    ))
    
    # Add request interceptor
    def add_metadata(message: Message) -> Message:
        """Add metadata to requests."""
        message.metadata["client"] = "nanobricks-demo"
        message.metadata["version"] = "1.0.0"
        return message
    
    api_processor.add_interceptor(add_metadata)
    
    # Mock API call (would fail in real scenario without actual API)
    print("Simulating API calls...")
    
    # Process locally
    result = await api_processor.invoke({
        "action": "chat",
        "data": {
            "messages": [{"role": "user", "content": "Hello AI!"}],
            "model": "gpt-4"
        }
    })
    print(f"Local processing result: {result}")
    
    # Stream data example
    data_queue = asyncio.Queue()
    
    # Add sample data
    for i in range(5):
        await data_queue.put({"id": i, "value": f"data-{i}"})
    await data_queue.put(None)  # End marker
    
    # Would stream to API in batches
    print("Would stream 5 items to API in batches")


async def example_protocol_bridge():
    """Example: Bridging multiple protocols."""
    print("\n=== Protocol Bridge Example ===")
    
    # Create protocol bridge
    bridge = ProtocolBridge()
    
    # Create mock adapters (in real scenario, these would be actual connections)
    print("Setting up protocol bridge...")
    
    # Define message transformer
    def transform_a2a_to_rest(msg: Message) -> Message:
        """Transform A2A message to REST format."""
        if msg.type == "a2a_message":
            return Message(
                id=msg.id,
                type="api_call",
                content={
                    "endpoint": "/agent/message",
                    "method": "POST",
                    "body": msg.content
                },
                metadata=msg.metadata
            )
        return msg
    
    # Register transformer
    bridge.register_transformer(
        ProtocolType.A2A,
        ProtocolType.ACP,
        transform_a2a_to_rest
    )
    
    # Set up routing
    bridge.add_route("a2a", ["acp", "agui"])
    bridge.add_route("agui", ["a2a"])
    
    print("Protocol bridge configured with routes:")
    print("- A2A -> ACP, AGUI")
    print("- AGUI -> A2A")
    
    # In real scenario, bridge.start() would begin routing messages


async def example_multi_skill_integration():
    """Example: Combining multiple AI skills."""
    print("\n=== Multi-Skill Integration Example ===")
    
    # Create base processor
    processor = AIProcessor()
    
    # Layer multiple skills
    # First add A2A
    a2a_skill = SkillA2A(agent_id="multi-agent")
    processor_with_a2a = a2a_skill.enhance(processor)
    
    # Then add AGUI
    agui_skill = SkillAGUI(auto_render=False)
    processor_with_ui = agui_skill.enhance(processor_with_a2a)
    
    # Finally add ACP
    acp_skill = SkillACP(base_url="https://api.example.com")
    final_processor = acp_skill.enhance(processor_with_ui)
    
    print(f"Created multi-skill processor: {final_processor}")
    print(f"Name: {final_processor.name}")
    print("Available capabilities:")
    print("- A2A: send_to, broadcast, on_message")
    print("- AGUI: create_ui, render, show_dialog")
    print("- ACP: call_api, register_endpoint, stream_to_api")
    
    # Use the multi-skill processor
    result = await final_processor.invoke({
        "action": "multi-process",
        "data": {"test": "value"}
    })
    print(f"Multi-skill result: {result}")


async def main():
    """Run all examples."""
    print("=== Nanobricks Multi-Protocol AI Examples ===")
    
    # Run examples
    await example_a2a_communication()
    await example_agui_interface()
    await example_acp_rest_api()
    await example_protocol_bridge()
    await example_multi_skill_integration()
    
    print("\n=== Examples Complete ===")


if __name__ == "__main__":
    asyncio.run(main())