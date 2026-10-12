"""Reproduce a few engine-only demo scenarios; never calls OpenAI."""

from __future__ import annotations

import json
from pathlib import Path
import sys


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from app.models import BusinessProfile, InvestorProfile, MatchRequest  # noqa: E402
from app.services.matching import match_profiles  # noqa: E402
from app.tools import MatchingCatalog  # noqa: E402


def main() -> None:
    catalog = MatchingCatalog.from_demo()
    business = next(item for item in catalog.businesses if item.id == "business_solargrid_africa")
    investor = next(item for item in catalog.investors if item.id == "investor_greenfront")
    turkish_business = next(item for item in catalog.businesses if item.id == "business_anatolia_pay")
    turkish_investor = next(item for item in catalog.investors if item.id == "investor_bosphorus_seed")

    expensive = BusinessProfile.model_validate({
        **business.model_dump(), "amount_raising": {"amount": 1_000_000_000_000, "currency": "NGN"},
    })
    narrow = InvestorProfile.model_validate({
        **investor.model_dump(), "ticket_size": {"minimum": 250_000, "maximum": 300_000, "currency": "USD"},
    })
    cases = [
        ("founder_baseline", "founder", business, {}, 3),
        ("investor_baseline", "investor", investor, {}, 3),
        ("founder_large_raise", "founder", expensive, {}, 0),
        ("investor_narrow_ticket", "investor", narrow, {}, 0),
        ("investor_series_a_filter", "investor", investor, {"stages": ["series_a"], "include_exploration_matches": True}, 0),
        ("founder_multi_location", "founder", business, {"geographies": ["nigeria", "turkiye"]}, 3),
        ("investor_multi_location", "investor", investor, {"geographies": ["nigeria", "kenya"]}, 2),
        ("founder_asia", "founder", turkish_business, {"geographies": ["asia"]}, 2),
        ("investor_asia", "investor", turkish_investor, {"geographies": ["asia"]}, 2),
        ("investor_north_america", "investor", investor, {"geographies": ["north america"]}, 0),
    ]
    for name, mode, profile, constraints, expected_count in cases:
        request = MatchRequest.model_validate({
            "mode": mode,
            "objective": "Find compatible fictional demo partners.",
            "business_profile": profile if mode == "founder" else None,
            "investor_profile": profile if mode == "investor" else None,
            "constraints": constraints,
            "top_k": 10,
        })
        result = match_profiles(request, catalog)
        matches = result.response.matches
        assert result.considered_count == expected_count, name
        if name.endswith("baseline"):
            assert matches and matches[0].eligibility_status == "core_eligible"
        assert all(match.rank == index + 1 for index, match in enumerate(matches))
        assert all(match.evidence for match in matches)
        print(json.dumps({
            "scenario": name,
            "considered": result.considered_count,
            "top": [{"name": match.candidate_name, "score": round(match.overall_score, 2),
                     "eligibility": match.eligibility_status} for match in matches[:3]],
        }))


if __name__ == "__main__":
    main()
