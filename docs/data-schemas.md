# VentureMatch AI Data Schemas

## Purpose

These schemas form the contract among the synthetic dataset, matching engine, agent tools, FastAPI endpoints, and frontend. The backend Pydantic models are canonical; TypeScript interfaces mirror their JSON representation.

## Schema groups

| Group | Core models | Purpose |
|---|---|---|
| Shared values | `Location`, `MoneyAmount`, `MoneyRange` | Reusable validated primitives |
| Business | `BusinessProfile`, `TractionMetrics` | Founder and company information |
| Investor | `InvestorProfile`, `PortfolioCompany` | Investment preferences and portfolio evidence |
| Matching | `ScoreBreakdown`, `MatchEvidence`, `MatchConcern`, `MatchResult` | Explainable ranked recommendations |
| Agent API | `MatchRequest`, `RefinementRequest`, `MatchResponse` | Agent input, refinement, progress, and output |

## Important distinctions

### Exact amount versus range

`MoneyAmount` represents one amount, such as a company raising USD 750,000. `MoneyRange` represents an investor's acceptable inclusive ticket range, such as USD 250,000–1,500,000.

### Hard constraints versus scores

Eligibility rules run before ranking. A candidate that violates a hard constraint should be removed or marked as blocking; a high semantic-similarity score must not override the conflict.

### Facts versus explanations

`MatchEvidence` identifies the entity and field supporting a recommendation. The natural-language explanation may summarize that evidence, but it may not introduce unsupported claims.

### Mode-safe requests

- `founder` mode requires `business_profile` and rejects `investor_profile`.
- `investor` mode requires `investor_profile` and rejects `business_profile`.

This prevents ambiguous tool selection and accidental cross-mode processing.

## Normalization rules

- Entity identifiers use lowercase letters, numbers, underscores, and hyphens.
- Country codes use two uppercase ISO-style characters.
- Currency codes use three uppercase ISO-style characters.
- User-entered matching terms are trimmed, converted to lowercase, and de-duplicated.
- Compatibility scores range from 0 to 100.
- Unknown fields are rejected instead of being silently ignored.

## File locations

- Backend source of truth: `backend/app/models/`
- Backend contract tests: `backend/tests/test_schemas.py`
- Frontend mirror: `frontend/src/types/`

The next development stage will create synthetic JSON records that validate against these models.

