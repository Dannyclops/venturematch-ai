"""Demo runner. Live API usage is opt-in with --live; credentials never go to stdout."""

import argparse
import asyncio
import json
import os
from pathlib import Path

from dotenv import load_dotenv
from openai import AsyncOpenAI

from app.models import MatchRequest
from app.tools import MatchingCatalog, MatchingTools
from .runtime import AgentFailure, AgentSettings, VentureMatchAgent, function_definitions


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="VentureMatch agent demo (live runs incur API usage).")
    query = parser.add_mutually_exclusive_group(required=True)
    query.add_argument("--business")
    query.add_argument("--investor")
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument("--definitions", action="store_true", help="Print API tool schemas; no API call")
    action.add_argument("--live", action="store_true", help="Authorize one billable agent run")
    parser.add_argument("--model", default=None)
    parser.add_argument("--environment", choices=["openai_hosted", "none"], default="openai_hosted")
    parser.add_argument("--timeout", type=float, default=120)
    parser.add_argument("--top-k", type=int, choices=range(1, 11), default=3)
    parser.add_argument("--core-only", action="store_true")
    parser.add_argument("--objective", default="Find compatible partners and highlight relevant evidence.")
    args = parser.parse_args(argv)
    catalog = MatchingCatalog.from_demo()
    founder = args.business is not None
    profile = next((item for item in (catalog.businesses if founder else catalog.investors)
                    if item.id == (args.business if founder else args.investor)), None)
    if profile is None:
        parser.error("Unknown demo profile ID.")
    try:
        request = MatchRequest(mode="founder" if founder else "investor", objective=args.objective,
                               business_profile=profile if founder else None,
                               investor_profile=None if founder else profile, top_k=args.top_k,
                               constraints={"include_exploration_matches": not args.core_only})
    except ValueError:
        parser.error("Invalid objective or request options.")
    if args.definitions:
        print(json.dumps(function_definitions(MatchingTools(request, catalog)), indent=2))
        return
    # Explicit repo file only: do not search parent folders or interpolate arbitrary variables.
    load_dotenv(Path(__file__).resolve().parents[3] / ".env", override=False, interpolate=False)
    if not os.environ.get("OPENAI_API_KEY", "").strip():
        parser.error("OPENAI_API_KEY is missing. Configure the repo's ignored .env file.")
    try:
        settings = AgentSettings(model=args.model or os.environ.get("OPENAI_MODEL", "gpt-6-astra"),
                                 environment=args.environment, timeout_seconds=args.timeout)
    except ValueError:
        parser.error("Invalid agent settings; timeout must be between 1 and 300 seconds.")

    async def execute():
        async with AsyncOpenAI(api_key=os.environ["OPENAI_API_KEY"],
                               base_url="https://api.openai.com/v1", max_retries=0,
                               timeout=min(settings.timeout_seconds, 30)) as client:
            return await VentureMatchAgent(request, catalog, settings).run(client)

    try:
        result = asyncio.run(execute())
    except AgentFailure as error:
        print(json.dumps({"ok": False, "error": error.as_dict()}, indent=2))
        raise SystemExit(1) from None
    except KeyboardInterrupt:
        print(json.dumps({"ok": False, "error": {"code": "interrupted",
              "message": "Run interrupted; verify remote session cleanup before retrying."}}))
        raise SystemExit(130) from None
    print(json.dumps({"ok": True, "data": result.model_dump(mode="json")}, indent=2))


if __name__ == "__main__":
    main()
