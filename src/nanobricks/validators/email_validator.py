"""Email validation nanobrick."""

import re

from nanobricks.validators.base import ValidatorBase


class EmailValidator(ValidatorBase[str]):
    """Validates email addresses.

    Supports:
    - Basic format validation
    - Domain validation
    - Allowed/blocked domains
    - Case normalization
    """

    # RFC 5322 simplified regex for email validation
    EMAIL_REGEX = re.compile(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$")

    def __init__(
        self,
        *,
        allowed_domains: list[str] | None = None,
        blocked_domains: list[str] | None = None,
        normalize: bool = True,
        check_mx: bool = False,  # Future enhancement
        name: str = "email_validator",
        version: str = "1.0.0",
    ):
        """Initialize email validator.

        Args:
            allowed_domains: List of allowed email domains
            blocked_domains: List of blocked email domains
            normalize: Whether to normalize emails (lowercase)
            check_mx: Whether to check MX records (not implemented)
            name: Validator name
            version: Validator version
        """
        super().__init__(name=name, version=version)
        self.allowed_domains = set(allowed_domains or [])
        self.blocked_domains = set(blocked_domains or [])
        self.normalize = normalize
        self.check_mx = check_mx

        if self.allowed_domains and self.blocked_domains:
            overlap = self.allowed_domains & self.blocked_domains
            if overlap:
                raise ValueError(
                    f"Domains in both allowed and blocked lists: {overlap}"
                )

    async def validate(self, value: str) -> str:
        """Validate email address.

        Args:
            value: Email address to validate

        Returns:
            Valid email (possibly normalized)

        Raises:
            ValueError: If email is invalid
        """
        if not isinstance(value, str):
            raise ValueError(f"Expected string, got {type(value).__name__}")

        # Basic format check
        email = value.strip()
        if not email:
            raise ValueError("Email cannot be empty")

        if not self.EMAIL_REGEX.match(email):
            raise ValueError(f"Invalid email format: {email}")

        # Extract domain
        try:
            local, domain = email.rsplit("@", 1)
        except ValueError:
            raise ValueError(f"Invalid email format: {email}")

        # Domain validation
        domain_lower = domain.lower()

        if self.allowed_domains and domain_lower not in self.allowed_domains:
            raise ValueError(
                f"Email domain '{domain}' not in allowed list: {sorted(self.allowed_domains)}"
            )

        if self.blocked_domains and domain_lower in self.blocked_domains:
            raise ValueError(f"Email domain '{domain}' is blocked")

        # Normalize if requested
        if self.normalize:
            email = f"{local.lower()}@{domain_lower}"

        return email


class EmailListValidator(ValidatorBase[list[str]]):
    """Validates a list of email addresses."""

    def __init__(
        self,
        *,
        allowed_domains: list[str] | None = None,
        blocked_domains: list[str] | None = None,
        normalize: bool = True,
        allow_duplicates: bool = False,
        max_count: int | None = None,
        name: str = "email_list_validator",
        version: str = "1.0.0",
    ):
        """Initialize email list validator.

        Args:
            allowed_domains: List of allowed email domains
            blocked_domains: List of blocked email domains
            normalize: Whether to normalize emails
            allow_duplicates: Whether to allow duplicate emails
            max_count: Maximum number of emails allowed
            name: Validator name
            version: Validator version
        """
        super().__init__(name=name, version=version)
        self.email_validator = EmailValidator(
            allowed_domains=allowed_domains,
            blocked_domains=blocked_domains,
            normalize=normalize,
        )
        self.allow_duplicates = allow_duplicates
        self.max_count = max_count

    async def validate(self, value: list[str]) -> list[str]:
        """Validate list of emails.

        Args:
            value: List of email addresses

        Returns:
            Valid email list

        Raises:
            ValueError: If any email is invalid or constraints violated
        """
        if not isinstance(value, list):
            raise ValueError(f"Expected list, got {type(value).__name__}")

        if self.max_count is not None and len(value) > self.max_count:
            raise ValueError(f"Too many emails: {len(value)} > {self.max_count}")

        validated = []
        seen = set()

        for i, email in enumerate(value):
            try:
                valid_email = await self.email_validator.validate(email)

                if not self.allow_duplicates:
                    if valid_email in seen:
                        raise ValueError(f"Duplicate email: {valid_email}")
                    seen.add(valid_email)

                validated.append(valid_email)

            except ValueError as e:
                raise ValueError(f"Email at index {i}: {e}")

        return validated
