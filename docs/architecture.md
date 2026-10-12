# VentureMatch AI Architecture

## Design principle

The system separates **agentic orchestration** from **deterministic decision logic**.

- The agent interprets goals, selects tools, manages refinement, and explains results.
- The matching engine applies filters, calculates scores, and returns evidence.
- The dataset supplies the only businesses, investors, and portfolio facts available to the MVP.

This prevents the language model from silently changing the scoring rules or inventing investment information.

## Core components

### 1. Web interface

Collects structured profile fields and an optional natural-language objective. It displays tool progress, ranked matches, score components, evidence, and limitations.

### 2. FastAPI service

The implemented service validates requests, lists demo profiles, invokes the local
matching engine, and returns structured engine-only responses. Live agent HTTP
execution and session persistence are not implemented. See [backend-api.md](backend-api.md).

### 3. VentureMatch Agent

A single agent operates in either founder or investor mode. It determines which tools are needed, but it may not bypass eligibility checks or invent missing fields.

### 4. Matching tools

Thin tool interfaces expose profile analysis, candidate retrieval, scoring, portfolio analysis, and evidence retrieval to the agent.

The local tool registry and JSON dispatcher live in `app/tools/`. Each instance is
bound to a validated request and catalog snapshot; the agent cannot change these through
tool arguments. Additional search filters apply to every candidate-scoring/evidence path.
Provider-specific registration and the single-turn Agents API runner are implemented
in `app/agent/`. Live API access and behavior still need verification. Final rankings
are rechecked locally; the model selects evidence highlights rather than writing facts.
See [agent-runtime.md](agent-runtime.md) for limits and lifecycle handling.
See [agent-tools.md](agent-tools.md) for the exact call and error contracts.

### 5. Matching engine

Pure Python functions perform hard filtering, component scoring, weight application, ranking, and confidence calculation. These functions should have unit tests and no dependency on an LLM.

The eligibility layer evaluates investor activity, industry mandate, funding stage, normalized ticket size, geography, and revenue requirements. It returns all rule outcomes so the interface and agent can explain both accepted and rejected candidates.

The offline scorer is implemented as `CompatibilityEngine`, with explicit eligibility
rechecks, versioned heuristic weights, lexical thesis similarity, portfolio warnings,
and deterministic rankings in both directions. See
[`compatibility-scoring.md`](compatibility-scoring.md) for the complete policy.

### 6. Data layer

The first version uses synthetic JSON for portability and transparency. SQLite can be introduced when session or user persistence is required.

## Planned agent execution flow

1. The API validates the request.
2. The agent determines the user mode and objective.
3. `analyze_profile` normalises the supplied fields, including money values through one timestamped FX snapshot, and reports missing information.
4. A search tool classifies candidates as core eligible, exploration eligible, or ineligible according to hard constraints and the investor's stage policy.
5. `score_matches` calculates component and total scores.
6. Investor-mode requests may call `analyze_portfolio_fit`.
7. `retrieve_match_evidence` supplies the factual basis for explanations.
8. The agent returns ranked matches using a structured response schema.
9. A follow-up request can refine constraints and rerun the relevant tools.

## Implemented API boundary

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/api/health` | Confirm backend availability |
| `GET` | `/api/businesses` | Return demo business profiles |
| `GET` | `/api/investors` | Return demo investor profiles |
| `GET` | `/api/businesses/{entity_id}` | Retrieve one demo business |
| `GET` | `/api/investors/{entity_id}` | Retrieve one demo investor |
| `GET` | `/api/metadata` | Form options and synthetic FX provenance |
| `POST` | `/api/matches` | Run engine-only matching with structured constraints |

`/api/agent/match` and `/api/agent/refine` remain planned and are not registered.
For now, refinement means submitting a new `MatchRequest` with changed constraints.

## Match-response requirements

Each recommended match must include:

- Entity identifier and display name
- Core or exploration eligibility status
- Overall compatibility score
- Component scores
- Supporting evidence
- Concise explanation
- Potential mismatch or concern
- Confidence indicator

## Guardrails

- Use only the supplied profile and dataset.
- Never fabricate portfolio companies, funding history, or traction.
- Never present compatibility as investment advice.
- Never claim that discovery constitutes due diligence.
- Report missing information explicitly.
- Preserve hard constraints during conversational refinement.
- Preserve submitted currencies and expose the rate, source, timestamp, and estimated normalized value used for comparisons.
- Label matches outside an investor's preferred funding stages as exploration results.

## MVP success criteria

The MVP succeeds when both user modes can complete an end-to-end matching run, the ranking can be reproduced from deterministic scores, and every explanation can be traced to stored profile evidence.

