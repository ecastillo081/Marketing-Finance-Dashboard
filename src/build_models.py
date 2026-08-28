"""Execute numbered SQL models against the local DuckDB warehouse."""

from __future__ import annotations

import duckdb

from src.paths import SQL_MODELS


def build_models(con: duckdb.DuckDBPyConnection) -> list[str]:
    built: list[str] = []
    for sql_path in SQL_MODELS:
        if not sql_path.exists():
            raise FileNotFoundError(f"Missing SQL model: {sql_path}")
        con.execute(sql_path.read_text(encoding="utf-8"))
        built.append(sql_path.name)
    return built
