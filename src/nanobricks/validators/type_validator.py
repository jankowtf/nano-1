"""Type validator for the nanobricks framework."""

from typing import Any, get_origin

from nanobricks.validators.base import ValidatorBrick


class TypeValidator(ValidatorBrick[Any]):
    """Validates that input matches expected type(s)."""

    def __init__(
        self,
        expected_type: type[Any] | tuple[type[Any], ...],
        name: str = "type_validator",
        version: str = "1.0.0",
    ):
        """Initialize the type validator.

        Args:
            expected_type: Expected type or tuple of types
            name: Name of the validator
            version: Version of the validator
        """
        super().__init__(name, version)
        self.expected_type = expected_type

    def validate(self, input: Any) -> None:
        """Validate that input matches expected type.

        Args:
            input: Input to validate

        Raises:
            ValueError: If input doesn't match expected type
        """
        if isinstance(self.expected_type, tuple):
            if not isinstance(input, self.expected_type):
                types_str = ", ".join(t.__name__ for t in self.expected_type)
                raise ValueError(
                    f"Expected one of types [{types_str}], got {type(input).__name__}"
                )
        else:
            # Handle generic types like List[int], Dict[str, int]
            origin = get_origin(self.expected_type)
            if origin is not None:
                # Check base type first
                if not isinstance(input, origin):
                    raise ValueError(
                        f"Expected type {self.expected_type}, got {type(input).__name__}"
                    )
                # For now, we don't validate generic parameters deeply
                # This could be extended to validate List[int] elements, etc.
            else:
                if not isinstance(input, self.expected_type):
                    raise ValueError(
                        f"Expected type {self.expected_type.__name__}, got {type(input).__name__}"
                    )
