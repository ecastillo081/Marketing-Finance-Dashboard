"""Load golden fixtures and modeled assumptions into local DuckDB."""

from __future__ import annotations

from pathlib import Path

import duckdb

from src.paths import (
    ARPU_CSV,
    FINANCE_CSV,
    GOOGLE_CSV,
    META_CSV,
    RETENTION_CSV,
    WAREHOUSE_DB,
    WAREHOUSE_DIR,
)


def _read_csv_sql(path: Path) -> str:
    return path.resolve().as_posix().replace("'", "''")


def create_warehouse(replace: bool = True) -> duckdb.DuckDBPyConnection:
    WAREHOUSE_DIR.mkdir(parents=True, exist_ok=True)
    if replace and WAREHOUSE_DB.exists():
        WAREHOUSE_DB.unlink()
    con = duckdb.connect(str(WAREHOUSE_DB))
    con.execute("CREATE SCHEMA IF NOT EXISTS raw")
    con.execute("CREATE SCHEMA IF NOT EXISTS assumptions")
    con.execute("CREATE SCHEMA IF NOT EXISTS stg")
    return con


def load_raw_and_assumptions(con: duckdb.DuckDBPyConnection) -> None:
    for label, path in [
        ("Google Ads fixture", GOOGLE_CSV),
        ("Meta Ads fixture", META_CSV),
        ("finance drivers", FINANCE_CSV),
        ("retention template", RETENTION_CSV),
        ("ARPU template", ARPU_CSV),
    ]:
        if not path.exists():
            raise FileNotFoundError(f"Missing {label}: {path}")

    con.execute(
        f"""
        CREATE OR REPLACE TABLE raw.google_ads_daily AS
        SELECT * FROM read_csv('{_read_csv_sql(GOOGLE_CSV)}', header := true, auto_detect := true)
        """
    )
    con.execute(
        f"""
        CREATE OR REPLACE TABLE raw.meta_ads_daily AS
        SELECT * FROM read_csv('{_read_csv_sql(META_CSV)}', header := true, auto_detect := true)
        """
    )
    con.execute(
        f"""
        CREATE OR REPLACE TABLE assumptions.finance AS
        SELECT * FROM read_csv('{_read_csv_sql(FINANCE_CSV)}', header := true, auto_detect := true)
        """
    )
    con.execute(
        f"""
        CREATE OR REPLACE TABLE assumptions.retention AS
        SELECT * FROM read_csv('{_read_csv_sql(RETENTION_CSV)}', header := true, auto_detect := true)
        """
    )
    con.execute(
        f"""
        CREATE OR REPLACE TABLE assumptions.arpu AS
        SELECT * FROM read_csv('{_read_csv_sql(ARPU_CSV)}', header := true, auto_detect := true)
        """
    )
