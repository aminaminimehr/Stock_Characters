"""Quarterly Compustat, earnings-announcement daily CRSP, quarterly-monthly merge."""
from __future__ import annotations

import numpy as np
import pandas as pd
import wrds

from config import QUARTERLY_MONTH_END_LAG, QUARTERLY_MONTH_START_LAG, QUARTERLY_OUTPUT_COLS
from wrds_utils import (
    attach_ccm_links_green,
    intnx_month,
    intnx_weekday,
    load_ccm_links_green,
    retry_wrds_query,
    rolling_sas_std,
    sql_between_date,
)


QUARTERLY_SQL = """
SELECT
    SUBSTR(REPLACE(c.cusip, ' ', ''), 1, 6) AS cnum,
    c.gvkey, f.fyearq, f.fqtr, f.datadate, f.rdq,
    SUBSTR(c.sic, 1, 2) AS sic2,
    f.ibq, f.saleq, f.txtq, f.revtq, f.cogsq, f.xsgaq,
    f.atq, f.actq, f.cheq, f.lctq, f.dlcq, f.ppentq,
    ABS(f.prccq) AS prccq,
    ABS(f.prccq) * f.cshoq AS mveq,
    f.ceqq, f.seqq, f.pstkq, f.ltq, f.pstkrq
FROM comp.company c
INNER JOIN comp.fundq f ON f.gvkey = c.gvkey
WHERE f.indfmt = 'INDL'
  AND f.datafmt = 'STD'
  AND f.popsrc = 'D'
  AND f.consol = 'C'
  AND f.ibq IS NOT NULL
  AND f.datadate >= '1975-01-01'
"""


def fetch_quarterly_compustat(db: wrds.Connection, sample_start: str | None, sample_end: str | None) -> pd.DataFrame:
    date_filter = sql_between_date("f.datadate", sample_start, sample_end)
    sql = QUARTERLY_SQL
    if date_filter != "1=1":
        sql = sql + f"\n  AND {date_filter}"
    df = retry_wrds_query(db, lambda conn: conn.raw_sql(sql))
    df["datadate"] = pd.to_datetime(df["datadate"])
    df["rdq"] = pd.to_datetime(df["rdq"])
    return df.sort_values(["gvkey", "datadate"]).drop_duplicates(["gvkey", "datadate"], keep="first")


def build_quarterly_characteristics(raw: pd.DataFrame) -> pd.DataFrame:
    df = raw.copy()
    g = df.groupby("gvkey", sort=False)
    df["count"] = g.cumcount() + 1

    df["pstk"] = np.where(df["pstkrq"].notna(), df["pstkrq"], df["pstkq"])
    df["scal"] = df["seqq"]
    df.loc[df["scal"].isna(), "scal"] = df["ceqq"] + df["pstk"]
    df.loc[df["scal"].isna() & (df["ceqq"].isna() | df["pstk"].isna()), "scal"] = df["atq"] - df["ltq"]

    lag_atq = g["atq"].shift(1)
    lag4_atq = g["atq"].shift(4)
    lag4_txtq = g["txtq"].shift(4)
    lag4_saleq = g["saleq"].shift(4)
    lag_scal = g["scal"].shift(1)

    df["chtx"] = (df["txtq"] - lag4_txtq) / lag4_atq
    df["roaq"] = df["ibq"] / lag_atq
    df["roeq"] = df["ibq"] / lag_scal
    df["rsup"] = (df["saleq"] - lag4_saleq) / df["mveq"]

    actq = df["actq"]
    cheq = df["cheq"]
    lctq = df["lctq"]
    dlcq = df["dlcq"]
    sacc_num = (actq - g["actq"].shift(1) - (cheq - g["cheq"].shift(1))) - (
        (lctq - g["lctq"].shift(1)) - (dlcq - g["dlcq"].shift(1))
    )
    df["sacc"] = sacc_num / df["saleq"]
    df.loc[df["saleq"] <= 0, "sacc"] = sacc_num / 0.01

    std_lags = list(range(1, 16))
    df["stdacc"] = rolling_sas_std(df, "sacc", std_lags)
    df["sgrvol"] = rolling_sas_std(df, "rsup", list(range(1, 15)))
    df["roavol"] = rolling_sas_std(df, "roaq", std_lags)

    df["scf"] = (df["ibq"] / df["saleq"]) - df["sacc"]
    df.loc[df["saleq"] <= 0, "scf"] = (df["ibq"] / 0.01) - df["sacc"]
    df["stdcf"] = rolling_sas_std(df, "scf", std_lags)
    df["cash"] = df["cheq"] / df["atq"]

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

    df["che"] = df["ibq"] - g["ibq"].shift(4)

    ibq = df["ibq"]
    l1 = g["ibq"].shift(1)
    l2 = g["ibq"].shift(2)
    l3 = g["ibq"].shift(3)
    l4 = g["ibq"].shift(4)
    l5 = g["ibq"].shift(5)
    l6 = g["ibq"].shift(6)
    l7 = g["ibq"].shift(7)
    l8 = g["ibq"].shift(8)
    df["nincr"] = (
        (ibq > l1).astype(int)
        + (ibq > l1).astype(int) * (l1 > l2).astype(int)
        + (ibq > l1).astype(int) * (l1 > l2).astype(int) * (l2 > l3).astype(int)
        + (ibq > l1).astype(int) * (l1 > l2).astype(int) * (l2 > l3).astype(int) * (l3 > l4).astype(int)
        + (ibq > l1).astype(int)
        * (l1 > l2).astype(int)
        * (l2 > l3).astype(int)
        * (l3 > l4).astype(int)
        * (l4 > l5).astype(int)
        + (ibq > l1).astype(int)
        * (l1 > l2).astype(int)
        * (l2 > l3).astype(int)
        * (l3 > l4).astype(int)
        * (l4 > l5).astype(int)
        * (l5 > l6).astype(int)
        + (ibq > l1).astype(int)
        * (l1 > l2).astype(int)
        * (l2 > l3).astype(int)
        * (l3 > l4).astype(int)
        * (l4 > l5).astype(int)
        * (l5 > l6).astype(int)
        * (l6 > l7).astype(int)
        + (ibq > l1).astype(int)
        * (l1 > l2).astype(int)
        * (l2 > l3).astype(int)
        * (l3 > l4).astype(int)
        * (l4 > l5).astype(int)
        * (l5 > l6).astype(int)
        * (l6 > l7).astype(int)
        * (l7 > l8).astype(int)
    )

    df.loc[df.groupby("gvkey").head(1).index, ["roaq", "roeq"]] = np.nan
    df.loc[df["count"] < 5, ["chtx", "che", "cinvest"]] = np.nan
    df.loc[df["count"] < 17, ["stdacc", "stdcf", "sgrvol", "roavol"]] = np.nan

    med = df.groupby(["fyearq", "fqtr", "sic2"], dropna=False)[["roavol", "sgrvol"]].transform("median")
    med.columns = ["md_roavol", "md_sgrvol"]
    df = pd.concat([df, med], axis=1)
    df["m7"] = np.where(df["roavol"] < df["md_roavol"], 1, 0)
    df["m8"] = np.where(df["sgrvol"] < df["md_sgrvol"], 1, 0)

  # SUE without IBES: che/mveq (SAS fallback L685)
    df["sue"] = df["che"] / df["mveq"]

    return df


def add_daily_earnings_variables(db: wrds.Connection, quarterly: pd.DataFrame) -> pd.DataFrame:
    """aeavol and ear from daily CRSP around rdq (SAS L709-741)."""
    df = quarterly[quarterly["rdq"].notna() & quarterly["permno"].notna()].copy()
    if df.empty:
        df["aeavol"] = np.nan
        df["ear"] = np.nan
        return df

    permnos = df["permno"].astype(int).unique().tolist()
    permno_list = ",".join(str(p) for p in permnos[:3000])
    dsf = retry_wrds_query(
        db,
        lambda conn: conn.raw_sql(f"""
            SELECT permno, date, vol, ret
            FROM crsp.dsf
            WHERE permno IN ({permno_list})
        """),
    )
    dsf["date"] = pd.to_datetime(dsf["date"])

    records = []
    for _, row in df[["permno", "datadate", "rdq"]].drop_duplicates().iterrows():
        rdq = row["rdq"]
        win_pre_start = intnx_weekday(pd.Series([rdq]), -30).iloc[0]
        win_pre_end = intnx_weekday(pd.Series([rdq]), -10).iloc[0]
        win_evt_start = intnx_weekday(pd.Series([rdq]), -1).iloc[0]
        win_evt_end = intnx_weekday(pd.Series([rdq]), 1).iloc[0]
        sub = dsf[dsf["permno"] == row["permno"]]
        pre = sub[(sub["date"] >= win_pre_start) & (sub["date"] <= win_pre_end)]
        avgvol = pre["vol"].mean() if not pre.empty else np.nan
        evt = sub[(sub["date"] >= win_evt_start) & (sub["date"] <= win_evt_end)]
        if evt.empty or not np.isfinite(avgvol) or avgvol == 0:
            aeavol = np.nan
            ear = np.nan
        else:
            aeavol = (evt["vol"].mean() - avgvol) / avgvol
            ear = evt["ret"].sum()
        records.append(
            {
                "permno": row["permno"],
                "datadate": row["datadate"],
                "rdq": row["rdq"],
                "aeavol": aeavol,
                "ear": ear,
            }
        )
    daily_vars = pd.DataFrame(records)
    out = df.merge(daily_vars, on=["permno", "datadate", "rdq"], how="left")
    return out


def link_quarterly_to_crsp(db: wrds.Connection, quarterly: pd.DataFrame) -> pd.DataFrame:
    link = load_ccm_links_green(db)
    linked = attach_ccm_links_green(quarterly, link)
    return linked[linked["permno"].notna()].copy()


def run_quarterly_compustat(
    db: wrds.Connection,
    sample_start: str | None = None,
    sample_end: str | None = None,
) -> pd.DataFrame:
    raw = fetch_quarterly_compustat(db, sample_start, sample_end)
    built = build_quarterly_characteristics(raw)
    linked = link_quarterly_to_crsp(db, built)
    linked = linked[linked["rdq"].notna()].copy()
    with_daily = add_daily_earnings_variables(db, linked)
    keep = [c for c in QUARTERLY_OUTPUT_COLS if c in with_daily.columns]
    extra = [c for c in ["m7", "m8"] if c not in keep]
    return with_daily[keep + extra].copy()


def merge_quarterly_to_monthly(monthly: pd.DataFrame, quarterly: pd.DataFrame) -> pd.DataFrame:
    """SAS L760-801: quarterly alignment, eamonth, Mohanram ms."""
    left = monthly.drop(columns=["datadate"], errors="ignore").copy()
    left["date"] = pd.to_datetime(left["date"])
    q = quarterly.copy()
    q["datadate"] = pd.to_datetime(q["datadate"])

    left["win_start"] = intnx_month(left["date"], QUARTERLY_MONTH_START_LAG, "end")
    left["win_end"] = intnx_month(left["date"], QUARTERLY_MONTH_END_LAG, "beg")
    merged = left.merge(q, on="permno", how="left", suffixes=("", "_q"))
    in_window = merged["datadate"].notna() & (merged["datadate"] >= merged["win_start"]) & (
        merged["datadate"] <= merged["win_end"]
    )
    q_match = (
        merged.loc[in_window]
        .sort_values(["permno", "date", "datadate"], ascending=[True, True, False])
        .drop_duplicates(["permno", "date"], keep="first")
    )
    q_vars = [c for c in QUARTERLY_OUTPUT_COLS if c not in {"gvkey", "permno"}]
    pick_cols = ["permno", "date"] + [c for c in q_vars if c in q_match.columns]
    base = left.drop(columns=["win_start", "win_end"], errors="ignore")
    merged = base.merge(q_match[pick_cols], on=["permno", "date"], how="left", suffixes=("", "_q"))

    lst = q.loc[q["rdq"].notna(), ["permno", "rdq"]].drop_duplicates()
    merged = merged.merge(lst, on="permno", how="left", suffixes=("", "_eam"))
    rdq_col = "rdq_eam" if "rdq_eam" in merged.columns else "rdq"
    if rdq_col in merged.columns:
        same_month = (merged["date"].dt.year == merged[rdq_col].dt.year) & (
            merged["date"].dt.month == merged[rdq_col].dt.month
        )
        merged["eamonth"] = np.where(same_month, 1, 0)
        merged = merged.drop(columns=[rdq_col], errors="ignore")
    else:
        merged["eamonth"] = 0

    m_cols = [f"m{i}" for i in range(1, 9)]
    for col in m_cols:
        if col not in merged.columns:
            merged[col] = 0
    merged["ms"] = merged[m_cols].sum(axis=1)
    merged = merged.drop(columns=m_cols, errors="ignore")
    return merged
