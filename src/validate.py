"""Validation controls for the local Marketing Finance build."""

from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any

import duckdb
import pandas as pd


MONEY_TOL = 0.01
RATIO_TOL = 1e-8

# Fixture control expectations recomputed in the Phase 1 audit.
# These are source-tie-out constants, not business conclusions.
EXPECTED = {
    "google_rows": 100,
    "meta_rows": 100,
    "total_spend": 3_146_410.26,
    "total_new_customers": 64_017,
    "total_platform_conversions": 98_460,
    "total_platform_attributed_value": 7_887_101.71,
    "channel_spend": {
        "Google Ads - Search": 251_539.45,
        "Google Ads - YouTube": 58_598.69,
        "Meta Ads": 2_836_272.12,
    },
    "channel_new_customers": {
        "Google Ads - Search": 3_180,
        "Google Ads - YouTube": 1_435,
        "Meta Ads": 59_402,
    },
    "arpu_rows": 38,
    "retention_rows": 38,
    "arpu_value": 50.0,
}


@dataclass
class Check:
    check_id: str
    group: str
    status: str
    expected: str
    actual: str
    detail: str


def _money_eq(a: float, b: float, tol: float = MONEY_TOL) -> bool:
    return abs(float(a) - float(b)) <= tol


def _float_eq(a: float, b: float, tol: float = RATIO_TOL) -> bool:
    return abs(float(a) - float(b)) <= max(tol, abs(float(b)) * 1e-9)


def _scalar(con: duckdb.DuckDBPyConnection, sql: str) -> Any:
    return con.execute(sql).fetchone()[0]


def _df(con: duckdb.DuckDBPyConnection, sql: str) -> pd.DataFrame:
    return con.execute(sql).df()


def run_validations(con: duckdb.DuckDBPyConnection) -> list[Check]:
    checks: list[Check] = []
    checks.extend(_raw_input_checks(con))
    checks.extend(_assumption_checks(con))
    checks.extend(_consolidation_checks(con))
    checks.extend(_channel_total_checks(con))
    checks.extend(_monthly_rollup_checks(con))
    checks.extend(_cac_roas_checks(con))
    checks.extend(_cohort_identity_checks(con))
    checks.extend(_lifetime_payback_checks(con))
    checks.extend(_info_checks(con))
    return checks


def _add(
    checks: list[Check],
    check_id: str,
    group: str,
    ok: bool,
    expected: Any,
    actual: Any,
    detail: str = "",
    status: str | None = None,
) -> None:
    checks.append(
        Check(
            check_id=check_id,
            group=group,
            status=status or ("PASS" if ok else "FAIL"),
            expected=str(expected),
            actual=str(actual),
            detail=detail,
        )
    )


def _raw_input_checks(con: duckdb.DuckDBPyConnection) -> list[Check]:
    checks: list[Check] = []
    google_rows = _scalar(con, "SELECT COUNT(*) FROM raw.google_ads_daily")
    meta_rows = _scalar(con, "SELECT COUNT(*) FROM raw.meta_ads_daily")
    _add(checks, "raw.google_rows", "raw", google_rows == EXPECTED["google_rows"], EXPECTED["google_rows"], google_rows)
    _add(checks, "raw.meta_rows", "raw", meta_rows == EXPECTED["meta_rows"], EXPECTED["meta_rows"], meta_rows)

    google_neg = _scalar(con, "SELECT COUNT(*) FROM raw.google_ads_daily WHERE spend < 0")
    meta_neg = _scalar(con, "SELECT COUNT(*) FROM raw.meta_ads_daily WHERE spend < 0")
    _add(checks, "raw.google_nonnegative_spend", "raw", google_neg == 0, 0, google_neg)
    _add(checks, "raw.meta_nonnegative_spend", "raw", meta_neg == 0, 0, meta_neg)

    google_bad_dates = _scalar(con, "SELECT COUNT(*) FROM raw.google_ads_daily WHERE TRY_CAST(date AS DATE) IS NULL")
    meta_bad_dates = _scalar(con, "SELECT COUNT(*) FROM raw.meta_ads_daily WHERE TRY_CAST(date AS DATE) IS NULL")
    _add(checks, "raw.google_valid_dates", "raw", google_bad_dates == 0, 0, google_bad_dates)
    _add(checks, "raw.meta_valid_dates", "raw", meta_bad_dates == 0, 0, meta_bad_dates)

    google_dups = _scalar(
        con,
        """
        SELECT COUNT(*) FROM (
            SELECT date, campaign_id, ad_id, network, device, COUNT(*) AS n
            FROM raw.google_ads_daily
            GROUP BY 1,2,3,4,5
            HAVING COUNT(*) > 1
        )
        """,
    )
    meta_dups = _scalar(
        con,
        """
        SELECT COUNT(*) FROM (
            SELECT date, campaign_id, ad_id, COUNT(*) AS n
            FROM raw.meta_ads_daily
            GROUP BY 1,2,3
            HAVING COUNT(*) > 1
        )
        """,
    )
    _add(checks, "raw.google_unique_grain", "raw", google_dups == 0, 0, google_dups, "grain: date, campaign_id, ad_id, network, device")
    _add(checks, "raw.meta_unique_grain", "raw", meta_dups == 0, 0, meta_dups, "grain: date, campaign_id, ad_id")

    google_nulls = _scalar(
        con,
        """
        SELECT COUNT(*) FROM raw.google_ads_daily
        WHERE date IS NULL OR channel IS NULL OR campaign_id IS NULL OR ad_id IS NULL
           OR spend IS NULL OR new_customers IS NULL OR conversions IS NULL OR conversion_value IS NULL
        """,
    )
    meta_nulls = _scalar(
        con,
        """
        SELECT COUNT(*) FROM raw.meta_ads_daily
        WHERE date IS NULL OR channel IS NULL OR campaign_id IS NULL OR ad_id IS NULL
           OR spend IS NULL OR new_customers IS NULL OR purchases IS NULL OR purchase_value IS NULL
           OR conversions IS NULL
        """,
    )
    _add(checks, "raw.google_required_fields", "raw", google_nulls == 0, 0, google_nulls)
    _add(checks, "raw.meta_required_fields", "raw", meta_nulls == 0, 0, meta_nulls)
    return checks


def _assumption_checks(con: duckdb.DuckDBPyConnection) -> list[Check]:
    checks: list[Check] = []
    arpu = _df(con, "SELECT * FROM assumptions.arpu ORDER BY month_index")
    ret = _df(con, "SELECT * FROM assumptions.retention ORDER BY month_index")
    fin = _df(con, "SELECT * FROM assumptions.finance")

    _add(checks, "assumptions.arpu_row_count", "assumptions", len(arpu) == EXPECTED["arpu_rows"], EXPECTED["arpu_rows"], len(arpu))
    _add(
        checks,
        "assumptions.arpu_month_index",
        "assumptions",
        list(arpu["month_index"]) == list(range(38)),
        "0..37",
        f"{int(arpu['month_index'].min())}..{int(arpu['month_index'].max())}",
    )
    arpu_ok = bool((arpu["arpu_t"] == EXPECTED["arpu_value"]).all() and (arpu["arpu_t"] >= 0).all())
    _add(checks, "assumptions.arpu_constant_50", "assumptions", arpu_ok, 50.0, arpu["arpu_t"].unique().tolist())

    _add(checks, "assumptions.retention_row_count", "assumptions", len(ret) == EXPECTED["retention_rows"], EXPECTED["retention_rows"], len(ret))
    _add(
        checks,
        "assumptions.retention_month_index",
        "assumptions",
        list(ret["month_index"]) == list(range(38)),
        "0..37",
        f"{int(ret['month_index'].min())}..{int(ret['month_index'].max())}",
    )
    start_ok = _float_eq(ret["retention_rate_t"].iloc[0], 1.0)
    end_ok = _float_eq(ret["retention_rate_t"].iloc[-1], 0.01)
    bounds_ok = bool((ret["retention_rate_t"] <= 1.0).all() and (ret["retention_rate_t"] >= 0.0).all())
    nonincreasing = bool(ret["retention_rate_t"].is_monotonic_decreasing)
    _add(checks, "assumptions.retention_starts_at_1", "assumptions", start_ok, 1.0, float(ret["retention_rate_t"].iloc[0]))
    _add(checks, "assumptions.retention_ends_at_0_01", "assumptions", end_ok, 0.01, float(ret["retention_rate_t"].iloc[-1]))
    _add(checks, "assumptions.retention_bounds", "assumptions", bounds_ok, "0..1", f"min={ret['retention_rate_t'].min()} max={ret['retention_rate_t'].max()}")
    _add(checks, "assumptions.retention_nonincreasing", "assumptions", nonincreasing, True, nonincreasing)

    needed = {"Google Ads - Search", "Google Ads - YouTube", "Meta Ads"}
    present = set(fin["channel"])
    _add(checks, "assumptions.finance_required_channels", "assumptions", needed.issubset(present), sorted(needed), sorted(present))
    _add(
        checks,
        "assumptions.finance_default_present",
        "assumptions",
        "DEFAULT" in present,
        "DEFAULT row used as fallback only",
        "present" if "DEFAULT" in present else "missing",
        status="INFO",
    )
    return checks


def _consolidation_checks(con: duckdb.DuckDBPyConnection) -> list[Check]:
    checks: list[Check] = []
    row = _df(
        con,
        """
        SELECT
            SUM(spend) AS spend,
            SUM(new_customers) AS new_customers,
            SUM(platform_conversions) AS platform_conversions,
            SUM(platform_attributed_value) AS platform_attributed_value
        FROM stg.ads_daily
        """,
    ).iloc[0]

    google_spend = _scalar(con, "SELECT SUM(spend) FROM raw.google_ads_daily")
    meta_spend = _scalar(con, "SELECT SUM(spend) FROM raw.meta_ads_daily")
    google_nc = _scalar(con, "SELECT SUM(new_customers) FROM raw.google_ads_daily")
    meta_nc = _scalar(con, "SELECT SUM(new_customers) FROM raw.meta_ads_daily")
    google_conv = _scalar(con, "SELECT SUM(conversions) FROM raw.google_ads_daily")
    meta_purch = _scalar(con, "SELECT SUM(purchases) FROM raw.meta_ads_daily")
    google_val = _scalar(con, "SELECT SUM(conversion_value) FROM raw.google_ads_daily")
    meta_val = _scalar(con, "SELECT SUM(purchase_value) FROM raw.meta_ads_daily")

    _add(checks, "consol.total_spend_vs_fixture", "consolidation", _money_eq(row["spend"], EXPECTED["total_spend"]), EXPECTED["total_spend"], round(float(row["spend"]), 2))
    _add(checks, "consol.total_new_customers_vs_fixture", "consolidation", int(row["new_customers"]) == EXPECTED["total_new_customers"], EXPECTED["total_new_customers"], int(row["new_customers"]))
    _add(checks, "consol.total_platform_conversions_vs_fixture", "consolidation", int(row["platform_conversions"]) == EXPECTED["total_platform_conversions"], EXPECTED["total_platform_conversions"], int(row["platform_conversions"]))
    _add(checks, "consol.total_attributed_value_vs_fixture", "consolidation", _money_eq(row["platform_attributed_value"], EXPECTED["total_platform_attributed_value"]), EXPECTED["total_platform_attributed_value"], round(float(row["platform_attributed_value"]), 2))

    _add(checks, "consol.spend_ties_to_raw", "consolidation", _money_eq(row["spend"], google_spend + meta_spend), round(google_spend + meta_spend, 2), round(float(row["spend"]), 2))
    _add(checks, "consol.new_customers_tie_to_raw", "consolidation", int(row["new_customers"]) == int(google_nc + meta_nc), int(google_nc + meta_nc), int(row["new_customers"]))
    _add(checks, "consol.conversions_google_plus_meta_purchases", "consolidation", int(row["platform_conversions"]) == int(google_conv + meta_purch), int(google_conv + meta_purch), int(row["platform_conversions"]))
    _add(checks, "consol.value_google_plus_meta_purchase_value", "consolidation", _money_eq(row["platform_attributed_value"], google_val + meta_val), round(google_val + meta_val, 2), round(float(row["platform_attributed_value"]), 2))
    return checks


def _channel_total_checks(con: duckdb.DuckDBPyConnection) -> list[Check]:
    checks: list[Check] = []
    ch = _df(
        con,
        """
        SELECT channel, SUM(spend) AS spend, SUM(new_customers) AS new_customers
        FROM stg.ads_daily
        GROUP BY channel
        """,
    ).set_index("channel")
    for channel, expected_spend in EXPECTED["channel_spend"].items():
        actual = float(ch.loc[channel, "spend"])
        _add(checks, f"channel.spend.{channel}", "channel", _money_eq(actual, expected_spend), expected_spend, round(actual, 2))
    for channel, expected_nc in EXPECTED["channel_new_customers"].items():
        actual = int(ch.loc[channel, "new_customers"])
        _add(checks, f"channel.new_customers.{channel}", "channel", actual == expected_nc, expected_nc, actual)
    return checks


def _monthly_rollup_checks(con: duckdb.DuckDBPyConnection) -> list[Check]:
    checks: list[Check] = []
    daily = _df(
        con,
        """
        SELECT
            SUM(spend) AS spend,
            SUM(new_customers) AS new_customers,
            SUM(platform_conversions) AS platform_conversions,
            SUM(platform_attributed_value) AS platform_attributed_value
        FROM stg.ads_daily
        """,
    ).iloc[0]
    monthly = _df(
        con,
        """
        SELECT
            SUM(spend) AS spend,
            SUM(new_customers) AS new_customers,
            SUM(platform_conversions) AS platform_conversions,
            SUM(platform_attributed_value) AS platform_attributed_value
        FROM stg.monthly_channel_summary
        """,
    ).iloc[0]
    campaign = _df(
        con,
        """
        SELECT
            SUM(spend) AS spend,
            SUM(new_customers) AS new_customers,
            SUM(platform_conversions) AS platform_conversions,
            SUM(platform_attributed_value) AS platform_attributed_value
        FROM stg.campaign_reconciliation
        """,
    ).iloc[0]
    for col in ["spend", "new_customers", "platform_conversions", "platform_attributed_value"]:
        ok_m = _money_eq(daily[col], monthly[col]) if col in ("spend", "platform_attributed_value") else int(daily[col]) == int(monthly[col])
        ok_c = _money_eq(daily[col], campaign[col]) if col in ("spend", "platform_attributed_value") else int(daily[col]) == int(campaign[col])
        _add(checks, f"rollup.monthly.{col}", "rollup", ok_m, round(float(daily[col]), 2), round(float(monthly[col]), 2))
        _add(checks, f"rollup.campaign.{col}", "rollup", ok_c, round(float(daily[col]), 2), round(float(campaign[col]), 2), "campaign x channel grain; not for allocation")
    return checks


def _cac_roas_checks(con: duckdb.DuckDBPyConnection) -> list[Check]:
    checks: list[Check] = []
    cac_bad = _scalar(
        con,
        """
        SELECT COUNT(*) FROM stg.monthly_channel_summary
        WHERE new_customers > 0
          AND ABS(blended_cac - spend / new_customers) > 1e-8
        """,
    )
    cac_null = _scalar(
        con,
        """
        SELECT COUNT(*) FROM stg.monthly_channel_summary
        WHERE new_customers <= 0 AND blended_cac IS NOT NULL
        """,
    )
    roas_bad = _scalar(
        con,
        """
        SELECT COUNT(*) FROM stg.monthly_channel_summary
        WHERE spend > 0
          AND ABS(platform_attributed_roas - platform_attributed_value / spend) > 1e-8
        """,
    )
    _add(checks, "metrics.blended_cac_identity", "metrics", cac_bad == 0, 0, cac_bad)
    _add(checks, "metrics.blended_cac_null_when_no_customers", "metrics", cac_null == 0, 0, cac_null)
    _add(checks, "metrics.platform_attributed_roas_identity", "metrics", roas_bad == 0, 0, roas_bad)
    return checks


def _cohort_identity_checks(con: duckdb.DuckDBPyConnection) -> list[Check]:
    checks: list[Check] = []
    bad = _df(
        con,
        """
        SELECT COUNT(*) AS n FROM stg.monthly_cohorts
        WHERE ABS(modeled_active_customers - new_customers * assumed_retention_rate) > 1e-6
           OR ABS(modeled_gross_revenue - modeled_active_customers * assumed_arpu) > 1e-6
           OR ABS(modeled_refunds - modeled_gross_revenue * assumed_refund_rate_pct) > 1e-6
           OR ABS(modeled_net_revenue - (modeled_gross_revenue - modeled_refunds)) > 1e-6
           OR ABS(modeled_gross_profit - modeled_net_revenue * assumed_gross_margin_pct) > 1e-6
           OR ABS(modeled_cogs - modeled_net_revenue * (1 - assumed_gross_margin_pct)) > 1e-6
           OR ABS((modeled_gross_profit + modeled_cogs) - modeled_net_revenue) > 1e-6
           OR ABS(modeled_payment_fees - modeled_net_revenue * assumed_payment_processing_fee_pct) > 1e-6
           OR ABS(modeled_variable_costs - modeled_active_customers * assumed_variable_cost_per_order) > 1e-6
           OR ABS(
                modeled_contribution_margin
                - (modeled_gross_profit - modeled_payment_fees - modeled_variable_costs)
              ) > 1e-6
        """,
    ).iloc[0]["n"]
    _add(checks, "cohort.waterfall_identities", "cohort", int(bad) == 0, 0, int(bad), "GM treated as product margin before fees and variable fulfillment costs")

    horizon_bad = _scalar(
        con,
        """
        SELECT COUNT(*) FROM (
            SELECT cohort, channel, COUNT(*) AS n
            FROM stg.monthly_cohorts
            GROUP BY 1,2
            HAVING COUNT(*) <> 38
        )
        """,
    )
    _add(checks, "cohort.full_38_month_horizon", "cohort", horizon_bad == 0, 0, horizon_bad, "every cohort is forward-projected 38 months")

    cm_cust_bad = _scalar(
        con,
        """
        SELECT COUNT(*) FROM stg.monthly_cohorts
        WHERE new_customers > 0
          AND ABS(
                modeled_cm_per_acquired_customer
                - modeled_contribution_margin / new_customers
              ) > 1e-6
        """,
    )
    _add(checks, "cohort.cm_per_customer_identity", "cohort", cm_cust_bad == 0, 0, cm_cust_bad)

    cum_bad = _scalar(
        con,
        """
        WITH expected AS (
            SELECT
                cohort,
                channel,
                month_index,
                SUM(modeled_cm_per_acquired_customer) OVER (
                    PARTITION BY cohort, channel
                    ORDER BY month_index
                    ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
                ) AS expected_cum
            FROM stg.monthly_cohorts
        )
        SELECT COUNT(*)
        FROM expected e
        JOIN stg.monthly_cohorts c USING (cohort, channel, month_index)
        WHERE ABS(c.modeled_cum_cm_per_acquired_customer - e.expected_cum) > 1e-6
        """,
    )
    _add(checks, "cohort.cumulative_cm_identity", "cohort", cum_bad == 0, 0, cum_bad)

    # Search 2020-02 representative walkthrough from the audit.
    ex = _df(
        con,
        """
        SELECT *
        FROM stg.monthly_cohorts
        WHERE channel = 'Google Ads - Search'
          AND cohort = DATE '2020-02-01'
          AND month_index = 0
        """,
    )
    if len(ex) == 1:
        row = ex.iloc[0]
        ok = (
            int(row["new_customers"]) == 58
            and _money_eq(row["spend"], 4595.53)
            and _float_eq(row["assumed_retention_rate"], 1.0)
            and _float_eq(row["modeled_active_customers"], 58)
            and _money_eq(row["modeled_gross_revenue"], 2900)
        )
        _add(
            checks,
            "cohort.representative_search_2020_02_m0",
            "cohort",
            ok,
            "nc=58 spend=4595.53 m0 revenue=2900",
            f"nc={int(row['new_customers'])} spend={row['spend']} revenue={row['modeled_gross_revenue']}",
        )
    else:
        _add(checks, "cohort.representative_search_2020_02_m0", "cohort", False, "1 row", len(ex))
    return checks


def _lifetime_payback_checks(con: duckdb.DuckDBPyConnection) -> list[Check]:
    checks: list[Check] = []
    lifetime_bad = _scalar(
        con,
        """
        WITH summed AS (
            SELECT cohort, channel, SUM(modeled_cm_per_acquired_customer) AS expected_lt
            FROM stg.monthly_cohorts
            GROUP BY 1,2
        )
        SELECT COUNT(*)
        FROM summed s
        JOIN stg.unit_economics u USING (cohort, channel)
        WHERE ABS(u.modeled_lifetime_contribution_per_customer - s.expected_lt) > 1e-6
        """,
    )
    _add(checks, "unit.lifetime_equals_sum_of_monthly_cm", "unit_economics", lifetime_bad == 0, 0, lifetime_bad)

    ratio_bad = _scalar(
        con,
        """
        SELECT COUNT(*) FROM stg.unit_economics
        WHERE blended_cac > 0
          AND ABS(
                modeled_lifetime_contribution_to_cac
                - modeled_lifetime_contribution_per_customer / blended_cac
              ) > 1e-8
        """,
    )
    _add(checks, "unit.lifetime_to_cac_identity", "unit_economics", ratio_bad == 0, 0, ratio_bad)

    payback_bad = _scalar(
        con,
        """
        WITH expected AS (
            SELECT cohort, channel, MIN(month_index) AS expected_payback
            FROM stg.monthly_cohorts
            WHERE modeled_cum_cm_per_acquired_customer >= blended_cac
            GROUP BY 1,2
        )
        SELECT COUNT(*)
        FROM stg.unit_economics u
        LEFT JOIN expected e USING (cohort, channel)
        WHERE (u.modeled_payback_month_index IS DISTINCT FROM e.expected_payback)
        """,
    )
    _add(checks, "unit.payback_first_month_cum_cm_ge_cac", "unit_economics", payback_bad == 0, 0, payback_bad, "month_index 0 = acquisition month; no interpolation")

    flag_bad = _scalar(
        con,
        """
        SELECT COUNT(*) FROM stg.unit_economics
        WHERE new_customers > 0
          AND (
                (modeled_payback_month_index IS NULL AND never_pays_back_within_horizon = FALSE)
             OR (modeled_payback_month_index IS NOT NULL AND never_pays_back_within_horizon = TRUE)
          )
        """,
    )
    _add(checks, "unit.never_payback_flag", "unit_economics", flag_bad == 0, 0, flag_bad)

    weighted_bad = _scalar(
        con,
        """
        WITH w AS (
            SELECT
                channel,
                SUM(new_customers * modeled_lifetime_contribution_per_customer) / NULLIF(SUM(spend), 0) AS expected_weighted
            FROM stg.unit_economics
            GROUP BY channel
        )
        SELECT COUNT(*)
        FROM w
        JOIN stg.channel_allocation_summary a USING (channel)
        WHERE ABS(a.modeled_lifetime_contribution_to_cac_weighted - w.expected_weighted) > 1e-8
        """,
    )
    _add(checks, "allocation.weighted_lifetime_to_cac", "allocation", weighted_bad == 0, 0, weighted_bad)
    return checks


def _info_checks(con: duckdb.DuckDBPyConnection) -> list[Check]:
    checks: list[Check] = []
    meta_mismatch = _scalar(
        con,
        """
        SELECT COUNT(*) FROM raw.meta_ads_daily
        WHERE new_customers > purchases
        """,
    )
    source_vs_purch = _df(
        con,
        """
        SELECT
            SUM(source_conversions) AS source_conversions,
            SUM(platform_conversions) AS platform_conversions
        FROM stg.ads_daily
        WHERE platform = 'Meta Ads'
        """,
    ).iloc[0]
    _add(
        checks,
        "fixture.meta_new_customers_gt_purchases",
        "fixture_limitation",
        True,
        "generator derived new_customers from Meta conversions, not purchases",
        f"{int(meta_mismatch)} rows; source_conversions={int(source_vs_purch['source_conversions'])} purchases={int(source_vs_purch['platform_conversions'])}",
        status="INFO",
    )
    google_cross = _scalar(
        con,
        """
        SELECT COUNT(*) FROM (
            SELECT campaign_id, COUNT(DISTINCT channel) AS n
            FROM raw.google_ads_daily
            GROUP BY 1
            HAVING COUNT(DISTINCT channel) > 1
        )
        """,
    )
    _add(
        checks,
        "fixture.google_campaign_ids_cross_channels",
        "fixture_limitation",
        True,
        "Google campaign IDs are randomly crossed with Search/YouTube",
        f"{int(google_cross)} campaign_ids span multiple channels",
        status="INFO",
    )
    return checks


def validation_frame(checks: list[Check]) -> pd.DataFrame:
    return pd.DataFrame([asdict(c) for c in checks])


def failed_checks(checks: list[Check]) -> list[Check]:
    return [c for c in checks if c.status == "FAIL"]
