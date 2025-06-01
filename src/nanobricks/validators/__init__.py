"""Validators package for nanobricks framework."""

from nanobricks.validators.base import ValidatorBase, ValidatorBrick
from nanobricks.validators.email_validator import EmailListValidator, EmailValidator
from nanobricks.validators.json_schema_validator import (
    JSONSchemaBuilder,
    JSONSchemaValidator,
)
from nanobricks.validators.length_validator import LengthValidator
from nanobricks.validators.phone_validator import PhoneListValidator, PhoneValidator
from nanobricks.validators.range_validator import RangeValidator
from nanobricks.validators.regex_validator import RegexValidator
from nanobricks.validators.schema_validator import SchemaValidator
from nanobricks.validators.type_validator import TypeValidator

# Optional validators (require extra dependencies)
try:
    from nanobricks.validators.pydantic_validator import (
        PydanticListValidator,
        PydanticValidator,
        create_pydantic_validator,
    )

    _has_pydantic = True
except ImportError:
    _has_pydantic = False

__all__ = [
    "ValidatorBrick",
    "ValidatorBase",
    "TypeValidator",
    "RangeValidator",
    "SchemaValidator",
    "LengthValidator",
    "RegexValidator",
    "EmailValidator",
    "EmailListValidator",
    "PhoneValidator",
    "PhoneListValidator",
    "JSONSchemaValidator",
    "JSONSchemaBuilder",
]

if _has_pydantic:
    __all__.extend(
        ["PydanticValidator", "PydanticListValidator", "create_pydantic_validator"]
    )
