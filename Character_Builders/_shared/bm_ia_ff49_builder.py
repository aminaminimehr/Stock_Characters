"""FF49 × datadate industry-adjusted book-to-market (GKX accounting_60.py convention)."""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "Character_Builders"))

from Imputation.industry_codes import add_fama_french_industry_code  # noqa: E402
from _shared.green_builders import (  # noqa: E402
    attach_permno,
    compute_annual_characters,
    load_annual_age_lookup,
    load_annual_compustat,
    load_annual_orgcap_lookup,
    load_green_ccm_links,
)

ANNUAL_OUTPUT_COLUMNS = [
    "permno",
    "permco",
    "gvkey",
    "datadate",
    "sic",
    "fyear",
    "bm_ia_ff49",
]


def apply_ff49_datadate_demean(
    comp: pd.DataFrame,
    *,
    industry_scheme: int = 49,
    industry_sic_col: str = "sic",
    industry_output_col: str = "ffi49",
    group_keys: tuple[str, ...] = ("ffi49", "datadate"),
    demean_column: str = "bm",
    output_column: str = "bm_ia_ff49",
) -> pd.DataFrame:
    """Demean ``demean_column`` by Fama-French industry × datadate (GKX bm_ia recipe)."""
    comp = comp.copy()
    comp = add_fama_french_industry_code(
        comp,
        scheme=industry_scheme,
        sic_col=industry_sic_col,
        output_col=industry_output_col,
    )
    grouped = comp.groupby(list(group_keys), dropna=False)
    comp[output_column] = comp[demean_column] - grouped[demean_column].transform("mean")
    return comp


def build_bm_ia_ff49_character(
    db,
    ccm_linktypes=None,
    ccm_linkprim=None,
    *,
    industry_scheme: int = 49,
    industry_sic_col: str = "sic",
    industry_output_col: str = "ffi49",
    group_keys: tuple[str, ...] = ("ffi49", "datadate"),
    demean_column: str = "bm",
    output_column: str = "bm_ia_ff49",
) -> pd.DataFrame:
    """Build annual FF49 industry-adjusted book-to-market on the Green Compustat panel."""
    comp = compute_annual_characters(
        load_annual_compustat(db),
        age_lookup=load_annual_age_lookup(db),
        orgcap_lookup=load_annual_orgcap_lookup(db),
    )
    link = load_green_ccm_links(db, ccm_linktypes, ccm_linkprim)
    comp = attach_permno(comp, link)
    comp = apply_ff49_datadate_demean(
        comp,
        industry_scheme=industry_scheme,
        industry_sic_col=industry_sic_col,
        industry_output_col=industry_output_col,
        group_keys=group_keys,
        demean_column=demean_column,
        output_column=output_column,
    )
    comp = comp[comp["permno"].notna()].copy()
    comp = comp[
        comp[output_column].replace([np.inf, -np.inf], np.nan).notna()
    ].copy()
    return comp[ANNUAL_OUTPUT_COLUMNS]
