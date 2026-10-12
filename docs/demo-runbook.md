# Local hackathon demo

## Before presenting

1. Start the backend and browser demo using `frontend/README.md` in two VS Code
   terminals (`Terminal` → `New Terminal`). Use `http://127.0.0.1:3000/`.
2. Check that the search panel says **Local API connected**.
3. Leave execution on **Free matching engine** for a predictable, no-cost demo.
   If the backend was intentionally started with the live flag, the AI option
   becomes available, but each run consumes credits and needs confirmation.

## Two-minute walkthrough

1. **Founder:** Keep SolarGrid Africa selected. Its raise is in NGN. Click
   **Find matches**. Show ranked investor cards, then expand the top card for
   six factor scores, source-backed evidence, concerns, and illustrative USD
   normalization for ticket compatibility.
2. **Investor:** Switch to **I'm an investor**, which selects GreenFront
   Ventures. Click **Find matches**. Explain how its thesis, stage policy, ticket,
   and geography restrict and rank fictional businesses. Open a card to show
   why the result appeared.
3. **Exploration:** Change the stage filter or toggle **Include clearly labelled
   stage exploration**, then search again. Exploratory candidates are labelled
   separately from core eligible matches; other hard constraints still apply.
   If a filter yields zero results, show the empty-state guidance and clear it.

## Honest framing

- Profiles and FX rates are synthetic. This is investment discovery, not
  valuation, diligence, or financial advice.
- The deterministic engine enforces eligibility and computes scores. In engine
  mode the objective is displayed but does not change ranking. An optional
  bounded AI run chooses evidence through the matching tools.
- Thesis similarity is currently keyword-based, not embeddings. There is no
  conversation persistence, live market data, or deployment yet.
- One founder CLI AI run was observed. Investor live outcome and paid browser
  checks remain unverified; avoid claiming they succeeded.

If the browser cannot connect, use `http://127.0.0.1:8000/api/health` to check
the backend and verify both terminals are still running. The scripted local
API tests exercise both modes without spending credits.
