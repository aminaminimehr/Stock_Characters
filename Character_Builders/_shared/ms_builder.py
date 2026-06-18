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
    expand_quarterly_to_monthly,
    prepare_quarterly_compustat_panel,
)

M_COLUMNS = [f"m{i}" for i in range(1, 9)]


def _expand_annual_m_signals(db, comp) -> pd.DataFrame:
    monthly = load_crsp_monthly(db)[["permno", "signal_yyyymm"]].drop_duplicates()
    annual = comp[comp["permno"].notna()][
        ["permno", "permco", "gvkey", "datadate", "sic", "fyear"] + M_COLUMNS[:6]
    ].copy()
    return expand_annual_file_green(annual, M_COLUMNS[:6], crsp_month_index=monthly)


def build_ms_character(db, ccm_linktypes=None, ccm_linkprim=None, use_ibes=False, workers=None):
    _ = workers
    comp = compute_annual_characters(
        load_annual_compustat(db),
        age_lookup=load_annual_age_lookup(db),
        orgcap_lookup=load_annual_orgcap_lookup(db),
    )
    comp = attach_permno(comp, load_green_ccm_links(db, ccm_linktypes, ccm_linkprim))
    annual_m = _expand_annual_m_signals(db, comp)

    quarterly = prepare_quarterly_compustat_panel(db, use_ibes=use_ibes)
    q_monthly = expand_quarterly_to_monthly(db, quarterly, "m7")
    q_monthly = q_monthly.merge(
        expand_quarterly_to_monthly(db, quarterly, "m8")[["permno", "date", "m8"]],
        on=["permno", "date"],
        how="outer",
    )

    monthly = load_crsp_monthly(db)[
        ["permno", "permco", "date", "signal_yyyymm", "target_yyyymm", "siccd", "exchcd", "shrcd"]
    ].rename(columns={"siccd": "sic"})
    monthly["date"] = pd.to_datetime(monthly["date"])

    merged = monthly.merge(
        annual_m[["permno", "signal_yyyymm"] + M_COLUMNS[:6]],
        on=["permno", "signal_yyyymm"],
        how="left",
    )
    merged = merged.merge(q_monthly[["permno", "date", "m7", "m8"]], on=["permno", "date"], how="left")
    for col in M_COLUMNS:
        if col not in merged.columns:
            merged[col] = np.nan
    # Greens_code.sas L799: ms = m1+...+m8 via SAS's '+' operator, which yields MISSING if
    # ANY component is missing. A firm-month therefore needs BOTH the annual block (m1-m6)
    # AND a matched quarterly block (m7,m8) to receive a score. Filling components with 0
    # (the prior behavior) fabricated ~1.5M spurious ms=0 rows and biased ms low wherever a
    # component failed to merge, so we propagate missingness instead.
    merged["ms"] = merged[M_COLUMNS].sum(axis=1, min_count=len(M_COLUMNS))
    out = merged[merged["ms"].notna()].copy()
    return out[
        ["permno", "permco", "date", "signal_yyyymm", "target_yyyymm", "sic", "exchcd", "shrcd", "ms"]
    ]
