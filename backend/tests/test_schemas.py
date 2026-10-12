"""Contract tests for the first VentureMatch schema version."""

import pytest
from pydantic import ValidationError

from app.models import (
    BusinessModel,
    BusinessProfile,
    FundingStage,
    Industry,
    InvestmentRole,
    InvestorProfile,
    InvestorType,
    Location,
    MatchRequest,
    MoneyAmount,
    MoneyRange,
    StageFlexibility,
    TractionMetrics,
    UserMode,
)


def sample_business() -> BusinessProfile:
    return BusinessProfile(
        id="business_solargrid",
        name="SolarGrid Africa",
        one_liner="Distributed solar operations software for African businesses.",
        description=(
            "SolarGrid Africa helps commercial operators monitor distributed "
            "solar assets and reduce energy downtime across multiple sites."
        ),
        primary_industry=Industry.CLIMATE_TECH,
        industry_tags=["Solar", "Energy Management", "solar"],
        headquarters=Location(country_code="ng", city="Lagos"),
        operating_markets=["Nigeria", "Ghana"],
        funding_stage=FundingStage.SEED,
        amount_raising=MoneyAmount(amount=750_000, currency="usd"),
        business_model=BusinessModel.SAAS,
        founded_year=2024,
        team_size=12,
        traction=TractionMetrics(
            is_revenue_generating=True,
            customers=18,
            year_over_year_growth_percent=65,
        ),
        keywords=["Distributed Energy", "B2B SaaS"],
    )


def sample_investor() -> InvestorProfile:
    return InvestorProfile(
        id="investor_greenfront",
        name="GreenFront Ventures",
        investor_type=InvestorType.VENTURE_CAPITAL,
        thesis=(
            "We invest in seed-stage climate technology businesses improving "
            "energy access and infrastructure resilience in African markets."
        ),
        preferred_industries=[Industry.CLIMATE_TECH, Industry.ENTERPRISE_SOFTWARE],
        preferred_stages=[FundingStage.PRE_SEED, FundingStage.SEED],
        ticket_size=MoneyRange(minimum=250_000, maximum=1_500_000, currency="usd"),
        preferred_geographies=["Africa", "Nigeria"],
        investment_role=InvestmentRole.LEAD,
        portfolio_company_ids=["portfolio_gridwatch"],
        keywords=["Climate", "Energy Access", "Infrastructure"],
    )


def test_business_normalizes_codes_and_matching_terms() -> None:
    business = sample_business()

    assert business.headquarters.country_code == "NG"
    assert business.amount_raising.currency == "USD"
    assert business.industry_tags == ["solar", "energy management"]


def test_investor_ticket_range_must_be_ordered() -> None:
    with pytest.raises(ValidationError):
        MoneyRange(minimum=2_000_000, maximum=500_000, currency="USD")


def test_founder_mode_accepts_only_business_profile() -> None:
    request = MatchRequest(
        mode=UserMode.FOUNDER,
        objective="Find seed investors focused on African climate technology.",
        business_profile=sample_business(),
    )

    assert request.business_profile is not None
    assert request.investor_profile is None


def test_mode_profile_mismatch_is_rejected() -> None:
    with pytest.raises(ValidationError):
        MatchRequest(
            mode=UserMode.INVESTOR,
            objective="Find climate technology businesses for this portfolio.",
            business_profile=sample_business(),
        )


def test_unknown_fields_are_rejected() -> None:
    payload = sample_investor().model_dump()
    payload["unsupported_score"] = 99

    with pytest.raises(ValidationError):
        InvestorProfile.model_validate(payload)


def test_non_revenue_business_cannot_report_revenue_values() -> None:
    with pytest.raises(ValidationError):
        TractionMetrics(
            is_revenue_generating=False,
            annual_revenue=MoneyAmount(amount=100_000, currency="USD"),
        )


def test_investor_cannot_prefer_and_exclude_same_industry() -> None:
    payload = sample_investor().model_dump()
    payload["excluded_industries"] = [Industry.CLIMATE_TECH]

    with pytest.raises(ValidationError):
        InvestorProfile.model_validate(payload)


def test_adjacent_stage_policy_accepts_an_adjacent_exploratory_stage() -> None:
    payload = sample_investor().model_dump()
    payload["stage_flexibility"] = StageFlexibility.ADJACENT
    payload["exploratory_stages"] = [FundingStage.SERIES_A]

    investor = InvestorProfile.model_validate(payload)

    assert investor.exploratory_stages == [FundingStage.SERIES_A]


def test_adjacent_stage_policy_rejects_a_non_adjacent_stage() -> None:
    payload = sample_investor().model_dump()
    payload["stage_flexibility"] = StageFlexibility.ADJACENT
    payload["exploratory_stages"] = [FundingStage.GROWTH]

    with pytest.raises(ValidationError):
        InvestorProfile.model_validate(payload)


def test_open_stage_policy_does_not_require_an_exploratory_list() -> None:
    payload = sample_investor().model_dump()
    payload["stage_flexibility"] = StageFlexibility.OPEN

    investor = InvestorProfile.model_validate(payload)

    assert investor.exploratory_stages == []

