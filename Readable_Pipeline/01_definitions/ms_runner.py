"""Mohanram score ms = m1 + ... + m8."""
from __future__ import annotations

import numpy as np
import pandas as pd

from annual_helpers import add_lags
from annual_runner import fetch_green_ccm, fetch_green_funda
from catalog import QUARTERLY_FUNDA_ITEMS
from ccm import attach_ccm_links_green
from industry import apply_mohanram_m1_m6, should_apply_post_ccm_ia
from math_ops import lag
from monthly_runner import attach_monthly_sic, fetch_crsp_msf
from paths import SINGLE_CHARACTERS_DIR
from quarterly_runner import compute_quarterly_stem, fetch_quarterly_fundq
from sas_stats import rolling_sas_std
from timing import expand_annual_file_green
from writers import write_character

M_COLUMNS = [f"m{i}" for i in range(1, 9)]
MS_ANNUAL_ITEMS = ("ni", "oancf", "ib", "dp", "xrd", "capx", "xad", "at")


def _attach_m7_m8(comp: pd.DataFrame, quarterly: pd.DataFrame) -> pd.DataFrame:
    """Merge last-quarter m7/m8 from quarterly panel onto annual rows by fiscal year."""
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
        q_last, left_on=["_permno_num", "fyear"], right_on=["permno", "fyear"], how="left", suffixes=("", "_q")
    )
    return comp.drop(columns=["permno_q", "_permno_num"], errors="ignore")


def _compute_m7_m8(quarterly: pd.DataFrame) -> pd.DataFrame:
    """Compute Mohanram quarterly components m7/m8 on the quarterly panel.

    m7 = 1 if roavol (earnings volatility) is below its industry median, else 0.
    m8 = 1 if sgrvol (sales-growth volatility) is below its industry median, else 0.

    Industry medians are computed by (fyearq, fqtr, sic2). SAS treats missing
    values as -inf, so a NaN roavol with an available industry median yields m7=1
    (replicated below).
    """
    df = quarterly.copy().reset_index(drop=True)
    g = df.groupby("gvkey", sort=False)
    df["count"] = g.cumcount() + 1

    # rsup = (saleq - lag4_saleq) / mveq  (sales-growth surprise)
    lag4_saleq = g["saleq"].shift(4) if "saleq" in df.columns else None
    if "mveq" in df.columns and lag4_saleq is not None:
        df["rsup"] = (df["saleq"] - lag4_saleq) / df["mveq"]

    # sgrvol = rolling std of rsup over 8 quarters (current + 7 lags)
    if "rsup" in df.columns:
        df["sgrvol"] = rolling_sas_std(df, "rsup", list(range(1, 8)))

    # roavol is normally already produced by compute_quarterly_stem("roavol");
    # recompute defensively if absent.
    if "roavol" not in df.columns and "roaq" in df.columns:
        df["roavol"] = rolling_sas_std(df, "roaq", list(range(1, 8)))

    # Green SAS L268: null roavol/sgrvol when n < 8 (BEFORE medians so early
    # firms are excluded from the industry median).
    df.loc[df["count"] < 8, ["roavol", "sgrvol"]] = np.nan

    # Industry medians by (fyearq, fqtr, sic2)
    if "sic2" in df.columns and "roavol" in df.columns and "sgrvol" in df.columns:
        med = df.groupby(["fyearq", "fqtr", "sic2"], dropna=False)[["roavol", "sgrvol"]].transform("median")
        med.columns = ["md_roavol", "md_sgrvol"]
        df = pd.concat([df, med], axis=1)
        # SAS missing semantics: NaN roavol with available median -> m7 = 1
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


def build_ms_panel(db, use_cache: bool = True) -> pd.DataFrame:
    """Build Mohanram G-score ms = m1 + ... + m8 on monthly CRSP grid."""
    comp = fetch_green_funda(db, "ms", MS_ANNUAL_ITEMS, use_cache=use_cache)
    comp = add_lags(comp, ("at",))
    comp = attach_ccm_links_green(comp, fetch_green_ccm(db, "ms"))
    comp = comp[comp["permno"].notna()].copy()
    if should_apply_post_ccm_ia():
        avg_at = (comp["at"] + comp["lag_at"]) / 2
        comp = apply_mohanram_m1_m6(comp, avg_at)

    quarterly = fetch_quarterly_fundq(db, "ms", QUARTERLY_FUNDA_ITEMS["roavol"], use_cache=use_cache)
    quarterly = compute_quarterly_stem(quarterly, "roavol")
    quarterly = _compute_m7_m8(quarterly)
    quarterly = attach_ccm_links_green(quarterly, fetch_green_ccm(db, "ms"))
    comp = _attach_m7_m8(comp, quarterly)

    crsp = fetch_crsp_msf(db, "ms", use_cache=use_cache)
    crsp = attach_monthly_sic(crsp, db, "ms", use_cache=use_cache)
    monthly_index = crsp[["permno", "signal_yyyymm"]].drop_duplicates()
    annual_all = comp[comp["permno"].notna()][["permno", "permco", "gvkey", "datadate", "sic", "fyear"] + M_COLUMNS].copy()
    annual_expanded = expand_annual_file_green(annual_all, M_COLUMNS, crsp_month_index=monthly_index)
    crsp["date"] = pd.to_datetime(crsp["date"])
    merged = crsp.merge(annual_expanded[["permno", "signal_yyyymm"] + M_COLUMNS], on=["permno", "signal_yyyymm"], how="inner")
    merged["ms"] = merged[M_COLUMNS].sum(axis=1, min_count=len(M_COLUMNS))
    # SAS '+' yields missing if any component is missing (min_count enforces that).
    out = merged[merged["ms"].notna()].copy()
    cols = ["permno", "permco", "date", "signal_yyyymm", "target_yyyymm", "sic", "exchcd", "shrcd", "ms"]
    return out[[c for c in cols if c in out.columns]]


def write_ms(out: pd.DataFrame) -> None:
    """Write ms character parquet."""
    write_character(out, "ms", SINGLE_CHARACTERS_DIR)
