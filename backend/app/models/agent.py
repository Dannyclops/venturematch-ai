"""Agent request, refinement, progress, and response contracts."""

from __future__ import annotations

from enum import Enum
from typing import Annotated, Self

from pydantic import Field, field_validator, model_validator

from .business import BusinessProfile
from .common import EntityId, FundingStage, Industry, MoneyRange, SchemaModel
from .investor import InvestorProfile
from .match import MatchResult


class UserMode(str, Enum):
    FOUNDER = "founder"
    INVESTOR = "investor"


class AgentActivityStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class MatchConstraints(SchemaModel):
    industries: Annotated[list[Industry] | None, Field(min_length=1, max_length=10)] = None
    stages: Annotated[list[FundingStage] | None, Field(min_length=1, max_length=7)] = None
    geographies: Annotated[list[str] | None, Field(min_length=1, max_length=20)] = None
    ticket_size: MoneyRange | None = None
    excluded_entity_ids: Annotated[list[EntityId], Field(max_length=100)] = Field(default_factory=list)

    @field_validator("geographies")
    @classmethod
    def normalize_geographies(cls, values: list[str] | None) -> list[str] | None:
        if values is None:
            return None
        return list(dict.fromkeys(value.strip().lower() for value in values if value.strip()))

    @field_validator("excluded_entity_ids")
    @classmethod
    def deduplicate_excluded_ids(cls, values: list[str]) -> list[str]:
        return list(dict.fromkeys(values))


class MatchRequest(SchemaModel):
    """Starts a new founder-side or investor-side matching run."""

    mode: UserMode
    objective: Annotated[str, Field(min_length=10, max_length=1_000)]
    business_profile: BusinessProfile | None = None
    investor_profile: InvestorProfile | None = None
    constraints: MatchConstraints = Field(default_factory=MatchConstraints)
    top_k: Annotated[int, Field(ge=1, le=10)] = 5
    conversation_id: Annotated[str | None, Field(min_length=3, max_length=100)] = None

    @model_validator(mode="after")
    def profile_must_match_mode(self) -> Self:
        if self.mode is UserMode.FOUNDER:
            if self.business_profile is None or self.investor_profile is not None:
                raise ValueError("founder mode requires only business_profile")
        elif self.investor_profile is None or self.business_profile is not None:
            raise ValueError("investor mode requires only investor_profile")
        return self


class RefinementRequest(SchemaModel):
    """Changes the goal or constraints of a completed matching run."""

    run_id: Annotated[str, Field(min_length=3, max_length=100)]
    instruction: Annotated[str, Field(min_length=5, max_length=1_000)]
    constraints: MatchConstraints | None = None
    top_k: Annotated[int | None, Field(ge=1, le=10)] = None


class AgentActivity(SchemaModel):
    step: Annotated[str, Field(min_length=2, max_length=100)]
    status: AgentActivityStatus
    message: Annotated[str, Field(min_length=2, max_length=300)]


class MatchResponse(SchemaModel):
    run_id: Annotated[str, Field(min_length=3, max_length=100)]
    mode: UserMode
    query_entity_id: EntityId
    normalized_objective: Annotated[str, Field(min_length=10, max_length=1_000)]
    matches: Annotated[list[MatchResult], Field(max_length=10)]
    activity: Annotated[list[AgentActivity], Field(max_length=20)] = Field(default_factory=list)
    missing_information: Annotated[list[str], Field(max_length=20)] = Field(default_factory=list)
    warnings: Annotated[list[str], Field(max_length=20)] = Field(default_factory=list)
    suggested_refinements: Annotated[list[str], Field(max_length=10)] = Field(default_factory=list)

