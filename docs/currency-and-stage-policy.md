# Currency and Funding-Stage Policy

## Purpose

VentureMatch accepts financial amounts in a user's familiar currency while comparing every candidate consistently. It also distinguishes an investor's normal funding stages from stages they are willing to explore.

## Currency handling

The MVP supports:

- US dollar (`USD`)
- Euro (`EUR`)
- Turkish lira (`TRY`)
- Nigerian naira (`NGN`)
- Ghanaian cedi (`GHS`)
- Kenyan shilling (`KES`)
- South African rand (`ZAR`)
- Egyptian pound (`EGP`)
- UAE dirham (`AED`)

The submitted amount and currency remain the source record. Before ticket-size filtering or scoring, the backend converts the amount to the FX snapshot's base currency, currently USD. The normalized value is derived data and must not replace the original value.

```json
{
  "original": { "amount": 1200000000, "currency": "NGN" },
  "normalized_amount": "750000.00",
  "normalized_currency": "USD",
  "exchange_rate": "0.000625",
  "rate_source": "synthetic_hackathon_demo",
  "rate_timestamp": "2026-10-12T00:00:00Z",
  "is_estimate": true
}
```

Decimal values are serialized as strings so clients do not silently lose precision.

### Demo and production rates

`data/fx_rates.demo.json` contains fixed, synthetic rates for reproducible development and demonstration. They are estimates created for this fictional dataset and must not be described as live, historical, or suitable for a real financial decision.

A production version should retrieve rates from an attributable provider, record its name and timestamp, cache the snapshot used for each matching run, and display the conversion as an estimate. If no supported or sufficiently recent rate is available, the system should request a supported currency rather than guess.

## Funding-stage flexibility

An investor has `preferred_stages` for its usual mandate and one of three policies:

| Policy | Behaviour |
|---|---|
| `strict` | Only preferred stages are eligible. |
| `adjacent` | Preferred stages are core matches; explicitly listed neighbouring stages may appear as exploration matches. |
| `open` | Any non-preferred stage may be explored, subject to the remaining constraints. |

For `adjacent`, every `exploratory_stages` entry must be directly next to at least one preferred stage in the ordered funding lifecycle. Preferred and exploratory stages cannot overlap. `strict` and `open` do not use an explicit exploratory list.

The matching engine should classify candidates as:

| State | Meaning |
|---|---|
| `core_eligible` | The business is within the investor's preferred stages and passes the other hard constraints. |
| `exploration_eligible` | The stage is outside the normal mandate but permitted by the investor's flexibility policy; the deviation must be visible. |
| `ineligible` | The candidate violates the stage policy or another hard constraint. |

`include_exploration_matches` controls whether a search returns the second group. It defaults to `true`, but exploration matches must be labelled and ranked separately enough that users do not mistake them for normal mandate fits.

## Interface guidance

- Let users select their currency instead of asking them to calculate a conversion.
- Show both the submitted amount and its approximate normalized equivalent.
- Show the FX source and timestamp wherever the converted amount affects eligibility.
- Present normal-stage matches first and add a clear "outside usual stage" badge to exploration matches.
- Never let stage exploration override ticket size, excluded industries, revenue requirements, or other hard constraints.
