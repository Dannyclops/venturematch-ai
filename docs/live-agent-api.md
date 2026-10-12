# AI-assisted matching API

`POST /api/agent/match` connects the existing bounded Agents API runtime to the
local FastAPI app. Both founder and investor `MatchRequest` bodies are supported.
The route is registered only when explicitly enabled at server startup.
`POST /api/matches` always remains engine-only, even on an AI-enabled server.

## Enable locally

From `backend/` in PowerShell, with the existing key in the ignored repo-root `.env`:

```powershell
$env:VENTUREMATCH_ENABLE_LIVE_AGENT = '1'
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

The flag must be `1` in the launching process; putting it in `.env` does not activate
the endpoint. The key is loaded only after activation. A missing key fails startup
with a static error. `OPENAI_MODEL` selects the server's model (default `gpt-6-astra`).
Existing process variables take precedence over `.env`. Neither key nor model is
accepted from HTTP request bodies. Client initialization preserves the environment's
proxy settings; a SOCKS proxy may require `python -m pip install socksio` locally.

To return to engine-only mode, stop the server with Ctrl+C, then:

```powershell
Remove-Item Env:VENTUREMATCH_ENABLE_LIVE_AGENT -ErrorAction SilentlyContinue
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

The default app factory is engine-only. `/api/health` and `/api/metadata` expose
`live_agent_enabled`. Their `execution_mode: engine_only` field identifies the
default matching mode, not every available route. Disabled live routes return 404
and are absent from `/openapi.json` and `/docs`.

## Request and response

POST the same canonical `MatchRequest` used by `/api/matches`, with this header:

```http
Content-Type: application/json
X-VentureMatch-Live: true
```

The custom header marks an intentional billable request. It is not authentication.
Missing/wrong confirmation returns 403 without creating an OpenAI client. Invalid
profiles, `top_k` outside 1–10, or extra fields such as `model`, `api_key`,
`environment`, and `timeout_seconds` return 422 without inference.

The response is an `AgentRun` with two additional fields:

- `execution_mode: ai_assisted`.
- `elapsed_seconds`: server-side time including execution and cleanup.

`response` contains the canonical `MatchResponse`, retaining engine-owned scores,
rankings, eligibility, concerns, and FX evidence. `highlights` contains exact engine
evidence selected by the model. `model`, `session_id`, `turn_id`, `usage`,
`cleanup_warnings`, and `cleanup_diagnostics` describe execution. No free-form AI
factual explanation is accepted. The frontend must distinguish this result from
`engine_only`; failure never silently falls back to engine-only matching.

Token usage is optional and best effort. The runtime reads it from the completed
event or its nested turn; existing saved-turn reconciliation also retains usage.
Null usage means unknown, not zero cost. This endpoint does not calculate billed
cost or query the account balance. Use Platform billing for actual charges.

## Execution bounds

Each request creates a fresh runtime and disposable session. Server-owned settings
retain the default hosted small sandbox with network disabled, up to 18 distinct
tool calls, a 120-second execution timeout, and a separate 25-second cleanup ceiling.
The OpenAI client uses at most 30 seconds per HTTP request and zero automatic retries.

One live run may be active per application process. A concurrent request returns
409 immediately, without queuing or starting another session. Use a single server
worker for the local demo. This is not a global rate limit, idempotency guarantee,
or monetary spending cap: submitting another request after completion starts another
paid run. The client must not automatically retry failed or disconnected requests.

Browser disconnect does not reliably cancel remote work; the bounded server run
may continue through cleanup. Cancellation propagates through the runtime's cleanup
path and releases the concurrency guard. Process termination cannot guarantee remote
cleanup. There is no durable job store or reconnect endpoint. Preserve reported
session IDs and inspect them before retrying uncertain outcomes.

## Errors

| Status | Meaning |
|---|---|
| 403 | Missing explicit live-request header |
| 409 | Another live run is active; no new run started |
| 422 | Invalid request; no new run started |
| 429 | Provider rate or ambiguous rate/quota limit |
| 502 | Provider/agent failure, invalid output, or incomplete run |
| 503 | Billing, usage, access, credentials, or client setup problem |
| 504 | Run timeout; inspect cleanup status |

Agent errors retain the standard `error` envelope plus recovery IDs, allowlisted
diagnostics, and cleanup reports. Raw exception messages, credentials, profile input,
and raw model output are not returned. Client setup errors use safe metadata too.
General unexpected application failures retain the existing generic 500 response.

## Local-only boundary and verification

Keep the unauthenticated demo bound to loopback. CORS permits the two existing
localhost frontend origins and the live-request header. CORS and the confirmation
header do not provide authentication; public hosting needs a separate access and
spending-control design.

`tests/test_live_api.py` exercises the actual HTTP route and real agent runtime
against a scripted provider in both modes. It checks confirmation, validation,
ranking/evidence integrity, cleanup, concurrency, errors, secret redaction, mode
separation, activation, and nested usage. These tests do not make paid API requests.

On 2026-10-12 the complete suite passed: **204 tests passed in 9.97 seconds**.
This verifies local behavior with scripted provider responses, not live investor
access or the cost of a real HTTP invocation.

The earlier founder CLI live check succeeded. On 2026-10-12 investor CLI attempts
could not be verified: automatic approval review rejected result collection because
it attempted an additional Visual Studio telemetry destination outside the OpenAI
call. The result of the later bounded attempt was also unavailable. Outcome and
individual-run cost remain unknown. No paid HTTP test was launched. Inspect
account usage and any remaining session state before another live retry.
