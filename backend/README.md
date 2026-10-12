# VentureMatch AI Backend

This directory will contain the Python backend, including:

- FastAPI routes
- Pydantic data models
- Deterministic eligibility filters
- Compatibility scoring
- Embedding-based similarity
- Agent tool definitions
- VentureMatch Agent orchestration
- Scenario-based tests

The matching engine must remain usable and testable independently of the language model.

## Current structure

- `app/models/` contains the canonical Pydantic data contracts.
- `app/services/currency.py` normalizes supported currencies through a versioned FX snapshot.
- `app/matching/eligibility.py` applies deterministic hard filters before scoring.
- `app/matching/scoring.py` scores eligible pairs and ranks both discovery directions.
- `app/tools/` provides request-bound tool contracts, registry, dispatcher, and demo harness.
- `app/agent/` provides the OpenAI Agents API adapter, bounded runner, and evidence-only output validation.
- `python -m app.matching --business business_solargrid_africa` runs the offline JSON demo.
- `tests/` contains schema, currency-service, and eligibility-engine contract tests.
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

