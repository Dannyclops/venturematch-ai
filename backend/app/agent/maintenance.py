"""Inspect or remove ONE existing session. Never creates sessions or submits input."""

import argparse
import json
import os
import re
import time
from pathlib import Path

from dotenv import load_dotenv
from openai import APIStatusError, OpenAI

from .diagnostics import provider_code, safe_exception


SESSION_STATUSES = {"idle", "in_progress", "requires_action", "failed"}
TURN_STATUSES = {"queued", "in_progress", "waiting", "completed", "failed", "cancelled"}
ACTIVE_STATUSES = {"queued", "in_progress", "waiting"}


def validate_session_id(value: str) -> str:
    if not isinstance(value, str) or not re.fullmatch(r"sess_[A-Za-z0-9_-]{1,120}", value):
        raise ValueError("Expected the existing sess_ identifier, not an API key or URL.")
    return value


def _enum(value, allowed):
    return value if isinstance(value, str) and value in allowed else "unknown"


def _turn_summary(turn) -> dict:
    turn_id = getattr(turn, "id", None)
    return {
        "id": turn_id if isinstance(turn_id, str) and re.fullmatch(r"turn_[A-Za-z0-9_-]{1,120}", turn_id) else None,
        "status": _enum(getattr(turn, "status", None), TURN_STATUSES),
        "error_code": provider_code(getattr(getattr(turn, "error", None), "code", None)),
    }


def inspect_session(client, session_id: str) -> dict:
    """Read only metadata and one page of turn statuses; never retrieve message bodies."""
    validate_session_id(session_id)
    stage = "inspect_session"
    try:
        session = client.beta.agents.sessions.retrieve(session_id)
        if session.id != session_id:
            raise ValueError("Session identity mismatch.")
        stage = "list_turns"
        page = client.beta.agents.sessions.turns.list(session_id, limit=10, order="desc")
        return {
            "ok": True, "state": "found", "session_id": session_id,
            "session_status": _enum(session.status, SESSION_STATUSES),
            "environment_type": _enum(getattr(session.environment, "type", None),
                                      {"none", "openai_hosted", "self_hosted"}),
            "required_action_count": len(session.required_actions or []),
            "turns": [_turn_summary(turn) for turn in page.data],
            "more_turns_available": page.has_next_page(),
        }
    except APIStatusError as error:
        if error.status_code == 404 and stage == "inspect_session":
            return {"ok": True, "state": "not_found_or_not_visible", "session_id": session_id,
                    "notice": "No visible session at this ID. It may be removed, mistyped, or inaccessible."}
        return {"ok": False, "session_id": session_id, "diagnostics": safe_exception(error, stage)}
    except Exception as error:
        return {"ok": False, "session_id": session_id, "diagnostics": safe_exception(error, stage)}


def cleanup_session(client, session_id: str, *, pause=time.sleep) -> dict:
    """Inspect, optionally cancel, and delete the explicit disposable demo session."""
    before = inspect_session(client, session_id)
    report = {"ok": False, "before": before, "session_id": session_id,
              "cancellation_requested": False, "deletion_confirmed": False}
    if not before["ok"] or before.get("state") != "found":
        report["notice"] = "No cleanup performed; session identity/access could not be confirmed."
        return report
    sessions = client.beta.agents.sessions
    stage = "cancel_session"
    try:
        active = (before["session_status"] in {"in_progress", "requires_action"}
                  or any(turn["status"] in ACTIVE_STATUSES for turn in before["turns"]))
        if active:
            sessions.events.create(session_id, events=[{"type": "agent.session.input.cancel"}])
            report["cancellation_requested"] = True  # Acceptance is not proof the turn stopped.
        # Three attempts total; never retry authorization, network, or non-conflict failures.
        for attempt in range(3):
            stage = "delete_session"
            try:
                deleted = sessions.delete(session_id)
            except APIStatusError as error:
                if error.status_code != 409 or attempt == 2:
                    raise
                if not report["cancellation_requested"]:
                    stage = "cancel_session"
                    sessions.events.create(session_id, events=[{"type": "agent.session.input.cancel"}])
                    report["cancellation_requested"] = True
                pause(0.5)
                continue
            if deleted.id != session_id or deleted.deleted is not True:
                raise ValueError("Deletion confirmation did not match the requested session.")
            report.update(ok=True, deletion_confirmed=True,
                          notice="Session removed from the API; physical hosted cleanup may continue asynchronously.")
            return report
    except Exception as error:
        report["diagnostics"] = safe_exception(error, stage)
        report["notice"] = "Cleanup is not confirmed. Do not start another matching run yet."
    return report


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Inspect/clean up an existing demo session; no new model turn.")
    parser.add_argument("--session", help="Exact existing sess_ ID; prompts when omitted")
    action = parser.add_mutually_exclusive_group()
    action.add_argument("--inspect", action="store_true", help="Read-only metadata (default)")
    action.add_argument("--cleanup", action="store_true", help="Cancel/delete this disposable session and its saved history")
    args = parser.parse_args(argv)
    session_id = args.session or input("Paste the existing session_id from the failed run (not your API key): ").strip()
    try:
        validate_session_id(session_id)
    except ValueError:
        parser.error("Invalid session ID. Copy the complete sess_ value from your terminal.")
    load_dotenv(Path(__file__).resolve().parents[3] / ".env", override=False, interpolate=False)
    if not os.environ.get("OPENAI_API_KEY", "").strip():
        parser.error("OPENAI_API_KEY is missing from the configured environment or repo .env.")
    try:
        # Synchronous client avoids the restricted Windows asyncio startup issue.
        with OpenAI(api_key=os.environ["OPENAI_API_KEY"], base_url="https://api.openai.com/v1",
                    max_retries=0, timeout=10) as client:
            report = (cleanup_session if args.cleanup else inspect_session)(client, session_id)
    except Exception as error:
        report = {"ok": False, "diagnostics": safe_exception(error, "client_setup")}
    print(json.dumps(report, indent=2))
    if not report["ok"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
