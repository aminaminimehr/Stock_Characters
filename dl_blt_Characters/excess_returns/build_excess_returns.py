"""Flat procedural builder: monthly excess returns with Green distress delisting fill."""
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
    CACHE_DIR,
    CRSP_EXCHCD,
    CRSP_SHRCD,
    PANEL_DIR,
    SAMPLE_END,
    SAMPLE_START,
)


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


def crsp_msf_sql() -> str:
    return f"""
        SELECT m.permno, m.date, m.ret, m.retx,
               n.exchcd, n.shrcd
        FROM crsp.msf AS m
        JOIN crsp.msenames AS n
          ON m.permno = n.permno
         AND n.namedt <= m.date
         AND m.date <= COALESCE(n.nameendt, DATE '9999-12-31')
        WHERE {crsp_universe_filter("n")}
          AND {sql_date_filter("date", "m")}
    """


def load_crsp_monthly_returns(conn) -> pd.DataFrame:
    crsp = wrds_query(conn, crsp_msf_sql())
    crsp["date"] = pd.to_datetime(crsp["date"]) + pd.offsets.MonthEnd(0)
    crsp["ret"] = pd.to_numeric(crsp["ret"], errors="coerce")
    crsp["retx"] = pd.to_numeric(crsp["retx"], errors="coerce")
    crsp["permno"] = pd.to_numeric(crsp["permno"], errors="coerce").astype("int64")
    return crsp


def load_delisting_returns(conn) -> pd.DataFrame:
    dlret = wrds_query(
        conn,
        """
        SELECT permno, dlstdt, dlret, dlstcd
        FROM crsp.msedelist
        WHERE dlstdt IS NOT NULL
        """,
    )
    dlret["date"] = pd.to_datetime(dlret["dlstdt"]) + pd.offsets.MonthEnd(0)
    dlret["dlret"] = pd.to_numeric(dlret["dlret"], errors="coerce")
    dlret["permno"] = pd.to_numeric(dlret["permno"], errors="coerce").astype("int64")
    return dlret[["permno", "date", "dlret", "dlstcd"]]


def load_risk_free_rate(conn) -> pd.DataFrame:
    factors = wrds_query(
        conn,
        """
        SELECT date, rf
        FROM ff.factors_monthly
        """,
    )
    factors["date"] = pd.to_datetime(factors["date"]) + pd.offsets.MonthEnd(0)
    factors["rf"] = pd.to_numeric(factors["rf"], errors="coerce")
    median_abs_rf = factors["rf"].abs().median()
    if pd.notna(median_abs_rf) and median_abs_rf > 0.02:
        factors["rf"] = factors["rf"] / 100
    return factors


def apply_green_delisting_fill(returns: pd.DataFrame) -> pd.DataFrame:
    """Fill missing distress delisting returns: NYSE/AMEX -0.35, NASDAQ -0.55."""
    distress_codes = (
        returns["dlstcd"].between(500, 584)
        & ~returns["dlstcd"].isin([501, 502, 503, 504])
    )
    missing_distress_dlret = returns["dlret"].isna() & distress_codes
    nyse_amex = missing_distress_dlret & returns["exchcd"].isin([1, 2])
    nasdaq = missing_distress_dlret & returns["exchcd"].eq(3)
    returns = returns.copy()
    returns.loc[nyse_amex, "dlret"] = -0.35
    returns.loc[nasdaq, "dlret"] = -0.55
    return returns


def build_excess_returns(
    crsp: pd.DataFrame,
    dlret: pd.DataFrame,
    rf: pd.DataFrame,
) -> pd.DataFrame:
    """Compute retadj and excess_return keyed on permno, target_yyyymm."""
    returns = crsp.merge(dlret, on=["permno", "date"], how="left")
    returns = apply_green_delisting_fill(returns)

    returns["ret_for_adjustment"] = returns["ret"].fillna(0)
    returns["dlret_for_adjustment"] = returns["dlret"].fillna(0)
    returns["retadj"] = (
        (1 + returns["ret_for_adjustment"]) * (1 + returns["dlret_for_adjustment"]) - 1
    )
    returns.loc[returns["ret"].isna() & returns["dlret"].isna(), "retadj"] = np.nan

    returns = returns.merge(rf, on="date", how="left")
    returns["excess_return"] = returns["retadj"] - returns["rf"]
    returns["target_yyyymm"] = returns["date"].dt.year * 100 + returns["date"].dt.month

    returns = returns[
        returns["excess_return"].replace([np.inf, -np.inf], np.nan).notna()
    ].copy()

    return returns[["permno", "target_yyyymm", "excess_return"]].sort_values(
        ["permno", "target_yyyymm"]
    )


#######################################################################################################################
#                                                    Connect to WRDS                                                  #
#######################################################################################################################

_wrds_user = os.environ.get("WRDS_USERNAME") or os.environ.get("WRDS_USER")
conn = wrds.Connection(wrds_username=_wrds_user) if _wrds_user else wrds.Connection()

CACHE_DIR.mkdir(parents=True, exist_ok=True)
PANEL_DIR.mkdir(parents=True, exist_ok=True)

#######################################################################################################################
#                                              CRSP monthly returns (msf)                                             #
#######################################################################################################################

msf_cache = CACHE_DIR / "excess_msf.parquet"
if msf_cache.exists():
    print(f"Loading cached msf from {msf_cache}", flush=True)
    crsp = pd.read_parquet(msf_cache)
else:
    print("Pulling crsp.msf monthly returns...", flush=True)
    crsp = load_crsp_monthly_returns(conn)
    crsp.to_parquet(msf_cache, index=False)
    print(f"Cached msf -> {msf_cache} ({len(crsp):,} rows)", flush=True)

#######################################################################################################################
#                                              CRSP delisting (msedelist)                                             #
#######################################################################################################################

dlret_cache = CACHE_DIR / "excess_msedelist.parquet"
if dlret_cache.exists():
    print(f"Loading cached msedelist from {dlret_cache}", flush=True)
    dlret = pd.read_parquet(dlret_cache)
else:
    print("Pulling crsp.msedelist delisting returns...", flush=True)
    dlret = load_delisting_returns(conn)
    dlret.to_parquet(dlret_cache, index=False)
    print(f"Cached msedelist -> {dlret_cache} ({len(dlret):,} rows)", flush=True)

#######################################################################################################################
#                                              Fama-French risk-free rate                                             #
#######################################################################################################################

rf_cache = CACHE_DIR / "excess_rf.parquet"
if rf_cache.exists():
    print(f"Loading cached rf from {rf_cache}", flush=True)
    rf = pd.read_parquet(rf_cache)
else:
    print("Pulling ff.factors_monthly rf...", flush=True)
    rf = load_risk_free_rate(conn)
    rf.to_parquet(rf_cache, index=False)
    print(f"Cached rf -> {rf_cache} ({len(rf):,} rows)", flush=True)

#######################################################################################################################
#                                           Compute excess returns                                                    #
#######################################################################################################################

print("Computing excess returns (Green distress delisting fill)...", flush=True)
panel = build_excess_returns(crsp, dlret, rf)

#######################################################################################################################
#                                                       Output                                                        #
#######################################################################################################################

out_path = PANEL_DIR / "excess_returns.parquet"
panel.to_parquet(out_path, index=False)
print(f"Wrote {len(panel):,} rows -> {out_path}", flush=True)
