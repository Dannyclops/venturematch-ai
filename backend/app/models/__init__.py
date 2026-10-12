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
    MoneyAmount,
    MoneyRange,
)
from .investor import (
    InvestmentRole,
    InvestorProfile,
    InvestorType,
    PortfolioCompany,
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
    "PortfolioCompany",
    "RefinementRequest",
    "ScoreBreakdown",
    "TractionMetrics",
    "UserMode",
]

