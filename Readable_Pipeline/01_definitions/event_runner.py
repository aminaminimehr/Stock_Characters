"""EAR and aeavol from daily CRSP around quarterly rdq."""
from __future__ import annotations

import numpy as np
import pandas as pd

from catalog import QUARTERLY_FUNDA_ITEMS
from ccm import attach_ccm_links_green, load_ccm_links_green
from constants import QUARTERLY_MONTH_END_LAG, QUARTERLY_MONTH_START_LAG
from monthly_runner import fetch_crsp_msf, monthly_alignment_frame
from paths import SINGLE_CHARACTERS_DIR
from quarterly_runner import fetch_quarterly_fundq, intnx_month
from wrds_io import raw_sql_with_retry, sql_date_filter
from writers import write_character


def _load_dsf(db, permnos: list[int]) -> pd.DataFrame:
    if not permnos:
        return pd.DataFrame(columns=["permno", "date", "ret", "vol"])
    permno_list = ",".join(str(int(p)) for p in permnos)
    dsf = raw_sql_with_retry(
        db,
        f"""
        SELECT permno, date, ret, vol
        FROM crsp.dsf
        WHERE permno IN ({permno_list})
          AND {sql_date_filter("date")}
        """,
    )
    dsf["date"] = pd.to_datetime(dsf["date"])
    dsf["ret"] = pd.to_numeric(dsf["ret"], errors="coerce")
    dsf["vol"] = pd.to_numeric(dsf["vol"], errors="coerce")
    dsf["permno"] = pd.to_numeric(dsf["permno"], errors="coerce").astype("int64")
    return dsf.sort_values(["permno", "date"]).reset_index(drop=True)


def _intnx_weekday_scalar(ts) -> tuple[pd.Timestamp, pd.Timestamp]:
    rdq = pd.Timestamp(ts)
    return rdq + pd.tseries.offsets.BDay(-1), rdq + pd.tseries.offsets.BDay(1)


def _earnings_events(events: pd.DataFrame, dsf: pd.DataFrame) -> pd.DataFrame:
    records = []
    for permno, events_p in events.groupby("permno", sort=False):
        dsf_p = dsf[dsf["permno"] == permno]
        if events_p.empty or dsf_p.empty:
            continue
        dates = dsf_p["date"].to_numpy(dtype="datetime64[ns]")
        rets = dsf_p["ret"].to_numpy(dtype=float)
        vols = dsf_p["vol"].to_numpy(dtype=float)
        for row in events_p.drop_duplicates(["datadate", "rdq"]).itertuples(index=False):
            win_start, win_end = _intnx_weekday_scalar(row.rdq)
            i0 = int(np.searchsorted(dates, np.datetime64(win_start), side="left"))
            i1 = int(np.searchsorted(dates, np.datetime64(win_end), side="right"))
            if i1 <= i0:
                continue
            ear = float(np.nansum(rets[i0:i1]))
            if not np.isfinite(ear):
                continue
            rdq = pd.Timestamp(row.rdq)
            pre_start = rdq + pd.tseries.offsets.BDay(-30)
            pre_end = rdq + pd.tseries.offsets.BDay(-10)
            j0 = int(np.searchsorted(dates, np.datetime64(pre_start), side="left"))
            j1 = int(np.searchsorted(dates, np.datetime64(pre_end), side="right"))
            pre_mean = float(np.nanmean(vols[j0:j1])) if j1 > j0 else np.nan
            evt_mean = float(np.nanmean(vols[i0:i1])) if i1 > i0 else np.nan
            aeavol = (evt_mean - pre_mean) / pre_mean if np.isfinite(pre_mean) and pre_mean != 0 and np.isfinite(evt_mean) else np.nan
            records.append({"permno": int(permno), "datadate": row.datadate, "rdq": row.rdq, "ear": ear, "aeavol": aeavol})
    return pd.DataFrame(records)


def _merge_events_to_monthly(monthly: pd.DataFrame, events: pd.DataFrame, value_col: str) -> pd.DataFrame:
    parts = []
    for permno, m_grp in monthly.groupby("permno", sort=False):
        events_p = events[events["permno"] == permno]
        if events_p.empty:
            continue
        m_grp = m_grp.sort_values("date").copy()
        merged = m_grp.merge(events_p, on="permno", how="inner")
        merged["win_start"] = intnx_month(merged["date"], QUARTERLY_MONTH_START_LAG, "end")
        merged["win_end"] = intnx_month(merged["date"], QUARTERLY_MONTH_END_LAG, "beg")
        merged = merged[
            merged["datadate"].notna()
            & (merged["datadate"] >= merged["win_start"])
            & (merged["datadate"] <= merged["win_end"])
        ]
        if merged.empty:
            continue
        matched = merged.sort_values(["permno", "date", "datadate"], ascending=[True, True, False]).drop_duplicates(
            ["permno", "date"], keep="first"
        )
        parts.append(matched[["permno", "permco", "date", "signal_yyyymm", "target_yyyymm", "sic", "exchcd", "shrcd", value_col]])
    if not parts:
        return pd.DataFrame()
    out = pd.concat(parts, ignore_index=True)
    return out[out[value_col].replace([np.inf, -np.inf], np.nan).notna()]


def build_event_stem(db, stem: str, use_cache: bool = True) -> pd.DataFrame:
    items = QUARTERLY_FUNDA_ITEMS["nincr"]
    comp = fetch_quarterly_fundq(db, stem, items, use_cache=use_cache)
    comp = attach_ccm_links_green(comp, load_ccm_links_green(db))
    comp = comp[comp["permno"].notna() & comp["rdq"].notna()].copy()
    comp["permno"] = pd.to_numeric(comp["permno"], errors="coerce").astype("int64")
    events = comp[["permno", "datadate", "rdq"]].drop_duplicates()
    dsf = _load_dsf(db, events["permno"].astype(int).unique().tolist())
    evt = _earnings_events(events, dsf)
    monthly = monthly_alignment_frame(fetch_crsp_msf(db, stem, use_cache=use_cache))
    monthly["date"] = pd.to_datetime(monthly["date"])
    monthly["permno"] = pd.to_numeric(monthly["permno"], errors="coerce").astype("int64")
    evt["permno"] = pd.to_numeric(evt["permno"], errors="coerce").astype("int64")
    evt["datadate"] = pd.to_datetime(evt["datadate"])
    return _merge_events_to_monthly(monthly, evt, stem)


def write_event(out: pd.DataFrame, stem: str) -> None:
    write_character(out, stem, SINGLE_CHARACTERS_DIR)
