"""Logging skill for Nanobricks.

Adds automatic logging of inputs, outputs, and errors to any nanobrick.
"""

import json
import logging
from datetime import datetime
from typing import Any

from nanobricks.protocol import T_deps, T_in, T_out
from nanobricks.skill import NanobrickEnhanced, Skill, register_skill


def setup_logger(name: str, level: str = "INFO") -> logging.Logger:
    """Set up a logger with a nice format."""
    logger = logging.getLogger(name)

    # Only add handler if logger doesn't have one
    if not logger.handlers:
        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)

    logger.setLevel(getattr(logging, level.upper()))
    return logger


@register_skill("logging")
class LoggingSkill(Skill[T_in, T_out, T_deps]):
    """Adds automatic logging to brick invocations.

    Config options:
        - level: Log level (DEBUG, INFO, WARNING, ERROR)
        - log_inputs: Whether to log inputs (default: True)
        - log_outputs: Whether to log outputs (default: True)
        - log_errors: Whether to log errors (default: True)
        - truncate: Max length for logged values (default: 100)
        - pretty: Pretty-print JSON objects (default: False)
    """

    def _create_enhanced_brick(self, brick):
        # Get config options
        level = self.config.get("level", "INFO")
        log_inputs = self.config.get("log_inputs", True)
        log_outputs = self.config.get("log_outputs", True)
        log_errors = self.config.get("log_errors", True)
        truncate = self.config.get("truncate", 100)
        pretty = self.config.get("pretty", False)

        # Set up logger
        logger = setup_logger(f"nanobrick.{brick.name}", level)

        class LoggingEnhanced(NanobrickEnhanced[T_in, T_out, T_deps]):
            async def invoke(self, input: T_in, *, deps: T_deps | None = None) -> T_out:
                # Log input
                if log_inputs:
                    input_str = self._format_value(input, truncate, pretty)
                    logger.info(f"🔵 Input: {input_str}")

                # Track timing
                start_time = datetime.now()

                try:
                    # Invoke the wrapped brick
                    result = await self._wrapped.invoke(input, deps=deps)

                    # Calculate duration
                    duration = (datetime.now() - start_time).total_seconds()

                    # Log output
                    if log_outputs:
                        output_str = self._format_value(result, truncate, pretty)
                        logger.info(f"🟢 Output: {output_str} (took {duration:.3f}s)")

                    return result

                except Exception as e:
                    # Calculate duration
                    duration = (datetime.now() - start_time).total_seconds()

                    # Log error
                    if log_errors:
                        logger.error(
                            f"🔴 Error after {duration:.3f}s: {type(e).__name__}: {str(e)}"
                        )

                    # Re-raise the error
                    raise

            def _format_value(self, value: Any, max_length: int, pretty: bool) -> str:
                """Format a value for logging."""
                try:
                    # Handle different types
                    if isinstance(value, (dict, list)):
                        if pretty:
                            formatted = json.dumps(value, indent=2, default=str)
                        else:
                            formatted = json.dumps(value, default=str)
                    else:
                        formatted = str(value)

                    # Truncate if needed
                    if len(formatted) > max_length:
                        formatted = formatted[: max_length - 3] + "..."

                    return formatted
                except:
                    # Fallback to repr
                    return repr(value)[:max_length]

        return LoggingEnhanced(brick, self)
