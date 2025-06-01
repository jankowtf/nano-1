"""Example of a conversational nanobrick with AI."""

import asyncio
from typing import Any, Dict, List, Optional

from nanobricks import NanobrickBase
from nanobricks.skills import SkillAI, create_ai_skill


class ConversationalBrick(NanobrickBase[str, str, Dict[str, Any]]):
    """
    A nanobrick that can have conversations using AI.
    
    It maintains conversation context and can answer questions,
    provide explanations, and engage in dialogue.
    """
    
    def __init__(
        self,
        system_prompt: Optional[str] = None,
        max_context: int = 10,
        name: str = "conversational_brick",
        version: str = "1.0.0",
    ):
        """Initialize conversational brick.
        
        Args:
            system_prompt: System prompt for the AI
            max_context: Maximum conversation history to maintain
            name: Brick name
            version: Brick version
        """
        super().__init__(name=name, version=version)
        self.system_prompt = system_prompt or (
            "You are a helpful assistant integrated into a nanobrick. "
            "You help users understand and work with data processing pipelines."
        )
        self.max_context = max_context
        self.conversation_history: List[Dict[str, str]] = []
    
    async def invoke(
        self, input: str, *, deps: Optional[Dict[str, Any]] = None
    ) -> str:
        """Process conversational input.
        
        Args:
            input: User message
            deps: Optional dependencies with context
            
        Returns:
            AI response
        """
        # Add to conversation history
        self.conversation_history.append({"role": "user", "content": input})
        
        # Trim history if needed
        if len(self.conversation_history) > self.max_context * 2:
            self.conversation_history = self.conversation_history[-self.max_context * 2:]
        
        # Build context from dependencies
        context = ""
        if deps:
            if "data" in deps:
                context += f"\nCurrent data: {deps['data']}"
            if "pipeline_state" in deps:
                context += f"\nPipeline state: {deps['pipeline_state']}"
            if "error" in deps:
                context += f"\nRecent error: {deps['error']}"
        
        # In a real implementation, this would call an AI provider
        # For demo, we'll provide canned responses
        response = self._generate_response(input, context)
        
        # Add to history
        self.conversation_history.append({"role": "assistant", "content": response})
        
        return response
    
    def _generate_response(self, input: str, context: str) -> str:
        """Generate a response (mock for demo)."""
        input_lower = input.lower()
        
        # Pattern matching for common queries
        if "help" in input_lower:
            return (
                "I can help you with:\n"
                "- Understanding your data pipeline\n"
                "- Debugging errors\n"
                "- Optimizing performance\n"
                "- Explaining what each brick does\n"
                "What would you like to know?"
            )
        
        elif "error" in input_lower:
            if context and "error" in context:
                return (
                    f"I see you encountered an error. {context}\n"
                    "Here are some suggestions:\n"
                    "1. Check your input data format\n"
                    "2. Verify all required fields are present\n"
                    "3. Look at the error message for clues\n"
                    "Would you like me to help debug this specific error?"
                )
            else:
                return "What error are you experiencing? Please provide more details."
        
        elif "explain" in input_lower:
            return (
                "This nanobrick is part of a data processing pipeline. "
                "Each brick processes data and passes it to the next brick. "
                "You can compose bricks using the pipe operator (|) to create "
                "complex data transformations. Would you like to know more about "
                "a specific aspect?"
            )
        
        elif "optimize" in input_lower or "performance" in input_lower:
            return (
                "Here are some performance optimization tips:\n"
                "1. Use batching for multiple items\n"
                "2. Enable caching for repeated operations\n"
                "3. Add performance monitoring\n"
                "4. Consider using adaptive bricks\n"
                "What performance issue are you facing?"
            )
        
        else:
            return (
                f"I understand you're asking about: {input}\n"
                f"Context: {context if context else 'No additional context'}\n"
                "How can I help you with this?"
            )
    
    def clear_history(self):
        """Clear conversation history."""
        self.conversation_history.clear()
    
    def get_history(self) -> List[Dict[str, str]]:
        """Get conversation history."""
        return self.conversation_history.copy()


# Example usage
async def main():
    """Demonstrate conversational nanobrick."""
    
    # Create conversational brick
    assistant = ConversationalBrick(
        system_prompt="You are an expert in data processing and nanobricks.",
        max_context=20
    )
    
    # Enhance with AI
    ai_skill = create_ai_skill(
        enable_reasoning_trace=True,
        enable_memory=True,
    )
    ai_assistant = assistant.with_skill(ai_skill)
    
    print("Conversational Nanobrick Demo")
    print("=" * 50)
    print("Type 'quit' to exit")
    print()
    
    # Simulate a conversation
    conversation = [
        "Hello! What can you help me with?",
        "I'm having trouble with my data pipeline",
        "The error says 'ValueError: invalid data format'",
        "How can I optimize performance?",
        "explain how nanobricks work",
    ]
    
    # Context that might come from the pipeline
    pipeline_context = {
        "data": {"records": 1000, "processed": 750},
        "pipeline_state": "processing",
        "error": "ValueError: invalid data format in record 751",
    }
    
    for user_input in conversation:
        print(f"\nUser: {user_input}")
        
        # Get response with context
        response = await ai_assistant.invoke(user_input, deps=pipeline_context)
        
        print(f"Assistant: {response}")
        
        # Update context based on conversation
        if "error" in user_input.lower():
            pipeline_context["investigating_error"] = True
    
    # Show conversation history
    print("\n" + "=" * 50)
    print("Conversation History:")
    history = assistant.get_history()
    print(f"Total exchanges: {len(history) // 2}")
    
    # Show AI stats
    if hasattr(ai_assistant, 'get_memory_stats'):
        print(f"\nAI Memory Stats: {ai_assistant.get_memory_stats()}")
    
    print(f"\nAI Cost Report: {ai_skill.get_cost_report()}")


if __name__ == "__main__":
    asyncio.run(main())