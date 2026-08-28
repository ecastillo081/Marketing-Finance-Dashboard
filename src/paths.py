"""Repo-relative paths. Works when invoked from repo root or by absolute path."""

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

DATA_RAW = REPO_ROOT / "data" / "raw"
DATA_ASSUMPTIONS = REPO_ROOT / "data" / "assumptions"
SQL_DIR = REPO_ROOT / "sql"
OUTPUTS_DIR = REPO_ROOT / "outputs"
WAREHOUSE_DIR = REPO_ROOT / "warehouse"
WAREHOUSE_DB = WAREHOUSE_DIR / "marketing_finance.duckdb"

GOOGLE_CSV = DATA_RAW / "google_ads_daily.csv"
META_CSV = DATA_RAW / "meta_ads_daily.csv"
FINANCE_CSV = DATA_ASSUMPTIONS / "finance_drivers.csv"
RETENTION_CSV = DATA_ASSUMPTIONS / "retention_template.csv"
ARPU_CSV = DATA_ASSUMPTIONS / "arpu_template.csv"

SQL_MODELS = [
    SQL_DIR / "001_ads_daily.sql",
    SQL_DIR / "002_monthly_channel_summary.sql",
    SQL_DIR / "003_monthly_cohorts.sql",
    SQL_DIR / "004_unit_economics.sql",
    SQL_DIR / "005_channel_monthly_pnl.sql",
    SQL_DIR / "006_channel_allocation_summary.sql",
    SQL_DIR / "007_campaign_reconciliation.sql",
]
