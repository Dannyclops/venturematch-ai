"""Founder and business profile contracts."""

from __future__ import annotations

from typing import Annotated, Self

from pydantic import Field, field_validator, model_validator

from .common import (
    BusinessModel,
    EntityId,
    FundingStage,
    Industry,
    Location,
    MoneyAmount,
    SchemaModel,
    normalize_unique_strings,
)


class TractionMetrics(SchemaModel):
    """Optional indicators used to explain maturity, not value the company."""

    is_revenue_generating: bool
    annual_revenue: MoneyAmount | None = None
    monthly_recurring_revenue: MoneyAmount | None = None
    active_users: Annotated[int | None, Field(ge=0)] = None
    customers: Annotated[int | None, Field(ge=0)] = None
    year_over_year_growth_percent: Annotated[float | None, Field(ge=-100, le=10_000)] = None

    @model_validator(mode="after")
    def revenue_flag_must_match_revenue_values(self) -> Self:
        if not self.is_revenue_generating and (
            self.annual_revenue is not None or self.monthly_recurring_revenue is not None
        ):
            raise ValueError("revenue values require is_revenue_generating=true")
        return self


class BusinessProfile(SchemaModel):
    """Canonical company profile submitted by a founder."""

    id: EntityId
    name: Annotated[str, Field(min_length=2, max_length=120)]
    one_liner: Annotated[str, Field(min_length=10, max_length=180)]
    description: Annotated[str, Field(min_length=40, max_length=2_000)]
    primary_industry: Industry
    industry_tags: Annotated[list[str], Field(min_length=1, max_length=8)]
    headquarters: Location
    operating_markets: Annotated[list[str], Field(min_length=1, max_length=20)]
    funding_stage: FundingStage
    amount_raising: MoneyAmount
    business_model: BusinessModel
    founded_year: Annotated[int | None, Field(ge=1900, le=2100)] = None
    team_size: Annotated[int | None, Field(gt=0, le=100_000)] = None
    traction: TractionMetrics | None = None
    keywords: Annotated[list[str], Field(min_length=1, max_length=20)]

    @field_validator("industry_tags", "operating_markets", "keywords")
    @classmethod
    def normalize_matching_terms(cls, values: list[str]) -> list[str]:
        return normalize_unique_strings(values)

