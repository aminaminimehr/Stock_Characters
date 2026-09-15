"""Flat procedural builder: EAR and aeavol from daily CRSP around quarterly rdq."""
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

from config.conventions import (  # noqa: E402
    ANNUAL_ROLLING_END_LAG,
    ANNUAL_ROLLING_START_LAG,
    CACHE_DIR,
    CCM_LINKPRIM,
    CCM_LINKTYPES,
    CHARACTERS_DIR,
    CRSP_EXCHCD,
    CRSP_SHRCD,
    MONTHLY_ID_COLUMNS,
    QUARTERLY_MONTH_END_LAG,
    QUARTERLY_MONTH_START_LAG,
    SAMPLE_END,
    SAMPLE_START,
    SIC_SOURCE,
)

EVENT_VALUE_COLUMNS = ("ear", "aeavol")

ANNUAL_COMPUSTAT_WHERE = """
    f.indfmt = 'INDL'
    AND f.datafmt = 'STD'
    AND f.popsrc = 'D'
    AND f.consol = 'C'
    AND f.at IS NOT NULL
    AND f.prcc_f IS NOT NULL
    AND f.ni IS NOT NULL
"""


#######################################################################################################################
#                                                    Helper functions                                                 #
#######################################################################################################################


def wrds_query(conn, sql: str) -> pd.DataFrame:
    """Execute SQL on WRDS; one retry after 120 seconds on failure."""
    last_exc = None
    for attempt in range(2):
        try:
            return conn.raw_sql(sql)
        except Exception as exc:
            last_exc = exc
            if attempt == 0:
                print(f"WRDS query failed: {exc}; retrying in 120s...", flush=True)
                time.sleep(120)
            else:
                raise
    raise last_exc


def add_one_month(yyyymm: int) -> int:
    year = yyyymm // 100
    month = yyyymm % 100
    next_month = month + 1
    next_year = year + (next_month == 13)
    next_month = 1 if next_month == 13 else next_month
    return next_year * 100 + next_month


def sql_date_filter(column: str, table_alias: str | None = None) -> str:
    col = f"{table_alias}.{column}" if table_alias else column
    parts = []
    if SAMPLE_START:
        parts.append(f"{col} >= DATE '{SAMPLE_START}'")
    if SAMPLE_END:
        parts.append(f"{col} <= DATE '{SAMPLE_END}'")
    return " AND ".join(parts) if parts else "TRUE"


def crsp_universe_filter(table_alias: str = "n") -> str:
    parts = []
    if str(CRSP_SHRCD).strip().upper() not in ("", "ALL", "*"):
        codes = ", ".join(v.strip() for v in str(CRSP_SHRCD).split(",") if v.strip())
        parts.append(f"{table_alias}.shrcd IN ({codes})")
    if str(CRSP_EXCHCD).strip().upper() not in ("", "ALL", "*"):
        codes = ", ".join(v.strip() for v in str(CRSP_EXCHCD).split(",") if v.strip())
        parts.append(f"{table_alias}.exchcd IN ({codes})")
    return " AND ".join(parts) if parts else "TRUE"


def dedupe_compustat(comp: pd.DataFrame) -> pd.DataFrame:
    comp = comp.copy()
    comp["datadate"] = pd.to_datetime(comp["datadate"])
    if "sic" in comp.columns:
        sic_str = (
            pd.to_numeric(comp["sic"], errors="coerce")
            .astype("Int64")
            .astype(str)
            .str.replace("<NA>", "", regex=False)
        )
        comp["sic2"] = sic_str.str[:2].replace("", np.nan)
    return (
        comp.sort_values(["gvkey", "datadate"])
        .drop_duplicates(["gvkey", "datadate"], keep="last")
        .sort_values(["gvkey", "datadate"])
    )


def intnx_month(ts: pd.Series, n: int, alignment: str = "end") -> pd.Series:
    shifted = pd.to_datetime(ts) + pd.DateOffset(months=n)
    if alignment == "beg":
        return shifted.dt.to_period("M").dt.to_timestamp("s")
    return shifted.dt.to_period("M").dt.to_timestamp("h")


def load_ccm_links(conn) -> pd.DataFrame:
    linkprim_clause = ""
    if str(CCM_LINKPRIM).strip().upper() not in ("", "ALL", "*"):
        codes = ", ".join(f"'{c.strip()}'" for c in str(CCM_LINKPRIM).split(",") if c.strip())
        linkprim_clause = f" AND linkprim IN ({codes})"
    if str(CCM_LINKTYPES).strip().upper() in ("L*", "L"):
        linktype_clause = "linktype LIKE 'L%%'"
    else:
        codes = ", ".join(f"'{c.strip()}'" for c in str(CCM_LINKTYPES).split(",") if c.strip())
        linktype_clause = f"linktype IN ({codes})"
    link = wrds_query(conn, f"""
        SELECT gvkey, lpermno AS permno, lpermco AS permco, linkdt, linkenddt, linktype
        FROM crsp.ccmxpf_linktable
        WHERE {linktype_clause}
          {linkprim_clause}
          AND lpermno IS NOT NULL
    """)
    link["linkdt"] = pd.to_datetime(link["linkdt"])
    link["linkenddt"] = pd.to_datetime(link["linkenddt"])
    link["permno"] = pd.to_numeric(link["permno"], errors="coerce").astype("Int64")
    return link.sort_values(["gvkey", "linkdt"])


def attach_ccm_links(comp: pd.DataFrame, link: pd.DataFrame) -> pd.DataFrame:
    merged = comp.merge(link, on="gvkey", how="inner")
    linkdt_ok = merged["linkdt"].isna() | (merged["linkdt"] <= merged["datadate"])
    linkend_ok = merged["linkenddt"].isna() | (merged["datadate"] <= merged["linkenddt"])
    out = merged[linkdt_ok & linkend_ok & merged["permno"].notna()].copy()
    out["permno"] = pd.to_numeric(out["permno"], errors="coerce").astype("int64")
    if "permco" in out.columns:
        out["permco"] = pd.to_numeric(out["permco"], errors="coerce").astype("Int64")
    return out.drop(columns=["linkdt", "linkenddt", "linktype"], errors="ignore")


def fundq_rdq_sql() -> str:
    return f"""
        SELECT c.gvkey,
               f.datadate, f.fyearq, f.fqtr, f.rdq,
               f.ibq, c.sic
        FROM comp.company AS c
        JOIN comp.fundq AS f ON c.gvkey = f.gvkey
        WHERE f.indfmt = 'INDL' AND f.datafmt = 'STD' AND f.popsrc = 'D' AND f.consol = 'C'
          AND f.ibq IS NOT NULL
          AND f.datadate >= DATE '1975-01-01'
          AND {sql_date_filter("f.datadate")}
    """


def crsp_msf_sql() -> str:
    return f"""
        SELECT m.permno, m.permco, m.date, m.ret, m.prc, m.shrout, m.vol,
               n.exchcd, n.shrcd
        FROM crsp.msf AS m
        JOIN crsp.msenames AS n
          ON m.permno = n.permno
         AND n.namedt <= m.date
         AND m.date <= COALESCE(n.nameendt, DATE '9999-12-31')
        WHERE {crsp_universe_filter("n")}
          AND {sql_date_filter("date", "m")}
    """


def green_funda_sic_sql() -> str:
    return f"""
        SELECT c.gvkey, f.datadate, f.fyear, c.sic
        FROM comp.company AS c
        JOIN comp.funda AS f ON c.gvkey = f.gvkey
        WHERE {ANNUAL_COMPUSTAT_WHERE}
          AND {sql_date_filter("f.datadate")}
    """


def prepare_crsp_msf(crsp: pd.DataFrame) -> pd.DataFrame:
    crsp = crsp.sort_values(["permno", "date"]).copy()
    crsp["date"] = pd.to_datetime(crsp["date"])
    crsp["ret"] = pd.to_numeric(crsp["ret"], errors="coerce")
    crsp["signal_yyyymm"] = crsp["date"].dt.year * 100 + crsp["date"].dt.month
    crsp["target_yyyymm"] = crsp["signal_yyyymm"].map(add_one_month)
    return crsp[crsp["ret"].notna()].copy()


def expand_annual_sic_green(annual: pd.DataFrame, crsp_month_index: pd.DataFrame) -> pd.DataFrame:
    """Expand annual Compustat SIC to monthly signals using Green lags 7-19."""
    annual = annual.copy()
    annual["datadate"] = pd.to_datetime(annual["datadate"])
    chunks = []
    id_cols = ["permno", "permco", "gvkey", "datadate", "sic", "fyear"]
    for month_lag in range(ANNUAL_ROLLING_START_LAG, ANNUAL_ROLLING_END_LAG):
        chunk = annual[id_cols].copy()
        signal_dates = (chunk["datadate"] + pd.DateOffset(months=month_lag)).dt.to_period("M").dt.to_timestamp("M")
        chunk["signal_yyyymm"] = (signal_dates.dt.year * 100 + signal_dates.dt.month).astype(int)
        chunks.append(chunk)
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
    return expanded[["permno", "signal_yyyymm", "sic"]]


def load_dsf(conn, permnos: list[int]) -> pd.DataFrame:
    """Pull daily CRSP returns and volume for event-window permnos."""
    if not permnos:
        return pd.DataFrame(columns=["permno", "date", "ret", "vol"])
    chunks = []
    batch_size = 4000
    for start in range(0, len(permnos), batch_size):
        batch = permnos[start : start + batch_size]
        permno_list = ",".join(str(int(p)) for p in batch)
        dsf = wrds_query(
            conn,
            f"""
            SELECT permno, date, ret, vol
            FROM crsp.dsf
            WHERE permno IN ({permno_list})
              AND {sql_date_filter("date")}
            """,
        )
        chunks.append(dsf)
    dsf = pd.concat(chunks, ignore_index=True)
    dsf["date"] = pd.to_datetime(dsf["date"])
    dsf["ret"] = pd.to_numeric(dsf["ret"], errors="coerce")
    dsf["vol"] = pd.to_numeric(dsf["vol"], errors="coerce")
    dsf["permno"] = pd.to_numeric(dsf["permno"], errors="coerce").astype("int64")
    return dsf.sort_values(["permno", "date"]).reset_index(drop=True)


def intnx_weekday_scalar(ts) -> tuple[pd.Timestamp, pd.Timestamp]:
    """Business-day window [-1, +1] around an earnings announcement date."""
    rdq = pd.Timestamp(ts)
    return rdq + pd.tseries.offsets.BDay(-1), rdq + pd.tseries.offsets.BDay(1)


def compute_earnings_events(events: pd.DataFrame, dsf: pd.DataFrame) -> pd.DataFrame:
    """Compute ear (cumulative return) and aeavol (abnormal volume) around each rdq."""
    records = []
    for permno, events_p in events.groupby("permno", sort=False):
        dsf_p = dsf[dsf["permno"] == permno]
        if events_p.empty or dsf_p.empty:
            continue
        dates = dsf_p["date"].to_numpy(dtype="datetime64[ns]")
        rets = dsf_p["ret"].to_numpy(dtype=float)
        vols = dsf_p["vol"].to_numpy(dtype=float)
        for row in events_p.drop_duplicates(["datadate", "rdq"]).itertuples(index=False):
            win_start, win_end = intnx_weekday_scalar(row.rdq)
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
            aeavol = (
                (evt_mean - pre_mean) / pre_mean
                if np.isfinite(pre_mean) and pre_mean != 0 and np.isfinite(evt_mean)
                else np.nan
            )
            records.append(
                {
                    "permno": int(permno),
                    "datadate": row.datadate,
                    "rdq": row.rdq,
                    "ear": ear,
                    "aeavol": aeavol,
                }
            )
    return pd.DataFrame(records)


def merge_events_to_monthly(monthly: pd.DataFrame, events: pd.DataFrame) -> pd.DataFrame:
    """Map quarterly event values onto monthly CRSP rows via Green quarterly timing window."""
    value_cols = list(EVENT_VALUE_COLUMNS)
    monthly = monthly.copy()
    monthly["date"] = pd.to_datetime(monthly["date"])
    monthly["permno"] = pd.to_numeric(monthly["permno"], errors="coerce").astype("int64")

    evt = events[["permno", "datadate"] + value_cols].copy()
    evt["permno"] = pd.to_numeric(evt["permno"], errors="coerce").astype("int64")
    evt["datadate"] = pd.to_datetime(evt["datadate"])

    parts = []
    evt_by_permno = {int(p): grp.sort_values("datadate") for p, grp in evt.groupby("permno", sort=False)}
    for permno, m_grp in monthly.groupby("permno", sort=False):
        e_grp = evt_by_permno.get(int(permno))
        if e_grp is None or e_grp.empty:
            continue
        m_grp = m_grp.sort_values("date").copy()
        win_start = intnx_month(m_grp["date"], QUARTERLY_MONTH_START_LAG, "end")
        win_end = intnx_month(m_grp["date"], QUARTERLY_MONTH_END_LAG, "beg")
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
        for col in value_cols:
            part[col] = picked_rows[col].to_numpy()
        parts.append(part)

    if not parts:
        return pd.DataFrame()
    out = pd.concat(parts, ignore_index=True)
    out = out[out["ear"].replace([np.inf, -np.inf], np.nan).notna()]
    id_cols = [c for c in MONTHLY_ID_COLUMNS if c in out.columns or c == "sic"]
    return out[[c for c in id_cols if c in out.columns] + value_cols]


#######################################################################################################################
#                                                    Connect to WRDS                                                  #
#######################################################################################################################

_wrds_user = os.environ.get("WRDS_USERNAME") or os.environ.get("WRDS_USER")
conn = wrds.Connection(wrds_username=_wrds_user) if _wrds_user else wrds.Connection()

CACHE_DIR.mkdir(parents=True, exist_ok=True)
CHARACTERS_DIR.mkdir(parents=True, exist_ok=True)

#######################################################################################################################
#                                              Compustat quarterly rdq pull                                             #
#######################################################################################################################

fundq_cache = CACHE_DIR / "event_fundq.parquet"
if fundq_cache.exists():
    print(f"Loading cached fundq from {fundq_cache}", flush=True)
    comp = pd.read_parquet(fundq_cache)
else:
    print("Pulling comp.fundq (rdq events)...", flush=True)
    comp = wrds_query(conn, fundq_rdq_sql())
    comp["rdq"] = pd.to_datetime(comp["rdq"], errors="coerce")
    comp = dedupe_compustat(comp)
    comp = comp.sort_values(["gvkey", "datadate"]).drop_duplicates(["gvkey", "datadate"], keep="first")
    comp.to_parquet(fundq_cache, index=False)
    print(f"Cached fundq -> {fundq_cache}", flush=True)

comp["rdq"] = pd.to_datetime(comp["rdq"], errors="coerce")

#######################################################################################################################
#                                                  CCM Green merge                                                    #
#######################################################################################################################

print("Loading CCM links and merging...", flush=True)
link = load_ccm_links(conn)
comp = attach_ccm_links(comp, link)
comp = comp[comp["permno"].notna() & comp["rdq"].notna()].copy()
events = comp[["permno", "datadate", "rdq"]].drop_duplicates()

#######################################################################################################################
#                                              Daily CRSP (dsf) event windows                                         #
#######################################################################################################################

dsf_cache = CACHE_DIR / "event_dsf.parquet"
permno_list = events["permno"].astype(int).unique().tolist()
if dsf_cache.exists():
    print(f"Loading cached dsf from {dsf_cache}", flush=True)
    dsf = pd.read_parquet(dsf_cache)
else:
    print(f"Pulling crsp.dsf for {len(permno_list):,} event permnos...", flush=True)
    dsf = load_dsf(conn, permno_list)
    dsf.to_parquet(dsf_cache, index=False)
    print(f"Cached dsf -> {dsf_cache}", flush=True)

print("Computing ear and aeavol around rdq...", flush=True)
evt = compute_earnings_events(events, dsf)

#######################################################################################################################
#                                                  CRSP monthly pull                                                  #
#######################################################################################################################

msf_cache = CACHE_DIR / "event_msf.parquet"
if msf_cache.exists():
    print(f"Loading cached msf from {msf_cache}", flush=True)
    msf = pd.read_parquet(msf_cache)
else:
    print("Pulling crsp.msf...", flush=True)
    msf = wrds_query(conn, crsp_msf_sql())
    msf = prepare_crsp_msf(msf)
    msf.to_parquet(msf_cache, index=False)
    print(f"Cached msf -> {msf_cache}", flush=True)

monthly = msf[["permno", "permco", "date", "signal_yyyymm", "target_yyyymm", "exchcd", "shrcd"]].drop_duplicates(
    ["permno", "date"]
)

#######################################################################################################################
#                                        Attach monthly SIC (Compustat expansion)                                     #
#######################################################################################################################

if SIC_SOURCE == "comp_company":
    sic_cache = CACHE_DIR / "event_sic_timing.parquet"
    if sic_cache.exists():
        print(f"Loading cached annual SIC from {sic_cache}", flush=True)
        annual_sic = pd.read_parquet(sic_cache)
    else:
        print("Pulling comp.funda SIC for monthly attachment...", flush=True)
        sic_comp = wrds_query(conn, green_funda_sic_sql())
        sic_comp = dedupe_compustat(sic_comp)
        sic_comp = attach_ccm_links(sic_comp, link)
        annual_sic = sic_comp[sic_comp["permno"].notna()][
            ["permno", "permco", "gvkey", "datadate", "sic", "fyear"]
        ].copy()
        annual_sic.to_parquet(sic_cache, index=False)
        print(f"Cached annual SIC -> {sic_cache}", flush=True)

    crsp_idx = monthly[["permno", "signal_yyyymm"]].drop_duplicates()
    sic_monthly = expand_annual_sic_green(annual_sic, crsp_idx)
    monthly = monthly.merge(sic_monthly, on=["permno", "signal_yyyymm"], how="left")

#######################################################################################################################
#                                        Expand events to monthly (Green -10/-5)                                    #
#######################################################################################################################

print("Mapping events to monthly CRSP (Green window -10/-5 on datadate)...", flush=True)
panel = merge_events_to_monthly(monthly, evt)

#######################################################################################################################
#                                                       Output                                                        #
#######################################################################################################################

out_cols = [c for c in MONTHLY_ID_COLUMNS if c in panel.columns] + list(EVENT_VALUE_COLUMNS)
out_path = CHARACTERS_DIR / "event.parquet"
panel[out_cols].to_parquet(out_path, index=False)
print(f"Wrote {len(panel):,} rows -> {out_path}", flush=True)
