"""Range validator for the nanobricks framework."""

from typing import Union

from nanobricks.validators.base import ValidatorBrick

Numeric = Union[int, float]


class RangeValidator(ValidatorBrick[Numeric]):
    """Validates that numeric input is within specified range."""

    def __init__(
        self,
        min_value: Numeric | None = None,
        max_value: Numeric | None = None,
        inclusive_min: bool = True,
        inclusive_max: bool = True,
        name: str = "range_validator",
        version: str = "1.0.0",
    ):
        """Initialize the range validator.

        Args:
            min_value: Minimum allowed value (None for no minimum)
            max_value: Maximum allowed value (None for no maximum)
            inclusive_min: Whether min_value is inclusive
            inclusive_max: Whether max_value is inclusive
            name: Name of the validator
            version: Version of the validator
        """
        super().__init__(name, version)
        self.min_value = min_value
        self.max_value = max_value
        self.inclusive_min = inclusive_min
        self.inclusive_max = inclusive_max

        if min_value is not None and max_value is not None and min_value > max_value:
            raise ValueError(
                f"min_value ({min_value}) cannot be greater than max_value ({max_value})"
            )

    def validate(self, input: Numeric) -> None:
        """Validate that input is within range.

        Args:
            input: Numeric input to validate

        Raises:
            ValueError: If input is outside the specified range
        """
        if not isinstance(input, (int, float)):
            raise ValueError(f"Expected numeric input, got {type(input).__name__}")

        if self.min_value is not None:
            if self.inclusive_min:
                if input < self.min_value:
                    raise ValueError(
                        f"Value {input} is less than minimum {self.min_value}"
                    )
            else:
                if input <= self.min_value:
                    raise ValueError(
                        f"Value {input} is less than or equal to minimum {self.min_value}"
                    )

        if self.max_value is not None:
            if self.inclusive_max:
                if input > self.max_value:
                    raise ValueError(
                        f"Value {input} is greater than maximum {self.max_value}"
                    )
            else:
                if input >= self.max_value:
                    raise ValueError(
                        f"Value {input} is greater than or equal to maximum {self.max_value}"
                    )
