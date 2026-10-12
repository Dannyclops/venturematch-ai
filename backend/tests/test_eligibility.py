"""Tests for deterministic pre-scoring eligibility decisions."""

import json
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

import pytest
from pydantic import ValidationError

from app.matching import EligibilityEngine, business_geography_tags
from app.models import (
    BusinessModel,
    BusinessProfile,
    EligibilityOutcome,
    EligibilityStatus,
    FundingStage,
    FxRate,
    FxSnapshot,
    Industry,
    InvestorProfile,
    InvestorType,
    Location,
    MoneyAmount,
    MoneyRange,
    StageFlexibility,
    SupportedCurrency,
    TractionMetrics,
)
from app.services import CurrencyNormalizer


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]


def make_engine() -> EligibilityEngine:
    snapshot = FxSnapshot(
        base_currency=SupportedCurrency.USD,
        as_of=datetime(2026, 10, 12, tzinfo=timezone.utc),
        source="synthetic_test_snapshot",
        is_live=False,
        rates=[
            FxRate(currency=SupportedCurrency.USD, rate_to_base=Decimal("1")),
            FxRate(currency=SupportedCurrency.NGN, rate_to_base=Decimal("0.000625")),
            FxRate(currency=SupportedCurrency.TRY, rate_to_base=Decimal("0.0285714286")),
        ],
        notice="Synthetic rates used exclusively for automated tests.",
    )
    return EligibilityEngine(CurrencyNormalizer(snapshot))


def business(**updates: object) -> BusinessProfile:
    payload = {
        "id": "business_solargrid",
        "name": "SolarGrid Africa",
        "one_liner": "Distributed solar operations software for African businesses.",
        "description": (
            "SolarGrid Africa helps commercial operators monitor distributed "
            "solar assets and reduce energy downtime across multiple sites."
        ),
        "primary_industry": Industry.CLIMATE_TECH,
        "industry_tags": ["solar", "energy management"],
        "headquarters": Location(country_code="NG", city="Lagos"),
        "operating_markets": ["Nigeria", "Ghana"],
        "funding_stage": FundingStage.SEED,
        "amount_raising": MoneyAmount(amount=1_200_000_000, currency="NGN"),
        "business_model": BusinessModel.SAAS,
        "founded_year": 2024,
        "team_size": 12,
        "traction": TractionMetrics(is_revenue_generating=True, customers=18),
        "keywords": ["distributed energy", "b2b saas"],
    }
    payload.update(updates)
    return BusinessProfile.model_validate(payload)


def investor(**updates: object) -> InvestorProfile:
    payload = {
        "id": "investor_greenfront",
        "name": "GreenFront Ventures",
        "investor_type": InvestorType.VENTURE_CAPITAL,
        "thesis": (
            "We invest in climate technology businesses improving energy access "
            "and infrastructure resilience across African markets."
        ),
        "preferred_industries": [Industry.CLIMATE_TECH],
        "excluded_industries": [],
        "preferred_stages": [FundingStage.SEED],
        "exploratory_stages": [],
        "stage_flexibility": StageFlexibility.STRICT,
        "ticket_size": MoneyRange(minimum=250_000, maximum=1_500_000, currency="USD"),
        "preferred_geographies": ["Africa", "West Africa"],
        "actively_investing": True,
        "requires_revenue": False,
        "portfolio_company_ids": [],
        "keywords": ["climate", "energy access"],
    }
    payload.update(updates)
    return InvestorProfile.model_validate(payload)


def check_with_code(result, code: str):
    return next(check for check in result.checks if check.code == code)


def test_core_eligibility_uses_normalized_cross_currency_ticket_values() -> None:
    result = make_engine().evaluate_pair(business(), investor())

    assert result.status is EligibilityStatus.CORE_ELIGIBLE
    assert result.normalized_raise.normalized_amount == Decimal("750000.00")
    assert result.normalized_ticket.normalized_minimum == Decimal("250000.00")
    assert check_with_code(result, "ticket_compatible").outcome is EligibilityOutcome.PASSED


def test_result_schema_rejects_a_status_that_contradicts_its_checks() -> None:
    valid_result = make_engine().evaluate_pair(business(), investor())
    payload = valid_result.model_dump()
    payload["status"] = EligibilityStatus.INELIGIBLE

    with pytest.raises(ValidationError):
        type(valid_result).model_validate(payload)


def test_adjacent_stage_is_labelled_as_exploration() -> None:
    result = make_engine().evaluate_pair(
        business(funding_stage=FundingStage.SERIES_A),
        investor(
            exploratory_stages=[FundingStage.SERIES_A],
            stage_flexibility=StageFlexibility.ADJACENT,
        ),
    )

    assert result.status is EligibilityStatus.EXPLORATION_ELIGIBLE
    assert check_with_code(result, "stage_exploration").outcome is EligibilityOutcome.EXPLORATION


def test_strict_stage_policy_blocks_outside_stage() -> None:
    result = make_engine().evaluate_pair(
        business(funding_stage=FundingStage.SERIES_A),
        investor(),
    )

    assert result.status is EligibilityStatus.INELIGIBLE
    assert check_with_code(result, "stage_not_supported").outcome is EligibilityOutcome.BLOCKING


def test_open_stage_policy_allows_labelled_exploration() -> None:
    result = make_engine().evaluate_pair(
        business(funding_stage=FundingStage.GROWTH),
        investor(stage_flexibility=StageFlexibility.OPEN),
    )

    assert result.status is EligibilityStatus.EXPLORATION_ELIGIBLE


def test_ticket_limit_is_checked_after_currency_conversion() -> None:
    result = make_engine().evaluate_pair(
        business(amount_raising=MoneyAmount(amount=70_000_000, currency="TRY")),
        investor(),
    )

    assert result.normalized_raise.normalized_amount == Decimal("2000000.00")
    assert result.status is EligibilityStatus.INELIGIBLE
    assert check_with_code(result, "raise_above_ticket_maximum").outcome is (
        EligibilityOutcome.BLOCKING
    )


def test_all_blocking_reasons_are_returned_in_one_decision() -> None:
    result = make_engine().evaluate_pair(
        business(traction=TractionMetrics(is_revenue_generating=False)),
        investor(
            preferred_industries=[Industry.FINTECH],
            excluded_industries=[Industry.CLIMATE_TECH],
            preferred_geographies=["Europe"],
            actively_investing=False,
            requires_revenue=True,
        ),
    )

    blocking_codes = {
        check.code for check in result.checks if check.outcome is EligibilityOutcome.BLOCKING
    }
    assert result.status is EligibilityStatus.INELIGIBLE
    assert blocking_codes == {
        "investor_inactive",
        "industry_excluded",
        "geography_outside_mandate",
        "revenue_required",
    }


def test_geography_expands_country_names_into_regions() -> None:
    tags = business_geography_tags(
        business(
            headquarters=Location(country_code="TR", city="Istanbul"),
            operating_markets=["T\u00fcrkiye"],
        )
    )

    assert {"turkiye", "europe", "southeast europe", "emerging markets"} <= tags


def test_discovery_keeps_core_first_and_can_hide_exploration() -> None:
    target = business(funding_stage=FundingStage.SERIES_A)
    core = investor(
        id="investor_core",
        name="Core Stage Capital",
        preferred_stages=[FundingStage.SERIES_A],
    )
    exploratory = investor(
        id="investor_exploratory",
        name="Exploratory Capital",
        exploratory_stages=[FundingStage.SERIES_A],
        stage_flexibility=StageFlexibility.ADJACENT,
    )
    engine = make_engine()

    all_results = engine.discover_investors(target, [exploratory, core])
    core_only = engine.discover_investors(
        target,
        [exploratory, core],
        include_exploration_matches=False,
    )

    assert [result.investor_id for result in all_results] == [
        "investor_core",
        "investor_exploratory",
    ]
    assert [result.investor_id for result in core_only] == ["investor_core"]


def test_investor_discovery_honours_explicit_business_exclusions() -> None:
    first = business(id="business_first", name="First Solar Business")
    second = business(id="business_second", name="Second Solar Business")

    results = make_engine().discover_businesses(
        investor(),
        [first, second],
        excluded_business_ids=[first.id],
    )

    assert [result.business_id for result in results] == [second.id]


def test_demo_dataset_keeps_at_least_twenty_businesses_discoverable() -> None:
    businesses = [
        BusinessProfile.model_validate(item)
        for item in json.loads(
            (REPOSITORY_ROOT / "data" / "businesses.json").read_text(encoding="utf-8")
        )
    ]
    investors = [
        InvestorProfile.model_validate(item)
        for item in json.loads(
            (REPOSITORY_ROOT / "data" / "investors.json").read_text(encoding="utf-8")
        )
    ]
    engine = EligibilityEngine(
        CurrencyNormalizer.from_json_file(REPOSITORY_ROOT / "data" / "fx_rates.demo.json")
    )

    discoverable = [
        company for company in businesses if engine.discover_investors(company, investors)
    ]

    assert len(discoverable) >= 20
