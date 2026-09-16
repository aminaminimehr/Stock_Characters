"""Flat procedural builder: EAR and aeavol from daily CRSP around quarterly rdq.

Output characters (GKX datashare names):
  ear    = Earnings Announcement Return
           cumulative daily return over [-1, +1] business days around rdq
  aeavol = Abnormal Earnings Announcement Volume
           (event-window mean volume - pre-window mean volume) / pre-window mean volume
           event window: [-1, +1] BD around rdq; pre-window: [-30, -10] BD before rdq

Sample note: rdq is only reliably populated from ~1975, so ear/aeavol exist from ~1975 onward.

Baked-in conventions (from config/conventions.py):
  SAMPLE_START = 1950-01-01 (no SAMPLE_END upper bound)
  CCM: linktype LIKE 'L%%', linkprim IN ('P','C')
  CRSP universe: exchcd IN (1, 2, 3); no shrcd filter
  fundq floor: datadate >= 1975-01-01
  annual SIC expansion lags: 7..19 months after fiscal datadate
  quarterly event-to-monthly mapping: Green window -10/-5 months on datadate
"""
from __future__ import annotations

import os
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
import wrds

PIPELINE_ROOT = Path(__file__).resolve().parents[1]
if str(PIPELINE_ROOT) not in sys.path:
    sys.path.insert(0, str(PIPELINE_ROOT))

from config.conventions import CACHE_DIR, CHARACTERS_DIR, MONTHLY_ID_COLUMNS  # noqa: E402

#######################################################################################################################
# Connect to WRDS and ensure output directories exist
#######################################################################################################################

_wrds_user = os.environ.get("WRDS_USERNAME") or os.environ.get("WRDS_USER")
conn = wrds.Connection(wrds_username=_wrds_user) if _wrds_user else wrds.Connection()

CACHE_DIR.mkdir(parents=True, exist_ok=True)
CHARACTERS_DIR.mkdir(parents=True, exist_ok=True)

#######################################################################################################################
# Pull comp.fundq quarterly earnings announcement dates (rdq)
# WRDS tables:
#   comp.company  (c): gvkey, sic
#   comp.fundq    (f): gvkey, datadate, rdq
# Filters: standard Compustat (INDL/STD/D/C), ibq IS NOT NULL, datadate >= 1975-01-01
#######################################################################################################################

fundq_cache = CACHE_DIR / "event_fundq.parquet"
if fundq_cache.exists():
    print(f"Loading cached fundq from {fundq_cache}", flush=True)
    comp = pd.read_parquet(fundq_cache)
else:
    print("Pulling comp.fundq (rdq events)...", flush=True)
    fundq_sql = """
        SELECT c.gvkey,
               f.datadate,
               f.rdq,
               c.sic
        FROM comp.company AS c
        JOIN comp.fundq AS f ON c.gvkey = f.gvkey
        WHERE f.indfmt = 'INDL' AND f.datafmt = 'STD' AND f.popsrc = 'D' AND f.consol = 'C'
          AND f.ibq IS NOT NULL
          AND f.datadate >= DATE '1975-01-01'
    """
    for _attempt in range(2):
        try:
            comp = conn.raw_sql(fundq_sql)
            break
        except Exception as exc:
            if _attempt == 0:
                print(f"WRDS query failed: {exc}; resetting connection and retrying in 120s...", flush=True)
                try:
                    conn.connection.rollback()
                except Exception:
                    pass
                try:
                    conn.close()
                    conn.connect()
                except Exception as e2:
                    print(f"  reconnect failed: {e2}", flush=True)
                time.sleep(120)
            else:
                raise
    comp["rdq"] = pd.to_datetime(comp["rdq"], errors="coerce")
    comp["datadate"] = pd.to_datetime(comp["datadate"])
    comp = (
        comp.sort_values(["gvkey", "datadate"])
        .drop_duplicates(["gvkey", "datadate"], keep="last")
    )
    comp.to_parquet(fundq_cache, index=False)
    print(f"Cached fundq -> {fundq_cache}", flush=True)

# Ensure datetime types whether loaded from cache or freshly pulled
comp["rdq"] = pd.to_datetime(comp["rdq"], errors="coerce")
comp["datadate"] = pd.to_datetime(comp["datadate"])

#######################################################################################################################
# Pull CRSP-Compustat Merged (CCM) link table
# WRDS table: crsp.ccmxpf_linktable
#   gvkey      = Compustat global company key
#   lpermno    = CRSP permno (permanent security number)
#   lpermco    = CRSP permco (permanent company number)
#   linkdt     = link start date
#   linkenddt  = link end date
# Filters: linktype LIKE 'L%%', linkprim IN ('P','C'), lpermno IS NOT NULL
#######################################################################################################################

print("Pulling CCM links...", flush=True)
ccm_sql = """
    SELECT gvkey, lpermno AS permno, lpermco AS permco, linkdt, linkenddt
    FROM crsp.ccmxpf_linktable
    WHERE linktype LIKE 'L%%'
      AND linkprim IN ('P', 'C')
      AND lpermno IS NOT NULL
"""
for _attempt in range(2):
    try:
        link = conn.raw_sql(ccm_sql)
        break
    except Exception as exc:
        if _attempt == 0:
            print(f"WRDS query failed: {exc}; resetting connection and retrying in 120s...", flush=True)
            try:
                conn.connection.rollback()
            except Exception:
                pass
            try:
                conn.close()
                conn.connect()
            except Exception as e2:
                print(f"  reconnect failed: {e2}", flush=True)
            time.sleep(120)
        else:
            raise

link["linkdt"] = pd.to_datetime(link["linkdt"])
link["linkenddt"] = pd.to_datetime(link["linkenddt"])
link["permno"] = pd.to_numeric(link["permno"], errors="coerce").astype("Int64")
link = link.sort_values(["gvkey", "linkdt"])

#######################################################################################################################
# Attach CCM links to fundq: keep rows where datadate falls inside [linkdt, linkenddt]
#######################################################################################################################

print("Merging CCM links onto fundq...", flush=True)
comp = comp.merge(link, on="gvkey", how="inner")
linkdt_ok = comp["linkdt"].isna() | (comp["linkdt"] <= comp["datadate"])
linkend_ok = comp["linkenddt"].isna() | (comp["datadate"] <= comp["linkenddt"])
comp = comp[linkdt_ok & linkend_ok & comp["permno"].notna()].copy()
comp["permno"] = pd.to_numeric(comp["permno"], errors="coerce").astype("int64")
if "permco" in comp.columns:
    comp["permco"] = pd.to_numeric(comp["permco"], errors="coerce").astype("Int64")
comp = comp.drop(columns=["linkdt", "linkenddt"], errors="ignore")

# Event universe: one row per (permno, datadate, rdq) with valid announcement date
comp = comp[comp["rdq"].notna()].copy()
events = comp[["permno", "datadate", "rdq"]].drop_duplicates()

#######################################################################################################################
# Pull crsp.dsf daily returns and volume for event permnos (batched IN lists of 4000)
# WRDS table: crsp.dsf
#   permno = CRSP permanent security number
#   date   = trading date
#   ret    = daily return (used for ear)
#   vol    = daily share volume (used for aeavol)
# Filter: date >= 1950-01-01
#######################################################################################################################

dsf_cache = CACHE_DIR / "event_dsf.parquet"
permno_list = events["permno"].astype(int).unique().tolist()
if dsf_cache.exists():
    print(f"Loading cached dsf from {dsf_cache}", flush=True)
    dsf = pd.read_parquet(dsf_cache)
else:
    print(f"Pulling crsp.dsf for {len(permno_list):,} event permnos...", flush=True)
    dsf_chunks = []
    batch_size = 4000
    for batch_start in range(0, len(permno_list), batch_size):
        batch = permno_list[batch_start : batch_start + batch_size]
        permno_in_list = ",".join(str(int(p)) for p in batch)
        dsf_sql = f"""
            SELECT permno, date, ret, vol
            FROM crsp.dsf
            WHERE permno IN ({permno_in_list})
              AND date >= DATE '1950-01-01'
        """
        for _attempt in range(2):
            try:
                dsf_batch = conn.raw_sql(dsf_sql)
                break
            except Exception as exc:
                if _attempt == 0:
                    print(f"WRDS query failed: {exc}; resetting connection and retrying in 120s...", flush=True)
                    try:
                        conn.connection.rollback()
                    except Exception:
                        pass
                    try:
                        conn.close()
                        conn.connect()
                    except Exception as e2:
                        print(f"  reconnect failed: {e2}", flush=True)
                    time.sleep(120)
                else:
                    raise
        dsf_chunks.append(dsf_batch)
        print(f"  dsf batch {batch_start // batch_size + 1} / {(len(permno_list) + batch_size - 1) // batch_size}", flush=True)
    dsf = pd.concat(dsf_chunks, ignore_index=True)
    dsf["date"] = pd.to_datetime(dsf["date"])
    dsf["ret"] = pd.to_numeric(dsf["ret"], errors="coerce")
    dsf["vol"] = pd.to_numeric(dsf["vol"], errors="coerce")
    dsf["permno"] = pd.to_numeric(dsf["permno"], errors="coerce").astype("int64")
    dsf = dsf.sort_values(["permno", "date"]).reset_index(drop=True)
    dsf.to_parquet(dsf_cache, index=False)
    print(f"Cached dsf -> {dsf_cache}", flush=True)

#######################################################################################################################
# Compute ear (Earnings Announcement Return) and aeavol (Abnormal Earnings Announcement Volume)
#   ear:    sum of daily ret over [-1, +1] business days around rdq
#   aeavol: (mean vol in event window - mean vol in pre-window) / mean vol in pre-window
#           pre-window = business days [-30, -10] before rdq
#######################################################################################################################

print("Computing ear and aeavol around rdq...", flush=True)
records = []
for permno, events_p in events.groupby("permno", sort=False):
    dsf_p = dsf[dsf["permno"] == permno]
    if events_p.empty or dsf_p.empty:
        continue
    dates = dsf_p["date"].to_numpy(dtype="datetime64[ns]")
    rets = dsf_p["ret"].to_numpy(dtype=float)
    vols = dsf_p["vol"].to_numpy(dtype=float)
    for row in events_p.drop_duplicates(["datadate", "rdq"]).itertuples(index=False):
        rdq_ts = pd.Timestamp(row.rdq)
        win_start = rdq_ts + pd.tseries.offsets.BDay(-1)
        win_end = rdq_ts + pd.tseries.offsets.BDay(1)
        i0 = int(np.searchsorted(dates, np.datetime64(win_start), side="left"))
        i1 = int(np.searchsorted(dates, np.datetime64(win_end), side="right"))
        if i1 <= i0:
            continue
        ear = float(np.nansum(rets[i0:i1]))
        if not np.isfinite(ear):
            continue
        pre_start = rdq_ts + pd.tseries.offsets.BDay(-30)
        pre_end = rdq_ts + pd.tseries.offsets.BDay(-10)
        j0 = int(np.searchsorted(dates, np.datetime64(pre_start), side="left"))
        j1 = int(np.searchsorted(dates, np.datetime64(pre_end), side="right"))
        pre_mean = float(np.nanmean(vols[j0:j1])) if j1 > j0 else np.nan
        evt_mean = float(np.nanmean(vols[i0:i1])) if i1 > i0 else np.nan
        if np.isfinite(pre_mean) and pre_mean != 0 and np.isfinite(evt_mean):
            aeavol = (evt_mean - pre_mean) / pre_mean
        else:
            aeavol = np.nan
        records.append(
            {
                "permno": int(permno),
                "datadate": row.datadate,
                "rdq": row.rdq,
                "ear": ear,
                "aeavol": aeavol,
            }
        )
evt = pd.DataFrame(records)

#######################################################################################################################
# Pull crsp.msf monthly stock file joined to crsp.msenames for exchange/share codes
# WRDS tables:
#   crsp.msf      (m): permno, permco, date, ret
#   crsp.msenames (n): permno, namedt, nameenddt, exchcd, shrcd
# Filters: exchcd IN (1,2,3), date >= 1950-01-01; ret used only to drop missing-return rows
#######################################################################################################################

msf_cache = CACHE_DIR / "event_msf.parquet"
if msf_cache.exists():
    print(f"Loading cached msf from {msf_cache}", flush=True)
    msf = pd.read_parquet(msf_cache)
else:
    print("Pulling crsp.msf...", flush=True)
    msf_sql = """
        SELECT m.permno, m.permco, m.date, m.ret,
               n.exchcd, n.shrcd
        FROM crsp.msf AS m
        JOIN crsp.msenames AS n
          ON m.permno = n.permno
         AND n.namedt <= m.date
         AND m.date <= COALESCE(n.nameendt, DATE '9999-12-31')
        WHERE n.exchcd IN (1, 2, 3)
          AND m.date >= DATE '1950-01-01'
    """
    for _attempt in range(2):
        try:
            msf = conn.raw_sql(msf_sql)
            break
        except Exception as exc:
            if _attempt == 0:
                print(f"WRDS query failed: {exc}; resetting connection and retrying in 120s...", flush=True)
                try:
                    conn.connection.rollback()
                except Exception:
                    pass
                try:
                    conn.close()
                    conn.connect()
                except Exception as e2:
                    print(f"  reconnect failed: {e2}", flush=True)
                time.sleep(120)
            else:
                raise
    msf = msf.sort_values(["permno", "date"]).copy()
    msf["date"] = pd.to_datetime(msf["date"])
    msf["ret"] = pd.to_numeric(msf["ret"], errors="coerce")
    msf["signal_yyyymm"] = msf["date"].dt.year * 100 + msf["date"].dt.month
    sig_year = msf["signal_yyyymm"] // 100
    sig_month = msf["signal_yyyymm"] % 100
    msf["target_yyyymm"] = np.where(
        sig_month == 12,
        (sig_year + 1) * 100 + 1,
        sig_year * 100 + sig_month + 1,
    )
    msf = msf[msf["ret"].notna()].copy()
    msf.to_parquet(msf_cache, index=False)
    print(f"Cached msf -> {msf_cache}", flush=True)

monthly = msf[["permno", "permco", "date", "signal_yyyymm", "target_yyyymm", "exchcd", "shrcd"]].drop_duplicates(
    ["permno", "date"]
)

#######################################################################################################################
# Pull comp.funda annual SIC for monthly attachment (Green lags 7-19 after fiscal datadate)
# WRDS tables:
#   comp.company (c): gvkey, sic
#   comp.funda   (f): gvkey, datadate, fyear
# Filters: standard annual Compustat, at/prcc_f/ni NOT NULL, datadate >= 1950-01-01
#######################################################################################################################

sic_cache = CACHE_DIR / "event_sic_timing.parquet"
if sic_cache.exists():
    print(f"Loading cached annual SIC from {sic_cache}", flush=True)
    annual_sic = pd.read_parquet(sic_cache)
else:
    print("Pulling comp.funda SIC for monthly attachment...", flush=True)
    funda_sic_sql = """
        SELECT c.gvkey, f.datadate, f.fyear, c.sic
        FROM comp.company AS c
        JOIN comp.funda AS f ON c.gvkey = f.gvkey
        WHERE f.indfmt = 'INDL'
          AND f.datafmt = 'STD'
          AND f.popsrc = 'D'
          AND f.consol = 'C'
          AND f.at IS NOT NULL
          AND f.prcc_f IS NOT NULL
          AND f.ni IS NOT NULL
          AND f.datadate >= DATE '1950-01-01'
    """
    for _attempt in range(2):
        try:
            sic_comp = conn.raw_sql(funda_sic_sql)
            break
        except Exception as exc:
            if _attempt == 0:
                print(f"WRDS query failed: {exc}; resetting connection and retrying in 120s...", flush=True)
                try:
                    conn.connection.rollback()
                except Exception:
                    pass
                try:
                    conn.close()
                    conn.connect()
                except Exception as e2:
                    print(f"  reconnect failed: {e2}", flush=True)
                time.sleep(120)
            else:
                raise
    sic_comp["datadate"] = pd.to_datetime(sic_comp["datadate"])
    sic_comp = (
        sic_comp.sort_values(["gvkey", "datadate"])
        .drop_duplicates(["gvkey", "datadate"], keep="last")
    )
    sic_comp = sic_comp.merge(link, on="gvkey", how="inner")
    linkdt_ok = sic_comp["linkdt"].isna() | (sic_comp["linkdt"] <= sic_comp["datadate"])
    linkend_ok = sic_comp["linkenddt"].isna() | (sic_comp["datadate"] <= sic_comp["linkenddt"])
    sic_comp = sic_comp[linkdt_ok & linkend_ok & sic_comp["permno"].notna()].copy()
    sic_comp["permno"] = pd.to_numeric(sic_comp["permno"], errors="coerce").astype("int64")
    if "permco" in sic_comp.columns:
        sic_comp["permco"] = pd.to_numeric(sic_comp["permco"], errors="coerce").astype("Int64")
    sic_comp = sic_comp.drop(columns=["linkdt", "linkenddt"], errors="ignore")
    annual_sic = sic_comp[["permno", "permco", "gvkey", "datadate", "sic", "fyear"]].copy()
    annual_sic.to_parquet(sic_cache, index=False)
    print(f"Cached annual SIC -> {sic_cache}", flush=True)

#######################################################################################################################
# Expand annual SIC to monthly signal months: lags 7..19 months after fiscal datadate
#######################################################################################################################

annual_sic = annual_sic.copy()
annual_sic["datadate"] = pd.to_datetime(annual_sic["datadate"])
sic_expanded_chunks = []
for month_lag in range(7, 20):
    sic_chunk = annual_sic[["permno", "datadate", "sic"]].copy()
    signal_dates = (sic_chunk["datadate"] + pd.DateOffset(months=month_lag)).dt.to_period("M").dt.to_timestamp("M")
    sic_chunk["signal_yyyymm"] = (signal_dates.dt.year * 100 + signal_dates.dt.month).astype(int)
    sic_expanded_chunks.append(sic_chunk)
sic_monthly = pd.concat(sic_expanded_chunks, ignore_index=True)
sic_monthly = (
    sic_monthly.sort_values(["permno", "signal_yyyymm", "datadate"])
    .drop_duplicates(["permno", "signal_yyyymm"], keep="last")
)
crsp_idx = monthly[["permno", "signal_yyyymm"]].drop_duplicates()
sic_monthly = sic_monthly.merge(
    crsp_idx,
    on=["permno", "signal_yyyymm"],
    how="inner",
)
sic_monthly = sic_monthly[["permno", "signal_yyyymm", "sic"]]
monthly = monthly.merge(sic_monthly, on=["permno", "signal_yyyymm"], how="left")

#######################################################################################################################
# Map quarterly event values onto monthly CRSP rows (Green window -10/-5 on datadate)
# For each monthly row at date t, pick the most recent event with datadate in [t-10mo, t-5mo]
#######################################################################################################################

print("Mapping events to monthly CRSP (Green window -10/-5 on datadate)...", flush=True)
monthly = monthly.copy()
monthly["date"] = pd.to_datetime(monthly["date"])
monthly["permno"] = pd.to_numeric(monthly["permno"], errors="coerce").astype("int64")

evt_map = evt[["permno", "datadate", "ear", "aeavol"]].copy()
evt_map["permno"] = pd.to_numeric(evt_map["permno"], errors="coerce").astype("int64")
evt_map["datadate"] = pd.to_datetime(evt_map["datadate"])

panel_parts = []
evt_by_permno = {int(p): grp.sort_values("datadate") for p, grp in evt_map.groupby("permno", sort=False)}
for permno, m_grp in monthly.groupby("permno", sort=False):
    e_grp = evt_by_permno.get(int(permno))
    if e_grp is None or e_grp.empty:
        continue
    m_grp = m_grp.sort_values("date").copy()
    win_start = (pd.to_datetime(m_grp["date"]) + pd.DateOffset(months=-10)).dt.to_period("M").dt.to_timestamp("h")
    win_end = (pd.to_datetime(m_grp["date"]) + pd.DateOffset(months=-5)).dt.to_period("M").dt.to_timestamp("s")
    e_dates = e_grp["datadate"].to_numpy(dtype="datetime64[ns]")
    picked_idx = np.full(len(m_grp), -1, dtype=int)
    for i, (ws, we) in enumerate(zip(win_start.to_numpy(), win_end.to_numpy())):
        in_window = (e_dates >= ws) & (e_dates <= we)
        if in_window.any():
            picked_idx[i] = int(np.where(in_window)[0][-1])
    valid = picked_idx >= 0
    if not valid.any():
        continue
    part = m_grp.loc[valid].copy()
    picked_rows = e_grp.iloc[picked_idx[valid]]
    part["ear"] = picked_rows["ear"].to_numpy()
    part["aeavol"] = picked_rows["aeavol"].to_numpy()
    panel_parts.append(part)

if panel_parts:
    panel = pd.concat(panel_parts, ignore_index=True)
    panel = panel[panel["ear"].replace([np.inf, -np.inf], np.nan).notna()]
    id_cols = [c for c in MONTHLY_ID_COLUMNS if c in panel.columns or c == "sic"]
    panel = panel[[c for c in id_cols if c in panel.columns] + ["ear", "aeavol"]]
else:
    panel = pd.DataFrame()

#######################################################################################################################
# Write event.parquet: monthly panel with ear and aeavol
#######################################################################################################################

out_cols = [c for c in MONTHLY_ID_COLUMNS if c in panel.columns] + ["ear", "aeavol"]
out_path = CHARACTERS_DIR / "event.parquet"
panel[out_cols].to_parquet(out_path, index=False)
print(f"Wrote {len(panel):,} rows -> {out_path}", flush=True)
