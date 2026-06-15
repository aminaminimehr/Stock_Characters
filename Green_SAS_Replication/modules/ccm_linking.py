"""CCM linking and exchange/share-code screening (Greens_code.sas L409-448)."""
from __future__ import annotations

import pandas as pd
import wrds

from wrds_utils import (
    attach_ccm_links_green,
    debug_log,
    load_ccm_links_green,
    retry_wrds_query,
)


_REQUIRED_MSE_COLS = ("date", "permno", "exchcd", "shrcd", "siccd")
_REQUIRED_FILTER_COLS = ("exchcd", "shrcd", "permno", "datadate", "exchstdt", "exchedt")


def _require_columns(df: pd.DataFrame, required: tuple[str, ...], context: str) -> None:
    missing = [col for col in required if col not in df.columns]
    if missing:
        available = ", ".join(sorted(df.columns))
        raise KeyError(f"{context}: missing {missing}. Available columns: {available}")


def _normalize_mse_column_names(df: pd.DataFrame) -> pd.DataFrame:
    """Resolve pandas merge suffixes so CRSP mseall fields are plain exchcd/shrcd/siccd."""
    out = df.copy()
    for col in ("exchcd", "shrcd", "siccd"):
        if col in out.columns:
            continue
        for candidate in (f"{col}_y", f"{col}_mse", f"{col}_bounds"):
            if candidate in out.columns:
                out = out.rename(columns={candidate: col})
                break
        else:
            if f"{col}_x" in out.columns:
                out = out.rename(columns={f"{col}_x": col})
    return out


def screen_exchange_history(db: wrds.Connection, comp_linked: pd.DataFrame) -> pd.DataFrame:
    """Replicate mseall exchange window join and filters (Greens_code.sas L428-448)."""
    mse = retry_wrds_query(
        db,
        lambda conn: conn.raw_sql("""
            SELECT date, permno, exchcd, shrcd, siccd
            FROM crsp.mseall
            WHERE exchcd IN (1, 2, 3) OR shrcd IN (10, 11, 12)
        """),
    )
    mse.columns = [str(c).lower() for c in mse.columns]
    debug_log(f"mseall query columns: {list(mse.columns)} rows={len(mse):,}")

    _require_columns(mse, _REQUIRED_MSE_COLS, "crsp.mseall query")

    mse["date"] = pd.to_datetime(mse["date"])
    mse = mse.sort_values(["permno", "exchcd", "date"]).drop_duplicates(
        ["permno", "exchcd", "date"], keep="first"
    )

    # SAS: group by permno, exchcd; keep shrcd/siccd from mseall (select * ... group by)
    bounds = (
        mse.groupby(["permno", "exchcd"], as_index=False)
        .agg(
            exchstdt=("date", "min"),
            exchedt=("date", "max"),
            shrcd=("shrcd", "first"),
            siccd=("siccd", "first"),
        )
    )
    bounds = bounds.sort_values(["permno", "exchcd"]).drop_duplicates(["permno", "exchcd"], keep="first")
    debug_log(f"mseall bounds columns: {list(bounds.columns)} rows={len(bounds):,}")

    rows_before = len(comp_linked)
    temp = comp_linked.merge(bounds, on="permno", how="left", suffixes=("", "_mse"))
    debug_log(f"after permno merge columns: {list(temp.columns)} rows={len(temp):,}")

    temp = _normalize_mse_column_names(temp)
    _require_columns(temp, _REQUIRED_FILTER_COLS, "after mseall merge")

    # SAS: exchstdt <= datadate <= exchedt
    in_window = (temp["exchstdt"] <= temp["datadate"]) & (temp["datadate"] <= temp["exchedt"])
    temp = temp[in_window].copy()
    debug_log(f"rows in exchange date window: {len(temp):,} (from {rows_before:,} linked annual)")

    temp = temp[temp["exchcd"].isin([1, 2, 3]) & temp["shrcd"].isin([10, 11]) & temp["permno"].notna()]
    debug_log(f"rows after exchcd/shrcd filter: {len(temp):,}")

    temp = temp.drop(columns=["shrcd", "date", "siccd", "exchstdt", "exchedt"], errors="ignore")
    return temp.sort_values(["gvkey", "datadate"]).drop_duplicates(["gvkey", "datadate"], keep="first")


def link_annual_to_crsp(
    db: wrds.Connection,
    annual: pd.DataFrame,
) -> pd.DataFrame:
    link = load_ccm_links_green(db)
    linked = attach_ccm_links_green(annual, link)
    return screen_exchange_history(db, linked)


def run_ccm_annual(db: wrds.Connection, annual: pd.DataFrame) -> pd.DataFrame:
    return link_annual_to_crsp(db, annual)
