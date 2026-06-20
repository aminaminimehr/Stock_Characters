"""Canonical output locations for Stock Characters builds and panels."""
from __future__ import annotations

import os
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent
OUTPUT_ROOT = PROJECT_ROOT / "outputs"

CHARACTER_INDIVIDUAL_DIR = OUTPUT_ROOT / "characteristics" / "individual"
PANELS_DIR = OUTPUT_ROOT / "panels"
LOGS_DIR = OUTPUT_ROOT / "logs"
DIAGNOSTICS_DIR = OUTPUT_ROOT / "diagnostics"
CACHE_DIR = DIAGNOSTICS_DIR / "cache"
LEGACY_PANELS_DIR = PANELS_DIR / "legacy"

# Primary panel artifacts (full pipeline).
SIGNAL_PANEL_FILE = PANELS_DIR / "all_character_signal_panel.csv"
COMPLETE_ALL_PANEL_FILE = PANELS_DIR / "complete_all_character_prediction_panel.csv"
RESEARCH_PANEL_FILE = PANELS_DIR / "research_panel_1957_ranked.csv"
EXCESS_RETURNS_FILE = PANELS_DIR / "excess_returns.csv"
PIPELINE_LOG_FILE = LOGS_DIR / "pipeline_run.log"

# Deprecated narrow workflow (HXZ-only monthly panel); not produced by run_full_pipeline.py.
LEGACY_MONTHLY_PANEL_FILE = LEGACY_PANELS_DIR / "monthly_character_panel.csv"
LEGACY_ANNUAL_PANEL_FILE = LEGACY_PANELS_DIR / "annual_character_panel.csv"
LEGACY_COMPLETE_PANEL_FILE = LEGACY_PANELS_DIR / "complete_prediction_panel.csv"

# Default write location for per-character CSV builders.
OUTPUT_DIR = CHARACTER_INDIVIDUAL_DIR
LEGACY_FLAT_OUTPUT_DIR = OUTPUT_ROOT

NON_CHARACTER_STEMS = {
    "all_character_signal_panel",
    "annual_character_panel",
    "complete_all_character_prediction_panel",
    "complete_prediction_panel",
    "complete_prediction_panel_imputed",
    "excess_returns",
    "green_comparable_temp",
    "green_comparable_temp2_winsorized",
    "green_comparable_validation_summary",
    "green_comparable_winsorized_validation_summary",
    "green_comparable_winsorized_validation_summary_fresh",
    "green_missing_character_inventory",
    "monthly_character_panel",
    "research_panel_1957_ranked",
}

MONTHLY_ALIGNMENT_STEMS = ("me", "mvel1", "mom1m", "dolvol", "beta", "turn")


def ensure_output_tree():
    for path in (
        CHARACTER_INDIVIDUAL_DIR,
        PANELS_DIR,
        LOGS_DIR,
        DIAGNOSTICS_DIR,
        CACHE_DIR,
        LEGACY_PANELS_DIR,
    ):
        path.mkdir(parents=True, exist_ok=True)
    gitkeep = OUTPUT_ROOT / ".gitkeep"
    if not gitkeep.exists():
        gitkeep.touch()


def resolve_output_path(path, default_dir=CHARACTER_INDIVIDUAL_DIR):
    """Resolve a writer path; bare filenames go to default_dir (individual chars by default)."""
    path = Path(path)
    if path.is_absolute():
        return path
    if len(path.parts) == 1:
        return default_dir / path
    return PROJECT_ROOT / path


def resolve_legacy_panel_path(path):
    """Resolve deprecated narrow panel outputs under panels/legacy/."""
    path = Path(path)
    if path.is_absolute():
        return path
    if len(path.parts) == 1:
        return LEGACY_PANELS_DIR / path
    return PROJECT_ROOT / path


def character_csv_path(stem: str) -> Path:
    """Prefer new layout; fall back to legacy flat outputs/ during migration."""
    new_path = CHARACTER_INDIVIDUAL_DIR / f"{stem}.csv"
    if new_path.exists():
        return new_path
    legacy_path = LEGACY_FLAT_OUTPUT_DIR / f"{stem}.csv"
    if legacy_path.exists():
        return legacy_path
    return new_path


def iter_character_csv_paths():
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
    """Optional WRDS sample window via environment variables.

    Default annual start is 1975-01-01 (Green SAS) unless STOCK_CHARACTERS_SAMPLE_START is set.
    """
    start = os.environ.get("STOCK_CHARACTERS_SAMPLE_START")
    end = os.environ.get("STOCK_CHARACTERS_SAMPLE_END")
    if not start:
        start = os.environ.get("STOCK_CHARACTERS_DEFAULT_ANNUAL_START", "1975-01-01")
    return start, end


def sql_date_filter(column: str, table_alias: str | None = None) -> str:
    """Return an SQL predicate fragment for optional sample-date bounds."""
    col = f"{table_alias}.{column}" if table_alias else column
    start, end = get_sample_bounds()
    parts = []
    if start:
        parts.append(f"{col} >= DATE '{start}'")
    if end:
        parts.append(f"{col} <= DATE '{end}'")
    return " AND ".join(parts) if parts else "TRUE"
