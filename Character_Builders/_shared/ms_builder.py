"""Mohanram financial-statement score (ms = m1 + ... + m8)."""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from Character_Panels.timing import expand_annual_file_green  # noqa: E402
from _shared.green_builders import (
    attach_permno,
    compute_annual_characters,
    load_annual_age_lookup,
    load_annual_compustat,
    load_annual_orgcap_lookup,
    load_green_ccm_links,
    load_crsp_monthly,
)
from _shared.quarterly_builders import (
    prepare_quarterly_compustat_panel,
)

M_COLUMNS = [f"m{i}" for i in range(1, 9)]


def _attach_m7_m8_by_fiscal_year(comp: pd.DataFrame, quarterly: pd.DataFrame) -> pd.DataFrame:
    """Attach m7/m8 from the last quarter of the SAME fiscal year as the annual data.

    Green SAS links m7/m8 to the annual observation by fiscal year (fyearq = fyear),
    not by a rolling CRSP-date window.  Merging by CRSP date instead would pick up
    quarterly data from the NEXT fiscal year for the later months of the annual
    signal window (months 13-18), causing a fiscal-year mismatch and reducing the
    Spearman correlation from the expected ~0.95 to ~0.53.
    """
    q = quarterly[quarterly["permno"].notna()].copy()
    q["permno"] = pd.to_numeric(q["permno"], errors="coerce")

    # Keep only the last available quarter per (permno, fyearq).
    # Prefer fqtr=4 (Q4 is the fiscal-year-end quarter); fall back to max fqtr available.
    q_last = (
        q[["permno", "fyearq", "fqtr", "m7", "m8"]]
        .sort_values(["permno", "fyearq", "fqtr"])
        .groupby(["permno", "fyearq"], as_index=False)
        .last()
        .rename(columns={"fyearq": "fyear"})
    )
    q_last["m7"] = pd.to_numeric(q_last["m7"], errors="coerce")
    q_last["m8"] = pd.to_numeric(q_last["m8"], errors="coerce")
    q_last["fyear"] = pd.to_numeric(q_last["fyear"], errors="coerce")

    comp = comp.copy()
    comp["_permno_num"] = pd.to_numeric(comp["permno"], errors="coerce")
    comp["fyear"] = pd.to_numeric(comp["fyear"], errors="coerce")

    comp = comp.merge(
        q_last[["permno", "fyear", "m7", "m8"]],
        left_on=["_permno_num", "fyear"],
        right_on=["permno", "fyear"],
        how="left",
        suffixes=("", "_q"),
    )
    comp = comp.drop(columns=["permno_q", "_permno_num"], errors="ignore")
    return comp


def build_ms_character(db, ccm_linktypes=None, ccm_linkprim=None, use_ibes=False, workers=None):
    _ = workers
    comp = compute_annual_characters(
        load_annual_compustat(db),
        age_lookup=load_annual_age_lookup(db),
        orgcap_lookup=load_annual_orgcap_lookup(db),
    )
    comp = attach_permno(comp, load_green_ccm_links(db, ccm_linktypes, ccm_linkprim))

    quarterly = prepare_quarterly_compustat_panel(db, ccm_linktypes, ccm_linkprim, use_ibes=use_ibes)

    # Attach m7/m8 from the same fiscal year (fyear = fyearq) rather than via
    # the CRSP-date window.  This ensures all 8 components come from the same
    # fiscal period and eliminates the year-mismatch for months 13-18 of the
    # annual signal window.
    comp = _attach_m7_m8_by_fiscal_year(comp, quarterly)

    # Expand all 8 components together using annual Green timing (months 7-19
    # after fiscal year end).
    monthly_index = load_crsp_monthly(db)[["permno", "signal_yyyymm"]].drop_duplicates()
    annual_all = comp[comp["permno"].notna()][
        ["permno", "permco", "gvkey", "datadate", "sic", "fyear"] + M_COLUMNS
    ].copy()
    annual_expanded = expand_annual_file_green(annual_all, M_COLUMNS, crsp_month_index=monthly_index)

    monthly = load_crsp_monthly(db)[
        ["permno", "permco", "date", "signal_yyyymm", "target_yyyymm", "siccd", "exchcd", "shrcd"]
    ].rename(columns={"siccd": "sic"})
    monthly["date"] = pd.to_datetime(monthly["date"])

    merged = monthly.merge(
        annual_expanded[["permno", "signal_yyyymm"] + M_COLUMNS],
        on=["permno", "signal_yyyymm"],
        how="inner",
    )
    for col in M_COLUMNS:
        if col not in merged.columns:
            merged[col] = np.nan

    # Greens_code.sas L799: SAS '+' yields missing if any component is missing.
    merged["ms"] = merged[M_COLUMNS].sum(axis=1, min_count=len(M_COLUMNS))
    out = merged[merged["ms"].notna()].copy()
    return out[
        ["permno", "permco", "date", "signal_yyyymm", "target_yyyymm", "sic", "exchcd", "shrcd", "ms"]
    ]
