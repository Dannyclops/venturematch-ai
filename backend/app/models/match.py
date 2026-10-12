"""Explainable matching outputs shared by the API and agent."""

from __future__ import annotations

from enum import Enum
from typing import Annotated, Literal

from pydantic import Field

from .common import EntityId, SchemaModel, Score
from .eligibility import EligibilityResult, EligibilityStatus


class MatchDirection(str, Enum):
    FOUNDER_TO_INVESTOR = "founder_to_investor"
    INVESTOR_TO_BUSINESS = "investor_to_business"


class MatchFactor(str, Enum):
    INDUSTRY_ALIGNMENT = "industry_alignment"
    FUNDING_STAGE_ALIGNMENT = "funding_stage_alignment"
    TICKET_SIZE_COMPATIBILITY = "ticket_size_compatibility"
    SEMANTIC_THESIS_SIMILARITY = "semantic_thesis_similarity"
    GEOGRAPHIC_ALIGNMENT = "geographic_alignment"
    PORTFOLIO_COMPATIBILITY = "portfolio_compatibility"


class ConfidenceLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class ConcernSeverity(str, Enum):
    INFO = "info"
    WARNING = "warning"
    BLOCKING = "blocking"


class ScoreBreakdown(SchemaModel):
    industry_alignment: Score
    funding_stage_alignment: Score
    ticket_size_compatibility: Score
    semantic_thesis_similarity: Score
    geographic_alignment: Score
    portfolio_compatibility: Score


class MatchEvidence(SchemaModel):
    """A traceable fact supporting one component of a recommendation."""

    factor: MatchFactor
    source_entity_id: EntityId
    source_field: Annotated[str, Field(min_length=1, max_length=100)]
    statement: Annotated[str, Field(min_length=10, max_length=500)]


class MatchConcern(SchemaModel):
    code: Annotated[str, Field(min_length=3, max_length=64, pattern=r"^[a-z0-9_]+$")]
    severity: ConcernSeverity
    message: Annotated[str, Field(min_length=10, max_length=500)]


class MatchResult(SchemaModel):
    direction: MatchDirection
    query_entity_id: EntityId
    candidate_entity_id: EntityId
    candidate_name: Annotated[str, Field(min_length=2, max_length=120)]
    eligibility_status: Literal[
        EligibilityStatus.CORE_ELIGIBLE,
        EligibilityStatus.EXPLORATION_ELIGIBLE,
    ]
    rank: Annotated[int, Field(ge=1)]
    overall_score: Score
    score_breakdown: ScoreBreakdown
    evidence: Annotated[list[MatchEvidence], Field(min_length=1, max_length=20)]
    concerns: Annotated[list[MatchConcern], Field(max_length=10)] = Field(default_factory=list)
    explanation: Annotated[str, Field(min_length=20, max_length=1_500)]
    confidence: ConfidenceLevel
    scoring_version: Literal["compatibility_v1"]
    thesis_similarity_method: Literal["keyword_jaccard_v1"]
    scoring_weights: ScoreBreakdown
    eligibility: EligibilityResult

