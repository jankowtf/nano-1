"""Debugger for nanobricks pipelines."""

import asyncio
import inspect
import json
from datetime import datetime
from pathlib import Path
from typing import Any

from nanobricks import NanobrickProtocol


class DebugEvent:
    """Represents a debug event in the pipeline."""

    def __init__(
        self,
        brick_name: str,
        event_type: str,
        timestamp: datetime,
        data: dict[str, Any] | None = None,
    ):
        """Initialize debug event.

        Args:
            brick_name: Name of the brick
            event_type: Type of event (invoke_start, invoke_end, error, etc.)
            timestamp: When the event occurred
            data: Additional event data
        """
        self.brick_name = brick_name
        self.event_type = event_type
        self.timestamp = timestamp
        self.data = data or {}

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "brick_name": self.brick_name,
            "event_type": self.event_type,
            "timestamp": self.timestamp.isoformat(),
            "data": self.data,
        }


class BrickDebugger:
    """Debug nanobricks execution."""

    def __init__(
        self,
        capture_input: bool = True,
        capture_output: bool = True,
        capture_errors: bool = True,
        save_to_file: Path | None = None,
    ):
        """Initialize debugger.

        Args:
            capture_input: Capture input data
            capture_output: Capture output data
            capture_errors: Capture errors
            save_to_file: Save debug log to file
        """
        self.capture_input = capture_input
        self.capture_output = capture_output
        self.capture_errors = capture_errors
        self.save_to_file = save_to_file
        self.events: list[DebugEvent] = []
        self._breakpoints: dict[str, bool] = {}

    def set_breakpoint(self, brick_name: str):
        """Set a breakpoint on a brick.

        Args:
            brick_name: Name of brick to break on
        """
        self._breakpoints[brick_name] = True

    def clear_breakpoint(self, brick_name: str):
        """Clear a breakpoint.

        Args:
            brick_name: Name of brick to clear breakpoint
        """
        self._breakpoints.pop(brick_name, None)

    def wrap_brick(self, brick: NanobrickProtocol) -> NanobrickProtocol:
        """Wrap a brick with debugging.

        Args:
            brick: Brick to wrap

        Returns:
            Wrapped brick with debugging
        """
        debugger = self

        class DebuggedBrick:
            """Brick wrapped with debugging."""

            def __init__(self, wrapped: NanobrickProtocol):
                self._wrapped = wrapped
                self.name = getattr(wrapped, "name", wrapped.__class__.__name__)
                self.version = getattr(wrapped, "version", "0.0.0")

            async def invoke(self, input: Any, *, deps: Any = None) -> Any:
                """Invoke with debugging."""
                # Start event
                start_time = datetime.now()
                start_data = {}

                if debugger.capture_input:
                    start_data["input"] = self._serialize(input)
                    if deps:
                        start_data["deps"] = self._serialize(deps)

                debugger.events.append(
                    DebugEvent(self.name, "invoke_start", start_time, start_data)
                )

                # Check breakpoint
                if self.name in debugger._breakpoints:
                    await self._handle_breakpoint(input, deps)

                try:
                    # Execute
                    result = await self._wrapped.invoke(input, deps=deps)

                    # End event
                    end_time = datetime.now()
                    end_data = {
                        "duration_ms": (end_time - start_time).total_seconds() * 1000
                    }

                    if debugger.capture_output:
                        end_data["output"] = self._serialize(result)

                    debugger.events.append(
                        DebugEvent(self.name, "invoke_end", end_time, end_data)
                    )

                    return result

                except Exception as e:
                    # Error event
                    error_time = datetime.now()
                    error_data = {
                        "error_type": type(e).__name__,
                        "error_message": str(e),
                        "duration_ms": (error_time - start_time).total_seconds() * 1000,
                    }

                    if debugger.capture_errors:
                        error_data["traceback"] = inspect.trace()

                    debugger.events.append(
                        DebugEvent(self.name, "error", error_time, error_data)
                    )

                    raise

            def invoke_sync(self, input: Any, *, deps: Any = None) -> Any:
                """Synchronous invoke with debugging."""
                return asyncio.run(self.invoke(input, deps=deps))

            async def _handle_breakpoint(self, input: Any, deps: Any):
                """Handle breakpoint."""
                print(f"\n🔴 BREAKPOINT: {self.name}")
                print(f"   Input: {input}")
                if deps:
                    print(f"   Dependencies: {deps}")
                print("   Press Enter to continue...")
                # In real implementation, would use debugger protocol
                # For now, just log
                await asyncio.sleep(0.1)

            def _serialize(self, obj: Any) -> Any:
                """Serialize object for logging."""
                try:
                    # Try JSON serialization
                    json.dumps(obj)
                    return obj
                except:
                    # Fall back to string representation
                    return str(obj)

            def __rshift__(self, other):
                """Compose with debugging."""
                from nanobricks.composition import Pipeline

                return Pipeline(self, other)

        return DebuggedBrick(brick)
    def __or__(self, other):
        """Backwards compatibility for | operator. DEPRECATED: Use >> instead."""
        import warnings
        warnings.warn(
            "The | operator for nanobrick composition is deprecated. "
            "Use >> instead. This will be removed in v0.3.0.",
            DeprecationWarning,
            stacklevel=2
        )
        return self.__rshift__(other)
