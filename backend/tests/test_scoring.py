"""Scoring invariants and offline end-to-end ranking scenarios."""

import json
from decimal import Decimal
from pathlib import Path

import pytest

from app.matching import CompatibilityEngine, IneligibleMatchError
from app.matching.scoring import SCORING_WEIGHTS, jaccard, tokens
from app.models import (
    BusinessProfile, ConfidenceLevel, EligibilityStatus, FundingStage, InvestorProfile,
    MatchDirection, MatchFactor, MatchResult, MoneyAmount, MoneyRange, PortfolioCompany,
    StageFlexibility,
)
from test_eligibility import business, investor, make_engine


def engine(portfolios=()):
    return CompatibilityEngine(make_engine(), portfolios)


def portfolio(**updates):
    payload = {
        "id": "portfolio_solar", "name": "Solar Monitor",
        "one_liner": "Software monitoring solar assets for business operators.",
        "primary_industry": "climate_tech",
        "headquarters": {"country_code": "NG"},
        "funding_stage_at_investment": "seed", "business_model": "saas",
        "keywords": ["distributed energy", "solar", "asset monitoring"],
    }
    payload.update(updates)
    return PortfolioCompany.model_validate(payload)


def test_weighted_total_is_reproducible_and_versioned():
    result = engine().score_pair(business(), investor())
    expected = sum(
        Decimal(str(value)) * SCORING_WEIGHTS[key] / 100
        for key, value in result.score_breakdown.model_dump().items()
    )
    assert result.overall_score == float(expected.quantize(Decimal("0.01")))
    assert sum(SCORING_WEIGHTS.values()) == 100
    assert result.scoring_version == "compatibility_v1"
    assert result.thesis_similarity_method == "keyword_jaccard_v1"
    assert MatchResult.model_validate_json(result.model_dump_json()) == result
    assert {item.factor for item in result.evidence} == set(MatchFactor)


@pytest.mark.parametrize("updates", [
    {"actively_investing": False},
    {"preferred_stages": [FundingStage.GROWTH]},
    {"preferred_geographies": ["Antarctica"]},
    {"ticket_size": MoneyRange(minimum=1, maximum=10, currency="USD")},
])
def test_ineligible_pairs_cannot_be_scored_or_ranked(updates):
    rejected = investor(**updates)
    with pytest.raises(IneligibleMatchError) as error:
        engine().score_pair(business(), rejected)
    assert error.value.eligibility.status is EligibilityStatus.INELIGIBLE
    assert engine().rank_investors(business(), [rejected]) == []


def test_same_value_in_different_currencies_produces_same_scores():
    local = engine().score_pair(business(), investor())
    usd = engine().score_pair(
        business(amount_raising=MoneyAmount(amount=750000, currency="USD")), investor(),
    )
    assert local.score_breakdown == usd.score_breakdown
    assert local.overall_score == usd.overall_score
    assert local.eligibility.normalized_raise.original.currency == "NGN"


@pytest.mark.parametrize("amount,expected", [(250000, 75), (875000, 100), (1500000, 75)])
def test_ticket_midpoint_and_inclusive_boundaries(amount, expected):
    result = engine().score_pair(
        business(amount_raising=MoneyAmount(amount=amount, currency="USD")), investor(),
    )
    assert result.score_breakdown.ticket_size_compatibility == expected


def test_fixed_ticket_range_has_no_division_by_zero():
    result = engine().score_pair(
        business(), investor(ticket_size=MoneyRange(minimum=750000, maximum=750000)),
    )
    assert result.score_breakdown.ticket_size_compatibility == 100


@pytest.mark.parametrize("geography,expected", [("Nigeria", 100), ("Africa", 80), ("global", 60)])
def test_geographic_specificity_scores(geography, expected):
    result = engine().score_pair(business(), investor(preferred_geographies=[geography]))
    assert result.score_breakdown.geographic_alignment == expected


@pytest.mark.parametrize("stage,expected", [
    (FundingStage.SEED, 100), (FundingStage.SERIES_A, 70), (FundingStage.GROWTH, 40),
])
def test_stage_score_tracks_distance_without_changing_eligibility(stage, expected):
    result = engine().score_pair(
        business(funding_stage=stage), investor(stage_flexibility=StageFlexibility.OPEN),
    )
    assert result.score_breakdown.funding_stage_alignment == expected


def test_industry_preference_order_does_not_change_score():
    first = investor(preferred_industries=["climate_tech", "enterprise_software"])
    second = investor(preferred_industries=["enterprise_software", "climate_tech"])
    assert engine().score_pair(business(), first).score_breakdown == (
        engine().score_pair(business(), second).score_breakdown
    )


def test_lexical_baseline_is_order_and_repetition_invariant():
    assert tokens("Solar SOLAR energy") == tokens("energy solar")
    assert jaccard(tokens("solar energy"), tokens("energy solar")) == 1
    assert jaccard(tokens("solar energy"), tokens("payments credit")) == 0
    assert jaccard(set(), set()) == 0


def test_stronger_thesis_token_overlap_ranks_first():
    company = business(description="Solar energy monitoring supports distributed power assets.",
                       one_liner="Solar energy monitoring software.",
                       industry_tags=["solar energy"], keywords=["monitoring"])
    strong = investor(id="investor_strong",
                      thesis="Solar energy monitoring supports distributed power assets.",
                      keywords=["software"])
    weak = investor(id="investor_weak",
                    thesis="Payments credit lending insurance banking finance services.",
                    keywords=["payments"])
    results = engine().rank_investors(company, [weak, strong])
    assert [result.candidate_entity_id for result in results] == [strong.id, weak.id]
    assert results[0].score_breakdown.semantic_thesis_similarity > (
        results[1].score_breakdown.semantic_thesis_similarity
    )


def test_core_ranks_before_higher_scoring_exploration():
    company = business()
    core = investor(id="investor_core",
                    thesis="Payments credit lending insurance banking finance services.",
                    keywords=["payments"], preferred_geographies=["global"],
                    ticket_size=MoneyRange(minimum=750000, maximum=1500000))
    explore = investor(id="investor_explore", preferred_stages=[FundingStage.PRE_SEED],
                       exploratory_stages=[FundingStage.SEED],
                       stage_flexibility=StageFlexibility.ADJACENT,
                       preferred_geographies=["Nigeria"],
                       thesis=company.description + " " + company.one_liner,
                       keywords=company.keywords + company.industry_tags,
                       ticket_size=MoneyRange(minimum=500000, maximum=1000000))
    scorer = engine()
    assert scorer.score_pair(company, explore).overall_score > (
        scorer.score_pair(company, core).overall_score
    )
    assert [r.candidate_entity_id for r in scorer.rank_investors(company, [explore, core])] == [
        core.id, explore.id,
    ]
    assert [r.candidate_entity_id for r in scorer.rank_investors(
        company, [explore, core], include_exploration_matches=False,
    )] == [core.id]


def test_ties_are_resolved_by_id_not_input_order_and_top_k_applies():
    a, b = investor(id="investor_aaa"), investor(id="investor_bbb")
    scorer = engine()
    assert scorer.rank_investors(business(), [a, b]) == (
        scorer.rank_investors(business(), [b, a])
    )
    assert [r.rank for r in scorer.rank_investors(business(), [b, a])] == [1, 2]
    assert scorer.rank_investors(business(), [b, a], top_k=1)[0].candidate_entity_id == a.id
    assert scorer.rank_investors(
        business(), [a, b], excluded_investor_ids=[a.id],
    )[0].candidate_entity_id == b.id


def test_portfolio_overlap_is_a_warning_not_a_reward():
    record = portfolio()
    target = investor(portfolio_company_ids=[record.id])
    result = engine([record]).score_pair(business(), target)
    assert result.score_breakdown.portfolio_compatibility == 30
    assert "possible_portfolio_competition" in {c.code for c in result.concerns}
    assert any(e.source_entity_id == record.id for e in result.evidence)
    unrelated = portfolio(id="portfolio_unrelated", keywords=["water", "irrigation"])
    result = engine([unrelated]).score_pair(
        business(), investor(portfolio_company_ids=[unrelated.id]),
    )
    assert result.score_breakdown.portfolio_compatibility == 70


def test_only_linked_portfolios_are_used_and_missing_records_lower_confidence():
    record = portfolio()
    scorer = engine([record])
    no_links = scorer.score_pair(business(), investor())
    assert no_links.score_breakdown.portfolio_compatibility == 50
    assert no_links.confidence is ConfidenceLevel.LOW
    partial = scorer.score_pair(
        business(), investor(portfolio_company_ids=[record.id, "portfolio_missing"]),
    )
    assert partial.score_breakdown.portfolio_compatibility == 30
    assert partial.confidence is ConfidenceLevel.LOW
    complete = scorer.score_pair(business(), investor(portfolio_company_ids=[record.id]))
    assert complete.confidence is ConfidenceLevel.MEDIUM
    assert scorer.score_pair(business(traction=None),
                             investor(portfolio_company_ids=[record.id])).confidence == "low"


def test_investor_mode_uses_correct_ids_and_exclusions():
    a, b = business(id="business_aaa"), business(id="business_bbb")
    target = investor()
    results = engine().rank_businesses(target, [b, a], excluded_business_ids=[b.id])
    assert len(results) == 1
    assert results[0].direction is MatchDirection.INVESTOR_TO_BUSINESS
    assert results[0].query_entity_id == target.id
    assert results[0].candidate_entity_id == a.id
    assert engine().rank_businesses(target, []) == []


@pytest.mark.parametrize("top_k", [0, -1, 11, True, 1.5])
def test_invalid_limits_are_rejected(top_k):
    with pytest.raises(ValueError, match="top_k"):
        engine().rank_investors(business(), [], top_k=top_k)


def test_duplicate_candidate_and_portfolio_ids_are_rejected():
    with pytest.raises(ValueError, match="unique"):
        engine().rank_investors(business(), [investor(), investor()])
    with pytest.raises(ValueError, match="unique"):
        engine([portfolio(), portfolio()])


@pytest.mark.parametrize("args", [
    ["--business", "business_solargrid_africa", "--core-only"],
    ["--investor", "investor_greenfront"],
])
def test_demo_command_returns_valid_json(args, capsys):
    from app.matching.__main__ import main
    main(args)
    payload = json.loads(capsys.readouterr().out)
    assert "synthetic FX" in payload["notice"]
    assert payload["matches"]
    for item in payload["matches"]:
        MatchResult.model_validate(item)


def test_demo_command_rejects_unknown_id():
    from app.matching.__main__ import main
    with pytest.raises(SystemExit) as error:
        main(["--business", "business_unknown"])
    assert error.value.code == 2


def test_all_demo_rankings_are_valid_traceable_and_reproducible():
    root = Path(__file__).resolve().parents[2] / "data"
    def read(name, model):
        return [model.model_validate(item)
                for item in json.loads((root / name).read_text(encoding="utf-8"))]
    businesses = read("businesses.json", BusinessProfile)
    investors = read("investors.json", InvestorProfile)
    portfolios = read("portfolios.json", PortfolioCompany)
    from app.matching import EligibilityEngine
    from app.services import CurrencyNormalizer
    scorer = CompatibilityEngine(
        EligibilityEngine(CurrencyNormalizer.from_json_file(root / "fx_rates.demo.json")),
        portfolios,
    )
    records = {item.id: item for item in [*businesses, *investors, *portfolios]}
    found = 0
    for company in businesses:
        results = scorer.rank_investors(company, investors, top_k=10)
        found += bool(results)
        assert results == scorer.rank_investors(company, list(reversed(investors)), top_k=10)
        for result in results:
            assert 0 <= result.overall_score <= 100
            assert result.eligibility_status != "ineligible"
            for item in result.evidence:
                assert item.source_entity_id in records
                assert item.source_field in type(records[item.source_entity_id]).model_fields
    assert found >= 20
    solar = scorer.score_pair(records["business_solargrid_africa"], records["investor_greenfront"])
    assert "possible_portfolio_competition" in {c.code for c in solar.concerns}
    assert any(e.source_entity_id == "portfolio_gridwatch" for e in solar.evidence)
    for target in investors:
        for result in scorer.rank_businesses(target, businesses, top_k=10):
            assert result.query_entity_id == target.id
            assert result.eligibility_status != "ineligible"
