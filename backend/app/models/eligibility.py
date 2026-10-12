"""Deterministic eligibility decisions produced before match scoring."""

from __future__ import annotations

from enum import Enum
from typing import Annotated, Self

from pydantic import Field, model_validator

from .common import (
    EntityId,
    NormalizedMoneyAmount,
    NormalizedMoneyRange,
    SchemaModel,
)


class EligibilityStatus(str, Enum):
    CORE_ELIGIBLE = "core_eligible"
    EXPLORATION_ELIGIBLE = "exploration_eligible"
    INELIGIBLE = "ineligible"


class EligibilityRule(str, Enum):
    INVESTOR_ACTIVITY = "investor_activity"
    INDUSTRY_MANDATE = "industry_mandate"
    FUNDING_STAGE = "funding_stage"
    TICKET_SIZE = "ticket_size"
    GEOGRAPHY = "geography"
    REVENUE_REQUIREMENT = "revenue_requirement"


class EligibilityOutcome(str, Enum):
    PASSED = "passed"
    EXPLORATION = "exploration"
    BLOCKING = "blocking"


class EligibilityCheck(SchemaModel):
    """One reproducible rule decision with an agent-readable explanation."""

    rule: EligibilityRule
    outcome: EligibilityOutcome
    code: Annotated[str, Field(min_length=3, max_length=64, pattern=r"^[a-z0-9_]+$")]
    message: Annotated[str, Field(min_length=10, max_length=500)]


class EligibilityResult(SchemaModel):
    """Complete pre-scoring decision for one business-investor pair."""

    business_id: EntityId
    investor_id: EntityId
    status: EligibilityStatus
    checks: Annotated[list[EligibilityCheck], Field(min_length=1, max_length=10)]
    normalized_raise: NormalizedMoneyAmount
    normalized_ticket: NormalizedMoneyRange

    @model_validator(mode="after")
    def status_must_match_check_outcomes(self) -> Self:
        rules = [check.rule for check in self.checks]
        if len(rules) != len(set(rules)):
            raise ValueError("checks must contain each eligibility rule at most once")

        if any(check.outcome is EligibilityOutcome.BLOCKING for check in self.checks):
            expected = EligibilityStatus.INELIGIBLE
        elif any(check.outcome is EligibilityOutcome.EXPLORATION for check in self.checks):
            expected = EligibilityStatus.EXPLORATION_ELIGIBLE
        else:
            expected = EligibilityStatus.CORE_ELIGIBLE

        if self.status is not expected:
            raise ValueError(f"status must be {expected.value} for the supplied checks")
        return self
