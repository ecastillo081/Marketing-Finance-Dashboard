"""Build the local Marketing Finance DuckDB warehouse, validate, and export CSVs.

Usage (from repo root, or via absolute path):

    python build.py
    python build.py --report
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.build_models import build_models  # noqa: E402
from src.load_data import create_warehouse, load_raw_and_assumptions  # noqa: E402
from src.paths import OUTPUTS_DIR  # noqa: E402
from src.sensitivity import failed_sensitivity_checks, run_sensitivity, write_sensitivity  # noqa: E402
from src.validate import failed_checks, run_validations, validation_frame  # noqa: E402


OUTPUT_QUERIES = {
    "channel_monthly_summary.csv": """
        SELECT *
        FROM stg.monthly_channel_summary
        ORDER BY cohort, channel
    """,
    "channel_unit_economics.csv": """
        SELECT *
        FROM stg.unit_economics
        ORDER BY cohort, channel
    """,
    "cohort_economics.csv": """
        SELECT *
        FROM stg.monthly_cohorts
        ORDER BY cohort, channel, month_index
    """,
    "channel_allocation_summary.csv": """
        SELECT *
        FROM stg.channel_allocation_summary
        ORDER BY total_spend DESC
    """,
    "campaign_summary.csv": """
        SELECT
            *,
            'SECONDARY / FIXTURE-LIMITED: Google campaign IDs are randomly crossed with Search and YouTube. Do not use for allocation.'
                AS fixture_limitation
        FROM stg.campaign_reconciliation
        ORDER BY platform, channel, campaign_id
    """,
}


def write_outputs(con) -> list[str]:
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
    written: list[str] = []
    for name, sql in OUTPUT_QUERIES.items():
        path = OUTPUTS_DIR / name
        con.execute(sql).df().to_csv(path, index=False)
        written.append(str(path.relative_to(REPO_ROOT)).replace("\\", "/"))
    return written


def print_summary(con, checks, written: list[str], sens_checks) -> None:
    fails = failed_checks(checks)
    n_pass = sum(1 for c in checks if c.status == "PASS")
    n_info = sum(1 for c in checks if c.status == "INFO")
    n_fail = len(fails)
    s_fail = failed_sensitivity_checks(sens_checks)
    s_pass = sum(1 for c in sens_checks if c.status == "PASS")

    alloc = con.execute(
        """
        SELECT
            channel,
            total_spend,
            spend_mix_pct,
            attributed_new_customers,
            blended_cac,
            platform_attributed_roas,
            modeled_lifetime_contribution_per_customer,
            modeled_lifetime_contribution_to_cac_weighted,
            modeled_lifetime_contribution_to_cac_unweighted_mean_of_cohorts,
            modeled_payback_month_index,
            acquisition_cohorts,
            cohorts_never_pay_back,
            share_of_cohorts_never_pay_back
        FROM stg.channel_allocation_summary
        ORDER BY total_spend DESC
        """
    ).df()

    print()
    print("=" * 72)
    print("Marketing Finance local build")
    print("=" * 72)
    print("Runtime: local DuckDB (no credentials, no Supabase, no Mode)")
    print("Source: committed synthetic fixtures + explicit modeled assumptions")
    print()
    print("Channel allocation summary (weighted / portfolio)")
    print("-" * 72)
    for _, row in alloc.iterrows():
        payback = row["modeled_payback_month_index"]
        payback_txt = "NULL (never within 38 months)" if payback is None or (isinstance(payback, float) and payback != payback) else int(payback)
        print(f"{row['channel']}")
        print(f"  spend                 {row['total_spend']:,.2f}  ({100 * row['spend_mix_pct']:.1f}% mix)")
        print(f"  new customers         {int(row['attributed_new_customers']):,}")
        print(f"  blended CAC           {row['blended_cac']:,.2f}")
        print(f"  platform-attributed ROAS {row['platform_attributed_roas']:.3f}")
        print(f"  modeled lifetime CM / customer {row['modeled_lifetime_contribution_per_customer']:,.2f}")
        print(f"  modeled lifetime CM / CAC (weighted) {row['modeled_lifetime_contribution_to_cac_weighted']:.3f}")
        print(f"  modeled lifetime CM / CAC (unweighted mean of cohorts) {row['modeled_lifetime_contribution_to_cac_unweighted_mean_of_cohorts']:.3f}")
        print(f"  modeled payback month_index (vs blended CAC) {payback_txt}")
        print(f"  cohorts never paying back  {int(row['cohorts_never_pay_back'])} / {int(row['acquisition_cohorts'])} ({100 * row['share_of_cohorts_never_pay_back']:.1f}%)")
        print()

    print("Payback convention: month_index 0 = acquisition month; first month")
    print("where cumulative modeled CM per acquired customer >= blended CAC.")
    print("No interpolation. NULL = does not pay back within the 38-month horizon.")
    print()
    print("Outputs:")
    for path in written:
        print(f"  {path}")
    print()
    print(f"Phase 1 validation: {n_pass} PASS  {n_fail} FAIL  {n_info} INFO")
    print(f"Sensitivity validation: {s_pass} PASS  {len(s_fail)} FAIL")
    if fails:
        print("FAILED CHECKS:")
        for check in fails:
            print(f"  [{check.group}] {check.check_id}: expected {check.expected} actual {check.actual} {check.detail}")
    if s_fail:
        print("FAILED SENSITIVITY CHECKS:")
        for check in s_fail:
            print(f"  {check.check_id}: expected {check.expected} actual {check.actual} {check.detail}")
    if fails or s_fail:
        print()
        print("BUILD: FAIL")
    else:
        print()
        print("BUILD: PASS")


def main() -> int:
    parser = argparse.ArgumentParser(description="Local Marketing Finance build")
    parser.add_argument(
        "--report",
        action="store_true",
        help="Also generate charts and the 3-page case-study PDF (requires Chrome or Edge)",
    )
    args = parser.parse_args()

    con = create_warehouse(replace=True)
    try:
        load_raw_and_assumptions(con)
        build_models(con)
        checks = run_validations(con)
        written = write_outputs(con)
        summary_path = OUTPUTS_DIR / "validation_summary.csv"
        validation_frame(checks).to_csv(summary_path, index=False)
        written.append(str(summary_path.relative_to(REPO_ROOT)).replace("\\", "/"))

        sensitivity, sens_checks = run_sensitivity(con)
        written.extend(write_sensitivity(sensitivity, sens_checks))
        print_summary(con, checks, written, sens_checks)

        analytics_ok = not failed_checks(checks) and not failed_sensitivity_checks(sens_checks)
        if args.report:
            if not analytics_ok:
                print("Skipping --report because analytics validation failed.")
                return 1
            alloc = con.execute("SELECT * FROM stg.channel_allocation_summary").df()
            retention = con.execute("SELECT * FROM assumptions.retention ORDER BY month_index").df()
            from src.charts import generate_charts
            from src.report import generate_report

            charts = generate_charts(alloc, sensitivity, retention)
            print("Charts:")
            for path in charts:
                print(f"  {path}")
            info = generate_report(alloc, sensitivity)
            print()
            print("Case study:")
            print(f"  {info['html']}")
            print(f"  {info['pdf']}")
            print(f"  pages: {info['pages']}")
            print(f"  GitHub: {info['github']}")
            if info["pages"] != "3":
                print(f"WARNING: expected 3 pages, got {info['pages']}")
                return 1
        return 0 if analytics_ok else 1
    finally:
        con.close()


if __name__ == "__main__":
    sys.exit(main())
