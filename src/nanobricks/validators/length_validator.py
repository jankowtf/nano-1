"""Length validator for the nanobricks framework."""

from typing import Protocol, TypeVar

from nanobricks.validators.base import ValidatorBrick


class Sized(Protocol):
    """Protocol for objects with a length."""

    def __len__(self) -> int: ...


T = TypeVar("T", bound=Sized)


class LengthValidator(ValidatorBrick[T]):
    """Validates that input has expected length."""

    def __init__(
        self,
        min_length: int | None = None,
        max_length: int | None = None,
        exact_length: int | None = None,
        name: str = "length_validator",
        version: str = "1.0.0",
    ):
        """Initialize the length validator.

        Args:
            min_length: Minimum allowed length (None for no minimum)
            max_length: Maximum allowed length (None for no maximum)
            exact_length: Exact required length (overrides min/max if set)
            name: Name of the validator
            version: Version of the validator
        """
        super().__init__(name, version)
        self.min_length = min_length
        self.max_length = max_length
        self.exact_length = exact_length

        if exact_length is not None and exact_length < 0:
            raise ValueError(f"exact_length must be non-negative, got {exact_length}")

        if min_length is not None and min_length < 0:
            raise ValueError(f"min_length must be non-negative, got {min_length}")

        if max_length is not None and max_length < 0:
            raise ValueError(f"max_length must be non-negative, got {max_length}")

        if (
            min_length is not None
            and max_length is not None
            and min_length > max_length
        ):
            raise ValueError(
                f"min_length ({min_length}) cannot be greater than max_length ({max_length})"
            )

    def validate(self, input: T) -> None:
        """Validate that input has expected length.

        Args:
            input: Input with length to validate

        Raises:
            ValueError: If input length doesn't meet requirements
        """
        try:
            length = len(input)
        except TypeError:
            raise ValueError(f"Input of type {type(input).__name__} has no length")

        if self.exact_length is not None:
            if length != self.exact_length:
                raise ValueError(f"Expected length {self.exact_length}, got {length}")
            return

        if self.min_length is not None and length < self.min_length:
            raise ValueError(f"Length {length} is less than minimum {self.min_length}")

        if self.max_length is not None and length > self.max_length:
            raise ValueError(
                f"Length {length} is greater than maximum {self.max_length}"
            )
