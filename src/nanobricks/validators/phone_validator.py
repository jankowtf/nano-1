"""Phone number validation nanobrick with international support."""

import re

from nanobricks.validators.base import ValidatorBase


class PhoneValidator(ValidatorBase[str]):
    """Validates phone numbers with international support.

    Supports:
    - Multiple formats (national, international)
    - Country-specific validation
    - Number normalization
    - Extension support
    """

    # Country code patterns and rules
    COUNTRY_PATTERNS: dict[str, dict[str, any]] = {
        "US": {
            "code": "+1",
            "pattern": re.compile(
                r"^(?:\+?1[-.\s]?)?\(?([0-9]{3})\)?[-.\s]?([0-9]{3})[-.\s]?([0-9]{4})(?:\s?(?:ext|x|extension)\.?\s?(\d+))?$"
            ),
            "format": "+1 ({}) {}-{}",
            "digits": 10,
        },
        "UK": {
            "code": "+44",
            "pattern": re.compile(
                r"^(?:\+?44[-.\s]?)?0?([0-9]{2,5})[-.\s]?([0-9]{3,4})[-.\s]?([0-9]{3,4})$"
            ),
            "format": "+44 {} {} {}",
            "digits": 10,
        },
        "DE": {
            "code": "+49",
            "pattern": re.compile(
                r"^(?:\+?49[-.\s]?)?0?([0-9]{2,5})[-.\s]?([0-9]{3,8})$"
            ),
            "format": "+49 {} {}",
            "digits": (10, 11),
        },
        "FR": {
            "code": "+33",
            "pattern": re.compile(
                r"^(?:\+?33[-.\s]?)?0?([0-9])[-.\s]?([0-9]{2})[-.\s]?([0-9]{2})[-.\s]?([0-9]{2})[-.\s]?([0-9]{2})$"
            ),
            "format": "+33 {} {} {} {} {}",
            "digits": 9,
        },
        "JP": {
            "code": "+81",
            "pattern": re.compile(
                r"^(?:\+?81[-.\s]?)?0?([0-9]{1,4})[-.\s]?([0-9]{1,4})[-.\s]?([0-9]{4})$"
            ),
            "format": "+81 {}-{}-{}",
            "digits": (10, 11),
        },
    }

    # Generic international pattern
    INTL_PATTERN = re.compile(r"^\+?[1-9]\d{1,14}$")

    def __init__(
        self,
        *,
        country: str | None = None,
        allow_extensions: bool = True,
        normalize: bool = True,
        format_output: bool = False,
        strict: bool = True,
        name: str = "phone_validator",
        version: str = "1.0.0",
    ):
        """Initialize phone validator.

        Args:
            country: Country code (US, UK, DE, etc.) for specific validation
            allow_extensions: Whether to allow phone extensions
            normalize: Whether to normalize to E.164 format
            format_output: Whether to format output nicely
            strict: Whether to enforce strict validation
            name: Validator name
            version: Validator version
        """
        super().__init__(name=name, version=version)
        self.country = country.upper() if country else None
        self.allow_extensions = allow_extensions
        self.normalize = normalize
        self.format_output = format_output
        self.strict = strict

        if self.country and self.country not in self.COUNTRY_PATTERNS:
            raise ValueError(f"Unsupported country: {self.country}")

    async def validate(self, value: str) -> str:
        """Validate phone number.

        Args:
            value: Phone number to validate

        Returns:
            Valid phone number (possibly normalized/formatted)

        Raises:
            ValueError: If phone number is invalid
        """
        if not isinstance(value, str):
            raise ValueError(f"Expected string, got {type(value).__name__}")

        # Clean input
        phone = value.strip()
        if not phone:
            raise ValueError("Phone number cannot be empty")

        # Remove common formatting characters
        cleaned = re.sub(r"[^\d+xext]", "", phone.lower())

        # Extract extension if present
        extension = None
        if "ext" in cleaned or "x" in cleaned:
            if not self.allow_extensions:
                raise ValueError("Extensions not allowed")
            # Simple extension extraction
            parts = re.split(r"(?:ext|x)", cleaned)
            if len(parts) == 2:
                cleaned = parts[0]
                extension = parts[1].strip()

        # Country-specific validation
        if self.country:
            return await self._validate_country_specific(cleaned, extension)

        # Generic international validation
        if self.strict:
            if not self.INTL_PATTERN.match(cleaned):
                raise ValueError(f"Invalid international phone format: {value}")
        else:
            # Just check if it has reasonable number of digits
            digits_only = re.sub(r"\D", "", cleaned)
            if len(digits_only) < 7 or len(digits_only) > 15:
                raise ValueError(f"Invalid phone number length: {value}")

        # Return normalized or original
        result = cleaned
        if extension:
            result += f" ext. {extension}"

        return result

    async def _validate_country_specific(
        self, phone: str, extension: str | None
    ) -> str:
        """Validate phone for specific country.

        Args:
            phone: Cleaned phone number
            extension: Extension if any

        Returns:
            Valid formatted phone number

        Raises:
            ValueError: If invalid for country
        """
        rules = self.COUNTRY_PATTERNS[self.country]
        pattern = rules["pattern"]

        # Try to match the pattern
        match = pattern.match(phone)
        if not match:
            # Try adding country code if missing
            if not phone.startswith("+"):
                phone_with_code = rules["code"].replace("+", "") + phone
                match = pattern.match(phone_with_code)

        if not match:
            raise ValueError(f"Invalid {self.country} phone number format: {phone}")

        # Extract parts
        parts = match.groups()

        # Validate digit count
        digits_only = "".join(p for p in parts if p and p.isdigit())
        expected_digits = rules["digits"]

        if isinstance(expected_digits, tuple):
            if len(digits_only) not in expected_digits:
                raise ValueError(
                    f"Invalid {self.country} phone number length: expected {expected_digits} digits"
                )
        else:
            if len(digits_only) != expected_digits:
                raise ValueError(
                    f"Invalid {self.country} phone number length: expected {expected_digits} digits"
                )

        # Format output
        if self.format_output:
            # Filter out None values and extensions from parts
            format_parts = [
                p for p in parts[: len(parts)] if p and not (p.isdigit() and len(p) > 4)
            ]
            result = rules["format"].format(*format_parts)
        elif self.normalize:
            # E.164 format
            result = rules["code"] + digits_only
        else:
            result = phone

        # Add extension
        if extension:
            result += f" ext. {extension}"

        return result


class PhoneListValidator(ValidatorBase[list[str]]):
    """Validates a list of phone numbers."""

    def __init__(
        self,
        *,
        country: str | None = None,
        allow_extensions: bool = True,
        normalize: bool = True,
        format_output: bool = False,
        allow_duplicates: bool = False,
        max_count: int | None = None,
        name: str = "phone_list_validator",
        version: str = "1.0.0",
    ):
        """Initialize phone list validator.

        Args:
            country: Country code for validation
            allow_extensions: Whether to allow extensions
            normalize: Whether to normalize numbers
            format_output: Whether to format output
            allow_duplicates: Whether to allow duplicates
            max_count: Maximum number of phones allowed
            name: Validator name
            version: Validator version
        """
        super().__init__(name=name, version=version)
        self.phone_validator = PhoneValidator(
            country=country,
            allow_extensions=allow_extensions,
            normalize=normalize,
            format_output=format_output,
        )
        self.allow_duplicates = allow_duplicates
        self.max_count = max_count

    async def validate(self, value: list[str]) -> list[str]:
        """Validate list of phone numbers.

        Args:
            value: List of phone numbers

        Returns:
            Valid phone list

        Raises:
            ValueError: If any phone is invalid
        """
        if not isinstance(value, list):
            raise ValueError(f"Expected list, got {type(value).__name__}")

        if self.max_count is not None and len(value) > self.max_count:
            raise ValueError(f"Too many phones: {len(value)} > {self.max_count}")

        validated = []
        seen = set()

        for i, phone in enumerate(value):
            try:
                valid_phone = await self.phone_validator.validate(phone)

                if not self.allow_duplicates:
                    normalized = re.sub(r"\D", "", valid_phone)
                    if normalized in seen:
                        raise ValueError(f"Duplicate phone: {valid_phone}")
                    seen.add(normalized)

                validated.append(valid_phone)

            except ValueError as e:
                raise ValueError(f"Phone at index {i}: {e}")

        return validated
