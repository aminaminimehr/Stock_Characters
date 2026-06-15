"""CCM linking and exchange/share-code screening (Greens_code.sas L409-448)."""
from __future__ import annotations

import pandas as pd
import wrds

from wrds_utils import attach_ccm_links_green, load_ccm_links_green, retry_wrds_query, sql_between_date


def screen_exchange_history(db: wrds.Connection, comp_linked: pd.DataFrame) -> pd.DataFrame:
    """Replicate mseall exchange window join and filters."""
    mse = retry_wrds_query(
        db,
        lambda conn: conn.raw_sql("""
            SELECT date, permno, exchcd, shrcd, siccd
            FROM crsp.mseall
            WHERE exchcd IN (1, 2, 3) OR shrcd IN (10, 11, 12)
        """),
    )
    mse["date"] = pd.to_datetime(mse["date"])
    mse = mse.sort_values(["permno", "exchcd", "date"]).drop_duplicates(
        ["permno", "exchcd", "date"], keep="first"
    )
    bounds = (
        mse.groupby(["permno", "exchcd"], as_index=False)
        .agg(exchstdt=("date", "min"), exchedt=("date", "max"))
    )
    bounds = bounds.sort_values(["permno", "exchcd"]).drop_duplicates(["permno", "exchcd"], keep="first")

    temp = comp_linked.merge(bounds, on="permno", how="left")
    in_window = (temp["exchstdt"] <= temp["datadate"]) & (temp["datadate"] <= temp["exchedt"])
    temp = temp[in_window].copy()
    temp = temp[temp["exchcd"].isin([1, 2, 3]) & temp["shrcd"].isin([10, 11]) & temp["permno"].notna()]
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
