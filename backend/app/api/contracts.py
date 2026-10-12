"""HTTP response contracts, reusing the canonical domain models."""

from typing import Generic, Literal, TypeVar

from pydantic import Field

from app.models import FxSnapshot
from app.models.common import BusinessModel, FundingStage, Industry, SchemaModel, SupportedCurrency
from app.models.investor import InvestmentRole, InvestorType, StageFlexibility

Profile = TypeVar("Profile")


class ProfilePage(SchemaModel, Generic[Profile]):
    items: list[Profile]
    total: int
    next_offset: int | None
    notice: str


class HealthResponse(SchemaModel):
    status: Literal["ok"] = "ok"
    execution_mode: Literal["engine_only"] = "engine_only"
    live_agent_enabled: Literal[False] = False


class MetadataResponse(SchemaModel):
    execution_mode: Literal["engine_only"] = "engine_only"
    industries: list[Industry]
    funding_stages: list[FundingStage]
    currencies: list[SupportedCurrency]
    business_models: list[BusinessModel]
    investor_types: list[InvestorType]
    investment_roles: list[InvestmentRole]
    stage_flexibility: list[StageFlexibility]
    fx_snapshot: FxSnapshot
    notice: str


class ValidationIssue(SchemaModel):
    location: list[str | int]
    code: str


class ApiError(SchemaModel):
    code: str
    message: str
    issues: list[ValidationIssue] = Field(default_factory=list)


class ErrorResponse(SchemaModel):
    error: ApiError
