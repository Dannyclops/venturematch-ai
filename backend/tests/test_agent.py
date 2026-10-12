"""No credentials or network: real matching logic with a scripted provider stream."""

import asyncio
import json
from copy import deepcopy
from types import SimpleNamespace

import pytest

from app.agent import AgentFailure, AgentSettings, VentureMatchAgent
from app.agent.runtime import function_definitions, strict_schema
from app.tools import MatchingTools
from test_tools import catalog, request


def action(name, arguments=None, call_id=None, turn_id="turn_test"):
    return {"type": "function_call", "turn_id": turn_id, "call_id": call_id or name,
            "name": name, "arguments": arguments or {}}


def ready_agent(**updates):
    agent = VentureMatchAgent(request(**updates), catalog())
    agent.turn_id = "turn_test"
    agent.dispatch(action("analyze_profile"))
    agent.dispatch(action("score_matches", {"candidate_ids": None}))
    return agent


def draft_for(agent):
    matches = agent.toolbox.invoke("score_matches", {})["data"]["matches"]
    return {"recommendations": [{"candidate_id": match["candidate_entity_id"],
                                "focus_factors": [match["evidence"][0]["factor"]]}
                               for match in matches]}


@pytest.mark.parametrize("mode", ["founder", "investor"])
def test_finalize_keeps_engine_results_and_quotes_evidence(mode):
    agent = ready_agent(mode=mode)
    response, highlights = agent.finalize(json.dumps(draft_for(agent)))
    expected = agent.toolbox.invoke("score_matches", {})["data"]["matches"]
    assert [match.model_dump(mode="json") for match in response.matches] == expected
    factor = expected[0]["evidence"][0]["factor"]
    assert highlights[0].statements == [item["statement"] for item in expected[0]["evidence"]
                                      if item["factor"] == factor]
    assert response.normalized_objective == agent.request.objective


def test_tool_schema_conversion_is_non_mutating_and_mode_specific():
    toolbox = MatchingTools(request(), catalog())
    original = toolbox.definitions()
    schemas = function_definitions(toolbox)
    assert original == toolbox.definitions()
    assert len(schemas) == 5
    assert "search_businesses" not in {item["name"] for item in schemas}
    for item in schemas:
        assert set(item) == {"type", "name", "description", "parameters"}
        assert item["parameters"]["additionalProperties"] is False
        assert item["parameters"]["required"] == list(item["parameters"]["properties"])
        assert '"default"' not in json.dumps(item)
    assert strict_schema({"type": "object", "properties": {}})["required"] == []


@pytest.mark.parametrize("mutation,code", [
    (lambda d: d["recommendations"][0].update(candidate_id="invented_id"), "invalid_ranking"),
    (lambda d: d["recommendations"].append(deepcopy(d["recommendations"][0])), "invalid_ranking"),
    (lambda d: d.update(recommendations=[]), "invalid_ranking"),
    (lambda d: d["recommendations"][0].update(overall_score=100), "invalid_output"),
    (lambda d: d["recommendations"][0].update(focus_factors=["invented"]), "invalid_output"),
    (lambda d: d["recommendations"][0].update(focus_factors=["industry_alignment"] * 2), "invalid_evidence"),
])
def test_fabricated_or_incomplete_outputs_are_rejected(mutation, code):
    agent = ready_agent()
    draft = draft_for(agent)
    mutation(draft)
    with pytest.raises(AgentFailure) as exc:
        agent.finalize(json.dumps(draft))
    assert exc.value.code == code


def test_missing_tools_and_empty_results():
    agent = VentureMatchAgent(request(), catalog())
    with pytest.raises(AgentFailure, match="profile analysis"):
        agent.finalize('{"recommendations": []}')
    agent = ready_agent(constraints={"excluded_entity_ids": [catalog().investors[0].id]})
    response, highlights = agent.finalize('{"recommendations": []}')
    assert response.matches == highlights == []


def test_explicit_subset_scoring_does_not_satisfy_full_catalog_requirement():
    agent = ready_agent()
    agent._all_scored = False
    candidate = catalog().investors[0].id
    agent.dispatch(action("score_matches", {"candidate_ids": [candidate]}, call_id="subset"))
    with pytest.raises(AgentFailure) as exc:
        agent.finalize(json.dumps(draft_for(agent)))
    assert exc.value.code == "missing_tools"


def test_repeated_calls_cached_changed_calls_rejected_and_limits_enforced():
    agent = ready_agent()
    first = agent.dispatch(action("analyze_profile"))
    assert len(agent.activity) == 2
    first["output"] = "mutated"
    assert agent.dispatch(action("analyze_profile"))["output"] != "mutated"
    with pytest.raises(AgentFailure) as exc:
        agent.dispatch(action("analyze_profile", {"bad": 1}))
    assert exc.value.code == "changed_call"
    agent.settings.max_tool_calls = 3
    agent.dispatch(action("analyze_profile", call_id="third"))
    with pytest.raises(AgentFailure) as exc:
        agent.dispatch(action("analyze_profile", call_id="fourth"))
    assert exc.value.code == "tool_limit"


@pytest.mark.parametrize("call,code", [
    (action("search_businesses"), "unknown_tool"),
    (action("__init__"), "unknown_tool"),
    (action("analyze_profile", turn_id="another_turn"), "invalid_call"),
    ({"type": "environment_connection"}, "unsupported_action"),
])
def test_call_allowlist_and_turn_binding(call, code):
    with pytest.raises(AgentFailure) as exc:
        ready_agent().dispatch(call)
    assert exc.value.code == code


def test_invalid_tool_arguments_return_safe_errors():
    agent = ready_agent()
    output = agent.dispatch(action("search_investors", {"secret": "do-not-echo"}))
    assert output["success"] is False
    assert "do-not-echo" not in json.dumps(output)


class Event:
    def __init__(self, data):
        self.data = data

    def model_dump(self, **kwargs):
        return deepcopy(self.data)


class Stream:
    def __init__(self, events):
        self.events = iter(events)
        self.closed = False

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        self.closed = True

    def __aiter__(self):
        return self

    async def __anext__(self):
        try:
            return Event(next(self.events))
        except StopIteration:
            raise StopAsyncIteration


class Sessions:
    def __init__(self, events):
        self.stream = Stream(events)
        self.events = SimpleNamespace(create=self.submit)
        self.turns = SimpleNamespace(retrieve=self.retrieve_turn)
        self.items = SimpleNamespace(list=lambda *a, **k: Stream([]))
        self.submitted = []
        self.deleted = []
        self.payload = None

    async def create(self, **kwargs):
        self.payload = kwargs
        return self.stream

    async def submit(self, session_id, *, events):
        self.submitted.extend(events)

    async def delete(self, session_id):
        self.deleted.append(session_id)

    async def retrieve_turn(self, *args, **kwargs):
        return SimpleNamespace(status="in_progress")


def client_for(events):
    sessions = Sessions(events)
    return SimpleNamespace(beta=SimpleNamespace(agents=SimpleNamespace(sessions=sessions))), sessions


def events_for(agent):
    return [
        {"type": "agent.session.created", "session": {"id": "sess_test"}},
        {"type": "agent.session.turn.created", "session_id": "sess_test", "turn_id": "turn_test"},
        {"type": "agent.session.requires_action", "session": {"id": "sess_test", "required_actions": [
            action("analyze_profile"), action("score_matches", {"candidate_ids": None})]}},
        {"type": "agent.session.turn.item.done", "session_id": "sess_test", "turn_id": "turn_test",
         "item": {"type": "message", "role": "assistant", "phase": "final_answer", "status": "completed",
                  "content": [{"type": "output_text", "text": json.dumps(draft_for(agent))}]}},
        {"type": "agent.session.turn.completed", "session_id": "sess_test", "turn_id": "turn_test",
         "turn": {"status": "completed"}, "usage": {"total_tokens": 123}},
    ]


@pytest.mark.parametrize("mode", ["founder", "investor"])
def test_complete_stream_dispatch_and_cleanup(mode):
    agent = VentureMatchAgent(request(mode=mode), catalog())
    client, sessions = client_for(events_for(agent))
    output = asyncio.run(agent.run(client))
    assert output.response.matches and output.highlights
    assert output.usage == {"total_tokens": 123}
    assert sessions.deleted == ["sess_test"] and sessions.stream.closed
    assert len(sessions.submitted) == 2
    assert sessions.payload["environment"] == {"type": "openai_hosted", "container_size": "small",
                                               "network": {"access": "disabled"}}
    assert "OPENAI_API_KEY" not in json.dumps(sessions.payload)
    with pytest.raises(AgentFailure) as exc:
        asyncio.run(agent.run(client))
    assert exc.value.code == "already_used"


@pytest.mark.parametrize("ending,code", [
    ("agent.session.turn.failed", "remote_failure"),
    ("agent.session.turn.cancelled", "remote_failure"),
    ("agent.session.idle", "incomplete_turn"),
])
def test_failure_and_idle_are_not_success(ending, code):
    agent = VentureMatchAgent(request(), catalog())
    events = events_for(agent)[:2] + [{"type": ending, "session_id": "sess_test", "turn_id": "turn_test"}]
    client, sessions = client_for(events)
    with pytest.raises(AgentFailure) as exc:
        asyncio.run(agent.run(client))
    assert exc.value.code == code
    assert exc.value.session_id == "sess_test"
    assert sessions.submitted[-1]["type"] == "agent.session.input.cancel"
    assert sessions.deleted == ["sess_test"]


def test_timeout_is_bounded_and_does_not_retry_creation():
    agent = VentureMatchAgent(request(), catalog(), AgentSettings(timeout_seconds=1))
    client, sessions = client_for([])

    async def slow_create(**kwargs):
        await asyncio.sleep(2)

    sessions.create = slow_create
    with pytest.raises(AgentFailure) as exc:
        asyncio.run(agent.run(client))
    assert exc.value.code == "timeout"
    assert "No session ID" in exc.value.cleanup_warnings[0]


def test_cli_definitions_need_no_credentials(monkeypatch, capsys):
    from app.agent.__main__ import main
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    main(["--business", "business_solargrid_africa", "--definitions"])
    assert len(json.loads(capsys.readouterr().out)) == 5
