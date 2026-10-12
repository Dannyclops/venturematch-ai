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

