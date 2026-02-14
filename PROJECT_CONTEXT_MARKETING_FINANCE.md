# PROJECT_CONTEXT.md — Full System Narrative

*Internal architecture review. Reverse-engineered from repository; no hallucination. Unclear items marked "Cannot infer from repo."*

---

## 1. Project Overview

**What problem does this system solve?**  
It turns raw paid-ad data (Google Ads and Meta Ads) into finance-grade KPIs so that budget allocation across channels and campaigns can be decided on LTV, CAC, payback, and net value—not just spend and ROAS.

**Who is the intended user?**  
Finance and strategy teams (and possibly growth/marketing) who need to compare channels and campaigns on contribution margin, payback month, LTV/CAC, and net value created.

**What decision(s) does this system support?**  
- Where to shift ad budget (e.g. README recommendation: shift 10–15% from Google Search to Meta and YouTube).  
- Which channels/campaigns to scale or cut based on LTV/CAC, payback month, and a derived **priority score**: `(LTV/CAC - 1) / payback_month`.  
- Campaign-level P&L (spend, ROAS, CAC, LTV dollars, net value created) for reporting and planning.

**Revenue-generating, infrastructure, research, or internal tooling?**  
**Internal tooling / decision support.** It does not process payments or book revenue; it supports planning and allocation decisions.

**How does this repo fit into the broader portfolio?**  
Cannot infer from repo. README references a "Mode Analytics dashboard" and a PDF report (`reports/Marketing_Finance_Dashboard.pdf`); the repo contains no Mode config, no reports folder, and no references to other systems. Likely this repo is the **single source of truth for the marketing–finance pipeline** that feeds a downstream BI tool (Mode) and possibly other consumers.

---

## 2. Design Intent

**Philosophy**  
- **Correctness-first for finance logic:** Cohort LTV, contribution margin, payback, and net value are computed in SQL with explicit formulas; metrics are documented in `data_dictionary.metrics`.  
- **Unified semantics:** One consolidated ad daily layer (`stg.ads_daily`) with standardized column names; Meta’s `purchases`/`purchase_value` mapped to `conversions`/`conversion_value`.  
- **Assumption-driven:** Retention, ARPU, and finance drivers (margin, refund, fees, variable cost) are first-class inputs in `assumptions.*`; the pipeline is built to swap assumptions without changing view logic.  
- **Reporting over real-time:** Views are defined in SQL and executed on read; no streaming or event pipeline. Optimized for periodic refresh and dashboards, not sub-second latency.

**Tradeoffs**  
- **Views, not materialized tables:** All `stg.*` objects are views. Freshness and cost depend on Supabase/Postgres performance on each query; no incremental or partitioned materialization in repo.  
- **Manual / script-based orchestration:** No DAG, no scheduler in repo. Order of execution is implied (001 → 002 → 003 → 004 → 005); run locally or via ad-hoc scripts.  
- **Channel-keyed assumptions:** Finance and LTV logic are joined by `channel`. New channels require rows in `assumptions.finance`; otherwise LEFT JOIN yields NULLs and downstream math can break.  
- **Single retention/ARPU curve:** `assumptions.retention` and `assumptions.arpu` are global (no channel dimension). All channels share the same retention curve and ARPU pattern (e.g. flat $50 in `arpu_template.csv`).

**Where the system is opinionated**  
- Cohort = calendar month (`date_trunc('month', date)`).  
- LTV = sum of contribution margin per customer over the defined horizon (retention/ARPU months).  
- Payback = first month index where cumulative CM per customer ≥ CAC.  
- Priority score = `(LTV/CAC - 1) / payback_month`; used for ranking channels.  
- Campaign-level P&L reuses cohort-level LTV/CAC by joining on (month, channel).

---

## 3. Architecture Overview

**Runtime environment**  
Local (or any machine with Python and network access to Supabase). Scripts are run manually; no serverless, no containerization, no orchestration in repo.

**Data storage**  
- **Postgres (Supabase):** All persistent state.  
  - **Schemas:** `raw` (ads tables), `assumptions` (finance, retention, arpu), `stg` (views only), `data_dictionary` (metadata tables).  
  - **raw:** `raw.google_ads_daily`, `raw.meta_ads_daily` — base tables, loaded via pandas `to_sql(..., if_exists='replace')`.  
  - **assumptions:** `assumptions.finance`, `assumptions.retention`, `assumptions.arpu` — loaded from CSV or from generator scripts with `if_exists='replace'`.  
- **Files:** CSVs under `data/raw/`, `data/assumptions/`; generator scripts under `data/generator/` (note: `data/generator` is in `.gitignore`, so generator code may be missing in some clones).

**Compute**  
- **Python 3 + SQLAlchemy:** Scripts in `sql/*.py` and `supabase/*.py` create/replace views or push data using a single connection string from `.env`.  
- **Postgres:** All transforms are view definitions; compute happens at query time when dashboards or ad-hoc queries hit the views.

**Frontend / backend**  
No frontend in repo. Backend = Supabase (Postgres) + Python one-off scripts. README states that "Mode Analytics dashboard" consumes the data; integration and RLS are not in repo.

**CI/CD**  
None in repo. No GitHub Actions, no tests, no automated deploy.

**Text diagram of the system**

```
CSVs (data/raw/, data/assumptions/)
       │
       ▼
Python scripts (data_generator.py, finance_assumptions.py, retention_curves.py)
       │  → to_sql(..., if_exists='replace')
       ▼
Supabase Postgres
  ├── raw.google_ads_daily, raw.meta_ads_daily
  ├── assumptions.finance, assumptions.retention, assumptions.arpu
  └── stg.* (views only, created by sql/001–005)
       │
       ├── 001 → stg.ads_daily (UNION raw Google + Meta)
       ├── 002 → stg.monthly_channel_summary (cohort, channel, CAC)
       ├── 003 → stg.monthly_cohorts (retention × ARPU × finance → CM, cum_cm_per_customer_cohort)
       ├── 004 → stg.ltv_cac (LTV, payback_month, priority_score, channel_rank)
       └── 005 → stg.channel_campaign_monthly_pnl (campaign × month: spend, ROAS, CAC, LTV $, net value)
       │
       ▼
Mode Analytics (external) / PDF reports (path referenced in README; folder not in repo)
```

**Credentials**  
`supabase/credentials.py` reads `user`, `password`, `host`, `port`, `database` from `.env` (dotenv). `.env` is gitignored. No distinction between dev/staging/prod in repo.

---

## 4. Data Model & Flow

**Raw data sources**  
- **Google:** `data/raw/google_ads_daily.csv` — columns include date, customer_id, campaign_id, ad_id, network, device, channel, spend, conversions, conversion_value, new_customers, repeat_orders.  
- **Meta:** `data/raw/meta_ads_daily.csv` — similar, with purchases → conversions, purchase_value → conversion_value in the view.  
- **Assumptions:** `data/assumptions/finance_drivers.csv` (channel, gross_margin_pct, variable_cost_per_order, payment_processing_fee_pct, refund_rate_pct), `retention_template.csv` (month_index, retention_rate_t), `arpu_template.csv` (month_index, arpu_t).

**Transform layers**  
- **Staging (stg):**  
  - **stg.ads_daily:** Union of raw Google and Meta; standardized columns (date, channel, campaign_id, ad_id, spend, new_customers, conversions, conversion_value).  
  - **stg.monthly_channel_summary:** One row per (cohort, channel); spend, new_customers, CAC = spend/new_customers (NULL if no new_customers).  
  - **stg.monthly_cohorts:** Per (cohort, channel, month_index): active_customers, revenue, refunds, net_revenue, cogs, gross_profit, payment_fees, variable_costs, contribution_margin, cm_per_customer, cum_cm_per_customer_cohort. Uses assumptions.finance (by channel), assumptions.retention, assumptions.arpu.  
  - **stg.ltv_cac:** Per (cohort, channel): ltv_per_customer, cac, ltv_to_cac, payback_month, horizon_months, priority_score, channel_rank.  
  - **stg.channel_campaign_monthly_pnl:** Per (month, channel, campaign_id): spend, attributed_revenue, roas, new_customers, cac_campaign, ltv_per_customer, ltv_dollars, net_value_created, plus cohort-level cac_cohort, ltv_to_cac, payback_month, priority_score.

**Ledger or accounting logic**  
Not a general ledger. The pipeline implements a **contribution-margin and LTV model**:  
- Revenue and refunds from ARPU × retention; net_revenue after refunds; gross_profit = net_revenue × gross_margin_pct; contribution_margin = gross_profit − payment_fees − variable_costs.  
- LTV = sum of cm_per_customer over the retention/ARPU horizon. No double-entry; this is P&L-style attribution for marketing.

**Replace vs append**  
- **Raw and assumptions:** All loads use `if_exists='replace'`. Full replace each run; no append or SCD.  
- **Views:** `CREATE OR REPLACE VIEW`; no history, always current definition.

**Idempotency**  
- Re-running 001–005 is idempotent for view definitions.  
- Re-running data loads overwrites tables; idempotent in the sense “same input → same table state” but not incremental.

**Validation checks**  
None in repo. No dbt, no assertions, no row-count or uniqueness checks. Division-by-zero is avoided in SQL with `CASE WHEN new_customers > 0 THEN ... ELSE NULL` and `WHEN cac > 0`; no formal data-quality or invariant tests.

**dbt**  
Not present. No model layers, no dbt tests, no docs. Transforms are pure SQL in Python strings, executed via SQLAlchemy.

---

## 5. Core Business Logic

**What calculations matter**  
- **CAC:** spend / new_customers at cohort×channel and at campaign×month.  
- **Contribution margin (per customer, per month):** (net_revenue × gross_margin_pct) − payment_fees − variable_costs, with net_revenue = revenue × (1 − refund_rate_pct), revenue = new_customers × retention_rate × arpu.  
- **LTV per customer:** Sum of cm_per_customer over all month_index in the retention/ARPU horizon.  
- **Payback month:** First month_index where cumulative cm_per_customer ≥ CAC.  
- **LTV/CAC:** ltv_per_customer / cac.  
- **Priority score:** (LTV/CAC − 1) / payback_month; used to rank channels (higher = better).  
- **Net value created (campaign):** new_customers × ltv_per_customer − spend.  
- **ROAS (campaign):** attributed_revenue / spend.

**Assumptions embedded**  
- One retention curve and one ARPU series for all channels (flat $50 in repo).  
- Finance parameters (margin, refund, fees, variable cost) per channel from `assumptions.finance`; no DEFAULT fallback in the view (LEFT JOIN), so missing channel → NULLs.  
- Cohort = calendar month; LTV and payback are based on cohort-month and month_index.  
- Campaign-level LTV is inherited from cohort (month, channel); no campaign-specific retention or ARPU.

**Decisions that depend on this logic**  
- Budget reallocation across channels (e.g. from Search to Meta/YouTube).  
- Campaign prioritization and kill/scale decisions.  
- Reporting to finance on CAC, LTV, payback, and net value by channel and campaign.

---

## 6. Security & Risk Controls

**Secrets**  
Stored in `.env` (user, password, host, port, database); loaded by `supabase/credentials.py`. No vault, no rotation, no distinction by environment. Connection string is built with `sslmode=require`.

**Environment separation**  
Cannot infer from repo. Single `.env`; no dev/stage/prod branching or separate configs.

**Privilege boundaries**  
Scripts run with whatever credentials are in `.env`; they need DDL (CREATE/REPLACE VIEW, CREATE TABLE) and read/write to raw and assumptions. No RLS or role definitions in repo; Supabase may enforce additional policies not visible here.

**Data retention**  
Not specified. Raw and assumptions are fully replaced on load; no purge or retention logic in repo.

**Where the system could break**  
- **Missing or wrong channel in assumptions.finance:** New or renamed channel → NULL finance columns → invalid CM/LTV.  
- **Zero new_customers:** CAC and related metrics NULL; no crash but possible misinterpretation.  
- **Payback never reached:** Horizon may be shorter than payback; `payback_month` NULL, priority_score NULL.  
- **Credentials or network:** Wrong/missing `.env` or Supabase unreachable → all scripts fail.  
- **View order:** Dropping views (e.g. via `manage_views.py`) must respect dependencies (005 → 004 → 003 → 002 → 001); recreate in reverse order (001 → 005).

**Known failure modes**  
- `manage_views.py` drops views in dependency order (005 first), but does not recreate them; a separate run of 001–005 is required.  
- `drop_table.py` is a generic template (schema_name, table_name) and can drop any table if parameters are changed; high risk if used without care.  
- Generator scripts under `data/generator` are gitignored; if only the repo is deployed without that folder, raw/assumptions load steps are undefined unless CSVs are loaded by another process.

---

## 7. Operational Workflows

**How data gets refreshed**  
1. **Raw:** Run `data/generator/data_generator.py` to regenerate CSVs and push `google_ads_daily`, `meta_ads_daily` to `raw` with `to_sql(..., if_exists='replace')`. In production, real data likely replaces this with an export/ETL into `raw` (not in repo).  
2. **Assumptions:** Run `data/generator/finance_assumptions.py` and `data/generator/retention_curves.py` to write CSVs and push `assumptions.finance`, `assumptions.retention`, `assumptions.arpu`.  
3. **Views:** Run `sql/001_consolidated_ads_daily.py` through `sql/005_channeL_campaign_monthly_pnl.py` in order to create/replace stg views.  
4. **Data dictionary:** Optionally run `supabase/data_dictionary.py` and `supabase/metrics_dictionary.py` to create/refresh `data_dictionary` tables.

**Manual steps**  
- Ensure `.env` is present and correct.  
- Run Python from repo root (or adjust paths); generator scripts use relative paths (e.g. `../raw/`, `../assumptions/`).  
- Run 001–005 after any view definition change; after dropping views with `manage_views.py`, re-run 001–005 to recreate.  
- If using generated data, run generator scripts before view pipeline.

**Script roles**  
- **sql/001–005:** Deploy view layer only; no data movement.  
- **data/generator/data_generator.py:** Generate sample Google + Meta data, write CSVs, push to `raw`.  
- **data/generator/finance_assumptions.py:** Create finance_drivers CSV and push `assumptions.finance`.  
- **data/generator/retention_curves.py:** Create retention and ARPU CSVs and push `assumptions.retention`, `assumptions.arpu`.  
- **supabase/manage_views.py:** Drop all stg views (teardown).  
- **supabase/drop_table.py:** Generic table drop (schema/table name parameters).  
- **supabase/data_dictionary.py / metrics_dictionary.py:** Create data_dictionary schema and metadata tables.

**Scheduling**  
No cron, no scheduler, no CI in repo. Refresh is assumed to be manual or handled outside the repo.

**One-time / sandbox**  
Generator scripts are for synthetic data; `drop_table.py` is a generic utility. No other one-off or sandbox scripts evident.

---

## 8. Testing & Validation Philosophy

**What is validated**  
- **Documentation:** Column semantics and formulas are documented in `data_dictionary.metrics` and `data_dictionary.google_ads`.  
- **SQL defensiveness:** Division by zero avoided with CASE/WHEN for CAC, LTV/CAC, ROAS, cm_per_customer.

**What is not validated**  
- No unit tests, no integration tests, no dbt tests.  
- No checks for referential integrity (e.g. channel in raw exists in assumptions.finance).  
- No row-count, uniqueness, or freshness checks.  
- No reconciliation to a source system or ledger.

**Where silent failures could occur**  
- New channel in raw but not in assumptions.finance → NULL finance fields → wrong or NULL CM/LTV.  
- Bad or empty raw data → zeros or NULLs in KPIs with no alert.  
- Typo in channel name (e.g. "Meta Ads" vs "Meta ads") → LEFT JOIN miss → same as above.  
- Wrong order of script execution (e.g. 003 before 002) → view creation fails with missing dependency.

**Financial invariants**  
Not enforced by code. No assertion that, for example, total contribution margin reconciles to a control total, or that LTV/CAC is consistent with a separate model. Manual or external review is assumed.

---

## 9. Strengths of the System

- **Clear separation of raw, assumptions, and staging:** Raw and assumptions are explicit; stg is view-only, so one place to change logic.  
- **Unified ad model:** Single daily ad view with consistent columns; Meta/Google differences handled once in 001.  
- **Transparent business logic:** Formulas for CAC, CM, LTV, payback, priority score, and net value are in SQL and documented in metrics dictionary; finance teams can trace numbers.  
- **Assumption-driven design:** Retention, ARPU, and finance drivers are tables; changing curves or margins does not require editing view text (only data).  
- **Stable view API:** 001–005 use CREATE OR REPLACE VIEW; downstream (e.g. Mode) can rely on stable view names and column names.  
- **Single tech stack for pipeline:** Python + SQLAlchemy + Postgres; easy to run locally or on a dev machine.  
- **Explicit priority score:** Encodes both return (LTV/CAC) and speed (payback) for channel ranking.

---

## 10. Fragility & Technical Debt

- **No automated tests:** Logic changes can regress without detection.  
- **Views only:** Heavy or complex queries hit full view stack on each run; no materialization or incremental strategy.  
- **No schema lifecycle in repo:** Creation of `raw`, `stg`, `assumptions` schemas not in repo; depends on external or manual setup.  
- **Channel coupling:** New channels require manual rows in `assumptions.finance`; no DEFAULT fallback in SQL.  
- **Single retention/ARPU for all channels:** Limits differentiation of channel quality in LTV.  
- **Generator in .gitignore:** `data/generator` ignored; reproduction of raw/assumptions load may rely on external or lost scripts.  
- **Typo in filename:** `005_channeL_campaign_monthly_pnl.py` (capital L); minor but can break case-sensitive runners or scripts that glob by name.  
- **Credentials in env only:** Single .env; no separation of environments or secret rotation.  
- **manage_views.py only drops:** Teardown without rebuild; easy to leave DB without views after a drop.  
- **drop_table.py is dangerous:** Generic drop by (schema, table) could drop production tables if parameters are set incorrectly.

---

## 11. If This Repo Disappeared Tomorrow

- **Capability lost:** The only codified pipeline from Google/Meta ad data to LTV, CAC, payback, priority score, and campaign P&L would be lost. Mode (or any consumer) would have no updated view definitions or documented logic.  
- **Decisions degraded:** Finance and strategy would lose the single place that turns ad spend and new_customers into contribution margin, LTV/CAC, and net value by channel/campaign; re-creating it would require reverse-engineering from docs or memory.  
- **Systems that would break:** Any dashboard or report that queries `stg.*` views on this Supabase project would continue to run on existing view definitions until the DB is recreated or views are dropped; once the DB is reset or views are removed, those reports would break until the pipeline is reimplemented.  
- **Recovery:** Logic is entirely in the repo (SQL in 001–005, assumption shapes in CSV and generator scripts); recovery is possible from a clone plus .env and Supabase access, but orchestration and any external load into `raw` would need to be re-established.

---

## 12. One-Paragraph Executive Summary

This repository is the **marketing–finance pipeline** that turns Google and Meta ad data into finance KPIs (CAC, LTV, payback month, LTV/CAC, net value created, and a channel priority score). Raw and assumption data are loaded into Supabase (Postgres); five SQL views compute a unified ad daily table, monthly cohort summaries, contribution margin and LTV by cohort, and campaign-level P&L. The system is **internal decision-support**: it informs where to allocate ad budget and which channels or campaigns to scale, and is designed to feed a Mode Analytics dashboard and similar reporting. It is **correctness-oriented** and **assumption-driven** but has **no tests or CI**, depends on **manual run order** and **correct channel configuration** in assumptions, and leaves **schema creation and production data load** outside the repo. If lost, the organization would lose the single codified definition of how ad spend translates to LTV and payback until the pipeline is recreated from this logic.
