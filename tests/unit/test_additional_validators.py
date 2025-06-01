"""Tests for additional validators."""

import asyncio
import json

import pytest

from nanobricks.validators import (
    EmailListValidator,
    EmailValidator,
    JSONSchemaBuilder,
    JSONSchemaValidator,
    PhoneListValidator,
    PhoneValidator,
)


class TestEmailValidator:
    """Tests for EmailValidator."""

    @pytest.mark.asyncio
    async def test_valid_emails(self):
        """Test validation of valid emails."""
        validator = EmailValidator()

        valid_emails = [
            "test@example.com",
            "user.name@example.com",
            "user+tag@example.co.uk",
            "123@example.com",
            "test@sub.example.com",
        ]

        for email in valid_emails:
            result = await validator.validate(email)
            assert isinstance(result, str)

    @pytest.mark.asyncio
    async def test_invalid_emails(self):
        """Test rejection of invalid emails."""
        validator = EmailValidator()

        invalid_emails = [
            "",
            "notanemail",
            "@example.com",
            "user@",
            "user@@example.com",
            "user@example",
            "user example@test.com",
        ]

        for email in invalid_emails:
            with pytest.raises(ValueError):
                await validator.validate(email)

    @pytest.mark.asyncio
    async def test_email_normalization(self):
        """Test email normalization."""
        validator = EmailValidator(normalize=True)

        result = await validator.validate("TEST@EXAMPLE.COM")
        assert result == "test@example.com"

        # No normalization
        validator_no_norm = EmailValidator(normalize=False)
        result = await validator_no_norm.validate("TEST@EXAMPLE.COM")
        assert result == "TEST@EXAMPLE.COM"

    @pytest.mark.asyncio
    async def test_allowed_domains(self):
        """Test allowed domains restriction."""
        validator = EmailValidator(allowed_domains=["example.com", "test.com"])

        # Allowed
        result = await validator.validate("user@example.com")
        assert result == "user@example.com"

        # Not allowed
        with pytest.raises(ValueError, match="not in allowed list"):
            await validator.validate("user@other.com")

    @pytest.mark.asyncio
    async def test_blocked_domains(self):
        """Test blocked domains."""
        validator = EmailValidator(blocked_domains=["spam.com", "junk.com"])

        # Not blocked
        result = await validator.validate("user@example.com")
        assert result == "user@example.com"

        # Blocked
        with pytest.raises(ValueError, match="is blocked"):
            await validator.validate("user@spam.com")

    @pytest.mark.asyncio
    async def test_email_list_validator(self):
        """Test email list validation."""
        validator = EmailListValidator(max_count=3, allow_duplicates=False)

        # Valid list
        emails = ["user1@example.com", "user2@example.com"]
        result = await validator.validate(emails)
        assert len(result) == 2

        # Too many
        with pytest.raises(ValueError, match="Too many emails"):
            await validator.validate([f"user{i}@example.com" for i in range(5)])

        # Duplicates
        with pytest.raises(ValueError, match="Duplicate email"):
            await validator.validate(["user@example.com", "user@example.com"])


class TestPhoneValidator:
    """Tests for PhoneValidator."""

    @pytest.mark.asyncio
    async def test_us_phone_validation(self):
        """Test US phone number validation."""
        validator = PhoneValidator(country="US", format_output=True)

        valid_phones = [
            "555-123-4567",
            "(555) 123-4567",
            "5551234567",
            "+1 555 123 4567",
            "1-555-123-4567",
        ]

        for phone in valid_phones:
            result = await validator.validate(phone)
            assert result == "+1 (555) 123-4567"

    @pytest.mark.asyncio
    async def test_uk_phone_validation(self):
        """Test UK phone number validation."""
        validator = PhoneValidator(country="UK", normalize=True)

        valid_phones = [
            "020 7123 4567",
            "+44 20 7123 4567",
            "02071234567",
        ]

        for phone in valid_phones:
            result = await validator.validate(phone)
            assert result.startswith("+44")

    @pytest.mark.asyncio
    async def test_phone_extensions(self):
        """Test phone number extensions."""
        validator = PhoneValidator(country="US", allow_extensions=True)

        result = await validator.validate("555-123-4567 ext. 123")
        assert "ext. 123" in result

        # Extensions not allowed
        validator_no_ext = PhoneValidator(country="US", allow_extensions=False)
        with pytest.raises(ValueError, match="Extensions not allowed"):
            await validator_no_ext.validate("555-123-4567 ext. 123")

    @pytest.mark.asyncio
    async def test_international_validation(self):
        """Test generic international validation."""
        validator = PhoneValidator(strict=False)

        # Should accept various formats
        phones = [
            "+1234567890",
            "+44 20 7123 4567",
            "+49 30 12345678",
        ]

        for phone in phones:
            result = await validator.validate(phone)
            assert isinstance(result, str)

    @pytest.mark.asyncio
    async def test_phone_list_validator(self):
        """Test phone list validation."""
        validator = PhoneListValidator(
            country="US", normalize=True, allow_duplicates=False
        )

        phones = ["555-123-4567", "(555) 234-5678"]
        result = await validator.validate(phones)
        assert len(result) == 2

        # Duplicates
        with pytest.raises(ValueError, match="Duplicate phone"):
            await validator.validate(["555-123-4567", "5551234567"])


class TestJSONSchemaValidator:
    """Tests for JSONSchemaValidator."""

    @pytest.mark.asyncio
    async def test_basic_schema_validation(self):
        """Test basic JSON schema validation."""
        schema = {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "age": {"type": "integer", "minimum": 0},
            },
            "required": ["name"],
        }

        validator = JSONSchemaValidator(schema)

        # Valid
        data = {"name": "Alice", "age": 30}
        result = await validator.validate(data)
        assert result == data

        # Missing required
        with pytest.raises(ValueError, match="'name' is a required property"):
            await validator.validate({"age": 30})

        # Wrong type
        with pytest.raises(ValueError, match="is not of type 'integer'"):
            await validator.validate({"name": "Alice", "age": "thirty"})

    @pytest.mark.asyncio
    async def test_schema_with_defaults(self):
        """Test applying default values."""
        schema = {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "status": {"type": "string", "default": "active"},
                "count": {"type": "integer", "default": 0},
            },
        }

        validator = JSONSchemaValidator(schema, apply_defaults=True)

        data = {"name": "Test"}
        result = await validator.validate(data)

        assert result["status"] == "active"
        assert result["count"] == 0

    @pytest.mark.asyncio
    async def test_type_coercion(self):
        """Test type coercion."""
        schema = {
            "type": "object",
            "properties": {
                "count": {"type": "integer"},
                "price": {"type": "number"},
                "active": {"type": "boolean"},
            },
        }

        validator = JSONSchemaValidator(schema, coerce_types=True)

        data = {"count": "42", "price": "19.99", "active": "true"}

        result = await validator.validate(data)
        assert result["count"] == 42
        assert result["price"] == 19.99
        assert result["active"] is True

    @pytest.mark.asyncio
    async def test_custom_error_messages(self):
        """Test custom error messages."""
        schema = {
            "type": "object",
            "properties": {
                "email": {"type": "string", "minLength": 5},
                "age": {"type": "integer", "minimum": 0},
            },
            "required": ["email"],
        }

        custom_messages = {
            "email": "Email must be at least 5 characters",
            "age": "Age must be positive",
        }

        validator = JSONSchemaValidator(schema, custom_messages=custom_messages)

        with pytest.raises(ValueError, match="Email must be at least 5 characters"):
            await validator.validate({"email": "abc"})

    @pytest.mark.asyncio
    async def test_schema_builder(self):
        """Test JSONSchemaBuilder."""
        schema = (
            JSONSchemaBuilder()
            .type("object")
            .properties(
                name={"type": "string", "minLength": 1},
                age={"type": "integer", "minimum": 0, "maximum": 150},
            )
            .required("name")
            .additional_properties(False)
            .build()
        )

        validator = JSONSchemaValidator(schema)

        # Valid
        result = await validator.validate({"name": "Test", "age": 25})
        assert result["name"] == "Test"

        # Additional property not allowed
        with pytest.raises(ValueError):
            await validator.validate({"name": "Test", "extra": "field"})

    @pytest.mark.asyncio
    async def test_schema_from_string(self):
        """Test loading schema from JSON string."""
        schema_str = json.dumps(
            {"type": "object", "properties": {"id": {"type": "integer"}}}
        )

        validator = JSONSchemaValidator(schema_str)
        result = await validator.validate({"id": 123})
        assert result["id"] == 123


# Skip Pydantic tests if not installed
pydantic = pytest.importorskip("pydantic", reason="pydantic not installed")

if pydantic:
    from nanobricks.validators import (
        PydanticListValidator,
        PydanticValidator,
    )

    class TestPydanticValidator:
        """Tests for PydanticValidator."""

        def test_pydantic_model_validation(self):
            """Test validation with Pydantic model."""
            from pydantic import BaseModel, Field

            class UserModel(BaseModel):
                name: str = Field(..., min_length=1)
                age: int = Field(..., ge=0, le=150)
                email: str = Field(..., regex=r"^[\w\.-]+@[\w\.-]+\.\w+$")

            validator = PydanticValidator(UserModel, export_format="dict")

            # Valid
            data = {"name": "Alice", "age": 30, "email": "alice@example.com"}
            result = asyncio.run(validator.validate(data))
            assert result["name"] == "Alice"

            # Invalid
            with pytest.raises(ValueError, match="validation failed"):
                asyncio.run(validator.validate({"name": "", "age": -1}))

        def test_pydantic_type_coercion(self):
            """Test Pydantic type coercion."""
            from pydantic import BaseModel

            class DataModel(BaseModel):
                count: int
                price: float
                active: bool

            validator = PydanticValidator(DataModel, export_format="dict")

            # String inputs get coerced
            data = {"count": "42", "price": "19.99", "active": "yes"}
            result = asyncio.run(validator.validate(data))

            assert result["count"] == 42
            assert result["price"] == 19.99
            assert result["active"] is True

        def test_pydantic_list_validator(self):
            """Test list validation."""
            from pydantic import BaseModel

            class ItemModel(BaseModel):
                id: int
                name: str

            validator = PydanticListValidator(
                ItemModel, min_items=1, max_items=5, unique_fields=["id"]
            )

            # Valid
            items = [{"id": 1, "name": "Item 1"}, {"id": 2, "name": "Item 2"}]
            result = asyncio.run(validator.validate(items))
            assert len(result) == 2

            # Duplicate ID
            with pytest.raises(ValueError, match="Duplicate value for id"):
                items_dup = [{"id": 1, "name": "Item 1"}, {"id": 1, "name": "Item 2"}]
                asyncio.run(validator.validate(items_dup))
