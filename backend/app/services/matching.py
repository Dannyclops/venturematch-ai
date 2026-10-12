"""Engine-only application service: no provider client, credentials, or network."""

from typing import Literal
from uuid import uuid4

from app.models import MatchRequest, MatchResponse, SupportedCurrency
from app.models.common import SchemaModel
from app.tools import MatchingCatalog, MatchingTools
from app.tools.contracts import ProfileAnalysis, ScoredMatches


class EngineMatchResponse(SchemaModel):
    execution_mode: Literal["engine_only"] = "engine_only"
    response: MatchResponse
    considered_count: int
    display_currency: SupportedCurrency


class MatchingServiceError(Exception):
    """Static, safe errors for the HTTP adapter; no raw provider or profile data."""

    def __init__(self, code: str, message: str, status_code: int = 500):
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code


def match_profiles(request: MatchRequest, catalog: MatchingCatalog) -> EngineMatchResponse:
    toolbox = MatchingTools(request, catalog)

    def checked(name):
        result = toolbox.invoke(name, {})
        if not result["ok"]:
            if result["error"]["code"] == "missing_fx_rate":
                raise MatchingServiceError(
                    "missing_fx_rate", "A required currency rate is unavailable.", 503,
                )
            raise MatchingServiceError("matching_failed", "Matching could not be completed.")
        return result["data"]

    profile = ProfileAnalysis.model_validate(checked("analyze_profile"))
    scored = ScoredMatches.model_validate(checked("score_matches"))
    warnings = list(dict.fromkeys(profile.warnings + scored.warnings + [
        "Engine-only matching: no AI model was called.",
        "The objective is retained as entered; use structured constraints to change matching.",
    ]))
    if not scored.matches:
        warnings.append("No candidates satisfy the profile and current constraints.")
    return EngineMatchResponse(
        response=MatchResponse(
            run_id="run_" + uuid4().hex, mode=request.mode,
            query_entity_id=profile.profile.id, normalized_objective=request.objective,
            matches=scored.matches, missing_information=profile.missing_information,
            warnings=warnings,
        ),
        considered_count=scored.considered_count, display_currency=scored.display_currency,
    )
