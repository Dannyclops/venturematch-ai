# Repeatable demo scenarios

Run from the repository root with the backend virtual environment:

```powershell
backend\.venv\Scripts\python.exe scripts\evaluate_demo.py
```

This calls the deterministic matching service on fictional profiles. It does
not call OpenAI, consume credits, or change stored profiles. It checks ranks and
evidence and prints one JSON line per scenario. Observed on 2026-10-12:

| Scenario | Profiles considered | Example result |
|---|---:|---|
| SolarGrid founder baseline | 3 | Sahel Impact Partners, 77.36 |
| GreenFront investor baseline | 3 | ColdChain Solar, 77.06 |
| SolarGrid raise changed to NGN 1 trillion | 0 | Empty state |
| GreenFront ticket changed to USD 250k–300k | 0 | Empty state |
| GreenFront filtered to Series A | 0 | Empty state |
| SolarGrid filters Nigeria or Türkiye | 3 | Sahel Impact Partners, 77.36 |
| GreenFront filters Nigeria or Kenya | 2 | ColdChain Solar, 77.06 |
| Anatolia Pay founder filters Asia | 2 | Global Frontier Capital, 79.11 |
| Bosphorus Seed investor filters Asia | 2 | WorkflowDock, 79.14 |
| GreenFront filters North America | 0 | No fictional business there |

Multiple selected locations use **any** semantics. An empty selection means
**All locations**, with no geography filter. The UI offers all continents and
the specific countries and regions represented by the demo catalog. Country
tags map the fictional African businesses to Africa; Jordan, Saudi Arabia,
Türkiye, and the UAE to Asia; and Türkiye to Europe. An investor's broad MENA
mandate can overlap Africa or Asia. This mapping is scoped to the catalog,
not a comprehensive world-country database.

The scenario counts are eligibility/search outcomes for these exact profiles
and filters, not a measure of real-world match quality. The UI submits edited
money values with the current search and does not persist them. The natural
language objective does not affect deterministic engine ranking.
