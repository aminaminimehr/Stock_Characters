"""Flat procedural builder: Mohanram G-score (ms = m1 + ... + m8) on monthly CRSP grid."""
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
    INDUSTRY_AGG,
    MONTHLY_ID_COLUMNS,
    SAMPLE_END,
    SAMPLE_START,
    SIC_SOURCE,
)

M_COLUMNS = [f"m{i}" for i in range(1, 9)]
MS_ANNUAL_ITEMS = ("ni", "oancf", "ib", "dp", "xrd", "capx", "xad", "at")

FUNDQ_ROAVOL_ITEMS = (
    "ibq", "atq", "saleq", "mveq", "oiadpq", "ceqq", "seqq", "pstkq", "pstkrq",
    "ltq", "dlcq", "dlttq", "cheq", "rdq", "actq", "lctq",
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


def safe_divide(numerator, denominator):
    if isinstance(denominator, pd.Series):
        denom = denominator.replace(0, np.nan)
    else:
        denom = denominator
    return numerator / denom


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


def sas_std_row(values: np.ndarray) -> float:
    row = values[np.isfinite(values)]
    if len(row) < 2:
        return np.nan
    return float(np.std(row, ddof=1))


def rolling_sas_std(frame: pd.DataFrame, col: str, lags: list[int]) -> pd.Series:
    parts = [frame[col].to_numpy(dtype=float)]
    grouped = frame.groupby("gvkey", sort=False)
    for lag_n in lags:
        parts.append(grouped[col].shift(lag_n).to_numpy(dtype=float))
    mat = np.column_stack(parts)
    return pd.Series([sas_std_row(mat[i]) for i in range(len(mat))], index=frame.index)


def load_ccm_links(conn) -> pd.DataFrame:
    linkprim_clause = ""
    if str(CCM_LINKPRIM).strip().upper() not in ("", "ALL", "*"):
        codes = ", ".join(f"'{c.strip()}'" for c in str(CCM_LINKPRIM).split(",") if c.strip())
        linkprim_clause = f" AND linkprim IN ({codes})"
    if str(CCM_LINKTYPES).strip().upper() in ("L*", "L"):
        linktype_clause = "linktype LIKE 'L%'"
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


def green_funda_ms_sql() -> str:
    cols = ", ".join(["c.gvkey", "f.datadate", "f.fyear", "c.sic"] + [f"f.{item}" for item in MS_ANNUAL_ITEMS])
    return f"""
        SELECT {cols}
        FROM comp.company AS c
        JOIN comp.funda AS f ON c.gvkey = f.gvkey
        WHERE {ANNUAL_COMPUSTAT_WHERE}
          AND {sql_date_filter("f.datadate")}
    """


def fundq_roavol_sql() -> str:
    base = [
        "c.gvkey",
        "f.datadate", "f.fyearq", "f.fqtr", "f.rdq",
        "SUBSTR(c.sic, 1, 2) AS sic2", "c.sic",
    ]
    for item in FUNDQ_ROAVOL_ITEMS:
        if item == "rdq":
            continue
        if item == "mveq":
            base.append("ABS(f.prccq) * f.cshoq AS mveq")
        else:
            base.append(f"f.{item}")
    cols = ", ".join(base)
    return f"""
        SELECT {cols}
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


def expand_annual_file_green(
    df: pd.DataFrame,
    character_columns: list[str],
    crsp_month_index: pd.DataFrame | None = None,
) -> pd.DataFrame:
    """Expand annual data to monthly signals using Green rolling lags 7-19 months."""
    id_cols = ["permno", "permco", "gvkey", "datadate", "sic", "fyear"]
    df = df.copy()
    df["datadate"] = pd.to_datetime(df["datadate"])
    chunks = []
    keep_cols = id_cols + character_columns
    for month_lag in range(ANNUAL_ROLLING_START_LAG, ANNUAL_ROLLING_END_LAG):
        chunk = df[keep_cols].copy()
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
    return expanded


def apply_mohanram_m1_m6(comp: pd.DataFrame, avg_at: pd.Series) -> pd.DataFrame:
    """Compute Mohanram annual binary signals m1-m6 vs (fyear, sic2) medians."""
    comp = comp.copy()
    roa_ms = safe_divide(comp["ni"], avg_at)
    cfroa_ms = safe_divide(comp["oancf"], avg_at)
    cfroa_ms = cfroa_ms.where(comp["oancf"].notna(), safe_divide(comp["ib"] + comp["dp"], avg_at))
    xrdint_ms = safe_divide(comp["xrd"].fillna(0), avg_at)
    capxint_ms = safe_divide(comp["capx"], avg_at)
    xadint_ms = safe_divide(comp["xad"].fillna(0), avg_at)
    med = comp.assign(
        _roa_ms=roa_ms,
        _cfroa_ms=cfroa_ms,
        _xrdint_ms=xrdint_ms,
        _capxint_ms=capxint_ms,
        _xadint_ms=xadint_ms,
    ).groupby(["fyear", "sic2"], dropna=False)[
        ["_roa_ms", "_cfroa_ms", "_xrdint_ms", "_capxint_ms", "_xadint_ms"]
    ].transform("median")
    med.columns = ["md_roa", "md_cfroa", "md_xrdint", "md_capxint", "md_xadint"]
    comp["m1"] = (roa_ms > med["md_roa"]).fillna(False).astype(int)
    comp["m2"] = (cfroa_ms > med["md_cfroa"]).fillna(False).astype(int)
    comp["m3"] = (comp["oancf"] > comp["ni"]).fillna(False).astype(int)
    comp["m4"] = (xrdint_ms > med["md_xrdint"]).fillna(False).astype(int)
    comp["m5"] = (capxint_ms > med["md_capxint"]).fillna(False).astype(int)
    comp["m6"] = (xadint_ms > med["md_xadint"]).fillna(False).astype(int)
    return comp


def compute_quarterly_roavol(comp: pd.DataFrame) -> pd.DataFrame:
    """Compute roaq and roavol on quarterly panel (quarterly_runner roavol stem)."""
    df = comp.copy().reset_index(drop=True)
    g = df.groupby("gvkey", sort=False)
    df["count"] = g.cumcount() + 1
    lag_atq = g["atq"].shift(1)
    df["roaq"] = df["ibq"] / lag_atq
    df.loc[g.head(1).index, "roaq"] = np.nan
    df.loc[df["count"] < 8, "roavol"] = np.nan
    df["roavol"] = rolling_sas_std(df, "roaq", list(range(1, 8)))
    return df


def compute_m7_m8(quarterly: pd.DataFrame) -> pd.DataFrame:
    """Compute m7/m8 with SAS NaN->1 rule vs (fyearq, fqtr, sic2) medians."""
    df = quarterly.copy().reset_index(drop=True)
    g = df.groupby("gvkey", sort=False)
    df["count"] = g.cumcount() + 1

    lag4_saleq = g["saleq"].shift(4)
    df["rsup"] = (df["saleq"] - lag4_saleq) / df["mveq"]
    df["sgrvol"] = rolling_sas_std(df, "rsup", list(range(1, 8)))

    if "roavol" not in df.columns and "roaq" in df.columns:
        df["roavol"] = rolling_sas_std(df, "roaq", list(range(1, 8)))

    df.loc[df["count"] < 8, ["roavol", "sgrvol"]] = np.nan

    if "sic2" in df.columns and "roavol" in df.columns and "sgrvol" in df.columns:
        med = df.groupby(["fyearq", "fqtr", "sic2"], dropna=False)[["roavol", "sgrvol"]].transform("median")
        med.columns = ["md_roavol", "md_sgrvol"]
        df = pd.concat([df, med], axis=1)
        df["m7"] = np.where(
            df["roavol"].isna() & df["md_roavol"].notna(),
            1,
            np.where(df["roavol"].lt(df["md_roavol"]).fillna(False), 1, 0),
        )
        df["m8"] = np.where(
            df["sgrvol"].isna() & df["md_sgrvol"].notna(),
            1,
            np.where(df["sgrvol"].lt(df["md_sgrvol"]).fillna(False), 1, 0),
        )
    else:
        df["m7"] = np.nan
        df["m8"] = np.nan
    return df


def attach_m7_m8(comp: pd.DataFrame, quarterly: pd.DataFrame) -> pd.DataFrame:
    """Merge last-quarter m7/m8 from quarterly panel onto annual rows by permno x fyear."""
    q = quarterly[quarterly["permno"].notna()].copy()
    q["permno"] = pd.to_numeric(q["permno"], errors="coerce")
    q_last = (
        q[["permno", "fyearq", "fqtr", "m7", "m8"]]
        .sort_values(["permno", "fyearq", "fqtr"])
        .groupby(["permno", "fyearq"], as_index=False)
        .last()
        .rename(columns={"fyearq": "fyear"})
    )
    comp = comp.copy()
    comp["_permno_num"] = pd.to_numeric(comp["permno"], errors="coerce")
    comp["fyear"] = pd.to_numeric(comp["fyear"], errors="coerce")
    comp = comp.merge(
        q_last,
        left_on=["_permno_num", "fyear"],
        right_on=["permno", "fyear"],
        how="left",
        suffixes=("", "_q"),
    )
    return comp.drop(columns=["permno_q", "_permno_num"], errors="ignore")


#######################################################################################################################
#                                                    Connect to WRDS                                                  #
#######################################################################################################################

_wrds_user = os.environ.get("WRDS_USERNAME") or os.environ.get("WRDS_USER")
conn = wrds.Connection(wrds_username=_wrds_user) if _wrds_user else wrds.Connection()

CACHE_DIR.mkdir(parents=True, exist_ok=True)
CHARACTERS_DIR.mkdir(parents=True, exist_ok=True)

link = load_ccm_links(conn)

#######################################################################################################################
#                                              Compustat annual (m1-m6)                                               #
#######################################################################################################################

funda_cache = CACHE_DIR / "ms_funda.parquet"
if funda_cache.exists():
    print(f"Loading cached annual funda from {funda_cache}", flush=True)
    comp = pd.read_parquet(funda_cache)
else:
    print("Pulling comp.funda for Mohanram annual items...", flush=True)
    comp = wrds_query(conn, green_funda_ms_sql())
    comp.to_parquet(funda_cache, index=False)
    print(f"Cached annual funda -> {funda_cache}", flush=True)

comp = dedupe_compustat(comp)
comp["lag_at"] = comp.groupby("gvkey")["at"].shift(1)
comp = attach_ccm_links(comp, link)
comp = comp[comp["permno"].notna()].copy()

if INDUSTRY_AGG == "post_ccm":
    avg_at = (comp["at"] + comp["lag_at"]) / 2
    comp = apply_mohanram_m1_m6(comp, avg_at)

#######################################################################################################################
#                                           Compustat quarterly (m7-m8)                                               #
#######################################################################################################################

fundq_cache = CACHE_DIR / "ms_fundq.parquet"
if fundq_cache.exists():
    print(f"Loading cached quarterly fundq from {fundq_cache}", flush=True)
    quarterly = pd.read_parquet(fundq_cache)
else:
    print("Pulling comp.fundq for roavol / m7 / m8...", flush=True)
    quarterly = wrds_query(conn, fundq_roavol_sql())
    quarterly["rdq"] = pd.to_datetime(quarterly["rdq"], errors="coerce")
    quarterly = dedupe_compustat(quarterly)
    quarterly = quarterly.sort_values(["gvkey", "datadate"]).drop_duplicates(["gvkey", "datadate"], keep="first")
    quarterly.to_parquet(fundq_cache, index=False)
    print(f"Cached quarterly fundq -> {fundq_cache}", flush=True)

print("Computing roavol and m7/m8...", flush=True)
quarterly = compute_quarterly_roavol(quarterly)
quarterly = compute_m7_m8(quarterly)
quarterly = attach_ccm_links(quarterly, link)

comp = attach_m7_m8(comp, quarterly)

#######################################################################################################################
#                                                  CRSP monthly pull                                                  #
#######################################################################################################################

msf_cache = CACHE_DIR / "ms_msf.parquet"
if msf_cache.exists():
    print(f"Loading cached msf from {msf_cache}", flush=True)
    crsp = pd.read_parquet(msf_cache)
else:
    print("Pulling crsp.msf...", flush=True)
    crsp = wrds_query(conn, crsp_msf_sql())
    crsp = prepare_crsp_msf(crsp)
    crsp.to_parquet(msf_cache, index=False)
    print(f"Cached msf -> {msf_cache}", flush=True)

if SIC_SOURCE == "comp_company":
    sic_cache = CACHE_DIR / "ms_sic_timing.parquet"
    if sic_cache.exists():
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

    crsp_idx = crsp[["permno", "signal_yyyymm"]].drop_duplicates()
    sic_monthly = expand_annual_sic_green(annual_sic, crsp_idx)
    crsp = crsp.merge(sic_monthly, on=["permno", "signal_yyyymm"], how="left")

#######################################################################################################################
#                                    Green annual expand 7-19 + merge to CRSP monthly                                 #
#######################################################################################################################

print("Expanding annual m1-m8 to monthly (Green lags 7-19)...", flush=True)
monthly_index = crsp[["permno", "signal_yyyymm"]].drop_duplicates()
annual_all = comp[comp["permno"].notna()][
    ["permno", "permco", "gvkey", "datadate", "sic", "fyear"] + M_COLUMNS
].copy()
annual_expanded = expand_annual_file_green(annual_all, M_COLUMNS, crsp_month_index=monthly_index)

merged = crsp.merge(
    annual_expanded[["permno", "signal_yyyymm"] + M_COLUMNS],
    on=["permno", "signal_yyyymm"],
    how="inner",
)
merged["ms"] = merged[M_COLUMNS].sum(axis=1, min_count=len(M_COLUMNS))
panel = merged[merged["ms"].notna()].copy()

#######################################################################################################################
#                                                       Output                                                        #
#######################################################################################################################

out_cols = [c for c in MONTHLY_ID_COLUMNS if c in panel.columns] + ["ms"]
out_path = CHARACTERS_DIR / "ms.parquet"
panel[out_cols].to_parquet(out_path, index=False)
print(f"Wrote {len(panel):,} rows -> {out_path}", flush=True)
