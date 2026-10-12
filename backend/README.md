# VentureMatch AI Backend

This directory contains the Python backend: Pydantic contracts, deterministic
eligibility and compatibility scoring, local agent tools, a bounded OpenAI agent
runtime, and an engine-only FastAPI service. Thesis similarity currently uses a
keyword baseline; embeddings and live agent HTTP routes remain future work.

The matching engine must remain usable and testable independently of the language model.

## Current structure

- `app/main.py` and `app/api/` expose the local profile, metadata, and matching endpoints.
- `app/services/matching.py` assembles engine-only responses from existing tool outputs.
- `app/models/` contains the canonical Pydantic data contracts.
- `app/services/currency.py` normalizes supported currencies through a versioned FX snapshot.
- `app/matching/eligibility.py` applies deterministic hard filters before scoring.
- `app/matching/scoring.py` scores eligible pairs and ranks both discovery directions.
- `app/tools/` provides request-bound tool contracts, registry, dispatcher, and demo harness.
- `app/agent/` provides the OpenAI Agents API adapter, bounded runner, and evidence-only output validation.
- `python -m app.matching --business business_solargrid_africa` runs the offline JSON demo.
- `tests/` covers schemas, FX, eligibility, scoring, tools, agent recovery, and HTTP contracts.
- `pyproject.toml` declares the Python and development dependencies.

Install the backend development dependencies from this directory with:

```bash
python -m pip install -e ".[dev]"
```

Then run:

```bash
pytest
```

On Windows, the tested project environment can be invoked without activation:

```powershell
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m app.matching --business business_solargrid_africa
```

See [scoring policy](../docs/compatibility-scoring.md) for weights and limitations.

## Local HTTP API (no OpenAI credit needed)

After installing the dependencies above, start the service from this directory:

```powershell
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Open `http://127.0.0.1:8000/docs`. Profile lists are at `/api/businesses` and
`/api/investors`; POST a `MatchRequest` to `/api/matches` for engine-only results.
`/api/metadata` supplies form choices and synthetic FX provenance.
See [backend API](../docs/backend-api.md) for a runnable PowerShell example,
validation behavior, response contracts, and verification status.

## Local agent-tool harness

```powershell
.\.venv\Scripts\python.exe -m app.tools --business business_solargrid_africa --definitions
.\.venv\Scripts\python.exe -m app.tools --business business_solargrid_africa --tool score_matches
```

This invokes the local application tools, not an LLM. See
[agent tools](../docs/agent-tools.md) for contracts and the remaining runtime integration.

## OpenAI agent runner

```powershell
.\.venv\Scripts\python.exe -m app.agent --business business_solargrid_africa --definitions
# Billable live run; needs OPENAI_API_KEY in the repo-root .env or environment:
.\.venv\Scripts\python.exe -m app.agent --business business_solargrid_africa --live --top-k 3
```

See [agent runtime](../docs/agent-runtime.md) for configuration, the evidence-only
explanation policy, lifecycle cleanup, limits, and live-verification requirements.

For an existing failed live session, use `python -m app.agent.maintenance --inspect`
or `--cleanup`. These prompt for the original session ID and never start a new model
turn. Cleanup removes only that session and its history; inspect first if its
contents need to be retained. See the recovery section of the runtime documentation.

