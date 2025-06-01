"""Base validator brick for the nanobricks framework."""

from typing import Generic, TypeVar

from nanobricks.protocol import NanobrickBase

T = TypeVar("T")


class ValidatorBrick(NanobrickBase[T, T, None], Generic[T]):
    """Base class for validator bricks.

    Validators pass through valid input unchanged and raise ValueError for invalid input.
    """

    def __init__(self, name: str = "validator", version: str = "1.0.0"):
        """Initialize the validator brick.

        Args:
            name: Name of the validator
            version: Version of the validator
        """
        self.name = name
        self.version = version

    async def invoke(self, input: T, *, deps: None = None) -> T:
        """Validate input asynchronously.

        Args:
            input: Input to validate
            deps: No dependencies required

        Returns:
            The input unchanged if valid

        Raises:
            ValueError: If input is invalid
        """
        self.validate(input)
        return input

    def invoke_sync(self, input: T, *, deps: None = None) -> T:
        """Validate input synchronously.

        Args:
            input: Input to validate
            deps: No dependencies required

        Returns:
            The input unchanged if valid

        Raises:
            ValueError: If input is invalid
        """
        self.validate(input)
        return input

    def validate(self, input: T) -> None:
        """Validate the input.

        Override this method in subclasses to implement validation logic.

        Args:
            input: Input to validate

        Raises:
            ValueError: If input is invalid
        """
        raise NotImplementedError("Subclasses must implement validate()")


class ValidatorBase(NanobrickBase[T, T, None], Generic[T]):
    """Alternative base class for validators with async validate method.

    This base class is for validators that need async validation logic.
    """

    def __init__(self, name: str = "validator", version: str = "1.0.0"):
        """Initialize the validator.

        Args:
            name: Name of the validator
            version: Version of the validator
        """
        self.name = name
        self.version = version

    async def invoke(self, input: T, *, deps: None = None) -> T:
        """Validate input asynchronously.

        Args:
            input: Input to validate
            deps: No dependencies required

        Returns:
            The validated output (may be transformed)

        Raises:
            ValueError: If input is invalid
        """
        return await self.validate(input)

    async def validate(self, value: T) -> T:
        """Validate the value.

        Override this method to implement async validation logic.

        Args:
            value: Value to validate

        Returns:
            The validated value (possibly transformed)

        Raises:
            ValueError: If value is invalid
        """
        raise NotImplementedError("Subclasses must implement validate()")
