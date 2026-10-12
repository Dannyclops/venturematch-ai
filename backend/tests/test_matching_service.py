"""Network-free application service checks, separate from ASGI transport tests."""

import pytest

from app.models import MatchRequest
from app.services.matching import MatchingServiceError, match_profiles
from app.tools import MatchingCatalog, MatchingTools


@pytest.mark.parametrize("mode", ["founder", "investor"])
def test_service_preserves_tool_ranking_evidence_and_fx(mode):
    catalog = MatchingCatalog.from_demo()
    profile = catalog.businesses[0] if mode == "founder" else catalog.investors[0]
    key = "business_profile" if mode == "founder" else "investor_profile"
    request = MatchRequest.model_validate({
        "mode": mode, key: profile, "objective": "Find compatible investment partners.", "top_k": 3,
    })
    expected = MatchingTools(request, catalog).invoke("score_matches", {})["data"]
    result = match_profiles(request, catalog)
    assert result.execution_mode == "engine_only"
    assert result.response.model_dump(mode="json")["matches"] == expected["matches"]
    assert result.considered_count == expected["considered_count"]
    assert result.response.matches
    assert result.response.activity == []  # No fabricated agent steps.
    assert result.response.normalized_objective == request.objective
    assert any("no AI model" in warning for warning in result.response.warnings)


def test_no_matches_is_a_success_with_notice_and_no_constraint_relaxation():
    catalog = MatchingCatalog.from_demo()
    request = MatchRequest(
        mode="founder", business_profile=catalog.businesses[0],
        objective="Find compatible investment partners.",
        constraints={"excluded_entity_ids": [item.id for item in catalog.investors]},
    )
    result = match_profiles(request, catalog)
    assert result.considered_count == 0
    assert result.response.matches == []
    assert any("No candidates" in warning for warning in result.response.warnings)


@pytest.mark.parametrize("code,status", [("missing_fx_rate", 503), ("internal_error", 500)])
def test_tool_failures_are_not_disguised_as_empty_results(monkeypatch, code, status):
    catalog = MatchingCatalog.from_demo()
    request = MatchRequest(mode="founder", business_profile=catalog.businesses[0],
                           objective="Find compatible investment partners.")
    monkeypatch.setattr(MatchingTools, "invoke", lambda *args: {
        "ok": False, "error": {"code": code, "message": "private_internal_content"},
    })
    with pytest.raises(MatchingServiceError) as error:
        match_profiles(request, catalog)
    assert error.value.status_code == status
    assert "private_internal_content" not in str(error.value)
