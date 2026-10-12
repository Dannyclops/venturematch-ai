"""Public data contracts for the VentureMatch AI backend."""

from .agent import (
    AgentActivity,
    AgentActivityStatus,
    MatchConstraints,
    MatchRequest,
    MatchResponse,
    RefinementRequest,
    UserMode,
)
from .business import BusinessProfile, TractionMetrics
from .common import (
    BusinessModel,
    FundingStage,
    Industry,
    Location,
    FxRate,
    FxSnapshot,
    MoneyAmount,
    MoneyRange,
    NormalizedMoneyAmount,
    NormalizedMoneyRange,
    SupportedCurrency,
)
from .investor import (
    InvestmentRole,
    InvestorProfile,
    InvestorType,
    PortfolioCompany,
    StageFlexibility,
)
from .match import (
    ConfidenceLevel,
    ConcernSeverity,
    MatchConcern,
    MatchDirection,
    MatchEvidence,
    MatchFactor,
    MatchResult,
    ScoreBreakdown,
)

__all__ = [
    "AgentActivity",
    "AgentActivityStatus",
    "BusinessModel",
    "BusinessProfile",
    "ConfidenceLevel",
    "ConcernSeverity",
    "FundingStage",
    "FxRate",
    "FxSnapshot",
    "Industry",
    "InvestmentRole",
    "InvestorProfile",
    "InvestorType",
    "Location",
    "MatchConcern",
    "MatchConstraints",
    "MatchDirection",
    "MatchEvidence",
    "MatchFactor",
    "MatchRequest",
    "MatchResponse",
    "MatchResult",
    "MoneyAmount",
    "MoneyRange",
    "NormalizedMoneyAmount",
    "NormalizedMoneyRange",
    "PortfolioCompany",
    "RefinementRequest",
    "ScoreBreakdown",
    "StageFlexibility",
    "SupportedCurrency",
    "TractionMetrics",
    "UserMode",
]

