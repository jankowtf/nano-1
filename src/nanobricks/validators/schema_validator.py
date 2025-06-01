"""Schema validator for the nanobricks framework."""

from collections.abc import Callable
from typing import Any

from nanobricks.validators.base import ValidatorBrick


class SchemaValidator(ValidatorBrick[dict[str, Any]]):
    """Validates that input dictionary matches expected schema."""

    def __init__(
        self,
        schema: dict[str, type | tuple[type, ...] | Callable[[Any], bool]],
        required_fields: list[str] | None = None,
        allow_extra_fields: bool = False,
        name: str = "schema_validator",
        version: str = "1.0.0",
    ):
        """Initialize the schema validator.

        Args:
            schema: Expected schema mapping field names to types or validation functions
            required_fields: List of required field names (all fields required if None)
            allow_extra_fields: Whether to allow fields not in schema
            name: Name of the validator
            version: Version of the validator
        """
        super().__init__(name, version)
        self.schema = schema
        self.required_fields = set(required_fields or schema.keys())
        self.allow_extra_fields = allow_extra_fields

    def validate(self, input: dict[str, Any]) -> None:
        """Validate that input matches schema.

        Args:
            input: Dictionary input to validate

        Raises:
            ValueError: If input doesn't match schema
        """
        if not isinstance(input, dict):
            raise ValueError(f"Expected dict input, got {type(input).__name__}")

        # Check required fields
        missing_fields = self.required_fields - set(input.keys())
        if missing_fields:
            raise ValueError(f"Missing required fields: {sorted(missing_fields)}")

        # Check extra fields
        if not self.allow_extra_fields:
            extra_fields = set(input.keys()) - set(self.schema.keys())
            if extra_fields:
                raise ValueError(f"Unexpected fields: {sorted(extra_fields)}")

        # Validate each field
        for field_name, field_value in input.items():
            if field_name not in self.schema:
                continue  # Already handled by extra fields check

            expected = self.schema[field_name]

            if callable(expected) and not isinstance(expected, type):
                # It's a validation function
                try:
                    if not expected(field_value):
                        raise ValueError(f"Field '{field_name}' failed validation")
                except Exception as e:
                    raise ValueError(f"Field '{field_name}' validation error: {str(e)}")
            elif isinstance(expected, tuple):
                # Multiple allowed types
                if not isinstance(field_value, expected):
                    types_str = ", ".join(t.__name__ for t in expected)
                    raise ValueError(
                        f"Field '{field_name}' expected one of types [{types_str}], "
                        f"got {type(field_value).__name__}"
                    )
            else:
                # Single type
                if not isinstance(field_value, expected):
                    raise ValueError(
                        f"Field '{field_name}' expected type {expected.__name__}, "
                        f"got {type(field_value).__name__}"
                    )
