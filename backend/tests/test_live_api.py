"""Local HTTP-to-agent integration using scripted providers; no paid requests."""

import asyncio
from contextlib import asynccontextmanager
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from app.agent import AgentFailure, VentureMatchAgent
from app.main import create_app
from app.models import MatchRequest
from app.services.live_agent import LiveAgentService, LiveMatchResponse, live_service_from_environment
from app.tools import MatchingCatalog, MatchingTools
from test_agent import client_for, events_for
from test_api import payload


CONFIRM = {"X-VentureMatch-Live": "true"}
SECRET = "private-fake-key-never-return"


def scripted_client(monkeypatch, request, catalog):
    reference = VentureMatchAgent(request, catalog)
    client, sessions = client_for(events_for(reference))
    options = []

    @asynccontextmanager
    async def factory(**kwargs):
        options.append(kwargs)
        yield client

    monkeypatch.setattr("app.services.live_agent.AsyncOpenAI", factory)
    return sessions, options


@pytest.mark.parametrize("mode", ["founder", "investor"])
def test_live_endpoint_executes_real_runtime_with_scripted_provider(monkeypatch, mode):
    catalog = MatchingCatalog.from_demo()
    body = payload(catalog, mode)
    request = MatchRequest.model_validate(body)
    sessions, options = scripted_client(monkeypatch, request, catalog)
    service = LiveAgentService(SECRET)
    with TestClient(create_app(catalog, live_agent=service)) as client:
        assert client.get("/api/health").json()["live_agent_enabled"] is True
        assert client.get("/api/metadata").json()["live_agent_enabled"] is True
        response = client.post("/api/agent/match", json=body, headers=CONFIRM)
        assert response.status_code == 200, response.text
        result = LiveMatchResponse.model_validate(response.json())
        expected = MatchingTools(request, catalog).invoke("score_matches", {})["data"]["matches"]
        assert result.response.model_dump(mode="json")["matches"] == expected
        assert result.execution_mode == "ai_assisted"
        assert result.elapsed_seconds >= 0
        assert result.highlights and result.usage == {"total_tokens": 123}
        assert result.cleanup_warnings == []
        assert len(sessions.submitted) == 2
        assert sessions.deleted == ["sess_test"]
        assert len(options) == 1
        assert options[0]["max_retries"] == 0
        assert options[0]["base_url"] == "https://api.openai.com/v1"
        assert options[0]["timeout"] == 30
        assert SECRET not in response.text
        # Engine-only matching on the same enabled server never opens a provider client.
        assert client.post("/api/matches", json=body).json()["execution_mode"] == "engine_only"
        assert len(options) == 1


def test_live_endpoint_requires_header_and_valid_request_before_client_creation(monkeypatch):
    catalog = MatchingCatalog.from_demo()
    def forbidden(**kwargs):
        pytest.fail("Invalid/unconfirmed requests must not construct a client")
    monkeypatch.setattr("app.services.live_agent.AsyncOpenAI", forbidden)
    with TestClient(create_app(catalog, live_agent=LiveAgentService(SECRET))) as client:
        response = client.post("/api/agent/match", json=payload(catalog))
        assert response.status_code == 403
        assert response.json()["error"]["code"] == "live_confirmation_required"
        for change in ({"top_k": 11}, {"model": "client-selected"}, {"api_key": SECRET},
                       {"environment": "none"}, {"timeout_seconds": 999}):
            invalid = client.post("/api/agent/match", json={**payload(catalog), **change}, headers=CONFIRM)
            assert invalid.status_code == 422
            assert SECRET not in invalid.text


@pytest.mark.parametrize("code,status", [
    ("timeout", 504), ("usage_limit", 503), ("billing_or_quota_error", 503),
    ("authentication_error", 503), ("rate_limit", 429), ("connection_error", 502),
    ("invalid_ranking", 502), ("agent_busy", 409),
])
def test_live_failures_are_explicit_and_preserve_recovery_ids(code, status):
    async def fail(*args):
        error = AgentFailure(code, SECRET)
        error.session_id, error.turn_id = "sess_recovery", "turn_recovery"
        error.cleanup_warnings = ["Remote cancellation was not confirmed."]
        raise error
    service = LiveAgentService(SECRET)
    service.match = fail
    catalog = MatchingCatalog.from_demo()
    with TestClient(create_app(catalog, live_agent=service)) as client:
        response = client.post("/api/agent/match", json=payload(catalog), headers=CONFIRM)
        assert response.status_code == status
        body = response.json()
        assert body["error"]["code"] == code
        assert body["error"]["session_id"] == "sess_recovery"
        assert body["error"]["turn_id"] == "turn_recovery"
        assert body["error"]["cleanup_warnings"]
        assert "response" not in body  # No silent engine-only fallback.
        assert SECRET not in response.text


def test_live_client_construction_failure_is_safe_and_does_not_lock_service(monkeypatch):
    attempts = []
    def broken(**kwargs):
        attempts.append(1)
        raise ImportError(SECRET)
    monkeypatch.setattr("app.services.live_agent.AsyncOpenAI", broken)
    catalog = MatchingCatalog.from_demo()
    with TestClient(create_app(catalog, live_agent=LiveAgentService(SECRET))) as client:
        for _ in range(2):
            response = client.post("/api/agent/match", json=payload(catalog), headers=CONFIRM)
            assert response.status_code == 503
            assert response.json()["error"]["code"] == "client_error"
            assert SECRET not in response.text
        assert len(attempts) == 2  # Exactly one client attempt per explicit request.


@pytest.mark.parametrize("provider_code,status", [("usage_limit_exceeded", 503), ("rate_limit_exceeded", 429)])
def test_remote_turn_error_codes_are_classified(provider_code, status):
    async def fail(*args):
        error = AgentFailure("remote_failure", SECRET)
        error.diagnostics = {"provider_code": provider_code, "category": "agent_error"}
        raise error
    service = LiveAgentService(SECRET)
    service.match = fail
    catalog = MatchingCatalog.from_demo()
    with TestClient(create_app(catalog, live_agent=service)) as client:
        response = client.post("/api/agent/match", json=payload(catalog), headers=CONFIRM)
        assert response.status_code == status
        assert response.json()["error"]["diagnostics"]["provider_code"] == provider_code
        assert SECRET not in response.text


def test_live_concurrency_rejects_second_run_and_releases_on_cancellation(monkeypatch):
    catalog = MatchingCatalog.from_demo()
    request = MatchRequest.model_validate(payload(catalog))
    attempts = []

    @asynccontextmanager
    async def factory(**kwargs):
        attempts.append(1)
        yield SimpleNamespace()

    monkeypatch.setattr("app.services.live_agent.AsyncOpenAI", factory)

    async def scenario():
        entered = asyncio.Event()
        stopped = []
        async def waiting(self, client):
            entered.set()
            try:
                await asyncio.Event().wait()
            finally:
                stopped.append(True)
        monkeypatch.setattr(VentureMatchAgent, "run", waiting)
        service = LiveAgentService(SECRET)
        first = asyncio.create_task(service.match(request, catalog))
        await entered.wait()
        with pytest.raises(AgentFailure, match="already active"):
            await service.match(request, catalog)
        assert len(attempts) == 1
        first.cancel()
        with pytest.raises(asyncio.CancelledError):
            await first
        assert stopped == [True]
        assert not service._lock.locked()

    asyncio.run(scenario())


def test_environment_activation_is_explicit_and_secrets_never_loaded_when_disabled(monkeypatch):
    monkeypatch.delenv("VENTUREMATCH_ENABLE_LIVE_AGENT", raising=False)
    monkeypatch.setenv("OPENAI_API_KEY", SECRET)
    def forbidden(*args, **kwargs):
        pytest.fail("Disabled service must not load .env")
    monkeypatch.setattr("app.services.live_agent.load_dotenv", forbidden)
    assert live_service_from_environment() is None
    monkeypatch.setenv("VENTUREMATCH_ENABLE_LIVE_AGENT", "true")
    assert live_service_from_environment() is None  # Only literal 1 enables the endpoint.


def test_enabled_environment_requires_key_and_preserves_host_model(monkeypatch):
    monkeypatch.setattr("app.services.live_agent.load_dotenv", lambda *args, **kwargs: None)
    monkeypatch.setenv("VENTUREMATCH_ENABLE_LIVE_AGENT", "1")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    with pytest.raises(ValueError, match="required"):
        live_service_from_environment()
    monkeypatch.setenv("OPENAI_API_KEY", SECRET)
    monkeypatch.setenv("OPENAI_MODEL", "host-configured-model")
    service = live_service_from_environment()
    assert service._settings.model == "host-configured-model"
    assert SECRET not in repr(service)


def test_live_openapi_and_cors_header():
    with TestClient(create_app(live_agent=LiveAgentService(SECRET))) as client:
        schema = client.get("/openapi.json").json()
        assert "/api/agent/match" in schema["paths"]
        response_schema = schema["components"]["schemas"]["LiveMatchResponse"]
        assert response_schema["properties"]["execution_mode"]["const"] == "ai_assisted"
        preflight = client.options("/api/agent/match", headers={
            "Origin": "http://localhost:3000", "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type,x-venturematch-live",
        })
        assert preflight.status_code == 200


def test_nested_turn_usage_is_retained_without_extra_provider_requests():
    catalog = MatchingCatalog.from_demo()
    agent = VentureMatchAgent(MatchRequest.model_validate(payload(catalog)), catalog)
    events = events_for(agent)
    events[-1]["turn"]["usage"] = events[-1].pop("usage")
    client, sessions = client_for(events)
    result = asyncio.run(agent.run(client))
    assert result.usage == {"total_tokens": 123}
    assert sessions.deleted == ["sess_test"]
