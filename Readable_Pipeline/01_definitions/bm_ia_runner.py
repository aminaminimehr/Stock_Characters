"""bm_ia: SIC2 x month demean of HXZ bm (no WRDS)."""
from __future__ import annotations

import pandas as pd

from paths import SINGLE_CHARACTERS_DIR
from timing import expand_annual_file_june
from writers import write_character


def demean_by_industry_month(
    monthly: pd.DataFrame,
    *,
    value_column: str = "bm",
    industry_column: str = "sic",
    time_column: str = "signal_yyyymm",
    output_column: str = "bm_ia",
) -> pd.DataFrame:
    """Industry-adjust bm by subtracting SIC2×month mean (HXZ bm_ia definition)."""
    monthly = monthly.copy()
    sic = pd.to_numeric(monthly[industry_column], errors="coerce")
    monthly["_industry"] = (sic // 100).astype("Int64")
    grouped = monthly.groupby(["_industry", time_column], dropna=False)[value_column]
    monthly[output_column] = monthly[value_column] - grouped.transform("mean")
    return monthly.drop(columns=["_industry"])


def build_bm_ia_from_parquet(bm_parquet_path) -> pd.DataFrame:
    """Build bm_ia from existing bm parquet: June expand, then industry demean."""
    annual = pd.read_parquet(bm_parquet_path)
    monthly = expand_annual_file_june(annual, ["bm"])
    monthly = monthly[monthly["bm"].notna()].copy()
    monthly = demean_by_industry_month(monthly)
    return monthly[["permno", "signal_yyyymm", "target_yyyymm", "sic", "bm_ia"]]


def build_bm_ia_from_csv(bm_csv_path) -> pd.DataFrame:
    """Legacy alias; readable pipeline stores bm as Parquet."""
    return build_bm_ia_from_parquet(bm_csv_path)


def write_bm_ia(out: pd.DataFrame) -> None:
    """Write bm_ia character parquet."""
    write_character(out, "bm_ia", SINGLE_CHARACTERS_DIR)
