# Request-bound matching tools

## What is implemented

Six local tools expose the tested matching engines through typed arguments, typed results,
generated JSON Schema descriptors, and an allowlisted JSON dispatcher. The agent-development
guidance informed the separation between application tools and the agent runtime.

These are **callable local application tools**, not a running OpenAI agent. No model,
SDK, network dependency, API key, or paid inference is introduced by this layer.
The next integration step must adapt the portable descriptors to the selected provider's
tool format and return tool results using that runtime's call IDs. Do not submit these
descriptors directly as an OpenAI API payload; provider strict-schema requirements
and live tool-calling have not been verified here.

## Host-controlled boundary

The host first validates a `MatchRequest` and `MatchingCatalog`, then creates one
`MatchingTools` instance per request. Both are deep-copied. The tools cannot edit profiles,
constraints, FX rates, weights, catalog paths, or result limits. A conversational
refinement requires the host to validate a new request and create a new instance.

Profile/catalog text is data, not executable instructions. This is not a complete
prompt-injection defence for a future LLM; the agent must also treat retrieved text
as untrusted evidence and the host must enforce output and action permissions.

## Tool registry

| Tool | Arguments | Result |
|---|---|---|
| `analyze_profile` | Empty object | Normalized host-bound profile, original/base money, constraints, missing optional data, warnings |
| `search_investors` | `offset` (default 0), `limit` (default 20, max 50) | Founder-mode eligible investors, decisions, total and next offset |
| `search_businesses` | Same pagination arguments | Investor-mode eligible businesses, decisions, total and next offset |
| `score_matches` | Optional `candidate_ids` (null/omitted = all; 1–50 unique IDs otherwise) | Ranked results, number considered, display preference and warnings |
| `analyze_portfolio_fit` | `candidate_id` | Portfolio score, linked-record evidence, warnings and possible competition |
| `retrieve_match_evidence` | `candidate_id` | Fresh evidence, concerns, eligibility/FX provenance and scoring version |

Only the correct search direction is offered by `definitions()`; dispatching the
opposite direction still produces `wrong_mode`. Searches are core-first then ID-sorted,
not score-ranked; pagination does not alter the set scored by an unfiltered `score_matches`.
The host's `top_k` limits final scores, not discovery pages.

All direct scoring, portfolio and evidence calls recheck exclusions, filters, eligibility,
and exploration permission. Explicit selections fail atomically if any ID is invalid;
they do not quietly return a partial ranking. Searches skip excluded/ineligible records.
Unavailable FX is an error, not an empty result.

## Additional search filters

Filters can only narrow the base eligibility decision, never replace the investor's mandate.

| Bound constraint | Founder mode: investor candidate | Investor mode: business candidate |
|---|---|---|
| `industries` | At least one stated preferred industry intersects the filter | Primary industry belongs to the filter |
| `stages` | At least one preferred stage intersects the filter (not merely exploratory stages) | Current stage belongs to the filter |
| `geographies` | Mandate overlaps a requested location/region; global accepted | Supplied/derived business geography matches a requested term; global accepts all |
| `ticket_size` | Normalized candidate ticket range overlaps the requested range inclusively | Normalized business raise falls within requested range inclusively |
| `excluded_entity_ids` | Investor IDs excluded from every tool | Business IDs excluded from every tool |
| `include_exploration_matches` | False prevents exploration results in every tool | Same |

All comparisons use the same bound FX snapshot. A founder ticket-range filter is an
additional candidate-range-overlap requirement, not a replacement for the full-raise
eligibility check. Country/region resolution retains the limited demo taxonomy.
Two different countries are not deemed identical just because they share a continent.
Blank geographic filters are rejected rather than silently dropped.

`display_currency` is echoed as a presentation preference. Original money and base-currency
provenance are preserved; non-base display conversion is explicitly warned as unimplemented.

## Calling convention

~~~python
from app.models import MatchRequest
from app.tools import MatchingCatalog, MatchingTools

catalog = MatchingCatalog.from_demo()
request = MatchRequest(
    mode="founder",
    objective="Find compatible investors for this business.",
    business_profile=catalog.businesses[0],
)
tools = MatchingTools(request, catalog)
descriptors = tools.definitions()
search = tools.invoke("search_investors", '{"offset": 0, "limit": 20}')
ranking = tools.invoke("score_matches", "{}")
~~~

Success: `{"tool_name": "...", "ok": true, "data": {...}, "error": null}`.
Failure: `{"tool_name": "...", "ok": false, "data": null,
"error": {"code": "...", "message": "...", "details": {...}}}`.

Errors include `invalid_arguments`, `unknown_tool`, `wrong_mode`, `unknown_candidate`,
`duplicate_candidates`, `candidate_excluded`, `constraint_conflict`,
`ineligible_candidate`, `exploration_disabled`, `missing_fx_rate`, and `internal_error`.
Validation errors do not echo arbitrary inputs; internal exceptions do not leak stack
traces or local paths. The future host should record diagnostics in protected logs
and handle `internal_error` instead of endlessly retrying.

## Local harness

From `backend/`:

~~~powershell
.\.venv\Scripts\python.exe -m app.tools --business business_solargrid_africa --definitions
.\.venv\Scripts\python.exe -m app.tools --business business_solargrid_africa --tool search_investors
.\.venv\Scripts\python.exe -m app.tools --investor investor_greenfront --tool score_matches --core-only
.\.venv\Scripts\python.exe -m pytest -q
~~~

The harness performs an explicit local tool invocation. It does not pretend a model
selected or executed the call. All demo outputs identify fictional data and synthetic FX.
