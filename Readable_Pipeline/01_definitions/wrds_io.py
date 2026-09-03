"""WRDS connection and query execution for independent builders."""
from __future__ import annotations

import os
import time
from pathlib import Path

import pandas as pd
import wrds

from config import CRSP_EXCHCD, CRSP_SHRCD, SAMPLE_END, SAMPLE_START
from paths import stem_cache_path


def get_sample_bounds():
    """Return configured sample start/end dates from pipeline config."""
    return SAMPLE_START, SAMPLE_END


def _crsp_code_filter_disabled(value: str) -> bool:
    """True when CRSP shrcd/exchcd filter is disabled (ALL or empty)."""
    return str(value).strip().upper() in ("", "ALL", "*")


def _sql_int_list(values: str) -> str:
    """Format comma-separated integers for SQL IN (...) clauses."""
    codes = [v.strip() for v in str(values).split(",") if v.strip()]
    return ", ".join(codes)


def crsp_universe_filter(table_alias: str = "n") -> str:
    """SQL fragment filtering CRSP msenames by shrcd and exchcd."""
    parts = []
    if not _crsp_code_filter_disabled(CRSP_SHRCD):
        parts.append(f"{table_alias}.shrcd IN ({_sql_int_list(CRSP_SHRCD)})")
    if not _crsp_code_filter_disabled(CRSP_EXCHCD):
        parts.append(f"{table_alias}.exchcd IN ({_sql_int_list(CRSP_EXCHCD)})")
    return " AND ".join(parts) if parts else "TRUE"


def sql_date_filter(column: str, table_alias: str | None = None) -> str:
    """SQL fragment constraining a date column to SAMPLE_START/SAMPLE_END."""
    col = f"{table_alias}.{column}" if table_alias else column
    parts = []
    if SAMPLE_START:
        parts.append(f"{col} >= DATE '{SAMPLE_START}'")
    if SAMPLE_END:
        parts.append(f"{col} <= DATE '{SAMPLE_END}'")
    return " AND ".join(parts) if parts else "TRUE"


def read_wrds_sql(db, sql: str) -> pd.DataFrame:
    """Execute SQL on WRDS via raw DBAPI connection."""
    engine = getattr(db, "engine", None) or getattr(db, "connection", None)
    if engine is None:
        raise AttributeError("Expected WRDS connection with .engine or .connection")
    conn = engine.raw_connection()
    try:
        return pd.read_sql_query(sql, conn)
    finally:
        conn.close()


def connect_wrds(wrds_user: str | None = None):
    """Open WRDS connection using CLI arg or WRDS_USERNAME/WRDS_USER env var."""
    if not wrds_user:
        wrds_user = os.environ.get("WRDS_USERNAME") or os.environ.get("WRDS_USER")
    if not wrds_user:
        raise RuntimeError("No WRDS username. Pass --wrds-user or set WRDS_USERNAME / WRDS_USER.")
    return wrds.Connection(wrds_username=wrds_user)


def _reset_wrds_connection(db):
    """Rollback and reconnect after a failed WRDS query."""
    try:
        conn = getattr(db, "connection", None)
        if conn is not None and hasattr(conn, "rollback"):
            conn.rollback()
    except Exception:
        pass
    try:
        db.close()
        db.connect()
    except Exception as exc:
        print(f"Warning: could not reset WRDS connection: {exc}", flush=True)


def raw_sql_with_retry(db, sql: str, attempts: int = 5, pause_seconds=None) -> pd.DataFrame:
    """Execute WRDS SQL with exponential backoff on transient connection errors."""
    backoff = (30, 60, 120, 240)
    last_exc = None
    for attempt in range(1, attempts + 1):
        try:
            return read_wrds_sql(db, sql)
        except Exception as exc:
            last_exc = exc
            msg = str(exc).lower()
            retryable = any(
                token in msg
                for token in (
                    "timeout", "timed out", "connection", "ssl", "closed", "reset",
                    "rollback", "invalid transaction", "conflict with recovery",
                    "canceling statement", "serialization",
                )
            )
            if attempt == attempts or not retryable:
                raise
            wait = pause_seconds if pause_seconds is not None else backoff[min(attempt - 1, len(backoff) - 1)]
            print(f"WRDS query failed (attempt {attempt}/{attempts}): {exc}; retrying in {wait}s...", flush=True)
            _reset_wrds_connection(db)
            time.sleep(wait)
    raise last_exc


def maybe_load_cache(stem: str, tag: str) -> pd.DataFrame | None:
    """Load per-stem parquet cache ``cache/{stem}_{tag}.parquet`` if it exists."""
    path = stem_cache_path(stem, tag)
    if path.with_suffix(".parquet").exists():
        return pd.read_parquet(path.with_suffix(".parquet"))
    return None


def maybe_save_cache(stem: str, tag: str, df: pd.DataFrame) -> None:
    """Write per-stem parquet cache ``cache/{stem}_{tag}.parquet``."""
    path = stem_cache_path(stem, tag)
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(path.with_suffix(".parquet"), index=False)
