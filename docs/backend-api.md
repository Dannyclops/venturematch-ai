# Local matching API

This phase exposes the existing matching engine through FastAPI. It requires no
OpenAI key, API payment, or outbound network at runtime. Responses explicitly say
`execution_mode: "engine_only"`. The default server does not load `.env` or create
provider clients/sessions. This endpoint never switches to AI execution. A separate
[AI-assisted endpoint](live-agent-api.md) can be explicitly enabled at startup.

## Start on Windows

From `backend/` in normal PowerShell:

```powershell
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Open `http://127.0.0.1:8000/docs` for the interactive API documentation, or
`http://127.0.0.1:8000/api/health` for a health check. Stop the server with Ctrl+C.
Swagger UI assets load from a CDN; the endpoints and `/openapi.json` themselves
work offline. The local browser demo is described in
[`../frontend/README.md`](../frontend/README.md).

The catalog loads and validates once at application creation. Invalid/missing
dataset files prevent startup. Restart after editing the demo JSON. The editable
install expects the repository's `data/` folder alongside `backend/`.

## Endpoints

| Method | Path | Result |
|---|---|---|
| GET | `/api/health` | Availability, engine-only mode, live agent disabled |
| GET | `/api/metadata` | Form enums, supported currencies, complete synthetic FX snapshot and notice |
| GET | `/api/businesses` | ID-sorted page of fictional business profiles |
| GET | `/api/businesses/{entity_id}` | One full business profile |
| GET | `/api/investors` | ID-sorted page of fictional investor profiles |
| GET | `/api/investors/{entity_id}` | One full investor profile |
| POST | `/api/matches` | Ranked matches from a canonical `MatchRequest` |

List endpoints accept `offset >= 0` and `limit` from 1 to 50 (default 50).
Responses contain `items`, `total`, `next_offset` (null at the end), and `notice`.
They list the demo catalog, not search-filtered or score-ranked recommendations.
Unknown IDs return 404. Detail responses use the existing profile schema; their
fictional-data notice is provided by metadata and the list response.

## Run a founder example

Keep the server running and open a second PowerShell terminal:

```powershell
$baseUrl = 'http://127.0.0.1:8000'
$profile = Invoke-RestMethod "$baseUrl/api/businesses/business_solargrid_africa"
$body = @{
    mode = 'founder'
    objective = 'Find compatible investors for our solar business.'
    business_profile = $profile
    top_k = 3
    constraints = @{ include_exploration_matches = $true }
} | ConvertTo-Json -Depth 30
$result = Invoke-RestMethod "$baseUrl/api/matches" -Method Post -ContentType 'application/json' -Body $body
$result | ConvertTo-Json -Depth 40
```

For investor mode, GET `/api/investors/investor_greenfront`, set `mode` to
`investor`, and submit the profile under `investor_profile` instead. Exactly one
profile must match the selected mode. Clients may submit their own valid profile;
it is used for that request only and is not saved or added to the demo catalog.

## Matching response and behavior

The response contains:

- `execution_mode`: always `engine_only`.
- `response`: canonical `MatchResponse`, including full scores, rank, evidence,
  concerns, confidence, missing information, and eligibility/FX provenance.
- `considered_count`: number of eligible candidates scored after constraints,
  before `top_k` truncation; not the number of all catalog records.
- `display_currency`: the requested presentation preference. Display conversion
  is not implemented; comparisons remain in USD with the original money retained.

The service calls the existing request-bound `analyze_profile` and full-catalog
`score_matches` functions. It does not duplicate ranking logic. Core matches remain
ahead of exploratory matches. Structured constraints and `top_k` (1–10) apply.
The natural-language objective is retained but does not change numerical scores or
filtering. Change structured constraints to refine a search, then POST a new request.

Zero eligible results return 200 with an empty match list and an explanatory warning.
No constraint is relaxed automatically. `activity` and `suggested_refinements` remain
empty; no agent progress or AI suggestions are fabricated. Run IDs identify individual
responses only. There is no run persistence, conversation history, or resume endpoint.

## Errors and local boundary

Errors use `{ "error": { "code": "...", "message": "...", "issues": [] } }`.
Invalid bodies/parameters return 422 with field locations and error codes, without
echoing submitted values or validator contexts. Missing resources return 404;
missing FX rates return 503; matching/internal failures return 500 rather than empty
success. Unexpected exception messages are not returned in HTTP responses.

CORS allows only `http://localhost:3000` and `http://127.0.0.1:3000` for the planned
frontend. CORS is not authentication. This unauthenticated demo should stay bound to
loopback; public deployment needs an explicit authentication, request-limit, and
data-handling design. `/api/agent/match` is available only after explicit server
activation and requires an intentional live-request header. There is no refinement route.

## Verification

On 2026-10-12 the complete suite passed in this development session:
**184 tests passed in 14.42 seconds**, including the existing asynchronous agent
tests and all 18 new API contract tests. `pip check` reported no broken requirements.
Installed HTTP packages: FastAPI 0.143.0, Starlette 1.7.0, Uvicorn 0.54.0, HTTPX 0.28.1.

Uvicorn successfully reported application startup on `127.0.0.1:8000`. On
2026-10-12, a separate loopback check received a healthy API response and HTTP 200
for the browser demo page and script. Headless browser rendering did not return
usable output in this environment, so interaction in a real browser remains
unverified. Temporary servers were stopped; use the normal-terminal startup
commands in the frontend README to inspect the interface on your laptop.
The passing ASGI tests exercise routing, validation, serialization and responses
in process; they do not establish browser-to-server connectivity.

`tests/test_matching_service.py` checks both directions against existing tool outputs,
including complete evidence and FX, empty results, and safe tool failures.
`tests/test_api.py` exercises the actual ASGI application using FastAPI's TestClient:
profiles, pagination, metadata, both matching directions, request isolation,
constraints, input validation, safe errors, CORS, and OpenAPI contracts.

HTTP tests do not call OpenAI or require a running server. They do require a working
asyncio runtime. Earlier sessions stalled at Windows socket-pair initialization;
the full suite completed in this session. Use normal PowerShell if that environment
restriction recurs. One founder CLI live run is now verified (see
[agent runtime](agent-runtime.md)). Local tests also cover the optional AI-assisted
HTTP adapter; a paid HTTP smoke check remains unverified.
