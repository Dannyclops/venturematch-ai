# Deterministic Eligibility Engine

## Purpose

Eligibility runs before compatibility scoring or agent explanation. Its job is to prevent an attractive semantic similarity score from hiding a factual mandate conflict.

The implementation is in `backend/app/matching/eligibility.py`. It has no LLM dependency and evaluates the same business-investor pair identically when given the same profiles and FX snapshot.

## Result states

| State | Meaning | Can proceed to scoring? |
|---|---|---:|
| `core_eligible` | Every hard rule passes and the business is within the investor's preferred stages. | Yes |
| `exploration_eligible` | Every hard rule passes, but the funding stage is outside the normal mandate and permitted by the investor's exploration policy. | Yes, with a visible exploration label |
| `ineligible` | One or more hard rules fail. | No |

Core results are returned before exploration results. Callers can set `include_exploration_matches=false` to omit exploration results entirely.

## Evaluated rules

| Rule | Passing condition | Blocking condition |
|---|---|---|
| Investor activity | `actively_investing` is true. | The investor is not currently active. |
| Industry mandate | The primary industry is preferred and not excluded. | The industry is excluded or outside the stated mandate. |
| Funding stage | The stage is preferred, or is permitted for exploration. | The investor's strict, adjacent, or open policy does not permit the stage. |
| Ticket size | The normalized raise is inside the inclusive normalized ticket range. | The raise is below the minimum or above the maximum. |
| Geography | A direct country, market, or derived region overlaps the investor's mandate; `global` accepts every geography. | No supported overlap exists. |
| Revenue requirement | The investor does not require revenue, or the business is marked revenue-generating. | Revenue is required but absent or unknown. |

Every rule is evaluated, even after one fails. This produces all blocking reasons in one decision instead of forcing the user to fix incompatibilities one at a time.

## Currency comparison

The engine normalizes the company's raise and the investor's ticket range through the same `FxSnapshot`. The result preserves both original values and includes the normalized values, rate, source, and timestamp used in the decision.

If the snapshot lacks a required supported currency, normalization raises an explicit error. The engine never substitutes a guessed rate.

## Geography normalization

Direct operating markets and headquarters are converted to stable lowercase comparison keys. Country names can add transparent regional tags used by the demo dataset, including:

- Africa, East Africa, West Africa, and Southern Africa
- MENA
- Europe and Southeast Europe
- Emerging markets

Aliases such as `Turkey`/`Türkiye`, `UAE`/`United Arab Emirates`, and the expanded form of MENA are normalized. These mappings are application policy, not model inference. Production expansion should use a maintained geographic taxonomy and corresponding tests.

## Discovery methods

- `discover_investors` evaluates investors for a founder's business.
- `discover_businesses` evaluates businesses for an investor.
- Both methods omit ineligible records, optionally omit exploration matches, support explicit candidate exclusions, and keep input order within each eligibility group.

Scoring will consume only the results returned by these methods. It may rank eligible candidates, but it may not change their eligibility state.
