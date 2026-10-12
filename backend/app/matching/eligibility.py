"""Currency-aware hard filters for business-investor discovery."""

from __future__ import annotations

import unicodedata
from collections.abc import Iterable, Sequence
from decimal import Decimal

from app.models.business import BusinessProfile
from app.models.common import NormalizedMoneyRange
from app.models.eligibility import (
    EligibilityCheck,
    EligibilityOutcome,
    EligibilityResult,
    EligibilityRule,
    EligibilityStatus,
)
from app.models.investor import InvestorProfile, StageFlexibility
from app.services.currency import CurrencyNormalizer


COUNTRY_CODE_NAMES = {
    "AE": "united arab emirates",
    "EG": "egypt",
    "GH": "ghana",
    "KE": "kenya",
    "NG": "nigeria",
    "TR": "turkiye",
    "ZA": "south africa",
}

GEOGRAPHY_ALIASES = {
    "middle east and north africa": "mena",
    "turkey": "turkiye",
    "u a e": "united arab emirates",
    "uae": "united arab emirates",
}

COUNTRY_REGIONS = {
    "botswana": {"africa", "southern africa", "emerging markets"},
    "cote d'ivoire": {"africa", "west africa", "emerging markets"},
    "egypt": {"africa", "mena", "emerging markets"},
    "ghana": {"africa", "west africa", "emerging markets"},
    "jordan": {"mena", "emerging markets"},
    "kenya": {"africa", "east africa", "emerging markets"},
    "namibia": {"africa", "southern africa", "emerging markets"},
    "nigeria": {"africa", "west africa", "emerging markets"},
    "saudi arabia": {"mena", "emerging markets"},
    "senegal": {"africa", "west africa", "emerging markets"},
    "south africa": {"africa", "southern africa", "emerging markets"},
    "tanzania": {"africa", "east africa", "emerging markets"},
    "turkiye": {"europe", "southeast europe", "emerging markets"},
    "uganda": {"africa", "east africa", "emerging markets"},
    "united arab emirates": {"mena", "emerging markets"},
}


def normalize_geography(value: str) -> str:
    """Return one stable comparison key for user and dataset geography labels."""

    ascii_value = "".join(
        character
        for character in unicodedata.normalize("NFKD", value.casefold())
        if not unicodedata.combining(character)
    )
    normalized = " ".join(
        ascii_value.replace("\u2019", "'").replace(".", " ").replace("-", " ").split()
    )
    return GEOGRAPHY_ALIASES.get(normalized, normalized)


def business_geography_tags(business: BusinessProfile) -> set[str]:
    """Expand direct business locations into deterministic region tags."""

    direct_values = {
        *business.operating_markets,
        business.headquarters.city or "",
        business.headquarters.region or "",
        COUNTRY_CODE_NAMES.get(business.headquarters.country_code, ""),
    }
    tags = {normalize_geography(value) for value in direct_values if value}
    for value in tuple(tags):
        tags.update(COUNTRY_REGIONS.get(value, set()))
    return tags


def _check(
    rule: EligibilityRule,
    outcome: EligibilityOutcome,
    code: str,
    message: str,
) -> EligibilityCheck:
    return EligibilityCheck(rule=rule, outcome=outcome, code=code, message=message)


class EligibilityEngine:
    """Evaluates hard constraints before any compatibility score is calculated."""

    def __init__(self, currency_normalizer: CurrencyNormalizer) -> None:
        self.currency_normalizer = currency_normalizer

    def evaluate_pair(
        self,
        business: BusinessProfile,
        investor: InvestorProfile,
    ) -> EligibilityResult:
        normalized_raise = self.currency_normalizer.normalize_amount(business.amount_raising)
        normalized_ticket = self.currency_normalizer.normalize_range(investor.ticket_size)

        checks = [
            self._activity_check(investor),
            self._industry_check(business, investor),
            self._stage_check(business, investor),
            self._ticket_check(normalized_raise.normalized_amount, normalized_ticket),
            self._geography_check(business, investor),
            self._revenue_check(business, investor),
        ]

        if any(check.outcome is EligibilityOutcome.BLOCKING for check in checks):
            status = EligibilityStatus.INELIGIBLE
        elif any(check.outcome is EligibilityOutcome.EXPLORATION for check in checks):
            status = EligibilityStatus.EXPLORATION_ELIGIBLE
        else:
            status = EligibilityStatus.CORE_ELIGIBLE

        return EligibilityResult(
            business_id=business.id,
            investor_id=investor.id,
            status=status,
            checks=checks,
            normalized_raise=normalized_raise,
            normalized_ticket=normalized_ticket,
        )

    def discover_investors(
        self,
        business: BusinessProfile,
        investors: Sequence[InvestorProfile],
        *,
        include_exploration_matches: bool = True,
        excluded_investor_ids: Iterable[str] = (),
    ) -> list[EligibilityResult]:
        excluded = set(excluded_investor_ids)
        results = (
            self.evaluate_pair(business, investor)
            for investor in investors
            if investor.id not in excluded
        )
        return self._discoverable(results, include_exploration_matches)

    def discover_businesses(
        self,
        investor: InvestorProfile,
        businesses: Sequence[BusinessProfile],
        *,
        include_exploration_matches: bool = True,
        excluded_business_ids: Iterable[str] = (),
    ) -> list[EligibilityResult]:
        excluded = set(excluded_business_ids)
        results = (
            self.evaluate_pair(business, investor)
            for business in businesses
            if business.id not in excluded
        )
        return self._discoverable(results, include_exploration_matches)

    @staticmethod
    def _discoverable(
        results: Iterable[EligibilityResult],
        include_exploration_matches: bool,
    ) -> list[EligibilityResult]:
        accepted_statuses = {EligibilityStatus.CORE_ELIGIBLE}
        if include_exploration_matches:
            accepted_statuses.add(EligibilityStatus.EXPLORATION_ELIGIBLE)

        accepted = [result for result in results if result.status in accepted_statuses]
        return sorted(
            accepted,
            key=lambda result: result.status is EligibilityStatus.EXPLORATION_ELIGIBLE,
        )

    @staticmethod
    def _activity_check(investor: InvestorProfile) -> EligibilityCheck:
        if investor.actively_investing:
            return _check(
                EligibilityRule.INVESTOR_ACTIVITY,
                EligibilityOutcome.PASSED,
                "investor_active",
                f"{investor.name} is currently marked as actively investing.",
            )
        return _check(
            EligibilityRule.INVESTOR_ACTIVITY,
            EligibilityOutcome.BLOCKING,
            "investor_inactive",
            f"{investor.name} is not currently marked as actively investing.",
        )

    @staticmethod
    def _industry_check(
        business: BusinessProfile,
        investor: InvestorProfile,
    ) -> EligibilityCheck:
        industry = business.primary_industry
        if industry in investor.excluded_industries:
            return _check(
                EligibilityRule.INDUSTRY_MANDATE,
                EligibilityOutcome.BLOCKING,
                "industry_excluded",
                f"{industry.value} is explicitly excluded by {investor.name}.",
            )
        if industry in investor.preferred_industries:
            return _check(
                EligibilityRule.INDUSTRY_MANDATE,
                EligibilityOutcome.PASSED,
                "industry_preferred",
                f"{industry.value} is within {investor.name}'s preferred industries.",
            )
        return _check(
            EligibilityRule.INDUSTRY_MANDATE,
            EligibilityOutcome.BLOCKING,
            "industry_outside_mandate",
            f"{industry.value} is outside {investor.name}'s stated industry mandate.",
        )

    @staticmethod
    def _stage_check(
        business: BusinessProfile,
        investor: InvestorProfile,
    ) -> EligibilityCheck:
        stage = business.funding_stage
        if stage in investor.preferred_stages:
            return _check(
                EligibilityRule.FUNDING_STAGE,
                EligibilityOutcome.PASSED,
                "stage_preferred",
                f"{stage.value} is within {investor.name}'s preferred funding stages.",
            )

        can_explore = (
            investor.stage_flexibility is StageFlexibility.OPEN
            or stage in investor.exploratory_stages
        )
        if can_explore:
            return _check(
                EligibilityRule.FUNDING_STAGE,
                EligibilityOutcome.EXPLORATION,
                "stage_exploration",
                f"{stage.value} is outside the usual mandate but allowed for exploration.",
            )
        return _check(
            EligibilityRule.FUNDING_STAGE,
            EligibilityOutcome.BLOCKING,
            "stage_not_supported",
            f"{stage.value} is not permitted by {investor.name}'s funding-stage policy.",
        )

    @staticmethod
    def _ticket_check(
        normalized_raise: Decimal,
        normalized_ticket: NormalizedMoneyRange,
    ) -> EligibilityCheck:
        if normalized_raise < normalized_ticket.normalized_minimum:
            return _check(
                EligibilityRule.TICKET_SIZE,
                EligibilityOutcome.BLOCKING,
                "raise_below_ticket_minimum",
                "The normalized raise is below the investor's minimum ticket size.",
            )
        if normalized_raise > normalized_ticket.normalized_maximum:
            return _check(
                EligibilityRule.TICKET_SIZE,
                EligibilityOutcome.BLOCKING,
                "raise_above_ticket_maximum",
                "The normalized raise is above the investor's maximum ticket size.",
            )
        return _check(
            EligibilityRule.TICKET_SIZE,
            EligibilityOutcome.PASSED,
            "ticket_compatible",
            "The normalized raise falls within the investor's inclusive ticket range.",
        )

    @staticmethod
    def _geography_check(
        business: BusinessProfile,
        investor: InvestorProfile,
    ) -> EligibilityCheck:
        investor_geographies = {
            normalize_geography(value) for value in investor.preferred_geographies
        }
        if "global" in investor_geographies:
            return _check(
                EligibilityRule.GEOGRAPHY,
                EligibilityOutcome.PASSED,
                "geography_global",
                f"{investor.name} has a global geographic mandate.",
            )

        shared = business_geography_tags(business) & investor_geographies
        if shared:
            matched = ", ".join(sorted(shared))
            return _check(
                EligibilityRule.GEOGRAPHY,
                EligibilityOutcome.PASSED,
                "geography_supported",
                f"The business and investor share geographic coverage: {matched}.",
            )
        return _check(
            EligibilityRule.GEOGRAPHY,
            EligibilityOutcome.BLOCKING,
            "geography_outside_mandate",
            f"{business.name} does not operate within {investor.name}'s stated geographies.",
        )

    @staticmethod
    def _revenue_check(
        business: BusinessProfile,
        investor: InvestorProfile,
    ) -> EligibilityCheck:
        is_revenue_generating = business.traction is not None and (
            business.traction.is_revenue_generating
        )
        if investor.requires_revenue and not is_revenue_generating:
            return _check(
                EligibilityRule.REVENUE_REQUIREMENT,
                EligibilityOutcome.BLOCKING,
                "revenue_required",
                f"{investor.name} requires revenue, but the business is not revenue-generating.",
            )
        if investor.requires_revenue:
            message = "The business satisfies the investor's revenue requirement."
        else:
            message = "The investor does not require the business to be revenue-generating."
        return _check(
            EligibilityRule.REVENUE_REQUIREMENT,
            EligibilityOutcome.PASSED,
            "revenue_compatible",
            message,
        )
