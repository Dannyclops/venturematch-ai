# Local hackathon demo

Both engine-only search directions were reported working in the user's browser
on 2026-10-12. The same day, one AI-assisted investor browser run returned
ColdChain Solar at 77.06/100 with evidence. Rehearse on the presentation machine.

## Before presenting

1. Open the repository folder in VS Code. In one terminal (`Terminal` →
   `New Terminal`), run `backend\.venv\Scripts\python.exe scripts\run_demo.py`.
   The launcher opens `http://127.0.0.1:3000/`; leave the terminal open.
2. Check that the search panel says **Local API connected**.
3. Leave execution on **Free matching engine** for a predictable, no-cost demo.
   To demonstrate the agent, stop the launcher with Ctrl+C and rerun it with
   `--live`. Then refresh the browser; **AI-assisted (uses credits)** is selected
   on the page. Confirm one search. Each confirmed run consumes credits. Wait for a
   result before clicking again; if the outcome is uncertain, inspect the
   terminal and account usage before retrying.

## Two-minute walkthrough

1. **Founder:** Keep SolarGrid Africa selected. Its raise is in NGN. Click
   **Find matches**. Show ranked investor cards, then expand the top card for
   six factor scores, source-backed evidence, concerns, and illustrative USD
   normalization for ticket compatibility.
2. **Investor:** Switch to **I'm an investor**, which selects GreenFront
   Ventures. Click **Find matches**. Explain how its thesis, stage policy, ticket,
   and geography restrict and rank fictional businesses. Open a card to show
   why the result appeared.
3. **Exploration:** In investor mode, select **Nigeria** and **Kenya** under
   **Explore locations**, then search. GreenFront has two matching businesses
   in this scenario. Use **All locations (clear filters)** to restore the full
   catalog. Multiple choices mean *any* selected location. A continent groups
   the mapped demo countries; North America currently returns no demo matches.
4. **Sensitivity:** With GreenFront selected, change its USD ticket range to
   250,000–300,000 and search to show zero compatible businesses. Selecting a
   different profile restores its original ticket. You can similarly edit a
   founder's raise amount or currency for one search. Change the stage filter
   or toggle **Include clearly labelled stage exploration** to show how those
   constraints affect results. Exploratory candidates remain separate from
   core eligible matches.

## Honest framing

- Profiles and FX rates are synthetic. This is investment discovery, not
  valuation, diligence, or financial advice.
- The deterministic engine enforces eligibility and computes scores. In engine
  mode the objective is displayed but does not change ranking. An optional
  bounded AI run chooses evidence through the matching tools.
- Thesis similarity is currently keyword-based, not embeddings. There is no
  conversation persistence, live market data, or deployment yet.
- Location options include all continents, but the catalog covers only its
  fictional demo markets. The amount and currency fields edit a selected demo
  profile for one request; they do not save a new profile.
- One founder CLI AI run and one investor AI-assisted browser result were
  observed. Individual-run token usage and billed cost were not established.

If the browser cannot connect, use `http://127.0.0.1:8000/api/health` to check
the backend and verify both terminals are still running. The scripted local
API tests exercise both modes without spending credits.
The repeatable engine scenarios and observed counts are in
[`demo-evaluation.md`](demo-evaluation.md).
