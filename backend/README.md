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
- `tests/test_schemas.py` contains schema validation tests.
- `pyproject.toml` declares the Python and development dependencies.

Install the backend development dependencies from this directory with:

```bash
python -m pip install -e ".[dev]"
```

Then run:

```bash
pytest
```

