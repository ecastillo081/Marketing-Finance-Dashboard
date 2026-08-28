# Marketing Investment Economics

Self-directed Marketing Finance portfolio project using synthetic data.

**Business question:** How should Finance evaluate where to test incremental marketing investment when channel acquisition costs, attributed returns, and modeled customer economics differ?

This is not a live marketing account, not employer/client data, and not a recommendation for any real company.

## Architecture

```
data/raw + data/assumptions
        → DuckDB
        → SQL finance models
        → validation controls
        → sensitivity analysis
        → local charts / PDF
```

- **Canonical synthetic fixtures:** `data/raw/google_ads_daily.csv`, `data/raw/meta_ads_daily.csv`
- **Modeled assumptions:** `data/assumptions/arpu_template.csv`, `retention_template.csv`, `finance_drivers.csv`
- **Runtime:** local DuckDB only

No credentials, no environment variables, no Supabase, no Mode Analytics, and no cloud database are required.

The committed CSVs are the source of truth for the public build. A local synthetic generator (if present) is gitignored and is **not** part of the runtime.

## Reproduce

```bash
python -m pip install -r requirements.txt
python build.py
python build.py --report
```

- `python build.py` — load fixtures, build models, validate, write analytical CSVs and sensitivity results (no browser)
- `python build.py --report` — same, plus charts and the 3-page case study PDF (Chrome or Edge required)

**Case study PDF:** [case-study/Marketing_Investment_Economics_Case_Study.pdf](case-study/Marketing_Investment_Economics_Case_Study.pdf)

**Repository:** [https://github.com/ecastillo081/Marketing-Finance-Dashboard](https://github.com/ecastillo081/Marketing-Finance-Dashboard)

## Observed vs modeled

| Kind | Fields |
|---|---|
| Synthetic observed fixtures | spend, attributed new-customer proxy, platform conversions / purchases, platform-attributed conversion value, blended CAC, platform-attributed ROAS |
| Modeled assumptions | shared retention curve, flat $50 ARPU, channel-specific gross margin / refund / variable cost, 2.9% payment fee |
| Modeled outputs | active customers, contribution margin, lifetime contribution, payback, weighted lifetime contribution / CAC |

Every acquisition cohort is projected **38 months forward**. That is a unit-economics model, not realized historical cohort performance.

## Metric definitions

**Attributed new-customer proxy** — `new_customers` from the synthetic fixtures. For Meta, this field was generated from a separate conversions field and can exceed purchases; it is not CRM identity-matched customers.

**Blended CAC** — advertising spend ÷ attributed new-customer proxy at the same calendar month × channel (portfolio / channel totals use total spend ÷ total attributed new customers).

**Platform-attributed ROAS** — platform-attributed conversion value ÷ spend. Not profit, not contribution return, and not causal incremental return.

**Modeled contribution margin** — after refunds, product gross margin is applied to net revenue; payment fees and variable fulfillment-like costs are then subtracted.

**Modeled lifetime contribution per acquired customer** — sum of modeled contribution margin per acquired customer over the 38-month horizon.

**Weighted modeled lifetime contribution / CAC** — (attributed new customers × modeled lifetime contribution per customer) ÷ spend, which equals modeled lifetime contribution per customer ÷ blended CAC at channel level.

**Modeled payback month** — first month where cumulative modeled contribution margin per acquired customer ≥ blended CAC. **Payback month 0 = acquisition month.**

## Sensitivity scenarios

Downside cases recompute the contribution waterfall (they do not apply cosmetic percentages to the ratio):

- CAC +20% (customer contribution held constant)
- ARPU −20% ($50 → $40)
- Retention downside (month 0 stays 1.00; months ≥1 × 0.80)
- Gross margin −5 percentage points

**Key result:** Search is the most fragile. Under ARPU −20%, Search weighted modeled CM/CAC falls to **1.05x** with modeled payback month **29**. These are synthetic-case sensitivities, not a real-company forecast.

## Validated baseline results

Portfolio-weighted channel economics from the local build:

| Channel | Spend | Mix | Blended CAC | Platform-attributed ROAS | Weighted modeled CM / CAC | Modeled payback month |
|---|---:|---:|---:|---:|---:|---:|
| Meta Ads | $2,836,272.12 | 90.1% | $47.75 | 2.404x | 2.482x | 4 |
| Google Ads - Search | $251,539.45 | 8.0% | $79.10 | 2.938x | 1.436x | 13 |
| Google Ads - YouTube | $58,598.69 | 1.9% | $40.84 | 5.628x | 3.267x | 2 |

## Decision conclusion

Average modeled economics identify where incremental testing may deserve attention, but they do not establish marginal scalability.

- Search has the least downside cushion in the modeled economics.
- YouTube has the strongest baseline modeled economics but only 1.9% of fixture spend, so its ability to absorb incremental budget is unproven.
- Meta combines scale with stronger modeled economics than Search, but marginal returns remain unobserved.

Finance still needs marginal CAC, incremental contribution, capacity/saturation, attribution overlap, and realized customer quality before any structural reallocation.

## Fixture limitations

- Advertising-performance data is synthetic and sparsely sampled (not a continuous daily panel).
- Platform-attributed metrics are not causal incrementality.
- Retention and ARPU are shared modeled assumptions.
- Google campaign IDs/names are randomly crossed with Search and YouTube in the fixtures; channel is the analytical grain.
- There is no marginal-response or saturation evidence in this dataset.
