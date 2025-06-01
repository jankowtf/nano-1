"""Enhanced JSON Schema validation with additional features."""

import json
from pathlib import Path
from typing import Any

from nanobricks.validators.base import ValidatorBase


class JSONSchemaValidator(ValidatorBase[Any]):
    """Enhanced JSON Schema validator with extra features.

    Features:
    - Standard JSON Schema validation
    - Custom error messages
    - Default value injection
    - Schema composition support
    - External schema references
    """

    def __init__(
        self,
        schema: dict[str, Any] | str | Path,
        *,
        strict: bool = True,
        apply_defaults: bool = True,
        custom_messages: dict[str, str] | None = None,
        allow_additional: bool | None = None,
        coerce_types: bool = False,
        name: str = "json_schema_validator",
        version: str = "1.0.0",
    ):
        """Initialize JSON Schema validator.

        Args:
            schema: JSON schema dict, string, or path to schema file
            strict: Whether to use strict validation
            apply_defaults: Whether to apply default values
            custom_messages: Custom error messages by path
            allow_additional: Override additionalProperties setting
            coerce_types: Whether to coerce compatible types
            name: Validator name
            version: Validator version
        """
        super().__init__(name=name, version=version)

        # Load schema
        if isinstance(schema, (str, Path)):
            schema_path = Path(schema)
            if schema_path.exists():
                with open(schema_path) as f:
                    self.schema = json.load(f)
            else:
                # Try parsing as JSON string
                try:
                    self.schema = json.loads(str(schema))
                except json.JSONDecodeError:
                    raise ValueError("Invalid schema: not a file path or valid JSON")
        else:
            self.schema = schema

        self.strict = strict
        self.apply_defaults = apply_defaults
        self.custom_messages = custom_messages or {}
        self.allow_additional = allow_additional
        self.coerce_types = coerce_types

        # Override additionalProperties if specified
        if self.allow_additional is not None:
            self._override_additional_properties(self.schema)

        # Try to import jsonschema
        try:
            import jsonschema

            self._jsonschema = jsonschema
            self._validator_class = jsonschema.Draft7Validator

            # Check schema validity
            self._validator_class.check_schema(self.schema)
        except ImportError:
            raise ImportError(
                "jsonschema package required. Install with: pip install jsonschema"
            )

    def _override_additional_properties(self, schema: dict[str, Any]) -> None:
        """Recursively override additionalProperties in schema."""
        if isinstance(schema, dict):
            if "properties" in schema and "additionalProperties" not in schema:
                schema["additionalProperties"] = self.allow_additional

            for value in schema.values():
                if isinstance(value, dict):
                    self._override_additional_properties(value)

    async def validate(self, value: Any) -> Any:
        """Validate value against JSON schema.

        Args:
            value: Value to validate

        Returns:
            Valid value (possibly with defaults applied)

        Raises:
            ValueError: If validation fails
        """
        # Coerce types if requested
        if self.coerce_types:
            value = self._coerce_types(value, self.schema)

        # Create validator instance
        validator = self._validator_class(self.schema)

        # Apply defaults if requested
        if self.apply_defaults:
            value = self._apply_defaults(value, self.schema)

        # Collect all errors
        errors = list(validator.iter_errors(value))

        if errors:
            # Format error messages
            if self.custom_messages:
                error_msgs = self._format_custom_errors(errors)
            else:
                error_msgs = self._format_standard_errors(errors)

            if self.strict:
                raise ValueError("Schema validation failed:\n" + "\n".join(error_msgs))
            else:
                # In non-strict mode, just report first error
                raise ValueError(error_msgs[0])

        return value

    def _coerce_types(self, value: Any, schema: dict[str, Any]) -> Any:
        """Attempt to coerce compatible types."""
        if "type" not in schema:
            return value

        expected_type = schema["type"]

        # String to number coercion
        if expected_type in ("number", "integer") and isinstance(value, str):
            try:
                if expected_type == "integer":
                    return int(value)
                else:
                    return float(value)
            except ValueError:
                pass

        # Number to string coercion
        elif expected_type == "string" and isinstance(value, (int, float)):
            return str(value)

        # Boolean coercion
        elif expected_type == "boolean" and isinstance(value, str):
            if value.lower() in ("true", "1", "yes", "on"):
                return True
            elif value.lower() in ("false", "0", "no", "off"):
                return False

        # Recursive coercion for objects
        elif expected_type == "object" and isinstance(value, dict):
            if "properties" in schema:
                for prop, prop_schema in schema["properties"].items():
                    if prop in value:
                        value[prop] = self._coerce_types(value[prop], prop_schema)

        # Recursive coercion for arrays
        elif expected_type == "array" and isinstance(value, list):
            if "items" in schema:
                value = [self._coerce_types(item, schema["items"]) for item in value]

        return value

    def _apply_defaults(self, value: Any, schema: dict[str, Any]) -> Any:
        """Apply default values from schema."""
        if schema.get("type") == "object" and isinstance(value, dict):
            if "properties" in schema:
                for prop, prop_schema in schema["properties"].items():
                    if prop not in value and "default" in prop_schema:
                        value[prop] = prop_schema["default"]
                    elif prop in value:
                        value[prop] = self._apply_defaults(value[prop], prop_schema)

        elif schema.get("type") == "array" and isinstance(value, list):
            if "items" in schema:
                value = [self._apply_defaults(item, schema["items"]) for item in value]

        return value

    def _format_standard_errors(self, errors: list) -> list[str]:
        """Format standard jsonschema errors."""
        messages = []
        for error in errors:
            path = ".".join(str(p) for p in error.path) or "root"
            messages.append(f"  - {path}: {error.message}")
        return messages

    def _format_custom_errors(self, errors: list) -> list[str]:
        """Format errors with custom messages."""
        messages = []
        for error in errors:
            path = ".".join(str(p) for p in error.path) or "root"

            # Check for custom message
            custom_msg = None
            for custom_path, msg in self.custom_messages.items():
                if path == custom_path or path.startswith(custom_path + "."):
                    custom_msg = msg
                    break

            if custom_msg:
                messages.append(f"  - {path}: {custom_msg}")
            else:
                messages.append(f"  - {path}: {error.message}")

        return messages


class JSONSchemaBuilder:
    """Helper class to build JSON schemas programmatically."""

    def __init__(self):
        """Initialize schema builder."""
        self.schema: dict[str, Any] = {
            "$schema": "http://json-schema.org/draft-07/schema#"
        }

    def type(self, type_name: str) -> "JSONSchemaBuilder":
        """Set the type."""
        self.schema["type"] = type_name
        return self

    def properties(self, **props: dict[str, Any]) -> "JSONSchemaBuilder":
        """Add properties for object type."""
        if "properties" not in self.schema:
            self.schema["properties"] = {}
        self.schema["properties"].update(props)
        return self

    def required(self, *fields: str) -> "JSONSchemaBuilder":
        """Mark fields as required."""
        self.schema["required"] = list(fields)
        return self

    def additional_properties(self, allowed: bool) -> "JSONSchemaBuilder":
        """Set additionalProperties."""
        self.schema["additionalProperties"] = allowed
        return self

    def items(self, item_schema: dict[str, Any]) -> "JSONSchemaBuilder":
        """Set array item schema."""
        self.schema["items"] = item_schema
        return self

    def min_length(self, length: int) -> "JSONSchemaBuilder":
        """Set minimum length."""
        self.schema["minLength"] = length
        return self

    def max_length(self, length: int) -> "JSONSchemaBuilder":
        """Set maximum length."""
        self.schema["maxLength"] = length
        return self

    def minimum(self, value: int | float) -> "JSONSchemaBuilder":
        """Set minimum value."""
        self.schema["minimum"] = value
        return self

    def maximum(self, value: int | float) -> "JSONSchemaBuilder":
        """Set maximum value."""
        self.schema["maximum"] = value
        return self

    def pattern(self, regex: str) -> "JSONSchemaBuilder":
        """Set string pattern."""
        self.schema["pattern"] = regex
        return self

    def enum(self, *values: Any) -> "JSONSchemaBuilder":
        """Set enum values."""
        self.schema["enum"] = list(values)
        return self

    def default(self, value: Any) -> "JSONSchemaBuilder":
        """Set default value."""
        self.schema["default"] = value
        return self

    def build(self) -> dict[str, Any]:
        """Build the schema."""
        return self.schema

    def validator(self, **kwargs) -> JSONSchemaValidator:
        """Create a validator from the built schema."""
        return JSONSchemaValidator(self.schema, **kwargs)
