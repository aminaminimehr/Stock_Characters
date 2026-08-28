"""Datashare bm_ia: SIC2 x calendar-month demean of HXZ June-expanded bm.

bm_ia = bm - mean(bm) over (two-digit SIC, signal_yyyymm), recomputed every month.
Reads bm.csv (built by HXZ_BM_Generalized) — no WRDS access required.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from Character_Panels.timing import expand_annual_file_june  # noqa: E402

MONTHLY_OUTPUT_COLUMNS = [
    "permno",
    "signal_yyyymm",
    "target_yyyymm",
    "sic",
    "bm_ia",
]


def demean_by_industry_month(
    monthly: pd.DataFrame,
    *,
    value_column: str = "bm",
    industry_column: str = "sic",
    time_column: str = "signal_yyyymm",
    output_column: str = "bm_ia",
) -> pd.DataFrame:
    """Subtract equal-weight SIC2 x month mean (datashare convention)."""
    monthly = monthly.copy()
    sic = pd.to_numeric(monthly[industry_column], errors="coerce")
    monthly["_industry"] = (sic // 100).astype("Int64")
    grouped = monthly.groupby(["_industry", time_column], dropna=False)[value_column]
    monthly[output_column] = monthly[value_column] - grouped.transform("mean")
    return monthly.drop(columns=["_industry"])


def build_bm_ia_character(bm_csv_path: Path) -> pd.DataFrame:
    """Monthly SIC2-demeaned book-to-market from annual bm.csv."""
    annual = pd.read_csv(bm_csv_path)
    monthly = expand_annual_file_june(annual, ["bm"])
    monthly = monthly[monthly["bm"].notna()].copy()
    monthly = demean_by_industry_month(monthly)
    return monthly[MONTHLY_OUTPUT_COLUMNS]
