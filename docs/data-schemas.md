# VentureMatch AI Data Schemas

## Purpose

These schemas form the contract among the synthetic dataset, matching engine, agent tools, FastAPI endpoints, and frontend. The backend Pydantic models are canonical; TypeScript interfaces mirror their JSON representation.

## Schema groups

| Group | Core models | Purpose |
|---|---|---|
| Shared values | `Location`, `MoneyAmount`, `MoneyRange`, `FxSnapshot`, normalized money models | Reusable validated primitives and currency-conversion evidence |
| Business | `BusinessProfile`, `TractionMetrics` | Founder and company information |
| Investor | `InvestorProfile`, `PortfolioCompany` | Investment preferences and portfolio evidence |
| Eligibility | `EligibilityCheck`, `EligibilityResult` | Pre-scoring rule outcomes, normalized money evidence, and final eligibility state |
| Matching | `ScoreBreakdown`, `MatchEvidence`, `MatchConcern`, `MatchResult` | Explainable ranked recommendations |
| Agent API | `MatchRequest`, `RefinementRequest`, `MatchResponse` | Agent input, refinement, progress, and output |

## Important distinctions

### Exact amount versus range

`MoneyAmount` represents one amount, such as a company raising USD 750,000. `MoneyRange` represents an investor's acceptable inclusive ticket range, such as USD 250,000–1,500,000.

The original currency is preserved. `NormalizedMoneyAmount` and `NormalizedMoneyRange` add a derived USD value, the applied rate, its source and timestamp, and an estimate flag. Matching logic compares normalized amounts from the same FX snapshot.

### Preferred versus exploratory stages

`preferred_stages` represents the investor's normal mandate. `stage_flexibility` determines whether VentureMatch may also consider explicitly adjacent stages or any stage. Exploration changes candidate discovery, not the underlying investor preference, and every result outside the normal mandate must be labelled.

### Hard constraints versus scores

Eligibility rules run before ranking. A candidate that violates a hard constraint should be removed or marked as blocking; a high semantic-similarity score must not override the conflict.

`EligibilityResult` contains one check per evaluated rule and derives `core_eligible`, `exploration_eligible`, or `ineligible` from those outcomes. An `ineligible` result cannot proceed to scoring.

### Facts versus explanations

`MatchEvidence` identifies the entity and field supporting a recommendation. The natural-language explanation may summarize that evidence, but it may not introduce unsupported claims.

### Mode-safe requests

- `founder` mode requires `business_profile` and rejects `investor_profile`.
- `investor` mode requires `investor_profile` and rejects `business_profile`.

This prevents ambiguous tool selection and accidental cross-mode processing.

## Normalization rules

- Entity identifiers use lowercase letters, numbers, underscores, and hyphens.
- Country codes use two uppercase ISO-style characters.
- Currency values are restricted to the nine currencies supported by the MVP and are normalized to uppercase.
- User-entered matching terms are trimmed, converted to lowercase, and de-duplicated.
- Compatibility scores range from 0 to 100.
- Unknown fields are rejected instead of being silently ignored.

## File locations

- Backend source of truth: `backend/app/models/`
- Backend contract tests: `backend/tests/test_schemas.py`
- Frontend mirror: `frontend/src/types/`

See [`currency-and-stage-policy.md`](currency-and-stage-policy.md) for conversion provenance and funding-stage exploration rules.

