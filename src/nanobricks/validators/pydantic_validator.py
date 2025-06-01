"""Pydantic model validation nanobrick."""

from typing import Any, TypeVar

from nanobricks.validators.base import ValidatorBase

T = TypeVar("T")


class PydanticValidator(ValidatorBase[T]):
    """Validates data using Pydantic models.

    Features:
    - Full Pydantic validation
    - Automatic type coercion
    - Custom validation methods
    - Model export options
    """

    def __init__(
        self,
        model: type[T],
        *,
        strict: bool = False,
        coerce_types: bool = True,
        use_enum_values: bool = True,
        export_format: str | None = None,
        exclude_unset: bool = False,
        exclude_defaults: bool = False,
        custom_validators: dict[str, callable] | None = None,
        name: str | None = None,
        version: str = "1.0.0",
    ):
        """Initialize Pydantic validator.

        Args:
            model: Pydantic model class
            strict: Whether to use strict validation
            coerce_types: Whether to coerce types
            use_enum_values: Whether to use enum values
            export_format: Format for output (dict, json, model)
            exclude_unset: Exclude unset fields in output
            exclude_defaults: Exclude default fields in output
            custom_validators: Additional custom validators
            name: Validator name (defaults to model name)
            version: Validator version
        """
        # Check if pydantic is available
        try:
            import pydantic

            self._pydantic = pydantic

            # Check if model is a Pydantic model
            if not (isinstance(model, type) and issubclass(model, pydantic.BaseModel)):
                raise ValueError(f"{model} is not a Pydantic BaseModel")

        except ImportError:
            raise ImportError(
                "pydantic package required. Install with: pip install pydantic"
            )

        super().__init__(
            name=name or f"{model.__name__.lower()}_validator", version=version
        )

        self.model = model
        self.strict = strict
        self.coerce_types = coerce_types
        self.use_enum_values = use_enum_values
        self.export_format = export_format or "model"
        self.exclude_unset = exclude_unset
        self.exclude_defaults = exclude_defaults
        self.custom_validators = custom_validators or {}

    async def validate(self, value: Any) -> T | dict[str, Any] | str:
        """Validate value using Pydantic model.

        Args:
            value: Value to validate

        Returns:
            Validated model instance or exported format

        Raises:
            ValueError: If validation fails
        """
        # Apply custom validators first
        if self.custom_validators:
            for field, validator in self.custom_validators.items():
                if isinstance(value, dict) and field in value:
                    try:
                        value[field] = validator(value[field])
                    except Exception as e:
                        raise ValueError(f"Custom validation failed for {field}: {e}")

        # Create model instance
        try:
            if self.strict:
                # Use Pydantic v2 strict mode if available
                if hasattr(self.model, "model_validate"):
                    instance = self.model.model_validate(value, strict=True)
                else:
                    # Fallback for Pydantic v1
                    instance = self.model.parse_obj(value)
            else:
                # Normal validation with type coercion
                if hasattr(self.model, "model_validate"):
                    instance = self.model.model_validate(value)
                else:
                    instance = (
                        self.model(**value)
                        if isinstance(value, dict)
                        else self.model.parse_obj(value)
                    )

        except self._pydantic.ValidationError as e:
            # Format error messages
            errors = []
            for error in e.errors():
                loc = ".".join(str(l) for l in error.get("loc", []))
                msg = error.get("msg", "Unknown error")
                errors.append(f"  - {loc}: {msg}")

            raise ValueError("Pydantic validation failed:\n" + "\n".join(errors))

        # Export in requested format
        if self.export_format == "dict":
            if hasattr(instance, "model_dump"):
                # Pydantic v2
                return instance.model_dump(
                    mode="python",
                    exclude_unset=self.exclude_unset,
                    exclude_defaults=self.exclude_defaults,
                    by_alias=False,
                )
            else:
                # Pydantic v1
                return instance.dict(
                    exclude_unset=self.exclude_unset,
                    exclude_defaults=self.exclude_defaults,
                    by_alias=False,
                )

        elif self.export_format == "json":
            if hasattr(instance, "model_dump_json"):
                # Pydantic v2
                return instance.model_dump_json(
                    exclude_unset=self.exclude_unset,
                    exclude_defaults=self.exclude_defaults,
                    by_alias=False,
                )
            else:
                # Pydantic v1
                return instance.json(
                    exclude_unset=self.exclude_unset,
                    exclude_defaults=self.exclude_defaults,
                    by_alias=False,
                )

        else:  # model format
            return instance


class PydanticListValidator(ValidatorBase[list[T]]):
    """Validates a list of Pydantic models."""

    def __init__(
        self,
        model: type[T],
        *,
        min_items: int | None = None,
        max_items: int | None = None,
        unique_fields: list[str] | None = None,
        strict: bool = False,
        export_format: str | None = None,
        name: str | None = None,
        version: str = "1.0.0",
    ):
        """Initialize Pydantic list validator.

        Args:
            model: Pydantic model class
            min_items: Minimum number of items
            max_items: Maximum number of items
            unique_fields: Fields that must be unique
            strict: Whether to use strict validation
            export_format: Format for output
            name: Validator name
            version: Validator version
        """
        super().__init__(
            name=name or f"{model.__name__.lower()}_list_validator", version=version
        )

        self.item_validator = PydanticValidator(
            model, strict=strict, export_format=export_format
        )
        self.min_items = min_items
        self.max_items = max_items
        self.unique_fields = unique_fields or []

    async def validate(self, value: list[Any]) -> list[T | dict[str, Any] | str]:
        """Validate list of Pydantic models.

        Args:
            value: List to validate

        Returns:
            List of validated models

        Raises:
            ValueError: If validation fails
        """
        if not isinstance(value, list):
            raise ValueError(f"Expected list, got {type(value).__name__}")

        # Check list constraints
        if self.min_items is not None and len(value) < self.min_items:
            raise ValueError(f"Too few items: {len(value)} < {self.min_items}")

        if self.max_items is not None and len(value) > self.max_items:
            raise ValueError(f"Too many items: {len(value)} > {self.max_items}")

        # Validate each item
        validated = []
        seen_values = {field: set() for field in self.unique_fields}

        for i, item in enumerate(value):
            try:
                valid_item = await self.item_validator.validate(item)

                # Check uniqueness
                if self.unique_fields and isinstance(valid_item, dict):
                    for field in self.unique_fields:
                        if field in valid_item:
                            field_value = valid_item[field]
                            if field_value in seen_values[field]:
                                raise ValueError(
                                    f"Duplicate value for {field}: {field_value}"
                                )
                            seen_values[field].add(field_value)

                validated.append(valid_item)

            except ValueError as e:
                raise ValueError(f"Item at index {i}: {e}")

        return validated


def create_pydantic_validator(
    name: str,
    fields: dict[str, tuple[type, Any]],
    *,
    validators: dict[str, callable] | None = None,
    config: dict[str, Any] | None = None,
) -> type[PydanticValidator]:
    """Factory to create a Pydantic validator dynamically.

    Args:
        name: Model name
        fields: Field definitions as {name: (type, default)}
        validators: Field validators
        config: Pydantic config options

    Returns:
        PydanticValidator instance
    """
    try:
        from pydantic import Field, create_model
    except ImportError:
        raise ImportError("pydantic required for dynamic model creation")

    # Build field definitions
    field_defs = {}
    for field_name, (field_type, default) in fields.items():
        if default is ...:  # Required field
            field_defs[field_name] = (field_type, Field(...))
        else:
            field_defs[field_name] = (field_type, Field(default=default))

    # Create model class
    model_config = config or {}
    model = create_model(
        name,
        __config__=type("Config", (), model_config),
        __validators__=validators or {},
        **field_defs,
    )

    # Return validator instance
    return PydanticValidator(model)
