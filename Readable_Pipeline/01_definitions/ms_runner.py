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
from timing import expand_annual_file_green
from writers import write_character

M_COLUMNS = [f"m{i}" for i in range(1, 9)]
MS_ANNUAL_ITEMS = ("ni", "oancf", "ib", "dp", "xrd", "capx", "xad", "at")


def _attach_m7_m8(comp: pd.DataFrame, quarterly: pd.DataFrame) -> pd.DataFrame:
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


def build_ms_panel(db, use_cache: bool = True) -> pd.DataFrame:
    comp = fetch_green_funda(db, "ms", MS_ANNUAL_ITEMS, use_cache=use_cache)
    comp = add_lags(comp, ("at",))
    comp = attach_ccm_links_green(comp, fetch_green_ccm(db, "ms"))
    comp = comp[comp["permno"].notna()].copy()
    if should_apply_post_ccm_ia():
        avg_at = (comp["at"] + comp["lag_at"]) / 2
        comp = apply_mohanram_m1_m6(comp, avg_at)

    quarterly = fetch_quarterly_fundq(db, "ms", QUARTERLY_FUNDA_ITEMS["roavol"], use_cache=use_cache)
    quarterly = compute_quarterly_stem(quarterly, "roavol")
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
    out = merged[merged["ms"].notna()].copy()
    cols = ["permno", "permco", "date", "signal_yyyymm", "target_yyyymm", "sic", "exchcd", "shrcd", "ms"]
    return out[[c for c in cols if c in out.columns]]


def write_ms(out: pd.DataFrame) -> None:
    write_character(out, "ms", SINGLE_CHARACTERS_DIR)
