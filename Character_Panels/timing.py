"""Timing conventions for expanding annual characteristics to monthly signal months.

Annual Green-style timing (datadate + 7 .. + 19 months) replicates Greens_code.sas L484-L508.
HXZ June timing (Jun y+1 .. May y+2) applies to bm and operprof only.
"""
from __future__ import annotations

from pathlib import Path
from typing import Iterable

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]

MONTHLY_KEYS = ["permno", "signal_yyyymm", "target_yyyymm"]
ANNUAL_ID_COLUMNS = ["permno", "permco", "gvkey", "datadate", "sic", "fyear"]

# datadate + 7 months (inclusive) through datadate + 19 months (exclusive upper in SAS).
ANNUAL_ROLLING_START_LAG_MONTHS = 7
ANNUAL_ROLLING_END_LAG_MONTHS = 20

# HXZ June annuals use datashare column names directly.
HXZ_JUNE_STEMS = frozenset({"bm", "operprof"})

_GREEN_ANNUAL_STEMS_CACHE: frozenset[str] | None = None


def _green_annual_stems() -> frozenset[str]:
    """Lazy-load annual character stems from green_builders (avoids import cycle at module load)."""
    global _GREEN_ANNUAL_STEMS_CACHE
    if _GREEN_ANNUAL_STEMS_CACHE is not None:
        return _GREEN_ANNUAL_STEMS_CACHE
    import sys

    builders_root = PROJECT_ROOT / "Character_Builders"
    if str(builders_root) not in sys.path:
        sys.path.insert(0, str(builders_root))
    from _shared.green_builders import ANNUAL_CHARACTER_INFO

    _GREEN_ANNUAL_STEMS_CACHE = frozenset(ANNUAL_CHARACTER_INFO.keys())
    return _GREEN_ANNUAL_STEMS_CACHE


def add_one_month(yyyymm: int) -> int:
    year = yyyymm // 100
    month = yyyymm % 100
    next_month = month + 1
    next_year = year + (next_month == 13)
    next_month = 1 if next_month == 13 else next_month
    return next_year * 100 + next_month


def signal_yyyymm_from_timestamp(ts: pd.Timestamp) -> int:
    return int(ts.year * 100 + ts.month)


def annual_rolling_signal_yyyymm_offsets() -> range:
    """Inclusive month offsets for vectorized annual rolling expansion (7..19)."""
    return range(ANNUAL_ROLLING_START_LAG_MONTHS, ANNUAL_ROLLING_END_LAG_MONTHS)


def expansion_mode(stem: str, columns: Iterable[str]) -> str | None:
    """Return how to normalize a character CSV: monthly_native, hxz_june, annual_rolling, or None."""
    column_set = set(columns)
    if set(MONTHLY_KEYS).issubset(column_set):
        return "monthly_native"
    if {"permno", "datadate"}.issubset(column_set):
        if stem in HXZ_JUNE_STEMS:
            return "hxz_june"
        if stem in _green_annual_stems():
            return "annual_rolling"
    return None


def expand_annual_file_june(df: pd.DataFrame, character_columns: Iterable[str]) -> pd.DataFrame:
    """HXZ June availability: FY ending calendar year y -> Jun y+1 .. May y+2."""
    df = df.copy()
    df["datadate"] = pd.to_datetime(df["datadate"])
    availability_year = df["datadate"].dt.year + 1

    repeated = df.loc[df.index.repeat(12), list(ANNUAL_ID_COLUMNS) + list(character_columns)].copy()
    month_offsets = np.tile(np.arange(12), len(df))
    first_signal_month = availability_year.to_numpy().repeat(12) * 12 + 6
    month_index = first_signal_month + month_offsets
    repeated["signal_yyyymm"] = (month_index // 12) * 100 + (month_index % 12 + 1)
    repeated["target_yyyymm"] = repeated["signal_yyyymm"].map(add_one_month)
    repeated = (
        repeated.sort_values(["permno", "signal_yyyymm", "datadate"])
        .drop_duplicates(["permno", "signal_yyyymm"], keep="last")
    )

    keep = MONTHLY_KEYS + ["permco", "gvkey", "sic"] + list(character_columns)
    return repeated[keep]


def expand_annual_file_green(
    df: pd.DataFrame,
    character_columns: Iterable[str],
    crsp_month_index: pd.DataFrame | None = None,
) -> pd.DataFrame:
    """Annual rolling availability: datadate + 7 .. + 19 months (Greens_code.sas L484-L508)."""
    character_columns = list(character_columns)
    df = df.copy()
    df["datadate"] = pd.to_datetime(df["datadate"])

    chunks = []
    id_cols = list(ANNUAL_ID_COLUMNS) + character_columns
    for month_lag in annual_rolling_signal_yyyymm_offsets():
        chunk = df[id_cols].copy()
        signal_dates = (chunk["datadate"] + pd.DateOffset(months=month_lag)).dt.to_period("M").dt.to_timestamp("M")
        chunk["signal_yyyymm"] = (signal_dates.dt.year * 100 + signal_dates.dt.month).astype(int)
        chunks.append(chunk)

    if not chunks:
        return pd.DataFrame(columns=MONTHLY_KEYS + ["permco", "gvkey", "sic"] + character_columns)

    expanded = pd.concat(chunks, ignore_index=True)
    expanded = (
        expanded.sort_values(["permno", "signal_yyyymm", "datadate"])
        .drop_duplicates(["permno", "signal_yyyymm"], keep="last")
    )

    if crsp_month_index is not None and not crsp_month_index.empty:
        expanded = expanded.merge(
            crsp_month_index[["permno", "signal_yyyymm"]].drop_duplicates(),
            on=["permno", "signal_yyyymm"],
            how="inner",
        )

    expanded["target_yyyymm"] = expanded["signal_yyyymm"].map(add_one_month)
    keep = MONTHLY_KEYS + ["permco", "gvkey", "sic"] + character_columns
    return expanded[keep]


# Backward-compatible alias for validation scripts.
expand_annual_file = expand_annual_file_june


def build_crsp_month_index_from_panels(panels: list[pd.DataFrame]) -> pd.DataFrame:
    """Union permno x signal_yyyymm from monthly-native panels."""
    parts = []
    for panel in panels:
        if set(MONTHLY_KEYS).issubset(panel.columns):
            parts.append(panel[["permno", "signal_yyyymm"]].drop_duplicates())
    if not parts:
        return pd.DataFrame(columns=["permno", "signal_yyyymm"])
    return pd.concat(parts, ignore_index=True).drop_duplicates()
