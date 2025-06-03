"""test-nanobricks-app - Built with Nanobricks."""

from nanobricks import NanobrickSimple, Pipeline

__version__ = "0.1.0"


class GreetingBrick(NanobrickSimple[str, str]):
    """A simple greeting brick."""
    
    async def invoke(self, input: str) -> str:
        return f"Hello, {input}!"


class UppercaseBrick(NanobrickSimple[str, str]):
    """Converts text to uppercase."""
    
    async def invoke(self, input: str) -> str:
        return input.upper()


# Example pipeline
greeting_pipeline = GreetingBrick() >> UppercaseBrick()


__all__ = ["GreetingBrick", "UppercaseBrick", "greeting_pipeline"]
