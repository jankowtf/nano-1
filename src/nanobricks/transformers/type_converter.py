"""Enhanced type conversion transformers."""

import ast
import json
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from nanobricks.transformers.base import TransformerBase


class SmartTypeConverter(TransformerBase[Any, Any]):
    """Smart type converter with multiple strategies."""

    def __init__(
        self,
        *,
        target_type: type,
        strict: bool = False,
        fallback: Any | None = None,
        custom_converters: dict[type, callable] | None = None,
        date_format: str = "%Y-%m-%d",
        datetime_format: str = "%Y-%m-%d %H:%M:%S",
        bool_true_values: set | None = None,
        bool_false_values: set | None = None,
        name: str = "smart_type_converter",
        version: str = "1.0.0",
    ):
        """Initialize smart type converter.

        Args:
            target_type: Target type to convert to
            strict: Raise errors on conversion failure
            fallback: Fallback value on failure (if not strict)
            custom_converters: Custom conversion functions by type
            date_format: Format for date parsing
            datetime_format: Format for datetime parsing
            bool_true_values: Values considered True
            bool_false_values: Values considered False
            name: Transformer name
            version: Transformer version
        """
        super().__init__(name=name, version=version)
        self.target_type = target_type
        self.strict = strict
        self.fallback = fallback
        self.custom_converters = custom_converters or {}
        self.date_format = date_format
        self.datetime_format = datetime_format
        self.bool_true_values = bool_true_values or {
            "true",
            "yes",
            "on",
            "1",
            "t",
            "y",
            "enabled",
            "active",
        }
        self.bool_false_values = bool_false_values or {
            "false",
            "no",
            "off",
            "0",
            "f",
            "n",
            "disabled",
            "inactive",
        }

    async def transform(self, input: Any) -> Any:
        """Convert input to target type.

        Args:
            input: Value to convert

        Returns:
            Converted value

        Raises:
            ValueError: If conversion fails in strict mode
        """
        # Handle None
        if input is None:
            if self.strict:
                raise ValueError(f"Cannot convert None to {self.target_type}")
            return self.fallback

        # Already correct type
        if isinstance(input, self.target_type):
            return input

        # Check custom converters first
        input_type = type(input)
        if input_type in self.custom_converters:
            try:
                return self.custom_converters[input_type](input)
            except Exception as e:
                if self.strict:
                    raise ValueError(f"Custom conversion failed: {e}")
                return self.fallback

        try:
            # String conversions
            if isinstance(input, str):
                return self._convert_from_string(input)

            # Numeric conversions
            elif isinstance(input, (int, float, Decimal)):
                return self._convert_from_number(input)

            # Collection conversions
            elif isinstance(input, (list, tuple, set)):
                return self._convert_from_collection(input)

            # Dict conversions
            elif isinstance(input, dict):
                return self._convert_from_dict(input)

            # Default conversion attempt
            else:
                return self.target_type(input)

        except Exception as e:
            if self.strict:
                raise ValueError(
                    f"Cannot convert {type(input).__name__} to {self.target_type.__name__}: {e}"
                )
            return self.fallback

    def _convert_from_string(self, value: str) -> Any:
        """Convert from string."""
        value = value.strip()

        # Bool conversion
        if self.target_type == bool:
            lower = value.lower()
            if lower in self.bool_true_values:
                return True
            elif lower in self.bool_false_values:
                return False
            else:
                raise ValueError(f"Cannot parse '{value}' as boolean")

        # Numeric types
        elif self.target_type in (int, float, Decimal):
            # Remove common formatting
            clean = value.replace(",", "").replace("$", "").strip()
            return self.target_type(clean)

        # Date/time types
        elif self.target_type == date:
            return datetime.strptime(value, self.date_format).date()

        elif self.target_type == datetime:
            return datetime.strptime(value, self.datetime_format)

        # Collections from string
        elif self.target_type in (list, tuple, set):
            # Try to parse as JSON first
            try:
                parsed = json.loads(value)
                return self.target_type(parsed)
            except:
                # Try ast.literal_eval
                try:
                    parsed = ast.literal_eval(value)
                    return self.target_type(parsed)
                except:
                    # Fallback to comma-separated
                    items = [i.strip() for i in value.split(",")]
                    return self.target_type(items)

        # Dict from string
        elif self.target_type == dict:
            try:
                return json.loads(value)
            except:
                return ast.literal_eval(value)

        # Default string conversion
        else:
            return self.target_type(value)

    def _convert_from_number(self, value: int | float | Decimal) -> Any:
        """Convert from numeric type."""
        # Bool from number
        if self.target_type == bool:
            return bool(value)

        # String from number
        elif self.target_type == str:
            return str(value)

        # Between numeric types
        elif self.target_type in (int, float, Decimal):
            return self.target_type(value)

        # Date from timestamp
        elif self.target_type in (date, datetime):
            dt = datetime.fromtimestamp(float(value))
            return dt.date() if self.target_type == date else dt

        else:
            return self.target_type(value)

    def _convert_from_collection(self, value: list | tuple | set) -> Any:
        """Convert from collection."""
        # To string
        if self.target_type == str:
            return json.dumps(list(value))

        # Between collection types
        elif self.target_type in (list, tuple, set):
            return self.target_type(value)

        # To dict (enumerate)
        elif self.target_type == dict:
            return {i: v for i, v in enumerate(value)}

        else:
            return self.target_type(value)

    def _convert_from_dict(self, value: dict) -> Any:
        """Convert from dictionary."""
        # To string
        if self.target_type == str:
            return json.dumps(value)

        # To list (values)
        elif self.target_type in (list, tuple, set):
            return self.target_type(value.values())

        else:
            return self.target_type(value)


class BulkTypeConverter(TransformerBase[list[Any], list[Any]]):
    """Convert types for a list of values."""

    def __init__(
        self,
        *,
        target_type: type,
        skip_errors: bool = True,
        error_value: Any | None = None,
        report_errors: bool = False,
        **converter_kwargs,
    ):
        """Initialize bulk type converter.

        Args:
            target_type: Target type
            skip_errors: Skip values that fail conversion
            error_value: Value to use for failed conversions
            report_errors: Include error report in output
            **converter_kwargs: Arguments for SmartTypeConverter
        """
        super().__init__(
            name=converter_kwargs.pop("name", "bulk_type_converter"),
            version=converter_kwargs.pop("version", "1.0.0"),
        )
        self.converter = SmartTypeConverter(
            target_type=target_type, strict=False, **converter_kwargs
        )
        self.skip_errors = skip_errors
        self.error_value = error_value
        self.report_errors = report_errors
        self.errors = []

    async def transform(self, input: list[Any]) -> list[Any] | dict[str, Any]:
        """Convert list of values.

        Args:
            input: List of values

        Returns:
            Converted list or dict with results and errors
        """
        results = []
        self.errors = []

        for i, value in enumerate(input):
            try:
                converted = await self.converter.transform(value)
                # Check if conversion failed (None result when input wasn't None)
                if converted is None and value is not None:
                    # Track error
                    self.errors.append(
                        {"index": i, "value": value, "error": "Conversion failed"}
                    )
                    # Use error_value if specified
                    if self.error_value is not None:
                        results.append(self.error_value)
                    else:
                        results.append(None)
                else:
                    results.append(converted)
            except Exception as e:
                self.errors.append({"index": i, "value": value, "error": str(e)})
                if self.skip_errors:
                    if self.error_value is not None:
                        results.append(self.error_value)
                    else:
                        results.append(None)
                else:
                    raise

        if self.report_errors:
            return {
                "results": results,
                "errors": self.errors,
                "success_count": len(results) - len(self.errors),
                "error_count": len(self.errors),
            }

        return results


class DynamicTypeConverter(TransformerBase[Any, Any]):
    """Converts values based on dynamic type hints or inference."""

    def __init__(
        self,
        *,
        type_map: dict[str, type] | None = None,
        infer_types: bool = True,
        prefer_numeric: bool = True,
        name: str = "dynamic_type_converter",
        version: str = "1.0.0",
    ):
        """Initialize dynamic type converter.

        Args:
            type_map: Map of field names to types
            infer_types: Try to infer types
            prefer_numeric: Prefer numeric types when inferring
            name: Transformer name
            version: Transformer version
        """
        super().__init__(name=name, version=version)
        self.type_map = type_map or {}
        self.infer_types = infer_types
        self.prefer_numeric = prefer_numeric

    async def transform(self, input: Any) -> Any:
        """Convert based on type inference.

        Args:
            input: Value or dict of values

        Returns:
            Converted value(s)
        """
        if isinstance(input, dict):
            result = {}
            for key, value in input.items():
                if key in self.type_map:
                    # Use explicit type
                    converter = SmartTypeConverter(target_type=self.type_map[key])
                    result[key] = await converter.transform(value)
                elif self.infer_types:
                    # Infer type
                    result[key] = await self._infer_and_convert(value)
                else:
                    result[key] = value
            return result
        else:
            return await self._infer_and_convert(input)

    async def _infer_and_convert(self, value: Any) -> Any:
        """Infer type and convert."""
        if isinstance(value, str):
            # Try numeric conversion first if preferred
            if self.prefer_numeric:
                # Try int
                try:
                    if "." not in value:
                        return int(value.replace(",", ""))
                except:
                    pass

                # Try float
                try:
                    return float(value.replace(",", ""))
                except:
                    pass

            # Try boolean
            lower = value.lower()
            if lower in ("true", "false", "yes", "no"):
                return lower in ("true", "yes")

            # Keep as string
            return value

        # Already a good type
        return value
