"""Annual builder pipeline steps after per-character SQL (not formulas)."""
from __future__ import annotations

import numpy as np
import pandas as pd

from ccm import attach_ccm_links_green, load_ccm_links_green
from constants import ANNUAL_ID_COLUMNS, GREEN_CPI_BY_FYEAR
from firm_nulling import apply_firm_lag_nulling, dedupe_annual_compustat
from industry import (
    apply_ia_lag_nulling,
    apply_industry_adjusted_annual,
    should_apply_post_ccm_ia,
)
from math_ops import lag, safe_divide
from paths import SINGLE_CHARACTERS_DIR
from sql_templates import green_age_lookup_sql, green_ccm_sql, green_funda_full_history_sql, green_funda_sql
from wrds_io import maybe_load_cache, maybe_save_cache, raw_sql_with_retry
from writers import write_character


def fetch_green_funda(
    db, stem: str, items: tuple[str, ...], *, include_naics: bool = False, use_cache: bool = True
) -> pd.DataFrame:
    if use_cache:
        cached = maybe_load_cache(stem, "funda")
        if cached is not None:
            return cached
    sql = green_funda_sql(items, include_naics=include_naics)
    comp = dedupe_annual_compustat(raw_sql_with_retry(db, sql))
    if use_cache:
        maybe_save_cache(stem, "funda", comp)
    return comp


def fetch_green_ccm(db, stem: str) -> pd.DataFrame:
    cached = maybe_load_cache(stem, "ccm")
    if cached is not None:
        return cached
    link = load_ccm_links_green(db)
    maybe_save_cache(stem, "ccm", link)
    return link


def finalize_green_annual(
    comp: pd.DataFrame,
    character: str,
    *,
    needs_ia: bool = False,
    db=None,
    stem: str | None = None,
) -> pd.DataFrame:
    comp = apply_firm_lag_nulling(comp, character)
    link = fetch_green_ccm(db, stem or character)
    comp = attach_ccm_links_green(comp, link)
    if needs_ia and should_apply_post_ccm_ia():
        # Compute bases needed for IA on full linked universe
        if "cfp" in comp.columns and character == "cfp_ia":
            pass  # cfp already on comp
        comp = apply_industry_adjusted_annual(comp, character)
        comp = apply_ia_lag_nulling(comp, character)
    comp = comp[comp[character].replace([np.inf, -np.inf], np.nan).notna()]
    return comp


def fetch_age_lookup(db, stem: str) -> pd.DataFrame:
    cached = maybe_load_cache(stem, "age_lookup")
    if cached is not None:
        return cached
    age = dedupe_annual_compustat(raw_sql_with_retry(db, green_age_lookup_sql()))
    age["age"] = age.groupby("gvkey").cumcount() + 1
    age = age[["gvkey", "datadate", "age"]]
    maybe_save_cache(stem, "age_lookup", age)
    return age


def fetch_orgcap_lookup(db, stem: str) -> pd.DataFrame:
    from annual_helpers import accumulate_orgcap

    cached = maybe_load_cache(stem, "orgcap_lookup")
    if cached is not None:
        return cached
    comp = dedupe_annual_compustat(raw_sql_with_retry(db, green_funda_full_history_sql(("xsga", "at"))))
    comp["lag_at"] = lag(comp, "at")
    comp["avg_at"] = (comp["at"] + comp["lag_at"]) / 2
    comp["cpi"] = comp["fyear"].map(GREEN_CPI_BY_FYEAR)
    comp["xsga_cpi"] = safe_divide(comp["xsga"], comp["cpi"])
    parts = []
    for _, grp in comp.groupby("gvkey", sort=False):
        parts.append(accumulate_orgcap(grp))
    comp = pd.concat(parts, ignore_index=True)
    comp["orgcap"] = safe_divide(comp["_orgcap_1"], comp["avg_at"])
    comp.loc[comp.groupby("gvkey").cumcount() == 0, "orgcap"] = np.nan
    out = comp[["gvkey", "datadate", "orgcap"]]
    maybe_save_cache(stem, "orgcap_lookup", out)
    return out


def write_annual(comp: pd.DataFrame, character: str) -> None:
    cols = [c for c in ANNUAL_ID_COLUMNS + [character] if c in comp.columns]
    write_character(comp[cols], character, SINGLE_CHARACTERS_DIR)
