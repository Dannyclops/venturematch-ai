"""Investor and portfolio profile contracts."""

from __future__ import annotations

from enum import Enum
from typing import Annotated, Self

from pydantic import Field, field_validator, model_validator

from .common import (
    BusinessModel,
    EntityId,
    FundingStage,
    Industry,
    Location,
    MoneyRange,
    SchemaModel,
    normalize_unique_strings,
)


class InvestorType(str, Enum):
    ANGEL = "angel"
    CORPORATE_VC = "corporate_vc"
    FAMILY_OFFICE = "family_office"
    MICRO_VC = "micro_vc"
    VENTURE_CAPITAL = "venture_capital"


class InvestmentRole(str, Enum):
    LEAD = "lead"
    FOLLOW = "follow"
    FLEXIBLE = "flexible"


class StageFlexibility(str, Enum):
    STRICT = "strict"
    ADJACENT = "adjacent"
    OPEN = "open"


FUNDING_STAGE_ORDER = {
    FundingStage.BOOTSTRAPPED: 0,
    FundingStage.PRE_SEED: 1,
    FundingStage.SEED: 2,
    FundingStage.SERIES_A: 3,
    FundingStage.SERIES_B: 4,
    FundingStage.SERIES_C_PLUS: 5,
    FundingStage.GROWTH: 6,
}


class PortfolioCompany(SchemaModel):
    """Minimal evidence-bearing portfolio record used for fit analysis."""

    id: EntityId
    name: Annotated[str, Field(min_length=2, max_length=120)]
    one_liner: Annotated[str, Field(min_length=10, max_length=180)]
    primary_industry: Industry
    headquarters: Location
    funding_stage_at_investment: FundingStage
    business_model: BusinessModel
    keywords: Annotated[list[str], Field(min_length=1, max_length=20)]

    @field_validator("keywords")
    @classmethod
    def normalize_keywords(cls, values: list[str]) -> list[str]:
        return normalize_unique_strings(values)


class InvestorProfile(SchemaModel):
    """Canonical profile used to search and rank investment opportunities."""

    id: EntityId
    name: Annotated[str, Field(min_length=2, max_length=120)]
    investor_type: InvestorType
    thesis: Annotated[str, Field(min_length=40, max_length=2_000)]
    preferred_industries: Annotated[list[Industry], Field(min_length=1, max_length=10)]
    excluded_industries: Annotated[list[Industry], Field(max_length=10)] = Field(default_factory=list)
    preferred_stages: Annotated[list[FundingStage], Field(min_length=1, max_length=7)]
    exploratory_stages: Annotated[list[FundingStage], Field(max_length=7)] = Field(default_factory=list)
    stage_flexibility: StageFlexibility = StageFlexibility.STRICT
    ticket_size: MoneyRange
    preferred_geographies: Annotated[list[str], Field(min_length=1, max_length=20)]
    investment_role: InvestmentRole = InvestmentRole.FLEXIBLE
    actively_investing: bool = True
    requires_revenue: bool = False
    portfolio_company_ids: Annotated[list[EntityId], Field(max_length=100)] = Field(default_factory=list)
    keywords: Annotated[list[str], Field(min_length=1, max_length=20)]

    @field_validator("preferred_geographies", "keywords")
    @classmethod
    def normalize_matching_terms(cls, values: list[str]) -> list[str]:
        return normalize_unique_strings(values)

    @field_validator("portfolio_company_ids")
    @classmethod
    def deduplicate_portfolio_ids(cls, values: list[str]) -> list[str]:
        return list(dict.fromkeys(values))

    @model_validator(mode="after")
    def included_and_excluded_industries_must_not_overlap(self) -> Self:
        overlap = set(self.preferred_industries) & set(self.excluded_industries)
        if overlap:
            raise ValueError("preferred_industries and excluded_industries must not overlap")
        return self

    @model_validator(mode="after")
    def stage_policy_must_be_consistent(self) -> Self:
        preferred = set(self.preferred_stages)
        exploratory = set(self.exploratory_stages)

        if preferred & exploratory:
            raise ValueError("preferred_stages and exploratory_stages must not overlap")
        if self.stage_flexibility is StageFlexibility.STRICT and exploratory:
            raise ValueError("strict stage policy cannot define exploratory_stages")
        if self.stage_flexibility is StageFlexibility.OPEN and exploratory:
            raise ValueError("open stage policy infers all non-preferred stages automatically")
        if self.stage_flexibility is StageFlexibility.ADJACENT:
            if not exploratory:
                raise ValueError("adjacent stage policy requires exploratory_stages")
            for stage in exploratory:
                is_adjacent = any(
                    abs(FUNDING_STAGE_ORDER[stage] - FUNDING_STAGE_ORDER[core_stage]) == 1
                    for core_stage in preferred
                )
                if not is_adjacent:
                    raise ValueError(f"{stage.value} is not adjacent to a preferred stage")
        return self

