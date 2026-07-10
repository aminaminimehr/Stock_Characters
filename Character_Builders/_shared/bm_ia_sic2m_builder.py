"""Datashare-convention industry-adjusted book-to-market: SIC2 x calendar month.

Reverse-engineered from the published datashare.csv (docs/gkx/
datashare_reverse_engineering.md, 2026-07-09/10 updates):

    bm_ia = bm - mean(bm) over (two-digit SIC, calendar month)

where bm is the HXZ/June-expanded annual book-to-market (the repo's
``book_to_market``) and the equal-weight industry mean is recomputed EVERY
month over that month's universe. The monthly movement of the published
bm_ia comes from staggered fiscal-year refreshes of peers and monthly
membership churn, not from the firm's own bm.

This builder is WRDS-free: it reads the already-built book_to_market.csv,
expands it to signal months with the same June convention the panel uses,
and demeans within (sic2, month). Output is a monthly-native CSV that
build_all_character_panel.py auto-merges.

Every convention here is a keyword argument (industry digits, statistic,
time key, input column) per the repo rule that no convention is hard-coded.
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
    "bm_ia_sic2m",
]


def demean_by_industry_month(
    monthly: pd.DataFrame,
    *,
    value_column: str,
    industry_column: str = "sic",
    industry_digits: int = 2,
    time_column: str = "signal_yyyymm",
    stat: str = "mean",
    output_column: str = "bm_ia_sic2m",
) -> pd.DataFrame:
    """Subtract the per-(industry, month) ``stat`` of ``value_column``.

    ``industry_digits`` truncates 4-digit SIC codes (2 -> two-digit SIC,
    matching the published datashare bm_ia convention). Rows with missing
    industry are demeaned in their own bucket (mirrors the GKX 'other' bucket).
    """
    monthly = monthly.copy()
    sic = pd.to_numeric(monthly[industry_column], errors="coerce")
    monthly["_industry"] = (sic // (10 ** (4 - industry_digits))).astype("Int64")
    grouped = monthly.groupby(["_industry", time_column], dropna=False)[value_column]
    monthly[output_column] = monthly[value_column] - grouped.transform(stat)
    return monthly.drop(columns=["_industry"])


def build_bm_ia_sic2m_character(
    bm_csv_path: Path,
    *,
    bm_column: str = "book_to_market",
    industry_digits: int = 2,
    stat: str = "mean",
    output_column: str = "bm_ia_sic2m",
) -> pd.DataFrame:
    """Monthly SIC2-demeaned book-to-market from an annual book_to_market CSV."""
    annual = pd.read_csv(bm_csv_path)
    monthly = expand_annual_file_june(annual, [bm_column])
    monthly = monthly[monthly[bm_column].notna()].copy()
    monthly = demean_by_industry_month(
        monthly,
        value_column=bm_column,
        industry_digits=industry_digits,
        stat=stat,
        output_column=output_column,
    )
    keep = [c if c != "bm_ia_sic2m" else output_column for c in MONTHLY_OUTPUT_COLUMNS]
    return monthly[keep]
