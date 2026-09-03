"""Timing conventions for panel expansion (copied from Character_Panels/timing.py)."""
from __future__ import annotations

from typing import Iterable

import numpy as np
import pandas as pd

from catalog import GREEN_ANNUAL_STEMS
from math_ops import add_one_month

MONTHLY_KEYS = ["permno", "signal_yyyymm", "target_yyyymm"]
ANNUAL_ID_COLUMNS = ["permno", "permco", "gvkey", "datadate", "sic", "fyear"]
ANNUAL_ROLLING_START_LAG_MONTHS = 7
ANNUAL_ROLLING_END_LAG_MONTHS = 20
HXZ_JUNE_STEMS = frozenset({"bm", "operprof"})


def annual_rolling_signal_yyyymm_offsets() -> range:
    """Month lags 7–19 after fiscal year end for Green annual expansion."""
    return range(ANNUAL_ROLLING_START_LAG_MONTHS, ANNUAL_ROLLING_END_LAG_MONTHS)


def expansion_mode(stem: str, columns: Iterable[str]) -> str | None:
    """Decide how to expand a character file: monthly_native, annual_rolling, or hxz_june."""
    column_set = set(columns)
    if set(MONTHLY_KEYS).issubset(column_set):
        return "monthly_native"
    if {"permno", "datadate"}.issubset(column_set):
        if stem in HXZ_JUNE_STEMS:
            return "hxz_june"
        if stem in GREEN_ANNUAL_STEMS:
            return "annual_rolling"
    return None


def expand_annual_file_june(df: pd.DataFrame, character_columns: Iterable[str]) -> pd.DataFrame:
    """Expand annual data to 12 monthly signals starting June of availability year."""
    character_columns = [c for c in character_columns if c not in ANNUAL_ID_COLUMNS]
    df = df.copy()
    df["datadate"] = pd.to_datetime(df["datadate"])
    availability_year = df["datadate"].dt.year + 1
    repeated = df.loc[df.index.repeat(12), list(ANNUAL_ID_COLUMNS) + character_columns].copy()
    month_offsets = np.tile(np.arange(12), len(df))
    first_signal_month = availability_year.to_numpy().repeat(12) * 12 + 6  # June of year after datadate.
    month_index = first_signal_month + month_offsets
    repeated["signal_yyyymm"] = (month_index // 12) * 100 + (month_index % 12 + 1)
    repeated["target_yyyymm"] = repeated["signal_yyyymm"].map(add_one_month)
    repeated = (
        repeated.sort_values(["permno", "signal_yyyymm", "datadate"])
        .drop_duplicates(["permno", "signal_yyyymm"], keep="last")
    )
    keep = MONTHLY_KEYS + ["permco", "gvkey", "sic"] + character_columns
    return repeated[keep]


def expand_annual_file_green(
    df: pd.DataFrame,
    character_columns: Iterable[str],
    crsp_month_index: pd.DataFrame | None = None,
) -> pd.DataFrame:
    """Expand annual data to monthly signals using Green rolling lags 7–19 months."""
    character_columns = [c for c in character_columns if c not in ANNUAL_ID_COLUMNS]
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


def build_crsp_month_index_from_panels(panels: list[pd.DataFrame]) -> pd.DataFrame:
    """Union permno×signal_yyyymm keys from a list of monthly panels."""
    parts = []
    for panel in panels:
        if set(MONTHLY_KEYS).issubset(panel.columns):
            parts.append(panel[["permno", "signal_yyyymm"]].drop_duplicates())
    if not parts:
        return pd.DataFrame(columns=["permno", "signal_yyyymm"])
    return pd.concat(parts, ignore_index=True).drop_duplicates()
