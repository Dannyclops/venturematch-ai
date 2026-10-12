# Compatibility Scoring v1

## Scope

The engine in `backend/app/matching/scoring.py` evaluates eligibility before scoring.
It supports founder-to-investor and investor-to-business ranking, with the same pairwise
scores in either direction. This is an offline, deterministic baseline, not the final AI agent.

Scores measure compatibility under a provisional policy. They are not calibrated
probabilities, investment recommendations, valuations, or predictions of funding success.

## Component policy

| Component | Weight | Rule |
|---|---:|---|
| Industry | 25% | 100 for every eligible primary-industry match. Lists are unordered; no invented preference for the first listed industry. |
| Stage | 20% | 100 for a preferred stage. Otherwise max(40, 85 - 15 × distance to the nearest preferred stage). Exploration still requires eligibility approval. |
| Ticket | 20% | 100 at the normalized range midpoint; linearly falls to 75 at either inclusive endpoint. A fixed range scores 100. |
| Thesis | 15% | 100 × unique-token Jaccard similarity between business text and investor text. |
| Geography | 10% | 100 for direct location/market overlap; 80 for derived regional overlap; 60 for a global-only match. Most specific available overlap wins. |
| Portfolio | 10% | 70 for known same-sector experience without a detected overlap signal; 30 for possible competition; otherwise neutral 50. |

The ticket midpoint is an explicit heuristic, **not a known investor preference**.
The MVP also retains the eligibility assumption that the full requested raise must fit
one investor's ticket range. Syndicated/partial-round participation is not modelled.

Geography measures specificity, not investment quality. Country/region mappings come
from the eligibility layer's limited demo taxonomy, not live geographic inference.

Component scores are rounded to two decimals with half-up rounding. The total is
the weighted sum of those rounded components, rounded half-up to two decimals.
Weights sum to 100 and cannot be altered through the engine's public constant.

## Lexical thesis baseline

Business input: `description`, `one_liner`, `industry_tags`, `keywords`.
Investor input: `thesis`, `keywords`.

Text is Unicode-normalized, case-folded, split into word tokens, and stripped of a
fixed stop-word list. Repeated tokens do not increase the score. Jaccard is
intersection size divided by union size; an empty union scores zero.

The existing `semantic_thesis_similarity` contract field is retained for compatibility,
but every output explicitly labels the actual method `keyword_jaccard_v1`.
This does not understand synonyms, negation, multilingual equivalence, or intent.
A later embedding implementation needs its own method/version and evaluation.
No API key, model download, or network call is needed for this baseline.

## Portfolio handling

Only records linked by the investor's `portfolio_company_ids` are used.

A potential competition flag requires all three:

- Same primary industry.
- Same business model.
- Jaccard overlap of at least 0.25 between business keywords/tags and portfolio keywords.

The strongest overlapping record is cited, with its ID resolving exact ties.
This is a review signal, never proof of competition. No detected overlap does not
prove that no conflict exists.

No links or missing linked records mean incomplete evidence: use neutral 50,
except that a known overlap can still lower the score to 30. Missing data never
earns a no-conflict bonus. Different-sector holdings do not automatically imply
desirable diversification.

## Ranking and result contract

1. Reevaluate eligibility for each pair; direct scoring raises `IneligibleMatchError`
   for rejected pairs and includes the rejection decision on the exception.
2. Omit rejected and explicitly excluded candidates.
3. Optionally omit exploration candidates.
4. Sort core before exploration, then descending total, then ascending candidate ID.
5. Apply `top_k` (1–10) and assign contiguous ranks.

Duplicate candidate or portfolio IDs are rejected. Missing FX rates remain explicit
errors rather than being silently treated as zero scores or unmatched candidates.

Each result includes six component scores, weights, version, lexical-method label,
field-level evidence, concerns, and the full eligibility decision with FX provenance.
Standalone pair scoring uses rank 1 as a placeholder; ranking methods assign final ranks.

Confidence is **low** if portfolio evidence is incomplete or traction is absent;
otherwise **medium**. The heuristic version never claims high confidence.
Confidence concerns evidence completeness, not likelihood of investment.

The rank methods accept candidate exclusions and exploration controls directly.
They are not yet a `MatchRequest` adapter: additional request-level industry/stage/
geography/ticket refinements, display-currency formatting, and conversational parsing
remain work for the search/API/agent integration.

## Run the demo

From `backend/`, using the project environment on Windows:

~~~powershell
.\.venv\Scripts\python.exe -m app.matching --business business_solargrid_africa
.\.venv\Scripts\python.exe -m app.matching --investor investor_greenfront --top-k 5
.\.venv\Scripts\python.exe -m app.matching --business business_solargrid_africa --core-only
.\.venv\Scripts\python.exe -m pytest -q
~~~

The demo emits JSON with a fictional-data and synthetic-FX notice.
Tests cover arithmetic, inclusive ticket boundaries, currency equivalence, ineligible
pair rejection, lexical ordering, core-first ranking, deterministic ties, missing and
unlinked portfolio records, overlap warnings, both directions, and every demo profile.
