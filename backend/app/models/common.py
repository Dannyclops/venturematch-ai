"""Shared enums and value objects used across VentureMatch schemas."""

from __future__ import annotations

from enum import Enum
from typing import Annotated, Self

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


EntityId = Annotated[
    str,
    Field(
        min_length=3,
        max_length=64,
        pattern=r"^[a-z0-9][a-z0-9_-]*$",
        examples=["business_solargrid"],
    ),
]

CurrencyCode = Annotated[
    str,
    Field(pattern=r"^[A-Z]{3}$", examples=["USD", "EUR", "TRY"]),
]

Score = Annotated[float, Field(ge=0, le=100)]


class SchemaModel(BaseModel):
    """Strict base model shared by every external API schema."""

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
        validate_assignment=True,
    )


class FundingStage(str, Enum):
    BOOTSTRAPPED = "bootstrapped"
    PRE_SEED = "pre_seed"
    SEED = "seed"
    SERIES_A = "series_a"
    SERIES_B = "series_b"
    SERIES_C_PLUS = "series_c_plus"
    GROWTH = "growth"


class Industry(str, Enum):
    AGRITECH = "agritech"
    CLIMATE_TECH = "climate_tech"
    CONSUMER = "consumer"
    CYBERSECURITY = "cybersecurity"
    E_COMMERCE = "e_commerce"
    EDTECH = "edtech"
    ENTERPRISE_SOFTWARE = "enterprise_software"
    FINTECH = "fintech"
    HEALTHTECH = "healthtech"
    LOGISTICS_MOBILITY = "logistics_mobility"


class BusinessModel(str, Enum):
    B2B = "b2b"
    B2C = "b2c"
    B2B2C = "b2b2c"
    D2C = "d2c"
    MARKETPLACE = "marketplace"
    SAAS = "saas"
    OTHER = "other"


class Location(SchemaModel):
    """A physical headquarters or portfolio-company location."""

    country_code: Annotated[str, Field(pattern=r"^[A-Z]{2}$", examples=["NG", "TR"])]
    city: Annotated[str | None, Field(min_length=2, max_length=100)] = None
    region: Annotated[str | None, Field(min_length=2, max_length=100)] = None

    @field_validator("country_code", mode="before")
    @classmethod
    def uppercase_country_code(cls, value: object) -> object:
        return value.upper() if isinstance(value, str) else value


class MoneyAmount(SchemaModel):
    """One exact monetary amount, such as a founder's current raise."""

    amount: Annotated[int, Field(gt=0)]
    currency: CurrencyCode = "USD"

    @field_validator("currency", mode="before")
    @classmethod
    def uppercase_currency(cls, value: object) -> object:
        return value.upper() if isinstance(value, str) else value


class MoneyRange(SchemaModel):
    """An inclusive investment-ticket range."""

    minimum: Annotated[int, Field(ge=0)]
    maximum: Annotated[int, Field(gt=0)]
    currency: CurrencyCode = "USD"

    @field_validator("currency", mode="before")
    @classmethod
    def uppercase_currency(cls, value: object) -> object:
        return value.upper() if isinstance(value, str) else value

    @model_validator(mode="after")
    def maximum_must_cover_minimum(self) -> Self:
        if self.maximum < self.minimum:
            raise ValueError("maximum must be greater than or equal to minimum")
        return self


def normalize_unique_strings(values: list[str]) -> list[str]:
    """Trim, lower-case, and de-duplicate user-entered matching terms."""

    normalized: list[str] = []
    seen: set[str] = set()
    for raw_value in values:
        value = raw_value.strip().lower()
        if value and value not in seen:
            normalized.append(value)
            seen.add(value)
    return normalized

