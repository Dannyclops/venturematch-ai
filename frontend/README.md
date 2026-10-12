# VentureMatch AI Frontend

This directory contains a dependency-free HTML/CSS/JavaScript browser demo.
The TypeScript contracts in `src/types/` remain a reference for a later app.
There is no Node install or frontend build step.

## Start locally (Windows PowerShell)

From the repository root, one terminal is enough:

```powershell
backend\.venv\Scripts\python.exe scripts\run_demo.py
```

The launcher starts the engine-only backend and frontend, opens the browser,
and stays running until Ctrl+C. If either service is already healthy, it reuses
it.

To demonstrate the optional agent, stop the free launcher with Ctrl+C and run:

```powershell
backend\.venv\Scripts\python.exe scripts\run_demo.py --live
```

This enables the AI-assisted choice but does not call OpenAI until you select
that choice and confirm a search in the browser. Each confirmed search is
billable. The backend loads the ignored `.env` key; the browser never receives
it. If another engine-only backend still occupies port 8000, the launcher
will tell you to stop it first. For separate terminals instead, in terminal 1:

```powershell
cd backend
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

In terminal 2, from the repository root:

```powershell
cd frontend
..\backend\.venv\Scripts\python.exe -m http.server 3000 --bind 127.0.0.1
```

Open <http://127.0.0.1:3000/>. Stop each server with Ctrl+C. If the backend
virtual environment is missing, follow `backend/README.md` first. Opening
`index.html` as a `file://` URL is not the supported setup.

The default backend is engine-only and does not use OpenAI credits. The UI loads
fictional profiles, offers founder and investor modes, search-only raise or ticket
edits, industry and stage filters, multi-location exploration, optional stage
exploration, and ranked results. Choose several locations to include any of them;
**All locations** clears that filter. Continents cover the world as options, while
only fictional demo markets have profiles. The natural-language objective
is recorded but does not alter scores in engine mode. Each card exposes factor
scores, source evidence, concerns, and the illustrative FX comparison. There is
no persistent profile or conversation state. Edited amounts and currencies are
sent with that search request and reset when a different profile is selected.

To offer the **optional billable** AI-assisted choice, restart the backend with
the environment flag described in [`../docs/live-agent-api.md`](../docs/live-agent-api.md).
The UI never selects it by default and asks for confirmation before each request.
A browser disconnect can leave a paid run active, so inspect the server before
retrying.

See [`../docs/demo-runbook.md`](../docs/demo-runbook.md) for the presentation flow.
The engine-only scenario checks are documented in
[`../docs/demo-evaluation.md`](../docs/demo-evaluation.md).

## Later UI scope

1. Landing page and product explanation
2. Founder/investor mode selection
3. Structured profile form
4. Natural-language investment objective
5. Agent progress and tool-status display
6. Ranked match cards
7. Score breakdown and evidence panel
8. Conversational refinement

The demo consumes the FastAPI service documented in [`../docs/architecture.md`](../docs/architecture.md).

## Current structure

`src/types/` mirrors the backend's Pydantic contracts. The backend remains the source of truth; these interfaces describe its JSON request and response shapes for future typed UI work.

