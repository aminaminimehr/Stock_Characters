"""Flat procedural builder: Green monthly CRSP characters -> monthly panel."""
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
    MONTHLY_ID_COLUMNS,
    SAMPLE_END,
    SAMPLE_START,
)

MONTHLY_CHARACTERS = (
    "mvel1", "mom1m", "mom6m", "mom12m", "mom36m", "chmom", "dolvol", "turn", "indmom",
)

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
    """Execute SQL on WRDS; one retry after 120 seconds on failure (with connection reset)."""
    last_exc = None
    for attempt in range(2):
        try:
            return conn.raw_sql(sql)
        except Exception as exc:
            last_exc = exc
            if attempt == 0:
                print(f"WRDS query failed: {exc}; resetting connection and retrying in 120s...", flush=True)
                try:
                    conn.connection.rollback()
                except Exception:
                    pass
                try:
                    conn.close(); conn.connect()
                except Exception as e2:
                    print(f"  reconnect failed: {e2}", flush=True)
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


def crsp_exchcd_filter(table_alias: str = "n") -> str:
    codes = ", ".join(v.strip() for v in str(CRSP_EXCHCD).split(",") if v.strip())
    return f"{table_alias}.exchcd IN ({codes})"


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


def crsp_msf_sql() -> str:
    return f"""
        SELECT m.permno, m.permco, m.date, m.ret, m.prc, m.shrout, m.vol,
               n.exchcd, n.shrcd
        FROM crsp.msf AS m
        JOIN crsp.msenames AS n
          ON m.permno = n.permno
         AND n.namedt <= m.date
         AND m.date <= COALESCE(n.nameendt, DATE '9999-12-31')
        WHERE {crsp_exchcd_filter("n")}
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


def prepare_crsp(crsp: pd.DataFrame) -> pd.DataFrame:
    crsp = crsp.sort_values(["permno", "date"]).copy()
    crsp["date"] = pd.to_datetime(crsp["date"])
    crsp["ret"] = pd.to_numeric(crsp["ret"], errors="coerce")
    crsp["prc_abs"] = crsp["prc"].abs()
    crsp["market_equity"] = crsp["prc_abs"] * crsp["shrout"]
    crsp["signal_yyyymm"] = crsp["date"].dt.year * 100 + crsp["date"].dt.month
    crsp["target_yyyymm"] = crsp["signal_yyyymm"].map(add_one_month)
    return crsp[crsp["ret"].notna()].copy()


def rolling_return_product(crsp: pd.DataFrame, start_lag: int, end_lag: int) -> pd.Series:
    lagged_returns = pd.concat(
        [crsp.groupby("permno")["ret"].shift(period) for period in range(start_lag, end_lag + 1)],
        axis=1,
    )
    return (1 + lagged_returns).prod(axis=1, min_count=end_lag - start_lag + 1) - 1


def expand_annual_sic_green(
    annual: pd.DataFrame,
    crsp_month_index: pd.DataFrame,
) -> pd.DataFrame:
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
    expanded["target_yyyymm"] = expanded["signal_yyyymm"].map(add_one_month)
    sic_num = pd.to_numeric(expanded["sic"], errors="coerce")
    expanded["sic2"] = sic_num.apply(lambda x: f"{int(x):04d}"[:2] if pd.notna(x) else np.nan)
    return expanded[["permno", "signal_yyyymm", "sic", "sic2"]]


#######################################################################################################################
#                                                    Connect to WRDS                                                  #
#######################################################################################################################

_wrds_user = os.environ.get("WRDS_USERNAME") or os.environ.get("WRDS_USER")
conn = wrds.Connection(wrds_username=_wrds_user) if _wrds_user else wrds.Connection()

CACHE_DIR.mkdir(parents=True, exist_ok=True)
CHARACTERS_DIR.mkdir(parents=True, exist_ok=True)

#######################################################################################################################
#                                                  CRSP monthly pull                                                  #
#######################################################################################################################

msf_cache = CACHE_DIR / "monthly_msf.parquet"
if msf_cache.exists():
    print(f"Loading cached msf from {msf_cache}", flush=True)
    crsp = pd.read_parquet(msf_cache)
else:
    print("Pulling crsp.msf + msenames (exchcd 1,2,3; no shrcd filter)...", flush=True)
    crsp = wrds_query(conn, crsp_msf_sql())
    crsp = prepare_crsp(crsp)
    crsp.to_parquet(msf_cache, index=False)
    print(f"Cached msf -> {msf_cache}", flush=True)

#######################################################################################################################
#                                           Compustat annual SIC for indmom                                           #
#######################################################################################################################

sic_cache = CACHE_DIR / "monthly_sic_timing.parquet"
if sic_cache.exists():
    print(f"Loading cached annual SIC from {sic_cache}", flush=True)
    annual_sic = pd.read_parquet(sic_cache)
else:
    print("Pulling comp.funda SIC for industry momentum...", flush=True)
    comp = wrds_query(conn, green_funda_sic_sql())
    comp = dedupe_compustat(comp)
    link = load_ccm_links(conn)
    comp = attach_ccm_links(comp, link)
    annual_sic = comp[comp["permno"].notna()][["permno", "permco", "gvkey", "datadate", "sic", "fyear"]].copy()
    annual_sic.to_parquet(sic_cache, index=False)
    print(f"Cached annual SIC -> {sic_cache}", flush=True)

crsp_idx = crsp[["permno", "signal_yyyymm"]].drop_duplicates()
sic_monthly = expand_annual_sic_green(annual_sic, crsp_idx)
crsp = crsp.merge(sic_monthly, on=["permno", "signal_yyyymm"], how="left")

#######################################################################################################################
#                                           Compute monthly CRSP characters                                             #
#######################################################################################################################

print("Computing monthly CRSP characters...", flush=True)
g = crsp.groupby("permno", sort=False)
crsp["return_count"] = g.cumcount() + 1

# mvel1 = log(lag ME)
crsp["mvel1"] = np.log(g["market_equity"].shift(1))

# mom1m = lag ret
crsp["mom1m"] = g["ret"].shift(1)
crsp.loc[crsp["return_count"] == 1, "mom1m"] = np.nan

# mom6m compound lags 2-6
crsp["mom6m"] = rolling_return_product(crsp, 2, 6)
crsp.loc[crsp["return_count"] < 7, "mom6m"] = np.nan

# mom12m compound lags 2-12
crsp["mom12m"] = rolling_return_product(crsp, 2, 12)
crsp.loc[crsp["return_count"] < 13, "mom12m"] = np.nan

# mom36m compound lags 13-36
crsp["mom36m"] = rolling_return_product(crsp, 13, 36)
crsp.loc[crsp["return_count"] < 37, "mom36m"] = np.nan

# chmom = lags 1-6 minus lags 7-12 (Green lag window)
crsp["chmom"] = rolling_return_product(crsp, 1, 6) - rolling_return_product(crsp, 7, 12)
crsp.loc[crsp["return_count"] < 13, "chmom"] = np.nan

# dolvol = log(lag2 vol * prc)
crsp["dolvol"] = np.log(g["vol"].shift(2) * g["prc_abs"].shift(2))

# turn = mean lag vol 1-3 / shrout
vol_lags = [g["vol"].shift(i) for i in range(1, 4)]
crsp["turn"] = pd.concat(vol_lags, axis=1).mean(axis=1) / crsp["shrout"]

# indmom = mean mom12m by sic2 x date
crsp["indmom"] = crsp.groupby(["sic2", "date"])["mom12m"].transform("mean")

#######################################################################################################################
#                                                       Output                                                        #
#######################################################################################################################

out_cols = [c for c in MONTHLY_ID_COLUMNS if c in crsp.columns] + list(MONTHLY_CHARACTERS)
panel = crsp[out_cols].copy()

out_path = CHARACTERS_DIR / "monthly.parquet"
panel.to_parquet(out_path, index=False)
print(f"Wrote {len(panel):,} rows -> {out_path}", flush=True)
