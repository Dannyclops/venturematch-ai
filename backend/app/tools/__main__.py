"""Exercise local tool dispatch without an LLM: python -m app.tools --help."""

import argparse
import json

from app.models import MatchRequest
from . import MatchingCatalog, MatchingTools
from .matching import BY_NAME


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="VentureMatch local agent-tool harness.")
    query = parser.add_mutually_exclusive_group(required=True)
    query.add_argument("--business")
    query.add_argument("--investor")
    parser.add_argument("--definitions", action="store_true")
    parser.add_argument("--tool", choices=list(BY_NAME), default="score_matches")
    parser.add_argument("--arguments", default="{}", help="JSON arguments for the selected tool")
    parser.add_argument("--core-only", action="store_true")
    parser.add_argument("--top-k", type=int, choices=range(1, 11), default=5)
    args = parser.parse_args(argv)
    catalog = MatchingCatalog.from_demo()
    founder = args.business is not None
    records = catalog.businesses if founder else catalog.investors
    entity_id = args.business if founder else args.investor
    profile = next((record for record in records if record.id == entity_id), None)
    if profile is None:
        parser.error("Unknown query profile ID.")
    request = MatchRequest(
        mode="founder" if founder else "investor",
        objective="Find compatible partners for the supplied profile.",
        business_profile=profile if founder else None,
        investor_profile=profile if not founder else None,
        top_k=args.top_k,
        constraints={"include_exploration_matches": not args.core_only},
    )
    toolbox = MatchingTools(request, catalog)
    output = toolbox.definitions() if args.definitions else toolbox.invoke(args.tool, args.arguments)
    print(json.dumps(output, indent=2))
    if not args.definitions and not output["ok"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
