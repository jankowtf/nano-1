"""Regex validator for the nanobricks framework."""

import re
from re import Pattern

from nanobricks.validators.base import ValidatorBrick


class RegexValidator(ValidatorBrick[str]):
    """Validates that string input matches regex pattern."""

    def __init__(
        self,
        pattern: str | Pattern[str],
        flags: int = 0,
        full_match: bool = False,
        error_message: str | None = None,
        name: str = "regex_validator",
        version: str = "1.0.0",
    ):
        """Initialize the regex validator.

        Args:
            pattern: Regex pattern to match against
            flags: Regex flags (e.g., re.IGNORECASE)
            full_match: Whether to require full string match vs partial match
            error_message: Custom error message (uses default if None)
            name: Name of the validator
            version: Version of the validator
        """
        super().__init__(name, version)

        if isinstance(pattern, str):
            self.pattern = re.compile(pattern, flags)
            self.pattern_str = pattern
        else:
            self.pattern = pattern
            self.pattern_str = pattern.pattern

        self.full_match = full_match
        self.error_message = error_message

    def validate(self, input: str) -> None:
        """Validate that input matches regex pattern.

        Args:
            input: String input to validate

        Raises:
            ValueError: If input doesn't match pattern
        """
        if not isinstance(input, str):
            raise ValueError(f"Expected string input, got {type(input).__name__}")

        if self.full_match:
            match = self.pattern.fullmatch(input)
        else:
            match = self.pattern.search(input)

        if not match:
            if self.error_message:
                raise ValueError(self.error_message)
            else:
                match_type = "fully match" if self.full_match else "match"
                raise ValueError(
                    f"Input '{input}' does not {match_type} pattern '{self.pattern_str}'"
                )
