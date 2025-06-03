"""Tests for the typing module utilities."""

import pytest
from typing import Dict, List, Tuple, Any
import json

from nanobricks.typing import (
    Result,
    TypeAdapter,
    TypeMismatchError,
    auto_adapter,
    check_type_compatibility,
    dict_to_json,
    dict_to_string,
    json_to_dict,
    list_to_tuple,
    string_to_dict,
    tuple_to_list,
)
from nanobricks import Nanobrick
from nanobricks.protocol import NanobrickBase


class TestResult:
    """Test the Result type for error handling."""

    def test_ok_result(self):
        """Test creating and using a successful Result."""
        result = Result.ok(42)
        assert result.is_ok
        assert not result.is_err
        assert result.unwrap() == 42
        assert result.unwrap_or(0) == 42
        assert str(result) == "Ok(42)"

    def test_err_result(self):
        """Test creating and using an error Result."""
        result = Result.err("error message")
        assert not result.is_ok
        assert result.is_err
        assert result.unwrap_err() == "error message"
        assert result.unwrap_or(42) == 42
        assert str(result) == "Err('error message')"

    def test_result_cannot_be_both(self):
        """Test that Result cannot have both value and error."""
        with pytest.raises(ValueError, match="cannot have both"):
            Result(value=42, error="error")

    def test_result_must_have_one(self):
        """Test that Result must have either value or error."""
        with pytest.raises(ValueError, match="must have either"):
            Result()

    def test_unwrap_on_error_raises(self):
        """Test that unwrap on error Result raises."""
        result = Result.err("error")
        with pytest.raises(ValueError, match="Called unwrap on an error"):
            result.unwrap()

    def test_unwrap_err_on_ok_raises(self):
        """Test that unwrap_err on ok Result raises."""
        result = Result.ok(42)
        with pytest.raises(ValueError, match="Called unwrap_err on an ok"):
            result.unwrap_err()

    def test_map_on_ok(self):
        """Test mapping function on successful Result."""
        result = Result.ok(42)
        mapped = result.map(lambda x: x * 2)
        assert mapped.unwrap() == 84

    def test_map_on_err(self):
        """Test mapping function on error Result (no effect)."""
        result: Result[int, str] = Result.err("error")
        mapped = result.map(lambda x: x * 2)
        assert mapped.is_err
        assert mapped.unwrap_err() == "error"

    def test_map_err_on_err(self):
        """Test mapping error on error Result."""
        result = Result.err("error")
        mapped = result.map_err(lambda e: f"wrapped: {e}")
        assert mapped.unwrap_err() == "wrapped: error"

    def test_map_err_on_ok(self):
        """Test mapping error on ok Result (no effect)."""
        result: Result[int, str] = Result.ok(42)
        mapped = result.map_err(lambda e: f"wrapped: {e}")
        assert mapped.is_ok
        assert mapped.unwrap() == 42


class TestTypeAdapter:
    """Test the TypeAdapter class."""

    def test_create_adapter(self):
        """Test creating a basic type adapter."""
        adapter = TypeAdapter(
            name="test_adapter", converter=str, input_type=int, output_type=str
        )
        assert adapter.name == "test_adapter"
        assert adapter.version == "1.0.0"
        assert repr(adapter) == "TypeAdapter(test_adapter: int -> str)"

    async def test_adapter_invoke(self):
        """Test invoking a type adapter."""
        adapter = TypeAdapter(
            name="int_to_str", converter=str, input_type=int, output_type=str
        )
        result = await adapter.invoke(42)
        assert result == "42"

    def test_adapter_sync_invoke(self):
        """Test sync invoke on type adapter."""
        adapter = TypeAdapter(
            name="int_to_str", converter=str, input_type=int, output_type=str
        )
        result = adapter.invoke_sync(42)
        assert result == "42"


class TestTypeConversionHelpers:
    """Test the built-in type conversion helpers."""

    async def test_string_to_dict(self):
        """Test string to dict conversion."""
        adapter = string_to_dict()
        result = await adapter.invoke("a=1,b=2,c=3")
        assert result == {"a": "1", "b": "2", "c": "3"}

    async def test_string_to_dict_custom_delimiters(self):
        """Test string to dict with custom delimiters."""
        adapter = string_to_dict(delimiter=";", key_value_sep=":")
        result = await adapter.invoke("a:1;b:2;c:3")
        assert result == {"a": "1", "b": "2", "c": "3"}

    async def test_string_to_dict_empty(self):
        """Test string to dict with empty string."""
        adapter = string_to_dict()
        result = await adapter.invoke("")
        assert result == {}

    async def test_dict_to_string(self):
        """Test dict to string conversion."""
        adapter = dict_to_string()
        result = await adapter.invoke({"a": "1", "b": "2", "c": "3"})
        assert result in [
            "a=1,b=2,c=3",
            "a=1,c=3,b=2",
            "b=2,a=1,c=3",
            "b=2,c=3,a=1",
            "c=3,a=1,b=2",
            "c=3,b=2,a=1",
        ]

    async def test_dict_to_string_custom_delimiters(self):
        """Test dict to string with custom delimiters."""
        adapter = dict_to_string(delimiter=";", key_value_sep=":")
        result = await adapter.invoke({"a": "1", "b": "2"})
        assert result in ["a:1;b:2", "b:2;a:1"]

    async def test_list_to_tuple(self):
        """Test list to tuple conversion."""
        adapter = list_to_tuple()
        result = await adapter.invoke([1, 2, 3])
        assert result == (1, 2, 3)
        assert isinstance(result, tuple)

    async def test_tuple_to_list(self):
        """Test tuple to list conversion."""
        adapter = tuple_to_list()
        result = await adapter.invoke((1, 2, 3))
        assert result == [1, 2, 3]
        assert isinstance(result, list)

    async def test_json_to_dict(self):
        """Test JSON string to dict conversion."""
        adapter = json_to_dict()
        result = await adapter.invoke('{"a": 1, "b": 2}')
        assert result == {"a": 1, "b": 2}

    async def test_dict_to_json(self):
        """Test dict to JSON string conversion."""
        adapter = dict_to_json()
        result = await adapter.invoke({"a": 1, "b": 2})
        parsed = json.loads(result)
        assert parsed == {"a": 1, "b": 2}

    async def test_dict_to_json_with_indent(self):
        """Test dict to JSON with indentation."""
        adapter = dict_to_json(indent=2)
        result = await adapter.invoke({"a": 1})
        assert '{\n  "a": 1\n}' == result


class TestAutoAdapter:
    """Test automatic adapter creation."""

    def test_auto_adapter_identity(self):
        """Test auto adapter for same types."""
        adapter = auto_adapter(str, str)
        assert adapter is not None
        assert adapter.name == "identity_str"

    def test_auto_adapter_str_to_int(self):
        """Test auto adapter from string to int."""
        adapter = auto_adapter(str, int)
        assert adapter is not None
        assert adapter.name == "str_to_int"

    def test_auto_adapter_str_to_float(self):
        """Test auto adapter from string to float."""
        adapter = auto_adapter(str, float)
        assert adapter is not None
        assert adapter.name == "str_to_float"

    async def test_auto_adapter_str_to_bool(self):
        """Test auto adapter from string to bool."""
        adapter = auto_adapter(str, bool)
        assert adapter is not None
        assert adapter.name == "str_to_bool"

        # Test various true values
        assert await adapter.invoke("true") == True
        assert await adapter.invoke("True") == True
        assert await adapter.invoke("1") == True
        assert await adapter.invoke("yes") == True
        assert await adapter.invoke("on") == True

        # Test false values
        assert await adapter.invoke("false") == False
        assert await adapter.invoke("0") == False
        assert await adapter.invoke("no") == False

    def test_auto_adapter_number_conversions(self):
        """Test auto adapter between number types."""
        adapter = auto_adapter(int, float)
        assert adapter is not None
        assert adapter.name == "int_to_float"

        adapter = auto_adapter(float, int)
        assert adapter is not None
        assert adapter.name == "float_to_int"

    def test_auto_adapter_list_tuple(self):
        """Test auto adapter between list and tuple."""
        from typing import List, Tuple

        adapter = auto_adapter(List[int], Tuple[int, ...])
        assert adapter is not None

        adapter = auto_adapter(Tuple[int, ...], List[int])
        assert adapter is not None

    def test_auto_adapter_none_for_incompatible(self):
        """Test auto adapter returns None for incompatible types."""
        adapter = auto_adapter(str, dict)
        assert adapter is None

        adapter = auto_adapter(list, dict)
        assert adapter is None


class TestTypeCompatibility:
    """Test type compatibility checking."""

    def test_exact_match(self):
        """Test exact type match."""
        assert check_type_compatibility(str, str)
        assert check_type_compatibility(int, int)
        assert check_type_compatibility(List[str], List[str])

    def test_any_type(self):
        """Test Any type is compatible with everything."""
        assert check_type_compatibility(Any, str)
        assert check_type_compatibility(str, Any)
        assert check_type_compatibility(Any, Any)

    def test_subclass_compatibility(self):
        """Test subclass compatibility."""

        class Base:
            pass

        class Derived(Base):
            pass

        assert check_type_compatibility(Derived, Base)
        assert check_type_compatibility(Base, Derived)

    def test_generic_origin_compatibility(self):
        """Test generic types with same origin are compatible."""
        assert check_type_compatibility(List[str], List[Any])
        assert check_type_compatibility(Dict[str, int], Dict[Any, Any])
        assert check_type_compatibility(Tuple[int, ...], Tuple[Any, ...])

    def test_incompatible_types(self):
        """Test incompatible types."""
        assert not check_type_compatibility(str, int)
        assert not check_type_compatibility(List[str], Dict[str, str])
        assert not check_type_compatibility(list, dict)


class TestTypeMismatchError:
    """Test enhanced type mismatch errors."""

    def test_error_creation(self):
        """Test creating a type mismatch error."""
        error = TypeMismatchError(
            left_brick="StringBrick",
            right_brick="IntBrick",
            output_type=str,
            expected_type=int,
            suggestion="Use str_to_int adapter",
        )

        assert error.left_brick == "StringBrick"
        assert error.right_brick == "IntBrick"
        assert error.output_type == str
        assert error.expected_type == int
        assert error.suggestion == "Use str_to_int adapter"

        message = str(error)
        assert "StringBrick outputs: str" in message
        assert "IntBrick expects: int" in message
        assert "Use str_to_int adapter" in message

    def test_error_without_suggestion(self):
        """Test error without suggestion."""
        error = TypeMismatchError(
            left_brick="A", right_brick="B", output_type=list, expected_type=dict
        )

        message = str(error)
        assert "Suggestion:" not in message


class TestPipeOperatorWithTypeChecking:
    """Test pipe operator with enhanced type checking."""

    def test_compatible_types_work(self):
        """Test that compatible types still work."""

        class StringToInt(Nanobrick[str, int]):
            name = "string_to_int"

            async def invoke(self, input: str) -> int:
                return int(input)

        class IntToString(Nanobrick[int, str]):
            name = "int_to_string"

            async def invoke(self, input: int) -> str:
                return str(input)

        # This should work fine
        pipeline = StringToInt() | IntToString()
        assert pipeline.name == "StringToInt|IntToString"

    def test_with_type_adapter(self):
        """Test using type adapters in pipelines."""

        class ProduceString(Nanobrick[None, str]):
            name = "produce_string"

            async def invoke(self, input: None) -> str:
                return "key1=value1,key2=value2"

        class ConsumeDict(Nanobrick[Dict[str, str], str]):
            name = "consume_dict"

            async def invoke(self, input: Dict[str, str]) -> str:
                return f"Got {len(input)} items"

        # Use adapter to make types compatible
        pipeline = ProduceString() | string_to_dict() | ConsumeDict()
        assert "string_to_dict" in pipeline.name
