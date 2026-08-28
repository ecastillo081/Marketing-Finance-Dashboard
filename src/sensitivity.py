"""Downside sensitivity on modeled lifetime contribution and payback.

Baseline customer economics come from the same contribution-margin formula as
sql/003_monthly_cohorts.sql. Channel CAC and spend come from the validated
stg.channel_allocation_summary (portfolio / weighted grain).

Assumption CSVs are not overwritten. Scenarios are computed in-memory.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

import duckdb
import pandas as pd

from src.paths import OUTPUTS_DIR, REPO_ROOT


CHANNEL_ORDER = [
    "Meta Ads",
    "Google Ads - Search",
    "Google Ads - YouTube",
]

SCENARIOS = [
    ("baseline", "Baseline"),
    ("cac_plus_20", "CAC +20%"),
    ("arpu_minus_20", "ARPU -20%"),
    ("retention_downside", "Retention downside"),
    ("gm_minus_5pp", "Gross margin -5 pp"),
]


@dataclass
class SensitivityCheck:
    check_id: str
    status: str
    expected: str
    actual: str
    detail: str = ""


def _cm_per_customer(retention: pd.Series, arpu: pd.Series, gm: float, vc: float, fee: float, refund: float) -> pd.Series:
    """Match sql/003: (ret × ARPU × (1-refund) × GM) - (ret × ARPU × (1-refund) × fee) - (ret × VC)."""
    return (
        retention * arpu * (1 - refund) * gm
        - retention * arpu * (1 - refund) * fee
        - retention * vc
    )


def _payback(cum: pd.Series, cac: float) -> int | None:
    hits = cum.index[cum >= cac]
    if len(hits) == 0:
        return None
    return int(hits[0])


def _drivers(con: duckdb.DuckDBPyConnection) -> pd.DataFrame:
    return con.execute(
        """
        SELECT
            c.channel,
            COALESCE(f.gross_margin_pct, d.gross_margin_pct) AS gm,
            COALESCE(f.variable_cost_per_order, d.variable_cost_per_order) AS vc,
            COALESCE(f.payment_processing_fee_pct, d.payment_processing_fee_pct) AS fee,
            COALESCE(f.refund_rate_pct, d.refund_rate_pct) AS refund
        FROM (SELECT DISTINCT channel FROM stg.channel_allocation_summary) AS c
        LEFT JOIN assumptions.finance AS f ON c.channel = f.channel
        LEFT JOIN assumptions.finance AS d ON d.channel = 'DEFAULT'
        """
    ).df().set_index("channel")


def run_sensitivity(con: duckdb.DuckDBPyConnection) -> tuple[pd.DataFrame, list[SensitivityCheck]]:
    alloc = con.execute(
        """
        SELECT
            channel,
            total_spend,
            attributed_new_customers,
            blended_cac,
            modeled_lifetime_contribution_per_customer,
            modeled_lifetime_contribution_to_cac_weighted,
            modeled_payback_month_index
        FROM stg.channel_allocation_summary
        """
    ).df().set_index("channel")

    horizon = con.execute(
        """
        SELECT r.month_index, r.retention_rate_t AS retention, a.arpu_t AS arpu
        FROM assumptions.retention r
        INNER JOIN assumptions.arpu a USING (month_index)
        ORDER BY month_index
        """
    ).df()

    drivers = _drivers(con)
    rows: list[dict[str, Any]] = []

    for scenario_id, scenario_name in SCENARIOS:
        for channel in CHANNEL_ORDER:
            base = alloc.loc[channel]
            drv = drivers.loc[channel]
            retention = horizon["retention"].copy()
            arpu = horizon["arpu"].copy()
            gm = float(drv["gm"])
            vc = float(drv["vc"])
            fee = float(drv["fee"])
            refund = float(drv["refund"])
            cac = float(base["blended_cac"])

            if scenario_id == "cac_plus_20":
                cac = cac * 1.20
            elif scenario_id == "arpu_minus_20":
                arpu = arpu * 0.80
            elif scenario_id == "retention_downside":
                retention = retention.copy()
                retention.loc[horizon["month_index"] >= 1] = retention.loc[horizon["month_index"] >= 1] * 0.80
            elif scenario_id == "gm_minus_5pp":
                gm = gm - 0.05

            cm = _cm_per_customer(retention, arpu, gm, vc, fee, refund)
            cm.index = horizon["month_index"].astype(int)
            lifetime = float(cm.sum())
            cum = cm.cumsum()
            payback = _payback(cum, cac)
            weighted = lifetime / cac if cac > 0 else None
            rows.append(
                {
                    "scenario_id": scenario_id,
                    "scenario_name": scenario_name,
                    "channel": channel,
                    "blended_cac": cac,
                    "modeled_lifetime_contribution_per_customer": lifetime,
                    "weighted_lifetime_contribution_to_cac": weighted,
                    "modeled_payback_month_index": payback,
                    "pays_back_within_horizon": payback is not None,
                    "horizon_months": 38,
                }
            )

    result = pd.DataFrame(rows)
    baseline = result[result["scenario_id"] == "baseline"].set_index("channel")
    result["delta_weighted_vs_baseline"] = result.apply(
        lambda r: r["weighted_lifetime_contribution_to_cac"] - baseline.loc[r["channel"], "weighted_lifetime_contribution_to_cac"],
        axis=1,
    )
    result["channel_sort"] = result["channel"].map({ch: i for i, ch in enumerate(CHANNEL_ORDER)})
    result["scenario_sort"] = result["scenario_id"].map({s: i for i, (s, _) in enumerate(SCENARIOS)})
    result = result.sort_values(["scenario_sort", "channel_sort"]).drop(columns=["channel_sort", "scenario_sort"]).reset_index(drop=True)

    checks = _validate_sensitivity(result, alloc, horizon, drivers)
    return result, checks


def _validate_sensitivity(
    result: pd.DataFrame,
    alloc: pd.DataFrame,
    horizon: pd.DataFrame,
    drivers: pd.DataFrame,
) -> list[SensitivityCheck]:
    checks: list[SensitivityCheck] = []

    def add(check_id: str, ok: bool, expected: Any, actual: Any, detail: str = "") -> None:
        checks.append(
            SensitivityCheck(
                check_id=check_id,
                status="PASS" if ok else "FAIL",
                expected=str(expected),
                actual=str(actual),
                detail=detail,
            )
        )

    base = result[result["scenario_id"] == "baseline"].set_index("channel")
    for channel in CHANNEL_ORDER:
        a = alloc.loc[channel]
        b = base.loc[channel]
        add(
            f"baseline.lifetime.{channel}",
            abs(b["modeled_lifetime_contribution_per_customer"] - a["modeled_lifetime_contribution_per_customer"]) < 1e-6,
            round(float(a["modeled_lifetime_contribution_per_customer"]), 6),
            round(float(b["modeled_lifetime_contribution_per_customer"]), 6),
            "Python waterfall must match Phase 1 SQL lifetime",
        )
        add(
            f"baseline.weighted.{channel}",
            abs(b["weighted_lifetime_contribution_to_cac"] - a["modeled_lifetime_contribution_to_cac_weighted"]) < 1e-8,
            round(float(a["modeled_lifetime_contribution_to_cac_weighted"]), 8),
            round(float(b["weighted_lifetime_contribution_to_cac"]), 8),
        )
        phase1_pb = a["modeled_payback_month_index"]
        phase1_pb = None if pd.isna(phase1_pb) else int(phase1_pb)
        add(
            f"baseline.payback.{channel}",
            b["modeled_payback_month_index"] == phase1_pb,
            phase1_pb,
            b["modeled_payback_month_index"],
        )

    cac20 = result[result["scenario_id"] == "cac_plus_20"].set_index("channel")
    for channel in CHANNEL_ORDER:
        add(
            f"cac20.lifetime_unchanged.{channel}",
            abs(cac20.loc[channel, "modeled_lifetime_contribution_per_customer"] - base.loc[channel, "modeled_lifetime_contribution_per_customer"]) < 1e-9,
            round(float(base.loc[channel, "modeled_lifetime_contribution_per_customer"]), 6),
            round(float(cac20.loc[channel, "modeled_lifetime_contribution_per_customer"]), 6),
            "CAC shock must not change customer contribution",
        )
        expected_cac = float(alloc.loc[channel, "blended_cac"]) * 1.20
        add(
            f"cac20.cac_times_1_2.{channel}",
            abs(cac20.loc[channel, "blended_cac"] - expected_cac) < 1e-9,
            expected_cac,
            float(cac20.loc[channel, "blended_cac"]),
        )
        expected_ratio = float(base.loc[channel, "modeled_lifetime_contribution_per_customer"]) / expected_cac
        add(
            f"cac20.weighted_identity.{channel}",
            abs(cac20.loc[channel, "weighted_lifetime_contribution_to_cac"] - expected_ratio) < 1e-10,
            expected_ratio,
            float(cac20.loc[channel, "weighted_lifetime_contribution_to_cac"]),
        )

    def expected_lifetime(channel: str, *, arpu_scale: float = 1.0, ret_after_m0: float = 1.0, gm_delta: float = 0.0) -> float:
        drv = drivers.loc[channel]
        retention = horizon["retention"].copy()
        if ret_after_m0 != 1.0:
            retention.loc[horizon["month_index"] >= 1] = retention.loc[horizon["month_index"] >= 1] * ret_after_m0
        arpu = horizon["arpu"] * arpu_scale
        cm = _cm_per_customer(
            retention,
            arpu,
            float(drv["gm"]) + gm_delta,
            float(drv["vc"]),
            float(drv["fee"]),
            float(drv["refund"]),
        )
        return float(cm.sum())

    arpu = result[result["scenario_id"] == "arpu_minus_20"].set_index("channel")
    for channel in CHANNEL_ORDER:
        add(
            f"arpu20.cac_unchanged.{channel}",
            abs(arpu.loc[channel, "blended_cac"] - float(alloc.loc[channel, "blended_cac"])) < 1e-9,
            float(alloc.loc[channel, "blended_cac"]),
            float(arpu.loc[channel, "blended_cac"]),
        )
        exp = expected_lifetime(channel, arpu_scale=0.80)
        add(
            f"arpu20.waterfall.{channel}",
            abs(arpu.loc[channel, "modeled_lifetime_contribution_per_customer"] - exp) < 1e-8,
            round(exp, 6),
            round(float(arpu.loc[channel, "modeled_lifetime_contribution_per_customer"]), 6),
            "ARPU $50 → $40 flows through revenue, refunds, GP, fees, and CM",
        )

    ret_m0 = float(horizon.loc[horizon["month_index"] == 0, "retention"].iloc[0])
    ret_m1 = float(horizon.loc[horizon["month_index"] == 1, "retention"].iloc[0])
    add("retention.month0_is_1", abs(ret_m0 - 1.0) < 1e-12, 1.0, ret_m0, "downside keeps month_index 0 at 1.00")
    add("retention.month1_baseline_is_0_45", abs(ret_m1 - 0.45) < 1e-12, 0.45, ret_m1, f"downside m1 = {ret_m1 * 0.80:.3f}")
    ret_sc = result[result["scenario_id"] == "retention_downside"].set_index("channel")
    for channel in CHANNEL_ORDER:
        exp = expected_lifetime(channel, ret_after_m0=0.80)
        add(
            f"retention.waterfall.{channel}",
            abs(ret_sc.loc[channel, "modeled_lifetime_contribution_per_customer"] - exp) < 1e-8,
            round(exp, 6),
            round(float(ret_sc.loc[channel, "modeled_lifetime_contribution_per_customer"]), 6),
        )

    gm_sc = result[result["scenario_id"] == "gm_minus_5pp"].set_index("channel")
    for channel in CHANNEL_ORDER:
        exp = expected_lifetime(channel, gm_delta=-0.05)
        add(
            f"gm.waterfall.{channel}",
            abs(gm_sc.loc[channel, "modeled_lifetime_contribution_per_customer"] - exp) < 1e-8,
            round(exp, 6),
            round(float(gm_sc.loc[channel, "modeled_lifetime_contribution_per_customer"]), 6),
            f"{float(drivers.loc[channel, 'gm']):.2f} → {float(drivers.loc[channel, 'gm']) - 0.05:.2f} (percentage points)",
        )

    flag_ok = True
    for _, row in result.iterrows():
        consistent = (row["pays_back_within_horizon"] and row["modeled_payback_month_index"] is not None) or (
            (not row["pays_back_within_horizon"]) and row["modeled_payback_month_index"] is None
        )
        if not consistent:
            flag_ok = False
            add(
                f"payback.flag.{row['scenario_id']}.{row['channel']}",
                False,
                "flag matches NULL payback",
                f"pays_back={row['pays_back_within_horizon']} payback={row['modeled_payback_month_index']}",
            )
    if flag_ok:
        add("payback.flags_consistent", True, "all 15 rows", "all 15 rows")

    add(
        "shape.rows",
        len(result) == 15,
        15,
        len(result),
        "5 scenarios x 3 channels",
    )
    return checks


def write_sensitivity(result: pd.DataFrame, checks: list[SensitivityCheck]) -> list[str]:
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
    out = OUTPUTS_DIR / "sensitivity_summary.csv"
    result.to_csv(out, index=False)
    check_path = OUTPUTS_DIR / "sensitivity_validation.csv"
    pd.DataFrame([asdict(c) for c in checks]).to_csv(check_path, index=False)
    return [
        str(out.relative_to(REPO_ROOT)).replace("\\", "/"),
        str(check_path.relative_to(REPO_ROOT)).replace("\\", "/"),
    ]


def failed_sensitivity_checks(checks: list[SensitivityCheck]) -> list[SensitivityCheck]:
    return [c for c in checks if c.status == "FAIL"]
