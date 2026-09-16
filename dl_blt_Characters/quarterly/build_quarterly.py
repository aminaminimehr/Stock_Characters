"""Flat procedural builder: 10 Green quarterly Compustat characters -> monthly panel."""
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
    CCM_LINKPRIM,
    CCM_LINKTYPES,
    CHARACTERS_DIR,
    CRSP_EXCHCD,
    CRSP_SHRCD,
    QUARTERLY_MONTH_END_LAG,
    QUARTERLY_MONTH_START_LAG,
    SAMPLE_END,
    SAMPLE_START,
)

QUARTERLY_CHARACTERS = (
    "chtx", "cinvest", "nincr", "roaq", "roeq", "rsup", "cash", "stdacc", "stdcf", "roavol",
)

FUNDQ_ITEMS = (
    "txtq", "atq", "ibq", "rdq", "ppentq", "saleq", "seqq", "ceqq", "pstkq", "pstkrq",
    "ltq", "dlcq", "dlttq", "cheq", "actq", "lctq", "oiadpq", "mveq",
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


def bool_to_int(left: pd.Series, right: pd.Series) -> pd.Series:
    return left.gt(right).fillna(False).astype(int)


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


def intnx_month(ts: pd.Series, n: int, alignment: str = "end") -> pd.Series:
    shifted = pd.to_datetime(ts) + pd.DateOffset(months=n)
    if alignment == "beg":
        return shifted.dt.to_period("M").dt.to_timestamp("s")
    return shifted.dt.to_period("M").dt.to_timestamp("h")


def fundq_sql(items: tuple[str, ...]) -> str:
    base = [
        "c.gvkey",
        "SUBSTR(REPLACE(f.cusip, ' ', ''), 1, 6) AS cusip6",
        "f.datadate", "f.fyearq", "f.fqtr", "f.rdq",
        "SUBSTR(c.sic, 1, 2) AS sic2", "c.sic",
    ]
    for item in items:
        if item == "rdq":
            continue
        if item == "mveq":
            base.append("ABS(f.prccq) * f.cshoq AS mveq")
        elif item in ("prccq",):
            base.append(f"ABS(f.{item}) AS {item}")
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


def compute_quarterly_characters(comp: pd.DataFrame) -> pd.DataFrame:
    """Apply Green quarterly formulas for all 10 characters (quarterly_runner logic)."""
    df = comp.copy().reset_index(drop=True)
    g = df.groupby("gvkey", sort=False)
    df["count"] = g.cumcount() + 1
    lag_atq = g["atq"].shift(1)
    lag4_txtq = g["txtq"].shift(4)
    lag4_saleq = g["saleq"].shift(4)

    # chtx
    df["chtx"] = (df["txtq"] - lag4_txtq) / lag_atq
    df.loc[df["count"] < 5, "chtx"] = np.nan

    # roaq
    df["roaq"] = df["ibq"] / lag_atq
    df.loc[g.head(1).index, "roaq"] = np.nan

    # roeq
    df["pstk"] = np.where(df["pstkrq"].notna(), df["pstkrq"], df["pstkq"])
    scal = df["seqq"].copy()
    scal = scal.fillna(df["ceqq"] + df["pstk"])
    need_at = scal.isna() & (df["ceqq"].isna() | df["pstk"].isna())
    scal = scal.where(~need_at, df["atq"] - df["ltq"])
    df["scal"] = scal
    lag_scal = g["scal"].shift(1)
    df["roeq"] = df["ibq"] / lag_scal
    df.loc[g.head(1).index, "roeq"] = np.nan

    # rsup
    df["rsup"] = (df["saleq"] - lag4_saleq) / df["mveq"]

    # cash
    df["cash_q"] = df["cheq"] / df["atq"]
    df["cash"] = df["cash_q"]

    # stdacc / stdcf / roavol (shared accrual base)
    sacc_num = (df["actq"] - g["actq"].shift(1) - (df["cheq"] - g["cheq"].shift(1))) - (
        (df["lctq"] - g["lctq"].shift(1)) - (df["dlcq"] - g["dlcq"].shift(1))
    )
    df["sacc"] = sacc_num / df["saleq"]
    df.loc[df["saleq"] <= 0, "sacc"] = sacc_num / 0.01

    df["stdacc"] = rolling_sas_std(df, "sacc", list(range(1, 16)))
    df.loc[df["count"] < 17, "stdacc"] = np.nan

    df["scf"] = (df["ibq"] / df["saleq"]) - df["sacc"]
    df.loc[df["saleq"] <= 0, "scf"] = (df["ibq"] / 0.01) - df["sacc"]
    df["stdcf"] = rolling_sas_std(df, "scf", list(range(1, 16)))
    df.loc[df["count"] < 17, "stdcf"] = np.nan

    df.loc[df["count"] < 8, "roavol"] = np.nan
    df["roavol"] = rolling_sas_std(df, "roaq", list(range(1, 8)))

    # cinvest
    ppent_chg = (df["ppentq"] - g["ppentq"].shift(1)) / df["saleq"]
    ind_mean = (
        (g["ppentq"].shift(1) - g["ppentq"].shift(2)) / g["saleq"].shift(1)
        + (g["ppentq"].shift(2) - g["ppentq"].shift(3)) / g["saleq"].shift(2)
        + (g["ppentq"].shift(3) - g["ppentq"].shift(4)) / g["saleq"].shift(3)
    ) / 3
    df["cinvest"] = ppent_chg - ind_mean
    bad_sale = df["saleq"] <= 0
    df.loc[bad_sale, "cinvest"] = (
        (df["ppentq"] - g["ppentq"].shift(1)) / 0.01
        - (
            (g["ppentq"].shift(1) - g["ppentq"].shift(2)) / 0.01
            + (g["ppentq"].shift(2) - g["ppentq"].shift(3)) / 0.01
            + (g["ppentq"].shift(3) - g["ppentq"].shift(4)) / 0.01
        )
        / 3
    )
    df.loc[df["count"] < 5, "cinvest"] = np.nan

    # nincr
    ibq = df["ibq"]
    l1, l2, l3, l4 = g["ibq"].shift(1), g["ibq"].shift(2), g["ibq"].shift(3), g["ibq"].shift(4)
    l5, l6, l7, l8 = g["ibq"].shift(5), g["ibq"].shift(6), g["ibq"].shift(7), g["ibq"].shift(8)
    b01 = bool_to_int(ibq, l1)
    b12 = bool_to_int(l1, l2)
    b23 = bool_to_int(l2, l3)
    b34 = bool_to_int(l3, l4)
    b45 = bool_to_int(l4, l5)
    b56 = bool_to_int(l5, l6)
    b67 = bool_to_int(l6, l7)
    b78 = bool_to_int(l7, l8)
    df["nincr"] = (
        b01 + b01 * b12 + b01 * b12 * b23 + b01 * b12 * b23 * b34
        + b01 * b12 * b23 * b34 * b45 + b01 * b12 * b23 * b34 * b45 * b56
        + b01 * b12 * b23 * b34 * b45 * b56 * b67 + b01 * b12 * b23 * b34 * b45 * b56 * b67 * b78
    )

    return df


def prepare_crsp_msf(crsp: pd.DataFrame) -> pd.DataFrame:
    crsp = crsp.sort_values(["permno", "date"]).copy()
    crsp["date"] = pd.to_datetime(crsp["date"])
    crsp["ret"] = pd.to_numeric(crsp["ret"], errors="coerce")
    crsp["signal_yyyymm"] = crsp["date"].dt.year * 100 + crsp["date"].dt.month
    year = crsp["signal_yyyymm"] // 100
    month = crsp["signal_yyyymm"] % 100
    next_month = month + 1
    next_year = year + (next_month == 13)
    next_month = np.where(next_month == 13, 1, next_month)
    crsp["target_yyyymm"] = next_year * 100 + next_month
    return crsp[crsp["ret"].notna()].copy()


def expand_quarterly_to_monthly(quarterly: pd.DataFrame, monthly: pd.DataFrame) -> pd.DataFrame:
    """Map quarterly values onto monthly CRSP via Green rdq/datadate timing window."""
    value_cols = list(QUARTERLY_CHARACTERS)
    monthly = monthly.copy()
    monthly["date"] = pd.to_datetime(monthly["date"])
    monthly["permno"] = pd.to_numeric(monthly["permno"], errors="coerce").astype("int64")

    q = quarterly[["permno", "datadate", "rdq"] + value_cols].copy()
    q["permno"] = pd.to_numeric(q["permno"], errors="coerce").astype("int64")
    q["datadate"] = pd.to_datetime(q["datadate"])
    q["rdq"] = pd.to_datetime(q["rdq"], errors="coerce")
    q = q[q["rdq"].notna()].copy()

    parts = []
    q_by_permno = {int(p): grp.sort_values("datadate") for p, grp in q.groupby("permno", sort=False)}
    for permno, m_grp in monthly.groupby("permno", sort=False):
        q_grp = q_by_permno.get(int(permno))
        if q_grp is None or q_grp.empty:
            continue
        m_grp = m_grp.sort_values("date").copy()
        win_start = intnx_month(m_grp["date"], QUARTERLY_MONTH_START_LAG, "end")
        win_end = intnx_month(m_grp["date"], QUARTERLY_MONTH_END_LAG, "beg")
        q_dates = q_grp["datadate"].to_numpy(dtype="datetime64[ns]")
        picked_idx = np.full(len(m_grp), -1, dtype=int)
        for i, (ws, we) in enumerate(zip(win_start.to_numpy(), win_end.to_numpy())):
            in_window = (q_dates >= ws) & (q_dates <= we)
            if in_window.any():
                picked_idx[i] = int(np.where(in_window)[0][-1])
        valid = picked_idx >= 0
        if not valid.any():
            continue
        part = m_grp.loc[valid].copy()
        picked_rows = q_grp.iloc[picked_idx[valid]]
        for col in value_cols:
            part[col] = picked_rows[col].to_numpy()
        parts.append(part)

    if not parts:
        return pd.DataFrame()
    out = pd.concat(parts, ignore_index=True)
    id_cols = ["permno", "permco", "date", "signal_yyyymm", "target_yyyymm", "exchcd", "shrcd"]
    return out[id_cols + value_cols]


#######################################################################################################################
#                                                    Connect to WRDS                                                  #
#######################################################################################################################

_wrds_user = os.environ.get("WRDS_USERNAME") or os.environ.get("WRDS_USER")
conn = wrds.Connection(wrds_username=_wrds_user) if _wrds_user else wrds.Connection()

CACHE_DIR.mkdir(parents=True, exist_ok=True)
CHARACTERS_DIR.mkdir(parents=True, exist_ok=True)

#######################################################################################################################
#                                              Compustat quarterly pull                                               #
#######################################################################################################################

fundq_cache = CACHE_DIR / "quarterly_fundq.parquet"
if fundq_cache.exists():
    print(f"Loading cached fundq from {fundq_cache}", flush=True)
    comp = pd.read_parquet(fundq_cache)
else:
    print("Pulling comp.fundq for 10 quarterly characters...", flush=True)
    comp = wrds_query(conn, fundq_sql(FUNDQ_ITEMS))
    comp["rdq"] = pd.to_datetime(comp["rdq"], errors="coerce")
    comp = dedupe_compustat(comp)
    comp = comp.sort_values(["gvkey", "datadate"]).drop_duplicates(["gvkey", "datadate"], keep="first")
    comp.to_parquet(fundq_cache, index=False)
    print(f"Cached fundq -> {fundq_cache}", flush=True)

#######################################################################################################################
#                                           Compute quarterly characters                                                #
#######################################################################################################################

print("Computing quarterly character formulas...", flush=True)
comp = compute_quarterly_characters(comp)

#######################################################################################################################
#                                                  CCM Green merge                                                    #
#######################################################################################################################

print("Loading CCM links and merging...", flush=True)
link = load_ccm_links(conn)
comp = attach_ccm_links(comp, link)
comp = comp[comp["permno"].notna()].copy()

#######################################################################################################################
#                                                  CRSP monthly pull                                                  #
#######################################################################################################################

msf_cache = CACHE_DIR / "quarterly_msf.parquet"
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
#                                        Expand quarterly to monthly (Green)                                          #
#######################################################################################################################

print("Expanding quarterly to monthly (Green window -10/-5)...", flush=True)
panel = expand_quarterly_to_monthly(comp, monthly)

#######################################################################################################################
#                                                       Output                                                        #
#######################################################################################################################

out_path = CHARACTERS_DIR / "quarterly.parquet"
panel.to_parquet(out_path, index=False)
print(f"Wrote {len(panel):,} rows -> {out_path}", flush=True)
