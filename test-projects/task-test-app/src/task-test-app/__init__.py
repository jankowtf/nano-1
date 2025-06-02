"""task-test-app - Built with Nanobricks."""

from nanobricks import NanobrickSimple, Pipeline

__version__ = "0.1.0"


class ExampleBrick(NanobrickSimple[str, str]):
    """An example nanobrick."""
    
    async def invoke(self, input: str) -> str:
        return f"Processed: {input}"


__all__ = ["ExampleBrick"]
