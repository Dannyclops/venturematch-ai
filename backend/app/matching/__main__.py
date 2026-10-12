"""Run offline demo rankings: python -m app.matching --business <id>."""

import argparse
import json
from pathlib import Path

from app.models import BusinessProfile, InvestorProfile, PortfolioCompany
from app.services import CurrencyNormalizer
from . import CompatibilityEngine, EligibilityEngine


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Rank fictional VentureMatch demo profiles.")
    query = parser.add_mutually_exclusive_group(required=True)
    query.add_argument("--business", help="Business ID for founder-to-investor discovery")
    query.add_argument("--investor", help="Investor ID for investor-to-business discovery")
    parser.add_argument("--top-k", type=int, choices=range(1, 11), default=5)
    parser.add_argument("--core-only", action="store_true")
    args = parser.parse_args(argv)
    data = Path(__file__).resolve().parents[3] / "data"
    businesses = [BusinessProfile.model_validate(item) for item in
                  json.loads((data / "businesses.json").read_text(encoding="utf-8"))]
    investors = [InvestorProfile.model_validate(item) for item in
                 json.loads((data / "investors.json").read_text(encoding="utf-8"))]
    portfolios = [PortfolioCompany.model_validate(item) for item in
                  json.loads((data / "portfolios.json").read_text(encoding="utf-8"))]
    engine = CompatibilityEngine(
        EligibilityEngine(CurrencyNormalizer.from_json_file(data / "fx_rates.demo.json")),
        portfolios,
    )
    options = {"top_k": args.top_k, "include_exploration_matches": not args.core_only}
    if args.business:
        target = next((item for item in businesses if item.id == args.business), None)
        if target is None:
            parser.error(f"Unknown business ID: {args.business}")
        results = engine.rank_investors(target, investors, **options)
    else:
        target = next((item for item in investors if item.id == args.investor), None)
        if target is None:
            parser.error(f"Unknown investor ID: {args.investor}")
        results = engine.rank_businesses(target, businesses, **options)
    print(json.dumps({
        "notice": "Fictional profiles and synthetic FX rates. Heuristic compatibility, "
                  "not investment advice or a funding probability.",
        "matches": [result.model_dump(mode="json") for result in results],
    }, indent=2))


if __name__ == "__main__":
    main()
