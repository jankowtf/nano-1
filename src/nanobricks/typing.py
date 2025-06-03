"""Type utilities for nanobricks framework.

This module provides utilities for type checking, adaptation, and conversion
to reduce friction when composing nanobricks with the pipe operator.
"""

from typing import (
    Any,
    Callable,
    Dict,
    Generic,
    List,
    Optional,
    Tuple,
    Type,
    TypeVar,
    Union,
    get_args,
    get_origin,
    get_type_hints,
)
from functools import wraps
import json
from typing_extensions import ParamSpec

from nanobricks.protocol import NanobrickBase, NanobrickProtocol

T = TypeVar("T")
E = TypeVar("E")
T_in = TypeVar("T_in")
T_out = TypeVar("T_out")
T_deps = TypeVar("T_deps")
P = ParamSpec("P")


class Result(Generic[T, E]):
    """A generic Result type for standardized error handling.

    Represents either a successful value (Ok) or an error (Err).
    Inspired by Rust's Result type.
    """

    def __init__(self, value: Optional[T] = None, error: Optional[E] = None):
        if value is not None and error is not None:
            raise ValueError("Result cannot have both value and error")
        if value is None and error is None:
            raise ValueError("Result must have either value or error")
        self._value = value
        self._error = error

    @classmethod
    def ok(cls, value: T) -> "Result[T, E]":
        """Create a successful Result."""
        return cls(value=value)

    @classmethod
    def err(cls, error: E) -> "Result[T, E]":
        """Create an error Result."""
        return cls(error=error)

    @property
    def is_ok(self) -> bool:
        """Check if the Result is successful."""
        return self._value is not None

    @property
    def is_err(self) -> bool:
        """Check if the Result is an error."""
        return self._error is not None

    def unwrap(self) -> T:
        """Get the value, raising if it's an error."""
        if self._error is not None:
            raise ValueError(f"Called unwrap on an error Result: {self._error}")
        return self._value  # type: ignore

    def unwrap_err(self) -> E:
        """Get the error, raising if it's a value."""
        if self._value is not None:
            raise ValueError(f"Called unwrap_err on an ok Result: {self._value}")
        return self._error  # type: ignore

    def unwrap_or(self, default: T) -> T:
        """Get the value or return a default."""
        return self._value if self._value is not None else default

    def map(self, func: Callable[[T], "T"]) -> "Result[T, E]":
        """Transform the value if successful."""
        if self.is_ok:
            return Result.ok(func(self._value))  # type: ignore
        return self

    def map_err(self, func: Callable[[E], "E"]) -> "Result[T, E]":
        """Transform the error if present."""
        if self.is_err:
            return Result.err(func(self._error))  # type: ignore
        return self

    def __repr__(self) -> str:
        if self.is_ok:
            return f"Ok({self._value!r})"
        return f"Err({self._error!r})"


class TypeMismatchError(TypeError):
    """Enhanced error for type mismatches in pipe operations."""

    def __init__(
        self,
        left_brick: str,
        right_brick: str,
        output_type: Type,
        expected_type: Type,
        suggestion: Optional[str] = None,
    ):
        self.left_brick = left_brick
        self.right_brick = right_brick
        self.output_type = output_type
        self.expected_type = expected_type
        self.suggestion = suggestion

        message = (
            f"Type mismatch in pipe operation:\n"
            f"  {left_brick} outputs: {self._format_type(output_type)}\n"
            f"  {right_brick} expects: {self._format_type(expected_type)}\n"
        )

        if suggestion:
            message += f"\nSuggestion: {suggestion}"

        super().__init__(message)

    @staticmethod
    def _format_type(type_: Type) -> str:
        """Format a type for display."""
        if hasattr(type_, "__name__"):
            return type_.__name__
        return str(type_)


class TypeAdapter(NanobrickBase[T_in, T_out, None]):
    """A nanobrick that adapts between types using a conversion function."""

    def __init__(
        self,
        name: str,
        converter: Callable[[T_in], T_out],
        input_type: Type[T_in],
        output_type: Type[T_out],
    ):
        self.name = name
        self.version = "1.0.0"
        self.converter = converter
        self.input_type = input_type
        self.output_type = output_type

    async def invoke(self, input: T_in, *, deps: None = None) -> T_out:
        return self.converter(input)

    def __repr__(self) -> str:
        return f"TypeAdapter({self.name}: {self.input_type.__name__} -> {self.output_type.__name__})"


# Common type conversion helpers
def string_to_dict(
    delimiter: str = ",", key_value_sep: str = "="
) -> TypeAdapter[str, Dict[str, str]]:
    """Create an adapter from string to dict.

    Example: "a=1,b=2" -> {"a": "1", "b": "2"}
    """

    def converter(s: str) -> Dict[str, str]:
        if not s:
            return {}
        pairs = s.split(delimiter)
        result = {}
        for pair in pairs:
            if key_value_sep in pair:
                key, value = pair.split(key_value_sep, 1)
                result[key.strip()] = value.strip()
        return result

    return TypeAdapter(
        name=f"string_to_dict({delimiter},{key_value_sep})",
        converter=converter,
        input_type=str,
        output_type=Dict[str, str],
    )


def dict_to_string(
    delimiter: str = ",", key_value_sep: str = "="
) -> TypeAdapter[Dict[str, str], str]:
    """Create an adapter from dict to string.

    Example: {"a": "1", "b": "2"} -> "a=1,b=2"
    """

    def converter(d: Dict[str, str]) -> str:
        return delimiter.join(f"{k}{key_value_sep}{v}" for k, v in d.items())

    return TypeAdapter(
        name=f"dict_to_string({delimiter},{key_value_sep})",
        converter=converter,
        input_type=Dict[str, str],
        output_type=str,
    )


def list_to_tuple() -> TypeAdapter[List[Any], Tuple[Any, ...]]:
    """Create an adapter from list to tuple."""
    return TypeAdapter(
        name="list_to_tuple",
        converter=tuple,
        input_type=List[Any],
        output_type=Tuple[Any, ...],
    )


def tuple_to_list() -> TypeAdapter[Tuple[Any, ...], List[Any]]:
    """Create an adapter from tuple to list."""
    return TypeAdapter(
        name="tuple_to_list",
        converter=list,
        input_type=Tuple[Any, ...],
        output_type=List[Any],
    )


def json_to_dict() -> TypeAdapter[str, Dict[str, Any]]:
    """Create an adapter from JSON string to dict."""
    return TypeAdapter(
        name="json_to_dict",
        converter=json.loads,
        input_type=str,
        output_type=Dict[str, Any],
    )


def dict_to_json(indent: Optional[int] = None) -> TypeAdapter[Dict[str, Any], str]:
    """Create an adapter from dict to JSON string."""
    converter = lambda d: json.dumps(d, indent=indent)
    return TypeAdapter(
        name=f"dict_to_json(indent={indent})",
        converter=converter,
        input_type=Dict[str, Any],
        output_type=str,
    )


def auto_adapter(
    from_type: Type[T_in], to_type: Type[T_out]
) -> Optional[TypeAdapter[T_in, T_out]]:
    """Attempt to create an automatic type adapter between two types.

    Returns None if no automatic conversion is available.
    """
    # Handle identical types
    if from_type == to_type:
        return TypeAdapter(
            name=f"identity_{from_type.__name__}",
            converter=lambda x: x,
            input_type=from_type,
            output_type=to_type,
        )

    # String conversions
    if from_type == str:
        if to_type == int:
            return TypeAdapter("str_to_int", int, str, int)
        elif to_type == float:
            return TypeAdapter("str_to_float", float, str, float)
        elif to_type == bool:
            converter = lambda s: s.lower() in ("true", "1", "yes", "on")
            return TypeAdapter("str_to_bool", converter, str, bool)

    # Number conversions
    if from_type in (int, float) and to_type in (int, float):
        return TypeAdapter(
            name=f"{from_type.__name__}_to_{to_type.__name__}",
            converter=to_type,
            input_type=from_type,
            output_type=to_type,
        )

    # Collection conversions
    from_origin = get_origin(from_type)
    to_origin = get_origin(to_type)

    if from_origin == list and to_origin == tuple:
        return list_to_tuple()  # type: ignore
    elif from_origin == tuple and to_origin == list:
        return tuple_to_list()  # type: ignore

    return None


def check_type_compatibility(output_type: Type, input_type: Type) -> bool:
    """Check if two types are compatible for pipe operations.

    This is a more lenient check than strict equality.
    """
    # Exact match
    if output_type == input_type:
        return True

    # Any type is compatible with everything
    if output_type == Any or input_type == Any:
        return True

    # Check if one is a subclass of the other
    try:
        if isinstance(output_type, type) and isinstance(input_type, type):
            if issubclass(output_type, input_type) or issubclass(
                input_type, output_type
            ):
                return True
    except TypeError:
        # Handle generic types that can't be used with issubclass
        pass

    # Check generic origins (e.g., List[str] compatible with List[Any])
    output_origin = get_origin(output_type)
    input_origin = get_origin(input_type)

    if output_origin and input_origin and output_origin == input_origin:
        # For now, consider same generic types compatible
        # More sophisticated checking could examine type parameters
        return True

    return False


def suggest_adapter(output_type: Type, input_type: Type) -> Optional[str]:
    """Suggest an adapter for incompatible types."""
    adapter = auto_adapter(output_type, input_type)
    if adapter:
        return f"Use {adapter.name} adapter or create a custom TypeAdapter"

    # Provide specific suggestions
    if output_type == str and get_origin(input_type) == dict:
        return "Use dict_to_string() adapter"
    elif output_type == dict and input_type == str:
        return "Use string_to_dict() adapter"
    elif get_origin(output_type) == list and get_origin(input_type) == tuple:
        return "Use tuple_to_list() adapter"
    elif get_origin(output_type) == tuple and get_origin(input_type) == list:
        return "Use list_to_tuple() adapter"

    return None
