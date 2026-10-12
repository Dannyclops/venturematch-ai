"""Provider-neutral tool input/output contracts; no LLM dependency."""

from typing import Annotated, Any, Self

from pydantic import Field, StrictInt, model_validator

from app.models import (
    BusinessProfile, EligibilityResult, InvestorProfile, MatchConcern, MatchConstraints,
    MatchEvidence, MatchResult, NormalizedMoneyAmount, NormalizedMoneyRange,
    SupportedCurrency, UserMode,
)
from app.models.common import EntityId, SchemaModel, Score


class EmptyArguments(SchemaModel):
    pass


class SearchArguments(SchemaModel):
    offset: Annotated[StrictInt, Field(ge=0)] = 0
    limit: Annotated[StrictInt, Field(ge=1, le=50)] = 20


class CandidateArguments(SchemaModel):
    candidate_id: EntityId


class ScoreArguments(SchemaModel):
    # None means the full eligible catalog, not an empty selection.
    candidate_ids: Annotated[list[EntityId] | None, Field(min_length=1, max_length=50)] = None


class ProfileAnalysis(SchemaModel):
    mode: UserMode
    profile: BusinessProfile | InvestorProfile
    normalized_money: NormalizedMoneyAmount | NormalizedMoneyRange
    constraints: MatchConstraints
    missing_information: list[str]
    warnings: list[str]


class SearchCandidate(SchemaModel):
    candidate_id: EntityId
    candidate_name: str
    eligibility: EligibilityResult


class SearchResult(SchemaModel):
    mode: UserMode
    query_entity_id: EntityId
    candidates: list[SearchCandidate]
    total: int
    next_offset: int | None
    warnings: list[str]


class ScoredMatches(SchemaModel):
    matches: list[MatchResult]
    considered_count: int
    display_currency: SupportedCurrency
    warnings: list[str]


class PortfolioAnalysis(SchemaModel):
    candidate_id: EntityId
    score: Score
    evidence: list[MatchEvidence]
    concerns: list[MatchConcern]
    warnings: list[str]


class EvidenceResult(SchemaModel):
    candidate_id: EntityId
    evidence: list[MatchEvidence]
    concerns: list[MatchConcern]
    eligibility: EligibilityResult
    scoring_version: str
    thesis_similarity_method: str
    warnings: list[str]


class ToolError(SchemaModel):
    code: str
    message: str
    details: dict[str, Any] = Field(default_factory=dict)


class ToolResponse(SchemaModel):
    tool_name: str
    ok: bool
    data: dict[str, Any] | None = None
    error: ToolError | None = None

    @model_validator(mode="after")
    def response_must_be_unambiguous(self) -> Self:
        if self.ok and (self.data is None or self.error is not None):
            raise ValueError("Successful responses require data and no error.")
        if not self.ok and (self.data is not None or self.error is None):
            raise ValueError("Failed responses require an error and no data.")
        return self
