"""Deterministic matching logic that runs independently of the agent."""

from .eligibility import EligibilityEngine, business_geography_tags
from .scoring import CompatibilityEngine, IneligibleMatchError

__all__ = [
    "CompatibilityEngine", "EligibilityEngine", "IneligibleMatchError",
    "business_geography_tags",
]
