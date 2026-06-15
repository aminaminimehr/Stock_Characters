"""Source-specific timing conventions for monthly signal panels.

Green annual timing replicates Greens_code.sas lines 475-508:
  intnx('MONTH', datadate, 7) <= crsp.date < intnx('MONTH', datadate, 20)
with latest fiscal datadate kept per permno x signal month (nodupkey).
"""
from __future__ import annotations

from enum import Enum
from functools import lru_cache
from pathlib import Path
from typing import Iterable

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]

MONTHLY_KEYS = ["permno", "signal_yyyymm", "target_yyyymm"]
ANNUAL_ID_COLUMNS = ["permno", "permco", "gvkey", "datadate", "sic", "fyear"]

# SAS Greens_code.sas L484, L505-L508
GREEN_ANNUAL_WINDOW_START_LAG_MONTHS = 7
GREEN_ANNUAL_WINDOW_END_LAG_MONTHS = 20  # exclusive upper bound in SAS join


class TimingConvention(str, Enum):
    """How an annual characteristic CSV is expanded to monthly signal months."""

    GREEN_ANNUAL_ROLLING = "green_annual_rolling"
    HXZ_JUNE = "hxz_june"
    MONTHLY_NATIVE = "monthly_native"
    LEGACY_JUNE = "legacy_june"  # alias of HXZ_JUNE for explicit legacy exports


HXZ_JUNE_STEMS = frozenset(
    {
        "book_to_market",
        "book_to_june_market_equity",
        "cash_flow_to_price",
        "operating_profitability",
    }
)


@lru_cache(maxsize=1)
def _green_annual_stems() -> frozenset[str]:
    import sys

    builders_root = PROJECT_ROOT / "Character_Builders"
    if str(builders_root) not in sys.path:
        sys.path.insert(0, str(builders_root))
    from _shared.green_builders import ANNUAL_CHARACTER_INFO

    return frozenset(ANNUAL_CHARACTER_INFO.keys())


def add_one_month(yyyymm: int) -> int:
    year = yyyymm // 100
    month = yyyymm % 100
    next_month = month + 1
    next_year = year + (next_month == 13)
    next_month = 1 if next_month == 13 else next_month
    return next_year * 100 + next_month


def signal_yyyymm_from_timestamp(ts: pd.Timestamp) -> int:
    return int(ts.year * 100 + ts.month)


def green_signal_month_ends(datadate: pd.Timestamp) -> list[pd.Timestamp]:
    """Month-end dates eligible for one annual fiscal row under Green SAS."""
    base = pd.Timestamp(datadate)
    start = (base + pd.DateOffset(months=GREEN_ANNUAL_WINDOW_START_LAG_MONTHS)).to_period("M").to_timestamp("M")
    end_exclusive = (base + pd.DateOffset(months=GREEN_ANNUAL_WINDOW_END_LAG_MONTHS)).to_period("M").to_timestamp("M")
    if start >= end_exclusive:
        return []
    return list(pd.date_range(start, end_exclusive - pd.Timedelta(days=1), freq="ME"))


def green_signal_yyyymm_offsets() -> range:
    """Inclusive month offsets used in vectorized Green expansion (7..19)."""
    return range(
        GREEN_ANNUAL_WINDOW_START_LAG_MONTHS,
        GREEN_ANNUAL_WINDOW_END_LAG_MONTHS,
    )


def timing_convention_for_stem(stem: str) -> TimingConvention | None:
    if stem in HXZ_JUNE_STEMS:
        return TimingConvention.HXZ_JUNE
    if stem in _green_annual_stems():
        return TimingConvention.GREEN_ANNUAL_ROLLING
    return None


def expand_annual_file_june(df: pd.DataFrame, character_columns: Iterable[str]) -> pd.DataFrame:
    """HXZ / Fama-French June availability: FY ending calendar year y -> Jun y+1 .. May y+2."""
    df = df.copy()
    df["datadate"] = pd.to_datetime(df["datadate"])
    availability_year = df["datadate"].dt.year + 1

    repeated = df.loc[df.index.repeat(12), list(ANNUAL_ID_COLUMNS) + list(character_columns)].copy()
    month_offsets = np.tile(np.arange(12), len(df))
    first_signal_month = availability_year.to_numpy().repeat(12) * 12 + 5
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
    """Green rolling annual availability (Greens_code.sas L484, L505-L508)."""
    character_columns = list(character_columns)
    df = df.copy()
    df["datadate"] = pd.to_datetime(df["datadate"])

    chunks = []
    id_cols = list(ANNUAL_ID_COLUMNS) + character_columns
    for month_lag in green_signal_yyyymm_offsets():
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


# Backward-compatible name used by legacy validation scripts.
expand_annual_file = expand_annual_file_june


def expand_annual_by_convention(
    df: pd.DataFrame,
    character_columns: Iterable[str],
    convention: TimingConvention,
    crsp_month_index: pd.DataFrame | None = None,
) -> pd.DataFrame:
    if convention in (TimingConvention.HXZ_JUNE, TimingConvention.LEGACY_JUNE):
        return expand_annual_file_june(df, character_columns)
    if convention == TimingConvention.GREEN_ANNUAL_ROLLING:
        return expand_annual_file_green(df, character_columns, crsp_month_index=crsp_month_index)
    raise ValueError(f"Cannot expand annual file with convention {convention!r}")


def build_crsp_month_index_from_panels(panels: list[pd.DataFrame]) -> pd.DataFrame:
    """Union permno x signal_yyyymm from monthly-native panels (CRSP month universe)."""
    parts = []
    for panel in panels:
        if set(MONTHLY_KEYS).issubset(panel.columns):
            parts.append(panel[["permno", "signal_yyyymm"]].drop_duplicates())
    if not parts:
        return pd.DataFrame(columns=["permno", "signal_yyyymm"])
    return pd.concat(parts, ignore_index=True).drop_duplicates()


def classify_stem(stem: str, columns: Iterable[str]) -> TimingConvention | None:
    """Infer how a CSV should be normalized from its stem and columns."""
    column_set = set(columns)
    if set(MONTHLY_KEYS).issubset(column_set):
        return TimingConvention.MONTHLY_NATIVE
    if {"permno", "datadate"}.issubset(column_set):
        return timing_convention_for_stem(stem)
    return None
