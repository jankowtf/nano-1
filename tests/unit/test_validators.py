"""Unit tests for validators."""

import re

import pytest

from nanobricks.validators import (
    LengthValidator,
    RangeValidator,
    RegexValidator,
    SchemaValidator,
    TypeValidator,
    ValidatorBrick,
)


class TestValidatorBrick:
    """Tests for the base ValidatorBrick class."""

    def test_base_validator_not_implemented(self):
        """Test that base validator raises NotImplementedError."""
        validator = ValidatorBrick[str]()

        with pytest.raises(NotImplementedError):
            validator.invoke_sync("test")

        with pytest.raises(NotImplementedError):
            validator.validate("test")

    @pytest.mark.asyncio
    async def test_base_validator_async_not_implemented(self):
        """Test that base validator raises NotImplementedError in async mode."""
        validator = ValidatorBrick[str]()

        with pytest.raises(NotImplementedError):
            await validator.invoke("test")


class TestTypeValidator:
    """Tests for TypeValidator."""

    def test_single_type_valid(self):
        """Test validation with single type - valid input."""
        validator = TypeValidator(int)
        assert validator.invoke_sync(42) == 42

    def test_single_type_invalid(self):
        """Test validation with single type - invalid input."""
        validator = TypeValidator(int)

        with pytest.raises(ValueError, match="Expected type int, got str"):
            validator.invoke_sync("not an int")

    def test_multiple_types_valid(self):
        """Test validation with multiple types - valid inputs."""
        validator = TypeValidator((int, str))
        assert validator.invoke_sync(42) == 42
        assert validator.invoke_sync("hello") == "hello"

    def test_multiple_types_invalid(self):
        """Test validation with multiple types - invalid input."""
        validator = TypeValidator((int, str))

        with pytest.raises(
            ValueError, match="Expected one of types \\[int, str\\], got list"
        ):
            validator.invoke_sync([1, 2, 3])

    def test_generic_type_validation(self):
        """Test validation with generic types."""
        validator = TypeValidator(list[int])
        assert validator.invoke_sync([1, 2, 3]) == [1, 2, 3]

        with pytest.raises(ValueError):
            validator.invoke_sync("not a list")

    @pytest.mark.asyncio
    async def test_async_validation(self):
        """Test async validation."""
        validator = TypeValidator(str)
        assert await validator.invoke("hello") == "hello"

        with pytest.raises(ValueError):
            await validator.invoke(123)


class TestRangeValidator:
    """Tests for RangeValidator."""

    def test_min_only_valid(self):
        """Test validation with only minimum - valid input."""
        validator = RangeValidator(min_value=0)
        assert validator.invoke_sync(0) == 0
        assert validator.invoke_sync(100) == 100

    def test_min_only_invalid(self):
        """Test validation with only minimum - invalid input."""
        validator = RangeValidator(min_value=0)

        with pytest.raises(ValueError, match="Value -1 is less than minimum 0"):
            validator.invoke_sync(-1)

    def test_max_only_valid(self):
        """Test validation with only maximum - valid input."""
        validator = RangeValidator(max_value=100)
        assert validator.invoke_sync(0) == 0
        assert validator.invoke_sync(100) == 100

    def test_max_only_invalid(self):
        """Test validation with only maximum - invalid input."""
        validator = RangeValidator(max_value=100)

        with pytest.raises(ValueError, match="Value 101 is greater than maximum 100"):
            validator.invoke_sync(101)

    def test_range_inclusive(self):
        """Test validation with inclusive range."""
        validator = RangeValidator(min_value=0, max_value=10)
        assert validator.invoke_sync(0) == 0
        assert validator.invoke_sync(5) == 5
        assert validator.invoke_sync(10) == 10

    def test_range_exclusive(self):
        """Test validation with exclusive range."""
        validator = RangeValidator(
            min_value=0, max_value=10, inclusive_min=False, inclusive_max=False
        )
        assert validator.invoke_sync(1) == 1
        assert validator.invoke_sync(9) == 9

        with pytest.raises(ValueError, match="less than or equal to minimum"):
            validator.invoke_sync(0)

        with pytest.raises(ValueError, match="greater than or equal to maximum"):
            validator.invoke_sync(10)

    def test_non_numeric_input(self):
        """Test validation with non-numeric input."""
        validator = RangeValidator(min_value=0)

        with pytest.raises(ValueError, match="Expected numeric input, got str"):
            validator.invoke_sync("not a number")

    def test_invalid_range_construction(self):
        """Test that invalid range construction raises error."""
        with pytest.raises(
            ValueError, match="min_value .* cannot be greater than max_value"
        ):
            RangeValidator(min_value=10, max_value=5)

    def test_float_values(self):
        """Test validation with float values."""
        validator = RangeValidator(min_value=0.0, max_value=1.0)
        assert validator.invoke_sync(0.5) == 0.5

        with pytest.raises(ValueError):
            validator.invoke_sync(1.5)


class TestSchemaValidator:
    """Tests for SchemaValidator."""

    def test_simple_schema_valid(self):
        """Test validation with simple schema - valid input."""
        schema = {"name": str, "age": int, "active": bool}
        validator = SchemaValidator(schema)

        data = {"name": "John", "age": 30, "active": True}
        assert validator.invoke_sync(data) == data

    def test_missing_required_field(self):
        """Test validation with missing required field."""
        schema = {"name": str, "age": int}
        validator = SchemaValidator(schema)

        with pytest.raises(ValueError, match="Missing required fields: \\['age'\\]"):
            validator.invoke_sync({"name": "John"})

    def test_optional_fields(self):
        """Test validation with optional fields."""
        schema = {"name": str, "age": int, "email": str}
        validator = SchemaValidator(schema, required_fields=["name"])

        data = {"name": "John"}
        assert validator.invoke_sync(data) == data

    def test_extra_fields_disallowed(self):
        """Test validation with extra fields disallowed."""
        schema = {"name": str}
        validator = SchemaValidator(schema, allow_extra_fields=False)

        with pytest.raises(ValueError, match="Unexpected fields: \\['extra'\\]"):
            validator.invoke_sync({"name": "John", "extra": "field"})

    def test_extra_fields_allowed(self):
        """Test validation with extra fields allowed."""
        schema = {"name": str}
        validator = SchemaValidator(schema, allow_extra_fields=True)

        data = {"name": "John", "extra": "field"}
        assert validator.invoke_sync(data) == data

    def test_wrong_field_type(self):
        """Test validation with wrong field type."""
        schema = {"age": int}
        validator = SchemaValidator(schema)

        with pytest.raises(ValueError, match="Field 'age' expected type int, got str"):
            validator.invoke_sync({"age": "thirty"})

    def test_multiple_allowed_types(self):
        """Test validation with multiple allowed types for a field."""
        schema = {"value": (int, str)}
        validator = SchemaValidator(schema)

        assert validator.invoke_sync({"value": 42}) == {"value": 42}
        assert validator.invoke_sync({"value": "42"}) == {"value": "42"}

        with pytest.raises(ValueError, match="Field 'value' expected one of types"):
            validator.invoke_sync({"value": 42.0})

    def test_validation_function(self):
        """Test validation with custom validation function."""

        def is_positive(x):
            return isinstance(x, (int, float)) and x > 0

        schema = {"price": is_positive}
        validator = SchemaValidator(schema)

        assert validator.invoke_sync({"price": 10.99}) == {"price": 10.99}

        with pytest.raises(ValueError, match="Field 'price' failed validation"):
            validator.invoke_sync({"price": -5})

    def test_non_dict_input(self):
        """Test validation with non-dict input."""
        validator = SchemaValidator({"name": str})

        with pytest.raises(ValueError, match="Expected dict input, got list"):
            validator.invoke_sync([1, 2, 3])


class TestLengthValidator:
    """Tests for LengthValidator."""

    def test_exact_length_valid(self):
        """Test validation with exact length - valid input."""
        validator = LengthValidator(exact_length=5)
        assert validator.invoke_sync("hello") == "hello"
        assert validator.invoke_sync([1, 2, 3, 4, 5]) == [1, 2, 3, 4, 5]

    def test_exact_length_invalid(self):
        """Test validation with exact length - invalid input."""
        validator = LengthValidator(exact_length=5)

        with pytest.raises(ValueError, match="Expected length 5, got 3"):
            validator.invoke_sync("bye")

    def test_min_length_valid(self):
        """Test validation with minimum length - valid input."""
        validator = LengthValidator(min_length=3)
        assert validator.invoke_sync("hello") == "hello"
        assert validator.invoke_sync("bye") == "bye"

    def test_min_length_invalid(self):
        """Test validation with minimum length - invalid input."""
        validator = LengthValidator(min_length=3)

        with pytest.raises(ValueError, match="Length 2 is less than minimum 3"):
            validator.invoke_sync("hi")

    def test_max_length_valid(self):
        """Test validation with maximum length - valid input."""
        validator = LengthValidator(max_length=5)
        assert validator.invoke_sync("hello") == "hello"
        assert validator.invoke_sync("hi") == "hi"

    def test_max_length_invalid(self):
        """Test validation with maximum length - invalid input."""
        validator = LengthValidator(max_length=5)

        with pytest.raises(ValueError, match="Length 6 is greater than maximum 5"):
            validator.invoke_sync("hello!")

    def test_min_max_length(self):
        """Test validation with both min and max length."""
        validator = LengthValidator(min_length=2, max_length=5)
        assert validator.invoke_sync("hi") == "hi"
        assert validator.invoke_sync("hello") == "hello"

        with pytest.raises(ValueError):
            validator.invoke_sync("x")

        with pytest.raises(ValueError):
            validator.invoke_sync("toolong")

    def test_no_length_attribute(self):
        """Test validation with input that has no length."""
        validator = LengthValidator(min_length=1)

        with pytest.raises(ValueError, match="Input of type int has no length"):
            validator.invoke_sync(42)

    def test_invalid_length_construction(self):
        """Test that invalid length construction raises error."""
        with pytest.raises(ValueError, match="exact_length must be non-negative"):
            LengthValidator(exact_length=-1)

        with pytest.raises(ValueError, match="min_length must be non-negative"):
            LengthValidator(min_length=-1)

        with pytest.raises(ValueError, match="max_length must be non-negative"):
            LengthValidator(max_length=-1)

        with pytest.raises(
            ValueError, match="min_length .* cannot be greater than max_length"
        ):
            LengthValidator(min_length=10, max_length=5)

    def test_various_sized_types(self):
        """Test validation with various types that have length."""
        validator = LengthValidator(min_length=2, max_length=4)

        # String
        assert validator.invoke_sync("abc") == "abc"

        # List
        assert validator.invoke_sync([1, 2, 3]) == [1, 2, 3]

        # Tuple
        assert validator.invoke_sync((1, 2)) == (1, 2)

        # Dict
        assert validator.invoke_sync({"a": 1, "b": 2}) == {"a": 1, "b": 2}

        # Set
        assert validator.invoke_sync({1, 2, 3}) == {1, 2, 3}


class TestRegexValidator:
    """Tests for RegexValidator."""

    def test_simple_pattern_match(self):
        """Test validation with simple pattern - match."""
        validator = RegexValidator(r"\d+")
        assert validator.invoke_sync("123") == "123"
        assert validator.invoke_sync("abc123def") == "abc123def"

    def test_simple_pattern_no_match(self):
        """Test validation with simple pattern - no match."""
        validator = RegexValidator(r"\d+")

        with pytest.raises(ValueError, match="does not match pattern"):
            validator.invoke_sync("abc")

    def test_full_match(self):
        """Test validation with full match requirement."""
        validator = RegexValidator(r"\d+", full_match=True)
        assert validator.invoke_sync("123") == "123"

        with pytest.raises(ValueError, match="does not fully match pattern"):
            validator.invoke_sync("abc123")

    def test_compiled_pattern(self):
        """Test validation with pre-compiled pattern."""
        pattern = re.compile(r"[A-Z]+", re.IGNORECASE)
        validator = RegexValidator(pattern)
        assert validator.invoke_sync("hello") == "hello"
        assert validator.invoke_sync("HELLO") == "HELLO"

    def test_pattern_with_flags(self):
        """Test validation with pattern flags."""
        validator = RegexValidator(r"hello", flags=re.IGNORECASE)
        assert validator.invoke_sync("HELLO world") == "HELLO world"
        assert validator.invoke_sync("hello world") == "hello world"

    def test_custom_error_message(self):
        """Test validation with custom error message."""
        validator = RegexValidator(
            r"^\d{3}-\d{3}-\d{4}$",
            full_match=True,
            error_message="Invalid phone number format",
        )

        with pytest.raises(ValueError, match="Invalid phone number format"):
            validator.invoke_sync("123-45-6789")

    def test_email_pattern(self):
        """Test validation with email pattern."""
        email_pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
        validator = RegexValidator(email_pattern, full_match=True)

        assert validator.invoke_sync("user@example.com") == "user@example.com"
        assert (
            validator.invoke_sync("test.email+tag@domain.co.uk")
            == "test.email+tag@domain.co.uk"
        )

        with pytest.raises(ValueError):
            validator.invoke_sync("invalid.email")

        with pytest.raises(ValueError):
            validator.invoke_sync("@example.com")

    def test_non_string_input(self):
        """Test validation with non-string input."""
        validator = RegexValidator(r"\d+")

        with pytest.raises(ValueError, match="Expected string input, got int"):
            validator.invoke_sync(123)

    @pytest.mark.asyncio
    async def test_async_regex_validation(self):
        """Test async regex validation."""
        validator = RegexValidator(r"^test")
        assert await validator.invoke("test123") == "test123"

        with pytest.raises(ValueError):
            await validator.invoke("123test")
