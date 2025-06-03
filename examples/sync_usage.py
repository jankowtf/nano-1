"""
Synchronous usage example for nanobricks.

This shows how to use nanobricks in a synchronous context,
which is useful for scripts, notebooks, or legacy code.
"""

from nanobricks import Nanobrick


# Create some simple bricks
class GreetBrick(Nanobrick[str, str]):
    """Adds a greeting."""
    
    async def invoke(self, input: str, *, deps=None) -> str:
        return f"Hello, {input}!"


class ShoutBrick(Nanobrick[str, str]):
    """Converts to uppercase."""
    
    async def invoke(self, input: str, *, deps=None) -> str:
        return input.upper()


class AddPunctuationBrick(Nanobrick[str, str]):
    """Adds extra punctuation."""
    
    async def invoke(self, input: str, *, deps=None) -> str:
        return f"{input}!!!"


def main():
    """Demonstrate sync usage of nanobricks."""
    
    print("=== Synchronous Nanobrick Usage ===\n")
    
    # Create bricks
    greet = GreetBrick(name="greet")
    shout = ShoutBrick(name="shout")
    punctuate = AddPunctuationBrick(name="punctuate")
    
    # Example 1: Single brick sync usage
    print("1. Single Brick Usage")
    print("-" * 30)
    
    result = greet.invoke_sync("World")
    print(f"  greet('World') = {result}")
    
    result = shout.invoke_sync("quiet")
    print(f"  shout('quiet') = {result}")
    
    # Example 2: Pipeline sync usage
    print("\n2. Pipeline Sync Usage")
    print("-" * 30)
    
    # Create a pipeline
    excited_greeting = greet | shout | punctuate
    
    result = excited_greeting.invoke_sync("Python")
    print(f"  Pipeline result: {result}")
    
    # Example 3: Step by step
    print("\n3. Step by Step Execution")
    print("-" * 30)
    
    input_name = "Alice"
    print(f"  Input: {input_name}")
    
    step1 = greet.invoke_sync(input_name)
    print(f"  After greet: {step1}")
    
    step2 = shout.invoke_sync(step1)
    print(f"  After shout: {step2}")
    
    step3 = punctuate.invoke_sync(step2)
    print(f"  After punctuate: {step3}")
    
    # Example 4: Error handling in sync mode
    print("\n4. Sync Error Handling")
    print("-" * 30)
    
    class ErrorBrick(Nanobrick[str, str]):
        async def invoke(self, input: str, *, deps=None) -> str:
            if input == "error":
                raise ValueError("Input cannot be 'error'")
            return input
    
    error_pipeline = greet | ErrorBrick(name="check") | shout
    
    try:
        result = error_pipeline.invoke_sync("error")
    except ValueError as e:
        print(f"  Caught error: {e}")
    
    # Example 5: Multiple pipelines
    print("\n5. Multiple Pipelines")
    print("-" * 30)
    
    # Create different pipelines from same bricks
    quiet_greeting = greet | punctuate  # Skip shouting
    loud_greeting = greet | shout | shout | punctuate  # Double shout!
    
    name = "Bob"
    print(f"  Input: {name}")
    print(f"  Quiet: {quiet_greeting.invoke_sync(name)}")
    print(f"  Loud:  {loud_greeting.invoke_sync(name)}")


if __name__ == "__main__":
    # This is a regular Python script, no asyncio needed!
    main()