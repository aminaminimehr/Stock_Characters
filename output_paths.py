"""Canonical output locations and WRDS SQL filter helpers."""
from __future__ import annotations

from pathlib import Path

import pandas as pd

from pipeline_config import CRSP_EXCHCD, CRSP_SHRCD, SAMPLE_END, SAMPLE_START


PROJECT_ROOT = Path(__file__).resolve().parent
OUTPUT_ROOT = PROJECT_ROOT / "outputs"

CHARACTER_INDIVIDUAL_DIR = OUTPUT_ROOT / "characteristics" / "individual"
PANELS_DIR = OUTPUT_ROOT / "panels"
LOGS_DIR = OUTPUT_ROOT / "logs"
DIAGNOSTICS_DIR = OUTPUT_ROOT / "diagnostics"
CACHE_DIR = DIAGNOSTICS_DIR / "cache"

# Single pipeline output: the 95-character datashare signal panel.
SIGNAL_PANEL_FILE = PANELS_DIR / "all_character_signal_panel.csv"
PIPELINE_LOG_FILE = LOGS_DIR / "pipeline_run.log"

# Default write location for per-character CSV builders.
OUTPUT_DIR = CHARACTER_INDIVIDUAL_DIR
LEGACY_FLAT_OUTPUT_DIR = OUTPUT_ROOT

NON_CHARACTER_STEMS = {
    "all_character_signal_panel",
}

MONTHLY_ALIGNMENT_STEMS = ("mvel1", "mom1m", "dolvol", "beta", "turn")


def ensure_output_tree():
    """Create the output directory tree if it does not exist."""
    for path in (
        CHARACTER_INDIVIDUAL_DIR,
        PANELS_DIR,
        LOGS_DIR,
        DIAGNOSTICS_DIR,
        CACHE_DIR,
    ):
        path.mkdir(parents=True, exist_ok=True)
    gitkeep = OUTPUT_ROOT / ".gitkeep"
    if not gitkeep.exists():
        gitkeep.touch()


def resolve_output_path(path, default_dir=CHARACTER_INDIVIDUAL_DIR):
    """Resolve a writer path; bare filenames go to default_dir."""
    path = Path(path)
    if path.is_absolute():
        return path
    if len(path.parts) == 1:
        return default_dir / path
    return PROJECT_ROOT / path


def character_csv_path(stem: str) -> Path:
    """Return path to a character CSV, preferring the individual/ layout."""
    new_path = CHARACTER_INDIVIDUAL_DIR / f"{stem}.csv"
    if new_path.exists():
        return new_path
    legacy_path = LEGACY_FLAT_OUTPUT_DIR / f"{stem}.csv"
    if legacy_path.exists():
        return legacy_path
    return new_path


def iter_character_csv_paths():
    """Yield character CSV paths, skipping non-character panel files."""
    seen = set()
    for directory in (CHARACTER_INDIVIDUAL_DIR, LEGACY_FLAT_OUTPUT_DIR):
        if not directory.exists():
            continue
        for path in sorted(directory.glob("*.csv")):
            if path.stem in NON_CHARACTER_STEMS or path.stem in seen:
                continue
            seen.add(path.stem)
            yield path


def list_character_stems():
    return sorted(path.stem for path in iter_character_csv_paths())


def get_sample_bounds():
    """Return the hardcoded WRDS sample window from pipeline_config."""
    return SAMPLE_START, SAMPLE_END


def sql_date_filter(column: str, table_alias: str | None = None) -> str:
    """Return an SQL predicate fragment for the sample-date bounds."""
    col = f"{table_alias}.{column}" if table_alias else column
    start, end = get_sample_bounds()
    parts = []
    if start:
        parts.append(f"{col} >= DATE '{start}'")
    if end:
        parts.append(f"{col} <= DATE '{end}'")
    return " AND ".join(parts) if parts else "TRUE"


def _crsp_code_filter_disabled(value: str) -> bool:
    """True when a CRSP code filter should be omitted (ALL / * / empty)."""
    return str(value).strip().upper() in ("", "ALL", "*")


def get_crsp_universe():
    """Return hardcoded CRSP share/exchange code filters."""
    return CRSP_SHRCD, CRSP_EXCHCD


def _sql_int_list(values: str) -> str:
    codes = [v.strip() for v in str(values).split(",") if v.strip()]
    return ", ".join(codes)


def crsp_universe_filter(table_alias: str = "n") -> str:
    """Return an SQL predicate fragment for CRSP share/exchange filters."""
    shrcd, exchcd = get_crsp_universe()
    parts = []
    if not _crsp_code_filter_disabled(shrcd):
        parts.append(f"{table_alias}.shrcd IN ({_sql_int_list(shrcd)})")
    if not _crsp_code_filter_disabled(exchcd):
        parts.append(f"{table_alias}.exchcd IN ({_sql_int_list(exchcd)})")
    return " AND ".join(parts) if parts else "TRUE"


def read_wrds_sql(db, sql: str) -> pd.DataFrame:
    """Execute SQL on WRDS via a DBAPI connection."""
    engine = getattr(db, "engine", None) or getattr(db, "connection", None)
    if engine is None:
        raise AttributeError("Expected WRDS connection with .engine or .connection")
    conn = engine.raw_connection()
    try:
        return pd.read_sql_query(sql, conn)
    finally:
        conn.close()
