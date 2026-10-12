"""HTTP contracts through the real ASGI app, with no network or OpenAI calls.

TestClient needs a working Windows asyncio runtime. Run in normal PowerShell
when the restricted environment cannot initialize the asyncio socket pair.
"""

import json

import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from app.models import MatchRequest
from app.services.matching import EngineMatchResponse, MatchingServiceError
from app.tools import MatchingCatalog, MatchingTools


@pytest.fixture
def catalog():
    return MatchingCatalog.from_demo()


@pytest.fixture
def client(catalog, monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    return TestClient(create_app(catalog), raise_server_exceptions=False)


def payload(catalog, mode="founder", **updates):
    key = "business_profile" if mode == "founder" else "investor_profile"
    profile = catalog.businesses[0] if mode == "founder" else catalog.investors[0]
    return {"mode": mode, key: profile.model_dump(mode="json"),
            "objective": "Find compatible investment partners.", "top_k": 3, **updates}


def test_http_health_metadata_and_no_live_routes(client):
    assert client.get("/api/health").json() == {
        "status": "ok", "execution_mode": "engine_only", "live_agent_enabled": False,
    }
    metadata = client.get("/api/metadata").json()
    assert len(metadata["currencies"]) == 9
    assert metadata["fx_snapshot"]["is_live"] is False
    assert set(metadata["stage_flexibility"]) == {"strict", "adjacent", "open"}
    assert client.post("/api/agent/match", json={}).status_code == 404


@pytest.mark.parametrize("path,total", [("businesses", 24), ("investors", 15)])
def test_http_profiles_pagination_and_detail(client, path, total):
    page = client.get(f"/api/{path}?limit=2").json()
    assert page["total"] == total
    assert page["next_offset"] == 2
    assert len(page["items"]) == 2
    assert "Fictional" in page["notice"]
    first = page["items"][0]
    assert client.get(f"/api/{path}/{first['id']}").json() == first
    second = client.get(f"/api/{path}?limit=2&offset=2").json()
    assert {item["id"] for item in page["items"]}.isdisjoint(item["id"] for item in second["items"])
    empty = client.get(f"/api/{path}?offset=100").json()
    assert empty["items"] == [] and empty["next_offset"] is None
    assert client.get(f"/api/{path}/unknown_id").status_code == 404
    assert client.get(f"/api/{path}?limit=51").status_code == 422


@pytest.mark.parametrize("mode", ["founder", "investor"])
def test_http_matching_equals_existing_tools(client, catalog, mode):
    request = payload(catalog, mode)
    expected = MatchingTools(MatchRequest.model_validate(request), catalog).invoke("score_matches", {})
    response = client.post("/api/matches", json=request)
    assert response.status_code == 200, response.text
    result = EngineMatchResponse.model_validate(response.json())
    assert result.execution_mode == "engine_only"
    assert result.response.model_dump(mode="json")["matches"] == expected["data"]["matches"]
    assert result.response.matches
    assert len(result.response.matches) <= 3
    assert result.response.activity == []


def test_http_constraints_empty_results_and_request_isolation(client, catalog):
    request = payload(catalog, constraints={"excluded_entity_ids": [i.id for i in catalog.investors]})
    empty = client.post("/api/matches", json=request)
    assert empty.status_code == 200
    assert empty.json()["response"]["matches"] == []
    assert client.post("/api/matches", json=payload(catalog)).json()["response"]["matches"]


def test_http_core_only_and_display_currency(client, catalog):
    result = client.post("/api/matches", json=payload(catalog, constraints={
        "include_exploration_matches": False, "display_currency": "EUR",
    })).json()
    assert result["display_currency"] == "EUR"
    assert all(m["eligibility_status"] == "core_eligible" for m in result["response"]["matches"])
    assert any("not implemented" in w for w in result["response"]["warnings"])


@pytest.mark.parametrize("updates", [
    {"top_k": 0}, {"top_k": 11}, {"mode": "investor"},
    {"objective": "short"}, {"execution_mode": "live"},
    {"constraints": {"display_currency": "XYZ"}},
])
def test_http_invalid_requests(client, catalog, updates):
    request = payload(catalog)
    request.update(updates)
    result = client.post("/api/matches", json=request)
    assert result.status_code == 422
    assert result.json()["error"]["code"] == "invalid_request"


def test_http_validation_does_not_echo_private_input(client, catalog):
    request = payload(catalog)
    request["business_profile"]["amount_raising"]["amount"] = "private_profile_secret"
    request["private_extra_field_secret"] = "private_value"
    result = client.post("/api/matches", json=request)
    assert result.status_code == 422
    assert "private_" not in result.text
    malformed = client.post("/api/matches", content='{"private_secret":',
                            headers={"Content-Type": "application/json"})
    assert malformed.status_code == 422
    assert "private_secret" not in malformed.text


@pytest.mark.parametrize("error,status,code", [
    (MatchingServiceError("missing_fx_rate", "A required currency rate is unavailable.", 503),
     503, "missing_fx_rate"),
    (RuntimeError("private_traceback_secret"), 500, "internal_error"),
])
def test_http_safe_server_errors(client, catalog, monkeypatch, error, status, code):
    def broken(*args):
        raise error
    monkeypatch.setattr("app.main.match_profiles", broken)
    result = client.post("/api/matches", json=payload(catalog))
    assert result.status_code == status
    assert result.json()["error"]["code"] == code
    assert "private_traceback_secret" not in result.text


def test_http_cors_allows_only_local_frontend_origins(client):
    local = client.options("/api/matches", headers={
        "Origin": "http://localhost:3000", "Access-Control-Request-Method": "POST",
        "Access-Control-Request-Headers": "content-type",
    })
    assert local.status_code == 200
    assert local.headers["access-control-allow-origin"] == "http://localhost:3000"
    external = client.get("/api/health", headers={"Origin": "https://example.com"})
    assert "access-control-allow-origin" not in external.headers


def test_openapi_documents_engine_mode_and_shared_contract(catalog):
    schema = create_app(catalog).openapi()
    assert "/api/matches" in schema["paths"]
    assert "/api/agent/match" not in schema["paths"]
    assert schema["components"]["schemas"]["EngineMatchResponse"]["properties"]["execution_mode"]["const"] == "engine_only"
    assert "MatchRequest" in schema["components"]["schemas"]
    json.dumps(schema, allow_nan=False)
