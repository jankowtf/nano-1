"""JSON transformation nanobricks."""

import json
from typing import Any, Union

from nanobricks.transformers.base import TransformerBrick


class JSONParser(TransformerBrick[Union[str, bytes], dict[str, Any], None]):
    """Parse JSON string or bytes into Python objects."""

    async def transform(self, input: str | bytes) -> dict[str, Any]:
        """Parse JSON input.

        Args:
            input: JSON string or bytes to parse

        Returns:
            Parsed Python dictionary

        Raises:
            ValueError: If input is not valid JSON
        """
        if not input:
            return {}

        try:
            if isinstance(input, bytes):
                input = input.decode("utf-8")
            return json.loads(input)
        except (json.JSONDecodeError, UnicodeDecodeError) as e:
            raise ValueError(f"Invalid JSON input: {e}")


class JSONSerializer(TransformerBrick[Any, str, None]):
    """Serialize Python objects to JSON string."""

    def __init__(self, name: str = None, indent: int = None, sort_keys: bool = False):
        """Initialize with serialization options.

        Args:
            name: Optional custom name
            indent: Number of spaces for indentation (None for compact)
            sort_keys: Whether to sort dictionary keys
        """
        super().__init__(name)
        self.indent = indent
        self.sort_keys = sort_keys

    async def transform(self, input: Any) -> str:
        """Serialize input to JSON.

        Args:
            input: Python object to serialize

        Returns:
            JSON string representation

        Raises:
            ValueError: If input cannot be serialized to JSON
        """
        try:
            return json.dumps(input, indent=self.indent, sort_keys=self.sort_keys)
        except (TypeError, ValueError) as e:
            raise ValueError(f"Cannot serialize to JSON: {e}")


class JSONPrettyPrinter(JSONSerializer):
    """Serialize Python objects to pretty-printed JSON."""

    def __init__(self, name: str = None, indent: int = 2):
        """Initialize with pretty-print settings.

        Args:
            name: Optional custom name
            indent: Number of spaces for indentation (default: 2)
        """
        super().__init__(name, indent=indent, sort_keys=True)
