# VentureMatch AI Synthetic Data

This directory contains the fictional dataset used for development, matching-engine tests, agent evaluations, and the hackathon demonstration.

## Dataset contents

| File | Records | Purpose |
|---|---:|---|
| `businesses.json` | 24 | Companies seeking investment |
| `investors.json` | 15 | Investor theses and eligibility preferences |
| `portfolios.json` | 45 | Three portfolio companies for every investor |
| `manifest.json` | 1 | Dataset version, counts, file map, and synthetic-data notice |

The businesses cover all ten MVP industries, multiple business models, pre-seed through Series A stages, and markets across Africa, Türkiye, MENA, and Europe.

## Why the records are deliberately varied

The data contains more than obvious positive matches. It includes:

- Strong industry, stage, ticket, and geography matches
- Strong matches with possible portfolio competition
- Relevant investors whose ticket range is incompatible
- Relevant investors whose stage preference is incompatible
- Revenue-required investors and pre-revenue businesses
- Businesses with several plausible investors
- A small number of intentionally difficult or unmatched profiles

Examples include:

- `business_solargrid_africa` fits `investor_greenfront`, but `portfolio_gridwatch` creates a possible overlap concern.
- `business_carbonledger_tr` fits the stage and ticket range of `investor_climatescale_growth`, while `portfolio_emissionworks` tests similarity-versus-competition reasoning.
- `business_carecircle_ng` is too early and too small for `investor_meridian_health`, but fits the pre-seed range of `investor_horizon_angels`.
- `business_nourishbox_eg` intentionally lacks a clean stage-and-sector investor match.

## Validation

Run the dependency-free integrity validator from the repository root:

```bash
node scripts/validate-data.mjs
```

It checks:

- JSON syntax and expected record counts
- Unique and correctly formatted IDs
- Portfolio foreign-key references
- Supported enums
- Money ranges and currency formats
- Required text and list fields
- Revenue consistency
- Investor industry conflicts
- Industry coverage
- Minimum structural match coverage

The validator complements the canonical Pydantic models in `backend/app/models/`. It does not replace backend validation.

## Data safety

Every company, investor, portfolio, metric, and investment thesis is fictional. The records must never be represented as real fundraising opportunities, verified investor preferences, financial advice, or completed due diligence.

Do not add private contact information, confidential pitch material, or scraped personal data. Generated or temporary datasets belong in `data/generated/`, which is ignored by Git.

