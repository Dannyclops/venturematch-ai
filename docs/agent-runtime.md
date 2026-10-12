# VentureMatch Agent runtime

## Implemented, with live verification still required

`backend/app/agent/` connects the existing request-bound tool dispatcher to the
OpenAI **Agents API** (`client.beta.agents`), using the official Python client.
It is not the separate `openai-agents` package, an Assistants API implementation,
or a fixed sequence presented as an AI run. The model chooses function calls.
Local scripted-provider tests do not establish remote API access or output quality.

Initial runtime verification: **128 tests passed in 4.84 seconds** in the user's normal
PowerShell terminal on 2026-10-12, as confirmed by the supplied test-result screenshot.
This includes the six asynchronous tests. Separately, 122 synchronous tests passed
inside the restricted development environment; its Windows asyncio socket-pair
startup stalls before application code starts, so async runs should use a normal
terminal. After the recovery changes, the complete suite passed in the user's normal
PowerShell terminal: **161 tests passed in 6.18 seconds** on 2026-10-12, confirmed
by the supplied screenshot. End-to-end live matching is not yet verified.
Run the complete suite with `.\.venv\Scripts\python.exe -m pytest -q`.

## Recovery after the first live failure

The first live session was inspected and successfully deleted on 2026-10-12.
The recovery output confirmed `ok: true` and `deletion_confirmed: true`; the
original turn had failed with `usage_limit_exceeded`. The account's billing screen
showed a free trial with $0.00 credit remaining. Resolve API billing/limits before
another live matching attempt; model access and live output quality remain unverified.
Safe diagnostics now include a stage, exception class, recognized provider code,
HTTP status if available, and application file/line locations. There are no raw
exception messages, headers, prompts, tool arguments, frame locals, or model output.
General streaming `APIError` is now classified separately from unexpected local
exceptions. Billing/quota, rate limits, and access codes are distinguished when the
provider supplies a recognized code. The original Python traceback was not retained;
the remote turn's failure code was obtained through the recovery command.

From `backend/`:

```powershell
# Read-only inspection; prompts for the existing sess_ ID when not supplied.
.\.venv\Scripts\python.exe -m app.agent.maintenance --inspect

# Inspect first, then cancel/delete ONLY the supplied disposable demo session.
.\.venv\Scripts\python.exe -m app.agent.maintenance --cleanup
```

Copy the exact `session_id` from the original terminal output, not screenshot OCR.
Do not enter an API key. Recovery uses a synchronous client and does not create a
session, submit user input, or request inference. It reports turn error codes and
statuses, never session message bodies. The cleanup report preserves the pre-delete
status/error summary; deleting removes the remote session and its saved history.
Existing hosted-resource costs may continue until cleanup finishes; the command
does not claim zero charges or stop billing merely because cancellation was accepted.

Deletion must explicitly confirm the same ID. A 404 is reported as not found/not
visible, not proof of deletion. Cleanup makes at most three delete attempts on 409;
other failures stop without retry. Each request has a 10-second timeout, with SDK
automatic retries disabled. Physical hosted cleanup may continue asynchronously
after successful deletion.

The regression suite includes the actual installed SDK with an in-memory HTTP
transport, exercising streaming-error handling and recovery endpoint shapes without
network access or charges. These recovery tests are included in the verified 161-test
result above; they do not establish that a live matching run will succeed.

The default model is `gpt-6-astra`, following the current Agents API quickstart.
Change it with `--model` or `OPENAI_MODEL`; project access must be checked live.
The default environment is a small OpenAI-hosted sandbox with network disabled.
No repository files, credentials, or packages are uploaded to it. Matching functions
execute in the local backend, not the hosted sandbox. `--environment none` explicitly
opts out of a sandbox for a function-only run. There is no silent environment fallback.
Hosted provisioning, model inference, and token usage may incur charges.

## Local setup

From `backend/`, install `python -m pip install -e ".[dev]"`.
Keep `OPENAI_API_KEY` in the repo-root `.env` (already ignored by Git) or the
process environment. Never put it in frontend code, logs, prompts, or screenshots.
The CLI loads that exact `.env`, without variable interpolation; existing environment
variables take precedence. The API destination is fixed to `https://api.openai.com/v1`.

These commands use the Windows project environment:

```powershell
# No network or key needed: inspect five mode-specific API tool definitions.
.\.venv\Scripts\python.exe -m app.agent --business business_solargrid_africa --definitions

# Explicitly opt into API usage. Each command starts one new session.
.\.venv\Scripts\python.exe -m app.agent --business business_solargrid_africa --live --top-k 3
.\.venv\Scripts\python.exe -m app.agent --investor investor_greenfront --live --top-k 3 --core-only

# Optional function-only mode, without a hosted sandbox.
.\.venv\Scripts\python.exe -m app.agent --business business_solargrid_africa --live --environment none
```

The application key needs Agents read/write and Responses write access. An installed
SDK and a correctly formatted key do not prove project access or available credit.

## Data flow and factual boundary

1. Validate and snapshot the host-approved `MatchRequest` and catalog.
2. Preflight local analysis/scoring before creating a remote session.
3. Advertise only the five applicable functions, with explicit JSON input fields.
4. Process `agent.session.requires_action`; dispatch only allowlisted functions,
   bound to the active session and turn. Submit results with the exact call and turn IDs.
5. Require successful model-requested `analyze_profile` and full-catalog
   `score_matches(candidate_ids=null)` before accepting final output.
6. Validate final JSON against `AgentDraft`; recompute rankings locally. Reject any
   missing, duplicated, invented, or reordered candidates.
7. Return `AgentRun`, containing the existing `MatchResponse` unchanged in scoring,
   plus AI-selected evidence highlights, provider IDs, usage if available, and cleanup warnings.

The model selects one or two factors per candidate. The host copies their exact
evidence statements into highlights. Names, scores, ranks, eligibility, concerns,
confidence, FX metadata, and deterministic explanations come only from the engine.
This first version deliberately does **not** accept model-written factual prose.
`explanation_method=evidence_selection_v1` makes that limitation explicit.
There are no model-authored refinement suggestions yet.

The objective affects evidence emphasis, not eligibility or numerical ranking.
Use structured `MatchConstraints` for filtering. The original objective is retained
in `normalized_objective`; no inferred rewrite is claimed. Conversational refinement
requires a newly approved request and fresh runtime instance; `conversation_id` does
not resume a provider session in this version.

## Limits and failure behavior

- Up to 18 distinct function calls, 2,000 stream events, and 65,536 characters per
  tool-argument payload/final answer. Duplicate pending call IDs replay cached results;
  changed arguments for the same ID are rejected.
- Default overall deadline: 120 seconds; configurable from 1 to 300. Cleanup has a
  separate 25-second ceiling. CLI HTTP requests time out after at most 30 seconds.
- Automatic SDK retries are disabled. These are execution bounds, **not a monetary
  spending cap** or a server-side token cap. Configure project billing controls separately.
- Idle is not success. Require the intended completed turn and final structured answer.
  If the stream ends cleanly before these arrive, retrieve persisted turn status/items.
  Connection exceptions fail safely rather than automatically resubmitting initial input.
- On failure, attempt remote cancellation; then delete the disposable session. A delete
  conflict permits one cancellation and one bounded retry. Successful runs also delete
  the session after assembling the local output. Hosted cleanup may finish asynchronously.
- Cleanup failures preserve the session ID in warnings. If creation returned no ID,
  its remote outcome is uncertain: inspect Platform before retrying. Process crashes
  cannot guarantee remote cancellation or cleanup.
- Raw provider errors, arbitrary arguments, streamed commentary, and model prose are
  not printed by the CLI. There is no durable session/job store or reconnecting worker.

The host enforces matching facts; prompts are not a complete prompt-injection defense.
Catalog data and profiles remain untrusted. No live web enrichment, embedding upgrade,
FastAPI route, UI, valuation, or investment execution is included in this phase.

## References

- [Agents API quickstart](https://developers.openai.com/api/docs/guides/agents-api/quickstart)
- [Application function tools](https://developers.openai.com/api/docs/guides/agents-api/tools/functions)
- [Tool contracts](agent-tools.md)
- [Scoring policy](compatibility-scoring.md)
