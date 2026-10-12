"""Recovery and privacy tests, including the real SDK with an in-memory transport."""

import asyncio
import json
from types import SimpleNamespace as NS

import httpx2 as httpx
import pytest
from openai import APIError, APIStatusError, OpenAI

from app.agent import AgentFailure, VentureMatchAgent
from app.agent.diagnostics import error_category, safe_exception
from app.agent.maintenance import cleanup_session, inspect_session, validate_session_id
from test_agent import client_for
from test_tools import catalog, request


SECRET = "sk-test-private-value-never-echo"


def test_async_cli_client_setup_failure_is_redacted(monkeypatch, capsys):
    from app.agent import __main__ as cli

    monkeypatch.setenv("OPENAI_API_KEY", SECRET)
    monkeypatch.setattr(cli, "load_dotenv", lambda *args, **kwargs: None)

    def fail_client(**kwargs):
        raise ImportError(SECRET)

    monkeypatch.setattr(cli, "AsyncOpenAI", fail_client)
    with pytest.raises(SystemExit) as exc:
        cli.main(["--business", "business_solargrid_africa", "--live", "--top-k", "1"])
    assert exc.value.code == 1
    captured = capsys.readouterr()
    result = json.loads(captured.out)
    assert result["error"]["code"] == "client_error"
    assert result["error"]["diagnostics"]["exception_type"] == "ImportError"
    assert result["error"]["diagnostics"]["stage"] == "client_setup"
    assert SECRET not in captured.out + captured.err


def api_error(code, status=None):
    req = httpx.Request("POST", "https://api.openai.com/v1/agents/sessions",
                        headers={"Authorization": "Bearer " + SECRET})
    body = {"code": code, "message": SECRET, "param": SECRET}
    if status is None:
        return APIError(SECRET, req, body=body)
    return APIStatusError(SECRET, response=httpx.Response(status, request=req), body=body)


@pytest.mark.parametrize("code,status,category", [
    ("insufficient_quota", 429, "billing_or_quota_error"),
    ("credit_balance_exhausted", None, "billing_or_quota_error"),
    ("billing_not_active", None, "billing_or_quota_error"),
    ("rate_limit_exceeded", 429, "rate_limit"),
    ("organization_spend_limit_exceeded", None, "usage_limit"),
    ("model_not_found", None, "access_or_resource_error"),
    ("invalid_api_key", 401, "authentication_error"),
    (None, 403, "access_denied"),
    (None, 429, "rate_or_quota_limit"),
    (SECRET, 400, "provider_error"),
])
def test_safe_codes_distinguish_stream_errors_billing_rate_and_access(code, status, category):
    error = api_error(code, status)
    result = safe_exception(error, "read_stream")
    assert result["category"] == error_category(error) == category
    assert SECRET not in json.dumps(result)
    assert result.get("provider_code") == (code if code and code != SECRET else None)


def test_safe_exception_does_not_echo_exception_text_or_unknown_metadata():
    error = type(SECRET, (Exception,), {})(SECRET)
    result = safe_exception(error, SECRET)
    assert result == {"stage": "unknown", "exception_type": "UnexpectedError", "category": "agent_error"}


def test_real_sdk_stream_error_uses_general_apierror_not_apistatuserror():
    """Regression: the old runtime hid this legitimate provider error as agent_error."""
    payload = 'event: error\ndata: ' + json.dumps({"error": {
        "code": "model_not_found", "message": SECRET, "type": "invalid_request_error"}}) + '\n\n'
    sent = []

    def respond(req):
        sent.append(req)
        return httpx.Response(200, headers={"content-type": "text/event-stream"}, content=payload)

    with OpenAI(api_key="local-test-only", http_client=httpx.Client(transport=httpx.MockTransport(respond)),
                max_retries=0) as client:
        with client.beta.agents.sessions.create(agent={"model": "test-model"}, environment={"type": "none"},
                                                input="Local transport test", stream=True) as stream:
            with pytest.raises(APIError) as exc:
                list(stream)
    assert not isinstance(exc.value, APIStatusError)
    assert len(sent) == 1
    assert safe_exception(exc.value, "read_stream")["provider_code"] == "model_not_found"
    assert SECRET not in json.dumps(safe_exception(exc.value, "read_stream"))


@pytest.mark.parametrize("value", [SECRET, "https://example.com", "", "sess_id/other", "sess_id\n", "sess_" + "x" * 121])
def test_session_input_is_confined_to_one_explicit_id(value):
    with pytest.raises(ValueError):
        validate_session_id(value)


class RecoverySessions:
    def __init__(self, status="requires_action", turn_status="failed", code="model_not_found"):
        self.events = NS(create=self.submit)
        self.turns = NS(list=self.list_turns)
        self.status, self.turn_status, self.code = status, turn_status, code
        self.calls = []
        self.deletions = []
        self.conflicts = 0
        self.delete_error = None
        self.retrieve_error = None

    def retrieve(self, session_id):
        self.calls.append(("retrieve", session_id))
        if self.retrieve_error:
            raise self.retrieve_error
        return NS(id=session_id, status=self.status, environment=NS(type="openai_hosted", env={"key": SECRET}),
                  required_actions=[{"arguments": {"secret": SECRET}}], error=SECRET)

    def list_turns(self, session_id, **kwargs):
        self.calls.append(("list_turns", session_id))
        assert kwargs == {"limit": 10, "order": "desc"}
        return NS(data=[NS(id="turn_test", status=self.turn_status, error=NS(code=self.code, message=SECRET))],
                  has_next_page=lambda: False)

    def submit(self, session_id, *, events):
        assert events == [{"type": "agent.session.input.cancel"}]
        self.calls.append(("cancel", session_id))

    def delete(self, session_id):
        self.calls.append(("delete", session_id))
        if self.delete_error:
            raise self.delete_error
        if self.conflicts:
            self.conflicts -= 1
            raise api_error(None, 409)
        self.deletions.append(session_id)
        return NS(id=session_id, deleted=True)


def recovery_client(**kwargs):
    sessions = RecoverySessions(**kwargs)
    return NS(beta=NS(agents=NS(sessions=sessions))), sessions


def test_inspection_is_read_only_and_redacts_provider_payloads():
    client, sessions = recovery_client()
    report = inspect_session(client, "sess_test")
    assert report["ok"] and report["turns"][0]["error_code"] == "model_not_found"
    assert report["required_action_count"] == 1
    assert SECRET not in json.dumps(report)
    assert sessions.calls == [("retrieve", "sess_test"), ("list_turns", "sess_test")]


def test_cleanup_inspects_then_cancels_and_deletes_only_requested_session():
    client, sessions = recovery_client()
    report = cleanup_session(client, "sess_test")
    assert report["ok"] and report["deletion_confirmed"] and report["cancellation_requested"]
    assert report["before"]["turns"][0]["error_code"] == "model_not_found"
    assert sessions.calls == [("retrieve", "sess_test"), ("list_turns", "sess_test"),
                              ("cancel", "sess_test"), ("delete", "sess_test")]
    assert SECRET not in json.dumps(report)


def test_terminal_session_cleanup_does_not_submit_cancel():
    client, sessions = recovery_client(status="idle", turn_status="completed")
    assert cleanup_session(client, "sess_test")["deletion_confirmed"]
    assert ("cancel", "sess_test") not in sessions.calls


def test_delete_conflicts_have_bounded_retries():
    client, sessions = recovery_client(status="idle")
    sessions.conflicts = 2
    waits = []
    assert cleanup_session(client, "sess_test", pause=waits.append)["deletion_confirmed"]
    assert waits == [0.5, 0.5]
    assert sessions.calls.count(("cancel", "sess_test")) == 1
    assert sessions.calls.count(("delete", "sess_test")) == 3


def test_unresolved_cleanup_does_not_claim_success_or_retry_forever():
    client, sessions = recovery_client()
    sessions.conflicts = 9
    report = cleanup_session(client, "sess_test", pause=lambda _: None)
    assert not report["ok"] and not report["deletion_confirmed"]
    assert report["diagnostics"]["http_status"] == 409
    assert sessions.calls.count(("delete", "sess_test")) == 3


@pytest.mark.parametrize("status", [401, 403, 404, 429, 500])
def test_inspection_failure_prevents_cleanup(status):
    client, sessions = recovery_client()
    sessions.retrieve_error = api_error(None, status)
    report = cleanup_session(client, "sess_test")
    assert not report["ok"] and not report["deletion_confirmed"]
    assert sessions.calls == [("retrieve", "sess_test")]
    assert SECRET not in json.dumps(report)


def test_cleanup_permission_failure_stops_without_retry():
    client, sessions = recovery_client()
    sessions.delete_error = api_error(None, 403)
    report = cleanup_session(client, "sess_test")
    assert not report["ok"] and report["diagnostics"]["category"] == "access_denied"
    assert sessions.calls.count(("delete", "sess_test")) == 1


def test_unknown_remote_codes_and_statuses_are_not_echoed():
    client, _ = recovery_client(status=SECRET, turn_status=SECRET, code=SECRET)
    assert SECRET not in json.dumps(inspect_session(client, "sess_test"))


def test_cleanup_does_not_accept_wrong_deletion_confirmation():
    client, sessions = recovery_client()
    sessions.delete = lambda _: NS(id="sess_other", deleted=True)
    report = cleanup_session(client, "sess_test")
    assert not report["ok"] and not report["deletion_confirmed"]


def test_real_sdk_recovery_uses_only_read_cancel_delete_endpoints():
    seen = []

    def respond(req):
        path = req.url.path
        seen.append((req.method, path))
        if req.method == "GET" and path.endswith("/turns"):
            return httpx.Response(200, json={"data": [{"id": "turn_test", "status": "failed",
                                  "error": {"code": "model_not_found", "message": SECRET}}],
                                  "has_more": False, "last_id": "turn_test"})
        if req.method == "GET":
            return httpx.Response(200, json={"id": "sess_test", "status": "requires_action",
                                  "required_actions": [], "environment": {"type": "none"}})
        if req.method == "POST" and path.endswith("/events"):
            assert json.loads(req.content) == {"events": [{"type": "agent.session.input.cancel"}]}
            return httpx.Response(202)
        if req.method == "DELETE":
            return httpx.Response(200, json={"id": "sess_test", "deleted": True,
                                           "object": "agent.session.deleted"})
        pytest.fail("Unexpected endpoint; recovery must never start a turn or session")

    with OpenAI(api_key="local-test-only", http_client=httpx.Client(transport=httpx.MockTransport(respond)),
                max_retries=0) as client:
        report = cleanup_session(client, "sess_test")
    assert report["ok"] and report["deletion_confirmed"]
    assert report["before"]["turns"][0]["error_code"] == "model_not_found"
    assert len(seen) == 4
    assert SECRET not in json.dumps(report)


def test_async_stream_failure_preserves_safe_diagnostics():
    agent = VentureMatchAgent(request(), catalog())
    client, _ = client_for([])

    async def fail(_):
        agent._stage = "read_stream"
        raise api_error("credit_balance_exhausted")

    agent._execute = fail
    with pytest.raises(AgentFailure) as exc:
        asyncio.run(agent.run(client))
    assert exc.value.code == "billing_or_quota_error"
    assert exc.value.diagnostics["provider_code"] == "credit_balance_exhausted"
    assert SECRET not in json.dumps(exc.value.as_dict())
