"""Versioned, offline compatibility scoring; never an investment probability."""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Iterable, Sequence
from decimal import Decimal, ROUND_HALF_UP
from types import MappingProxyType

from app.models import (
    BusinessProfile, ConfidenceLevel, ConcernSeverity, EligibilityResult,
    EligibilityStatus, InvestorProfile, MatchConcern, MatchDirection, MatchEvidence,
    MatchFactor, MatchResult, PortfolioCompany, ScoreBreakdown,
)
from app.models.investor import FUNDING_STAGE_ORDER
from .eligibility import (
    COUNTRY_CODE_NAMES, EligibilityEngine, business_geography_tags, normalize_geography,
)

SCORING_WEIGHTS = MappingProxyType({
    "industry_alignment": 25,
    "funding_stage_alignment": 20,
    "ticket_size_compatibility": 20,
    "semantic_thesis_similarity": 15,
    "geographic_alignment": 10,
    "portfolio_compatibility": 10,
})
STOP_WORDS = frozenset(
    "a an and are as at be by for from in into is it of on or our that the their "
    "this to we with invest invests investing back backs businesses business "
    "companies company founders teams technology solutions".split()
)


def tokens(*texts: str) -> set[str]:
    """Unique Unicode word tokens; no embeddings, stemming, or negation inference."""
    text = unicodedata.normalize("NFKC", " ".join(texts)).casefold()
    return {word for word in re.findall(r"[^\W_]+", text)
            if len(word) > 1 and word not in STOP_WORDS}


def jaccard(left: set[str], right: set[str]) -> float:
    union = left | right
    return len(left & right) / len(union) if union else 0.0


def rounded(value: Decimal | float) -> float:
    return float(Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


def weighted_total(scores: ScoreBreakdown) -> float:
    return rounded(sum(
        Decimal(str(getattr(scores, field))) * Decimal(weight) / 100
        for field, weight in SCORING_WEIGHTS.items()
    ))


class IneligibleMatchError(ValueError):
    """Includes the complete rejected decision for callers needing explanations."""

    def __init__(self, eligibility: EligibilityResult) -> None:
        self.eligibility = eligibility
        super().__init__("Ineligible pairs cannot receive compatibility scores.")


def evidence(factor: MatchFactor, entity_id: str, field: str, text: str) -> MatchEvidence:
    return MatchEvidence(
        factor=factor, source_entity_id=entity_id, source_field=field,
        statement=text[:500],
    )


def concern(code: str, text: str, *, warning: bool = True) -> MatchConcern:
    return MatchConcern(
        code=code,
        severity=ConcernSeverity.WARNING if warning else ConcernSeverity.INFO,
        message=text[:500],
    )


class CompatibilityEngine:
    """Always reevaluates eligibility; no caller-supplied approval can bypass it."""

    def __init__(
        self, eligibility_engine: EligibilityEngine,
        portfolios: Sequence[PortfolioCompany] = (),
    ) -> None:
        self.eligibility_engine = eligibility_engine
        self._portfolios = {company.id: company.model_copy(deep=True) for company in portfolios}
        if len(self._portfolios) != len(portfolios):
            raise ValueError("Portfolio company IDs must be unique.")

    def score_pair(
        self, business: BusinessProfile, investor: InvestorProfile, *,
        direction: MatchDirection = MatchDirection.FOUNDER_TO_INVESTOR,
    ) -> MatchResult:
        direction = MatchDirection(direction)
        decision = self.eligibility_engine.evaluate_pair(business, investor)
        if decision.status is EligibilityStatus.INELIGIBLE:
            raise IneligibleMatchError(decision)

        stage_distance = min(
            abs(FUNDING_STAGE_ORDER[business.funding_stage] - FUNDING_STAGE_ORDER[stage])
            for stage in investor.preferred_stages
        )
        stage_score = 100 if stage_distance == 0 else max(40, 85 - 15 * stage_distance)
        amount = decision.normalized_raise.normalized_amount
        lower = decision.normalized_ticket.normalized_minimum
        upper = decision.normalized_ticket.normalized_maximum
        # Inclusive eligibility is already checked. Fixed ranges score 100.
        ticket_score = (Decimal(100) if lower == upper else
                        Decimal(100) - 25 * abs(2 * amount - lower - upper) / (upper - lower))

        direct = {normalize_geography(value) for value in (
            *business.operating_markets, business.headquarters.city or "",
            business.headquarters.region or "",
            COUNTRY_CODE_NAMES.get(business.headquarters.country_code, ""),
        ) if value}
        preferred = {normalize_geography(value) for value in investor.preferred_geographies}
        shared_geo = sorted(business_geography_tags(business) & preferred)
        geo_score = 100 if direct & preferred else (80 if shared_geo else 60)

        business_words = tokens(business.description, business.one_liner,
                                *business.industry_tags, *business.keywords)
        investor_words = tokens(investor.thesis, *investor.keywords)
        shared_words = sorted(business_words & investor_words)
        thesis_score = rounded(100 * jaccard(business_words, investor_words))
        portfolio_score, portfolio_evidence, portfolio_concerns, incomplete = (
            self._portfolio_score(business, investor)
        )
        scores = ScoreBreakdown(
            industry_alignment=100,
            funding_stage_alignment=stage_score,
            ticket_size_compatibility=rounded(ticket_score),
            semantic_thesis_similarity=thesis_score,
            geographic_alignment=geo_score,
            portfolio_compatibility=portfolio_score,
        )
        total = weighted_total(scores)
        facts = [
            evidence(MatchFactor.INDUSTRY_ALIGNMENT, business.id, "primary_industry",
                     f"Business industry: {business.primary_industry.value}."),
            evidence(MatchFactor.INDUSTRY_ALIGNMENT, investor.id, "preferred_industries",
                     f"The stated mandate includes {business.primary_industry.value}."),
            evidence(MatchFactor.FUNDING_STAGE_ALIGNMENT, business.id, "funding_stage",
                     f"Current funding stage: {business.funding_stage.value}."),
            evidence(MatchFactor.FUNDING_STAGE_ALIGNMENT, investor.id, "preferred_stages",
                     f"Nearest preferred stage is {stage_distance} lifecycle step(s) away."),
            evidence(MatchFactor.TICKET_SIZE_COMPATIBILITY, business.id, "amount_raising",
                     f"Raise converts to {amount} {decision.normalized_raise.normalized_currency.value}; "
                     f"FX source: {decision.normalized_raise.rate_source}."),
            evidence(MatchFactor.TICKET_SIZE_COMPATIBILITY, investor.id, "ticket_size",
                     f"Converted inclusive ticket range: {lower} to {upper}. "
                     "Score uses distance from the range midpoint as a heuristic."),
            evidence(MatchFactor.GEOGRAPHIC_ALIGNMENT, investor.id, "preferred_geographies",
                     f"Geographic overlap: {', '.join(shared_geo) or 'global mandate'}. "
                     f"Geographic specificity score: {geo_score}."),
            evidence(MatchFactor.SEMANTIC_THESIS_SIMILARITY, business.id, "description",
                     "Compared description, one_liner, industry_tags and keywords "
                     "with investor thesis and keywords using unique-token Jaccard."),
            evidence(MatchFactor.SEMANTIC_THESIS_SIMILARITY, investor.id, "thesis",
                     "Shared tokens from thesis/keywords and business text: "
                     + (", ".join(shared_words[:30]) or "none") + "."),
            *portfolio_evidence,
        ]
        concerns = [
            concern("keyword_similarity_baseline",
                    "Thesis similarity is a lexical baseline, not semantic understanding; "
                    "it can miss synonyms and misread negation.", warning=False),
            concern("estimated_currency_conversion",
                    "Ticket comparison uses an estimated FX snapshot, not an execution quote.",
                    warning=False),
            *portfolio_concerns,
        ]
        if decision.status is EligibilityStatus.EXPLORATION_ELIGIBLE:
            concerns.append(concern("outside_usual_stage",
                                    "Outside the investor's preferred stages; permitted for exploration."))
        if business.traction is None:
            concerns.append(concern("traction_unknown",
                                    "Traction is not supplied; confidence in the profile is limited."))
        confidence = ConfidenceLevel.LOW if incomplete or business.traction is None else (
            ConfidenceLevel.MEDIUM
        )
        candidate = investor if direction is MatchDirection.FOUNDER_TO_INVESTOR else business
        query = business if direction is MatchDirection.FOUNDER_TO_INVESTOR else investor
        label = "Core" if decision.status is EligibilityStatus.CORE_ELIGIBLE else "Exploration"
        explanation = (
            f"{label} match: {total:.2f}/100 under compatibility_v1. "
            f"Industry {scores.industry_alignment:g}, stage {stage_score}, "
            f"ticket {scores.ticket_size_compatibility:g}, keyword thesis {thesis_score:g}, "
            f"geography {geo_score}, portfolio {portfolio_score:g}. "
            "All eligibility rules passed, with any stage exploration labelled. "
            "This heuristic score is not a probability of investment. "
            + " ".join(item.message for item in concerns
                       if item.severity is ConcernSeverity.WARNING)
        )
        return MatchResult(
            direction=direction, query_entity_id=query.id,
            candidate_entity_id=candidate.id, candidate_name=candidate.name,
            eligibility_status=decision.status, rank=1, overall_score=total,
            score_breakdown=scores, evidence=facts, concerns=concerns,
            explanation=explanation[:1500], confidence=confidence,
            scoring_version="compatibility_v1", thesis_similarity_method="keyword_jaccard_v1",
            scoring_weights=ScoreBreakdown(**SCORING_WEIGHTS), eligibility=decision,
        )

    def _portfolio_score(
        self, business: BusinessProfile, investor: InvestorProfile,
    ) -> tuple[float, list[MatchEvidence], list[MatchConcern], bool]:
        ids = sorted(set(investor.portfolio_company_ids))
        known = [self._portfolios[entity_id] for entity_id in ids if entity_id in self._portfolios]
        missing = len(ids) - len(known)
        incomplete = missing > 0 or not ids
        facts = [evidence(
            MatchFactor.PORTFOLIO_COMPATIBILITY, investor.id, "portfolio_company_ids",
            f"{len(known)} of {len(ids)} linked portfolio records available. "
            "Only this investor's linked records are compared.",
        )]
        concerns = []
        if incomplete:
            concerns.append(concern(
                "portfolio_data_incomplete",
                "Portfolio evidence is absent or incomplete; neutral 50 unless known overlap lowers it.",
            ))
        same_sector = [company for company in known
                       if company.primary_industry == business.primary_industry]
        business_words = tokens(*business.keywords, *business.industry_tags)
        overlaps = [
            (jaccard(business_words, tokens(*company.keywords)), company)
            for company in same_sector if company.business_model == business.business_model
        ]
        overlaps.sort(key=lambda item: (-item[0], item[1].id))
        if overlaps and overlaps[0][0] >= 0.25:
            similarity, company = overlaps[0]
            facts.append(evidence(
                MatchFactor.PORTFOLIO_COMPATIBILITY, company.id, "keywords",
                f"{company.name} shares industry and business model; keyword/tag Jaccard "
                f"is {similarity:.3f}, at least the 0.25 overlap threshold.",
            ))
            concerns.append(concern(
                "possible_portfolio_competition",
                f"Possible overlap with {company.name} ({company.id}); "
                "keyword similarity is a review signal, not proof of competition.",
            ))
            return 30, facts, concerns, incomplete
        if same_sector:
            company = sorted(same_sector, key=lambda item: item.id)[0]
            facts.append(evidence(
                MatchFactor.PORTFOLIO_COMPATIBILITY, company.id, "primary_industry",
                f"{company.name} supplies evidence of same-sector investing; "
                "no supplied record triggers the overlap heuristic.",
            ))
        # No reward for presumed diversification, and missing records cannot imply no conflict.
        return (50 if incomplete or not same_sector else 70), facts, concerns, incomplete

    def rank_investors(
        self, business: BusinessProfile, investors: Sequence[InvestorProfile], *,
        top_k: int = 5, include_exploration_matches: bool = True,
        excluded_investor_ids: Iterable[str] = (),
    ) -> list[MatchResult]:
        self._validate_candidates(investors, top_k)
        excluded = set(excluded_investor_ids)
        return self._rank(
            ((business, investor) for investor in investors if investor.id not in excluded),
            MatchDirection.FOUNDER_TO_INVESTOR, top_k, include_exploration_matches,
        )

    def rank_businesses(
        self, investor: InvestorProfile, businesses: Sequence[BusinessProfile], *,
        top_k: int = 5, include_exploration_matches: bool = True,
        excluded_business_ids: Iterable[str] = (),
    ) -> list[MatchResult]:
        self._validate_candidates(businesses, top_k)
        excluded = set(excluded_business_ids)
        return self._rank(
            ((business, investor) for business in businesses if business.id not in excluded),
            MatchDirection.INVESTOR_TO_BUSINESS, top_k, include_exploration_matches,
        )

    @staticmethod
    def _validate_candidates(
        candidates: Sequence[BusinessProfile] | Sequence[InvestorProfile], top_k: int,
    ) -> None:
        if type(top_k) is not int or not 1 <= top_k <= 10:
            raise ValueError("top_k must be an integer from 1 to 10.")
        if len({candidate.id for candidate in candidates}) != len(candidates):
            raise ValueError("Candidate IDs must be unique.")

    def _rank(
        self, pairs: Iterable[tuple[BusinessProfile, InvestorProfile]],
        direction: MatchDirection, top_k: int, include_exploration: bool,
    ) -> list[MatchResult]:
        results = []
        for business, investor in pairs:
            try:
                result = self.score_pair(business, investor, direction=direction)
            except IneligibleMatchError:
                continue
            if not include_exploration and (
                result.eligibility_status is EligibilityStatus.EXPLORATION_ELIGIBLE
            ):
                continue
            results.append(result)
        results.sort(key=lambda result: (
            result.eligibility_status is EligibilityStatus.EXPLORATION_ELIGIBLE,
            -result.overall_score, result.candidate_entity_id,
        ))
        selected = results[:top_k]
        for rank, result in enumerate(selected, start=1):
            result.rank = rank
        return selected
