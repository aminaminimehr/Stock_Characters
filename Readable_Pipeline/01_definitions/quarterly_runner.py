"""Quarterly Compustat builders: per-stem fundq SQL + Green formulas."""
from __future__ import annotations

import numpy as np
import pandas as pd

from ccm import attach_ccm_links_green, load_ccm_links_green
from constants import QUARTERLY_MONTH_END_LAG, QUARTERLY_MONTH_START_LAG
from firm_nulling import dedupe_annual_compustat
from math_ops import safe_divide
from monthly_runner import fetch_crsp_msf, monthly_alignment_frame
from paths import SINGLE_CHARACTERS_DIR
from sas_stats import rolling_sas_std
from sql_templates import fundq_sql
from wrds_io import maybe_load_cache, maybe_save_cache, raw_sql_with_retry
from writers import write_character


def intnx_month(ts: pd.Series, n: int, alignment: str = "end") -> pd.Series:
    shifted = pd.to_datetime(ts) + pd.DateOffset(months=n)
    if alignment == "beg":
        return shifted.dt.to_period("M").dt.to_timestamp("s")
    return shifted.dt.to_period("M").dt.to_timestamp("h")


def _bool_to_int(left: pd.Series, right: pd.Series) -> pd.Series:
    return left.gt(right).fillna(False).astype(int)


def fetch_quarterly_fundq(db, stem: str, items: tuple[str, ...], use_cache: bool = True) -> pd.DataFrame:
    if use_cache:
        cached = maybe_load_cache(stem, "fundq")
        if cached is not None:
            return cached
    comp = dedupe_annual_compustat(raw_sql_with_retry(db, fundq_sql(items)))
    comp["rdq"] = pd.to_datetime(comp["rdq"], errors="coerce")
    comp = comp.sort_values(["gvkey", "datadate"]).drop_duplicates(["gvkey", "datadate"], keep="first")
    if use_cache:
        maybe_save_cache(stem, "fundq", comp)
    return comp


def compute_quarterly_stem(comp: pd.DataFrame, stem: str) -> pd.DataFrame:
    df = comp.copy().reset_index(drop=True)
    g = df.groupby("gvkey", sort=False)
    df["count"] = g.cumcount() + 1
    lag_atq = g["atq"].shift(1)
    lag4_atq = g["atq"].shift(4)
    lag4_txtq = g["txtq"].shift(4)
    lag4_saleq = g["saleq"].shift(4)

    if stem == "chtx":
        df[stem] = (df["txtq"] - lag4_txtq) / lag_atq
        df.loc[df["count"] < 5, stem] = np.nan
    elif stem == "roaq":
        df[stem] = df["ibq"] / lag_atq
        df.loc[g.head(1).index, stem] = np.nan
    elif stem == "roeq":
        df["pstk"] = np.where(df["pstkrq"].notna(), df["pstkrq"], df["pstkq"])
        scal = df["seqq"].copy()
        scal = scal.fillna(df["ceqq"] + df["pstk"])
        need_at = scal.isna() & (df["ceqq"].isna() | df["pstk"].isna())
        scal = scal.where(~need_at, df["atq"] - df["ltq"])
        df["scal"] = scal
        lag_scal = g["scal"].shift(1)
        df[stem] = df["ibq"] / lag_scal
        df.loc[g.head(1).index, stem] = np.nan
    elif stem == "rsup":
        df[stem] = (df["saleq"] - lag4_saleq) / df["mveq"]
    elif stem == "cash":
        df["cash_q"] = df["cheq"] / df["atq"]
        df[stem] = df["cash_q"]
    elif stem in ("stdacc", "stdcf", "roavol"):
        sacc_num = (df["actq"] - g["actq"].shift(1) - (df["cheq"] - g["cheq"].shift(1))) - (
            (df["lctq"] - g["lctq"].shift(1)) - (df["dlcq"] - g["dlcq"].shift(1))
        )
        df["sacc"] = sacc_num / df["saleq"]
        df.loc[df["saleq"] <= 0, "sacc"] = sacc_num / 0.01
        if stem == "stdacc":
            df[stem] = rolling_sas_std(df, "sacc", list(range(1, 16)))
            df.loc[df["count"] < 17, stem] = np.nan
        elif stem == "stdcf":
            df["scf"] = (df["ibq"] / df["saleq"]) - df["sacc"]
            df.loc[df["saleq"] <= 0, "scf"] = (df["ibq"] / 0.01) - df["sacc"]
            df[stem] = rolling_sas_std(df, "scf", list(range(1, 16)))
            df.loc[df["count"] < 17, stem] = np.nan
        else:
            df["roaq"] = df["ibq"] / lag_atq
            df.loc[df["count"] < 8, stem] = np.nan
            df[stem] = rolling_sas_std(df, "roaq", list(range(1, 8)))
    elif stem == "cinvest":
        ppent_chg = (df["ppentq"] - g["ppentq"].shift(1)) / df["saleq"]
        ind_mean = (
            (g["ppentq"].shift(1) - g["ppentq"].shift(2)) / g["saleq"].shift(1)
            + (g["ppentq"].shift(2) - g["ppentq"].shift(3)) / g["saleq"].shift(2)
            + (g["ppentq"].shift(3) - g["ppentq"].shift(4)) / g["saleq"].shift(3)
        ) / 3
        df[stem] = ppent_chg - ind_mean
        bad_sale = df["saleq"] <= 0
        df.loc[bad_sale, stem] = (
            (df["ppentq"] - g["ppentq"].shift(1)) / 0.01
            - (
                (g["ppentq"].shift(1) - g["ppentq"].shift(2)) / 0.01
                + (g["ppentq"].shift(2) - g["ppentq"].shift(3)) / 0.01
                + (g["ppentq"].shift(3) - g["ppentq"].shift(4)) / 0.01
            )
            / 3
        )
        df.loc[df["count"] < 5, stem] = np.nan
    elif stem == "nincr":
        ibq = df["ibq"]
        l1, l2, l3, l4 = g["ibq"].shift(1), g["ibq"].shift(2), g["ibq"].shift(3), g["ibq"].shift(4)
        l5, l6, l7, l8 = g["ibq"].shift(5), g["ibq"].shift(6), g["ibq"].shift(7), g["ibq"].shift(8)
        b01 = _bool_to_int(ibq, l1)
        b12 = _bool_to_int(l1, l2)
        b23 = _bool_to_int(l2, l3)
        b34 = _bool_to_int(l3, l4)
        b45 = _bool_to_int(l4, l5)
        b56 = _bool_to_int(l5, l6)
        b67 = _bool_to_int(l6, l7)
        b78 = _bool_to_int(l7, l8)
        df[stem] = (
            b01 + b01 * b12 + b01 * b12 * b23 + b01 * b12 * b23 * b34
            + b01 * b12 * b23 * b34 * b45 + b01 * b12 * b23 * b34 * b45 * b56
            + b01 * b12 * b23 * b34 * b45 * b56 * b67 + b01 * b12 * b23 * b34 * b45 * b56 * b67 * b78
        )
    else:
        raise KeyError(stem)
    return df


def expand_quarterly_to_monthly(db, quarterly: pd.DataFrame, character: str, use_cache: bool = True) -> pd.DataFrame:
    value_col = "cash_q" if character == "cash" else character
    monthly = monthly_alignment_frame(fetch_crsp_msf(db, character, use_cache=use_cache))
    monthly["date"] = pd.to_datetime(monthly["date"])
    monthly["permno"] = pd.to_numeric(monthly["permno"], errors="coerce").astype("int64")
    q = quarterly[["permno", "datadate", "rdq", value_col]].copy()
    q["permno"] = pd.to_numeric(q["permno"], errors="coerce").astype("int64")
    q["datadate"] = pd.to_datetime(q["datadate"])
    q["rdq"] = pd.to_datetime(q["rdq"], errors="coerce")
    q = q[q["rdq"].notna() & q[value_col].replace([np.inf, -np.inf], np.nan).notna()].copy()
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
        picked = np.full(len(m_grp), np.nan, dtype=float)
        for i, (ws, we) in enumerate(zip(win_start.to_numpy(), win_end.to_numpy())):
            in_window = (q_dates >= ws) & (q_dates <= we)
            if in_window.any():
                picked[i] = float(q_grp.iloc[np.where(in_window)[0][-1]][value_col])
        valid = np.isfinite(picked)
        if not valid.any():
            continue
        part = m_grp.loc[valid].copy()
        part[character] = picked[valid]
        parts.append(part)
    if not parts:
        return pd.DataFrame()
    out = pd.concat(parts, ignore_index=True)
    cols = ["permno", "permco", "date", "signal_yyyymm", "target_yyyymm", "sic", "exchcd", "shrcd", character]
    return out[[c for c in cols if c in out.columns]]


def build_quarterly_stem(db, stem: str, items: tuple[str, ...], use_cache: bool = True) -> pd.DataFrame:
    comp = fetch_quarterly_fundq(db, stem, items, use_cache=use_cache)
    comp = compute_quarterly_stem(comp, stem)
    link = load_ccm_links_green(db)
    comp = attach_ccm_links_green(comp, link)
    comp = comp[comp["permno"].notna()].copy()
    return expand_quarterly_to_monthly(db, comp, stem if stem != "cash" else "cash", use_cache=use_cache)


def write_quarterly(out: pd.DataFrame, stem: str) -> None:
    if stem == "cash" and "cash_q" in out.columns:
        out = out.rename(columns={"cash_q": "cash"})
    write_character(out, stem, SINGLE_CHARACTERS_DIR)
