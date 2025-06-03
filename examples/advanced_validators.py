"""Examples of advanced validators in nanobricks."""

import asyncio
import json
from typing import List, Dict, Any

from nanobricks import Pipeline
from nanobricks.validators import (
    EmailValidator,
    EmailListValidator,
    PhoneValidator,
    PhoneListValidator,
    JSONSchemaValidator,
    JSONSchemaBuilder,
)


async def demo_email_validation():
    """Demonstrate email validation features."""
    print("\n=== Email Validation Demo ===\n")
    
    # Basic email validation
    email_validator = EmailValidator()
    
    emails = [
        "user@example.com",
        "admin@company.org",
        "invalid-email",
        "test@",
    ]
    
    print("Basic validation:")
    for email in emails:
        try:
            valid = await email_validator.invoke(email)
            print(f"  ✓ {email} -> {valid}")
        except ValueError as e:
            print(f"  ✗ {email} -> {e}")
    
    # Email with domain restrictions
    print("\nDomain-restricted validation:")
    corp_validator = EmailValidator(
        allowed_domains=["company.com", "company.org"],
        normalize=True
    )
    
    test_emails = [
        "USER@COMPANY.COM",  # Will be normalized
        "admin@company.org",
        "external@gmail.com",  # Not allowed
    ]
    
    for email in test_emails:
        try:
            valid = await corp_validator.invoke(email)
            print(f"  ✓ {email} -> {valid}")
        except ValueError as e:
            print(f"  ✗ {email} -> {e}")
    
    # Email list validation
    print("\nEmail list validation:")
    list_validator = EmailListValidator(
        max_count=5,
        allow_duplicates=False,
        normalize=True
    )
    
    email_lists = [
        ["user1@example.com", "user2@example.com"],
        ["admin@test.com", "ADMIN@TEST.COM"],  # Duplicate after normalization
    ]
    
    for email_list in email_lists:
        try:
            valid = await list_validator.invoke(email_list)
            print(f"  ✓ {email_list} -> {valid}")
        except ValueError as e:
            print(f"  ✗ {email_list} -> {e}")


async def demo_phone_validation():
    """Demonstrate phone number validation."""
    print("\n=== Phone Number Validation Demo ===\n")
    
    # US phone validation
    us_validator = PhoneValidator(
        country="US",
        format_output=True,
        allow_extensions=True
    )
    
    us_phones = [
        "555-123-4567",
        "(555) 123-4567",
        "5551234567",
        "+1-555-123-4567",
        "555-123-4567 ext. 123",
        "invalid-phone",
    ]
    
    print("US phone validation:")
    for phone in us_phones:
        try:
            valid = await us_validator.invoke(phone)
            print(f"  ✓ {phone} -> {valid}")
        except ValueError as e:
            print(f"  ✗ {phone} -> {e}")
    
    # International validation
    print("\nInternational phone validation:")
    intl_validator = PhoneValidator(strict=False, normalize=True)
    
    intl_phones = [
        "+44 20 7123 4567",  # UK
        "+49 30 12345678",   # Germany
        "+33 1 42 86 82 00", # France
        "+81 3-1234-5678",   # Japan
        "12345",             # Too short
    ]
    
    for phone in intl_phones:
        try:
            valid = await intl_validator.invoke(phone)
            print(f"  ✓ {phone} -> {valid}")
        except ValueError as e:
            print(f"  ✗ {phone} -> {e}")


async def demo_json_schema_validation():
    """Demonstrate JSON Schema validation."""
    print("\n=== JSON Schema Validation Demo ===\n")
    
    # User profile schema
    user_schema = {
        "type": "object",
        "properties": {
            "username": {
                "type": "string",
                "minLength": 3,
                "maxLength": 20,
                "pattern": "^[a-zA-Z0-9_]+$"
            },
            "email": {"type": "string", "format": "email"},
            "age": {"type": "integer", "minimum": 13, "maximum": 120},
            "preferences": {
                "type": "object",
                "properties": {
                    "theme": {"type": "string", "enum": ["light", "dark", "auto"]},
                    "notifications": {"type": "boolean", "default": True}
                }
            }
        },
        "required": ["username", "email"]
    }
    
    validator = JSONSchemaValidator(
        user_schema,
        apply_defaults=True,
        custom_messages={
            "username": "Username must be 3-20 alphanumeric characters",
            "age": "Age must be between 13 and 120"
        }
    )
    
    # Test data
    test_users = [
        {
            "username": "alice_smith",
            "email": "alice@example.com",
            "age": 25,
            "preferences": {"theme": "dark"}
        },
        {
            "username": "ab",  # Too short
            "email": "bob@example.com"
        },
        {
            "username": "charlie",
            "email": "not-an-email",  # Invalid format
            "age": 200  # Too old
        }
    ]
    
    print("User profile validation:")
    for user in test_users:
        try:
            valid = await validator.invoke(user)
            print(f"  ✓ {user['username']} -> Valid (notifications: {valid.get('preferences', {}).get('notifications', 'N/A')})")
        except ValueError as e:
            print(f"  ✗ {user['username']} -> {e}")
    
    # Using JSONSchemaBuilder
    print("\nUsing JSONSchemaBuilder:")
    
    # Build a product schema
    product_schema = (
        JSONSchemaBuilder()
        .type("object")
        .properties(
            id={"type": "integer", "minimum": 1},
            name={"type": "string", "minLength": 1},
            price={"type": "number", "minimum": 0},
            tags={"type": "array", "items": {"type": "string"}},
            in_stock={"type": "boolean", "default": True}
        )
        .required("id", "name", "price")
        .additional_properties(False)
        .build()
    )
    
    product_validator = JSONSchemaValidator(product_schema, apply_defaults=True)
    
    products = [
        {"id": 1, "name": "Widget", "price": 9.99, "tags": ["new", "popular"]},
        {"id": 2, "name": "Gadget", "price": 19.99},  # Missing tags, in_stock will default
        {"id": 3, "name": "", "price": -5},  # Invalid name and price
    ]
    
    for product in products:
        try:
            valid = await product_validator.invoke(product)
            print(f"  ✓ Product {product['id']} -> Valid (in_stock: {valid.get('in_stock', 'N/A')})")
        except ValueError as e:
            print(f"  ✗ Product {product['id']} -> {e}")


async def demo_validation_pipeline():
    """Demonstrate validation in a pipeline."""
    print("\n=== Validation Pipeline Demo ===\n")
    
    # Create a user registration pipeline
    from nanobricks import Nanobrick
    
    class NormalizeInputBrick(Nanobrick[Dict[str, Any], Dict[str, Any]]):
        """Normalize user input."""
        
        async def invoke(self, input: Dict[str, Any], *, deps=None) -> Dict[str, Any]:
            # Strip whitespace from strings
            normalized = {}
            for key, value in input.items():
                if isinstance(value, str):
                    normalized[key] = value.strip()
                else:
                    normalized[key] = value
            return normalized
    
    class EnrichUserBrick(Nanobrick[Dict[str, Any], Dict[str, Any]]):
        """Add derived fields."""
        
        async def invoke(self, input: Dict[str, Any], *, deps=None) -> Dict[str, Any]:
            enriched = input.copy()
            # Add username from email if not provided
            if "username" not in enriched and "email" in enriched:
                enriched["username"] = enriched["email"].split("@")[0]
            # Add registration timestamp
            import time
            enriched["registered_at"] = int(time.time())
            return enriched
    
    # Build registration pipeline
    email_validator = EmailValidator(normalize=True)
    
    user_schema_validator = JSONSchemaValidator({
        "type": "object",
        "properties": {
            "username": {"type": "string", "minLength": 3},
            "email": {"type": "string"},
            "phone": {"type": "string"},
            "age": {"type": "integer", "minimum": 13}
        },
        "required": ["email", "username"]
    })
    
    phone_validator = PhoneValidator(country="US", format_output=True)
    
    # Compose pipeline
    registration_pipeline = (
        NormalizeInputBrick() >> EnrichUserBrick()
    )
    
    # Test registrations
    registrations = [
        {
            "email": "  JOHN.DOE@EXAMPLE.COM  ",
            "phone": "555-123-4567",
            "age": 25
        },
        {
            "username": "alice",
            "email": "alice@test.com",
            "phone": "(555) 234-5678",
            "age": 30
        },
        {
            "email": "invalid-email",
            "phone": "not-a-phone",
            "age": 10  # Too young
        }
    ]
    
    print("User registration pipeline:")
    for i, reg_data in enumerate(registrations):
        try:
            # Process through pipeline
            processed = await registration_pipeline.invoke(reg_data)
            
            # Validate email
            processed["email"] = await email_validator.invoke(processed["email"])
            
            # Validate phone if provided
            if "phone" in processed:
                processed["phone"] = await phone_validator.invoke(processed["phone"])
            
            # Final schema validation
            valid_user = await user_schema_validator.invoke(processed)
            
            print(f"  ✓ Registration {i+1}: Success!")
            print(f"    - Username: {valid_user['username']}")
            print(f"    - Email: {valid_user['email']}")
            print(f"    - Phone: {valid_user.get('phone', 'N/A')}")
            
        except ValueError as e:
            print(f"  ✗ Registration {i+1}: Failed - {e}")


async def demo_pydantic_validation():
    """Demonstrate Pydantic validation (if available)."""
    try:
        from pydantic import BaseModel, Field, EmailStr, validator
        from nanobricks.validators import PydanticValidator, PydanticListValidator
    except ImportError:
        print("\n=== Pydantic Validation Demo ===")
        print("Pydantic not installed. Install with: pip install pydantic")
        return
    
    print("\n=== Pydantic Validation Demo ===\n")
    
    # Define a Pydantic model
    class ProductModel(BaseModel):
        id: int = Field(..., gt=0)
        name: str = Field(..., min_length=1, max_length=100)
        price: float = Field(..., gt=0)
        discount: float = Field(0.0, ge=0, le=1)
        tags: List[str] = Field(default_factory=list)
        
        @validator('name')
        def name_must_be_capitalized(cls, v):
            if not v[0].isupper():
                raise ValueError('Product name must start with capital letter')
            return v
        
        @property
        def discounted_price(self) -> float:
            return self.price * (1 - self.discount)
    
    # Create validator
    product_validator = PydanticValidator(
        ProductModel,
        export_format="dict",
        exclude_defaults=True
    )
    
    products = [
        {"id": 1, "name": "Laptop", "price": 999.99, "discount": 0.1},
        {"id": 2, "name": "mouse", "price": 29.99},  # lowercase name
        {"id": 3, "name": "Keyboard", "price": -50},  # negative price
    ]
    
    print("Product validation with Pydantic:")
    for product in products:
        try:
            valid = await product_validator.invoke(product)
            print(f"  ✓ Product {product['id']}: {valid['name']} - ${valid['price']}")
            if "discount" in valid:
                print(f"    Discount: {valid['discount']*100}%")
        except ValueError as e:
            print(f"  ✗ Product {product['id']}: {e}")
    
    # List validation
    print("\nBatch product validation:")
    list_validator = PydanticListValidator(
        ProductModel,
        min_items=1,
        max_items=10,
        unique_fields=["id"],
        export_format="dict"
    )
    
    product_batch = [
        {"id": 1, "name": "Widget", "price": 9.99},
        {"id": 2, "name": "Gadget", "price": 19.99},
        {"id": 1, "name": "Duplicate", "price": 5.99},  # Duplicate ID
    ]
    
    try:
        valid_batch = await list_validator.invoke(product_batch)
        print(f"  ✓ Batch validated: {len(valid_batch)} products")
    except ValueError as e:
        print(f"  ✗ Batch validation failed: {e}")


async def main():
    """Run all validation demos."""
    print("\n🚀 Advanced Validators in Nanobricks\n")
    
    await demo_email_validation()
    await demo_phone_validation()
    await demo_json_schema_validation()
    await demo_validation_pipeline()
    await demo_pydantic_validation()
    
    print("\n✅ All validation demos complete!\n")


if __name__ == "__main__":
    asyncio.run(main())