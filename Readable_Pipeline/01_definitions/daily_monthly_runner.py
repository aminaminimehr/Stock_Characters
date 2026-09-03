"""Daily-monthly CRSP characteristics: one aggregate per stem per WRDS query."""
from __future__ import annotations

import numpy as np
import pandas as pd

from monthly_runner import fetch_crsp_msf, monthly_alignment_frame
from paths import SINGLE_CHARACTERS_DIR
from wrds_io import maybe_load_cache, maybe_save_cache, raw_sql_with_retry, sql_date_filter
from writers import write_character

_DAILY_AGG_SQL = {
    "maxret": "MAX(ret) AS maxret",
    "retvol": "STDDEV_SAMP(ret) AS retvol",
    "baspread": "AVG((askhi - bidlo) / NULLIF(((askhi + bidlo) / 2), 0)) AS baspread",
    "std_dolvol": "STDDEV_SAMP(LOG(NULLIF(ABS(prc * vol), 0))) AS std_dolvol",
    "std_turn": "STDDEV_SAMP(vol / NULLIF(shrout, 0)) AS std_turn",
    "ill": "AVG(ABS(ret) / NULLIF(ABS(prc) * vol, 0)) AS ill",
}


def _daily_sql(stem: str) -> str:
    """Build SQL that aggregates crsp.dsf daily rows to monthly for one stem."""
    if stem == "zerotrade":
        return f"""
            SELECT permno,
                   DATE_TRUNC('month', date)::date AS month_start,
                   SUM(CASE WHEN vol = 0 THEN 1 ELSE 0 END)::double precision AS countzero,
                   COUNT(*)::double precision AS ndays,
                   SUM(vol / NULLIF(shrout, 0))::double precision AS turn_sum
            FROM crsp.dsf
            WHERE {sql_date_filter("date")}
            GROUP BY permno, DATE_TRUNC('month', date)::date
        """
    agg = _DAILY_AGG_SQL[stem]
    return f"""
        SELECT permno,
               DATE_TRUNC('month', date)::date AS month_start,
               {agg}
        FROM crsp.dsf
        WHERE {sql_date_filter("date")}
        GROUP BY permno, DATE_TRUNC('month', date)::date
    """


def fetch_daily_monthly(db, stem: str, use_cache: bool = True) -> pd.DataFrame:
    """Pull monthly-aggregated daily CRSP feature for one stem."""
    if use_cache:
        cached = maybe_load_cache(stem, "dsf_monthly")
        if cached is not None:
            return cached
    daily = raw_sql_with_retry(db, _daily_sql(stem))
    daily["month_start"] = pd.to_datetime(daily["month_start"])
    daily["source_yyyymm"] = daily["month_start"].dt.year * 100 + daily["month_start"].dt.month
    if stem == "zerotrade":
        daily[stem] = (daily["countzero"] + ((1 / daily["turn_sum"]) / 480000)) * 21 / daily["ndays"]
    if use_cache:
        maybe_save_cache(stem, "dsf_monthly", daily)
    return daily


def merge_daily_to_monthly(db, stem: str, use_cache: bool = True) -> pd.DataFrame:
    """Merge lagged daily-monthly aggregate onto monthly CRSP alignment frame."""
    daily = fetch_daily_monthly(db, stem, use_cache=use_cache)
    monthly = fetch_crsp_msf(db, stem, use_cache=use_cache)
    from monthly_runner import attach_monthly_sic

    monthly = attach_monthly_sic(monthly, db, stem, use_cache=use_cache)
    monthly = monthly_alignment_frame(monthly)
    monthly["source_yyyymm"] = monthly.groupby("permno")["signal_yyyymm"].shift(1)
    # Daily aggregate for month t is merged using prior month's signal_yyyymm.
    out = monthly.merge(daily[["permno", "source_yyyymm", stem]], on=["permno", "source_yyyymm"], how="left")
    return out[out[stem].replace([np.inf, -np.inf], np.nan).notna()].copy()


def write_daily_monthly(out: pd.DataFrame, stem: str) -> None:
    """Write daily-aggregated monthly character parquet."""
    cols = ["permno", "permco", "date", "signal_yyyymm", "target_yyyymm", "sic", "exchcd", "shrcd", stem]
    cols = [c for c in cols if c in out.columns]
    write_character(out[cols], stem, SINGLE_CHARACTERS_DIR)
