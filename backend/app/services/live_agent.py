"""Explicitly enabled, request-scoped OpenAI execution for the local demo API."""

import asyncio
import os
from pathlib import Path
from time import monotonic
from typing import Literal

from dotenv import load_dotenv
from openai import AsyncOpenAI
from pydantic import Field

from app.agent.diagnostics import safe_exception
from app.agent.runtime import AgentFailure, AgentRun, AgentSettings, VentureMatchAgent
from app.models import MatchRequest
from app.tools import MatchingCatalog


class LiveMatchResponse(AgentRun):
    execution_mode: Literal["ai_assisted"] = "ai_assisted"
    elapsed_seconds: float = Field(ge=0)


class LiveAgentService:
    """One active paid run per service/process; never queue or automatically retry."""

    def __init__(self, api_key: str, settings: AgentSettings | None = None):
        if not api_key.strip():
            raise ValueError("OPENAI_API_KEY is required to enable live matching.")
        self._api_key = api_key
        self._settings = (settings or AgentSettings()).model_copy(deep=True)
        self._lock = asyncio.Lock()

    async def match(self, request: MatchRequest, catalog: MatchingCatalog) -> LiveMatchResponse:
        if self._lock.locked():
            raise AgentFailure("agent_busy", "A live run is already active; no new run was started.")
        async with self._lock:
            started = monotonic()
            agent = VentureMatchAgent(request, catalog, self._settings)
            try:
                async with AsyncOpenAI(
                    api_key=self._api_key, base_url="https://api.openai.com/v1",
                    max_retries=0, timeout=min(self._settings.timeout_seconds, 30),
                ) as client:
                    result = await agent.run(client)
            except AgentFailure:
                raise
            except Exception as error:
                failure = AgentFailure("client_error", "Client setup or lifecycle failed.")
                failure.session_id, failure.turn_id = agent.session_id, agent.turn_id
                failure.diagnostics = safe_exception(error, "client_setup")
                raise failure from None
            return LiveMatchResponse(
                **result.model_dump(), elapsed_seconds=round(monotonic() - started, 3),
            )


def live_service_from_environment() -> LiveAgentService | None:
    # Activation must come from the launching process, not merely from finding a key.
    # The default engine-only server never reads secrets from .env.
    if os.environ.get("VENTUREMATCH_ENABLE_LIVE_AGENT") != "1":
        return None
    load_dotenv(Path(__file__).resolve().parents[3] / ".env", override=False, interpolate=False)
    settings = AgentSettings(model=os.environ.get("OPENAI_MODEL", "gpt-6-astra"))
    return LiveAgentService(os.environ.get("OPENAI_API_KEY", ""), settings)
