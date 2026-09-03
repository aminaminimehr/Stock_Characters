"""Monthly CRSP builder steps: per-stem WRDS pull + lean Compustat SIC expand."""
from __future__ import annotations

import numpy as np
import pandas as pd

from ccm import attach_ccm_links_green, load_ccm_links_green
from config import SIC_SOURCE
from constants import MONTHLY_OUTPUT_COLUMNS
from firm_nulling import dedupe_annual_compustat
from math_ops import add_one_month
from monthly_helpers import finalize_monthly, prepare_crsp_base, rolling_return_product
from paths import SINGLE_CHARACTERS_DIR
from sql_templates import crsp_msf_sql, green_funda_sql
from timing import expand_annual_file_green
from wrds_io import maybe_load_cache, maybe_save_cache, raw_sql_with_retry
from writers import write_character

MSF_ITEMS = ("permno", "permco", "date", "ret", "prc", "shrout", "vol")


def fetch_crsp_msf(db, stem: str, use_cache: bool = True) -> pd.DataFrame:
    """Pull monthly CRSP msf for one stem and prepare base return/market-equity columns."""
    if use_cache:
        cached = maybe_load_cache(stem, "msf")
        if cached is not None:
            return cached
    crsp = raw_sql_with_retry(db, crsp_msf_sql(MSF_ITEMS))
    crsp = prepare_crsp_base(crsp)
    if use_cache:
        maybe_save_cache(stem, "msf", crsp)
    return crsp


def _fetch_sic_timing(db, stem: str, use_cache: bool) -> pd.DataFrame:
    """Fetch annual Compustat SIC linked to permno for Green monthly SIC expansion."""
    if use_cache:
        cached = maybe_load_cache(stem, "sic_timing")
        if cached is not None:
            return cached
    comp = dedupe_annual_compustat(raw_sql_with_retry(db, green_funda_sql(())))
    link = load_ccm_links_green(db)
    comp = attach_ccm_links_green(comp, link)
    annual = comp[comp["permno"].notna()][["permno", "permco", "gvkey", "datadate", "sic", "fyear"]].copy()
    if use_cache:
        maybe_save_cache(stem, "sic_timing", annual)
    return annual


def attach_monthly_sic(crsp: pd.DataFrame, db, stem: str, use_cache: bool = True) -> pd.DataFrame:
    """Attach ``sic`` and ``sic2`` to monthly CRSP rows (Compustat or CRSP source)."""
    out = crsp.copy()
    if SIC_SOURCE == "comp_company":
        # Expand annual Compustat SIC onto monthly signal grid via Green timing.
        annual = _fetch_sic_timing(db, stem, use_cache)
        crsp_idx = out[["permno", "signal_yyyymm"]].drop_duplicates()
        expanded = expand_annual_file_green(annual, ["sic"], crsp_month_index=crsp_idx)
        sic_map = expanded[["permno", "signal_yyyymm", "sic"]].drop_duplicates()
        out = out.merge(sic_map, on=["permno", "signal_yyyymm"], how="left")
        sic_num = pd.to_numeric(out["sic"], errors="coerce")
        out["sic2"] = sic_num.apply(lambda x: f"{int(x):04d}"[:2] if pd.notna(x) else np.nan)
    else:
        sic_num = pd.to_numeric(out.get("siccd"), errors="coerce")
        out["sic2"] = sic_num.apply(lambda x: f"{int(x):04d}"[:2] if pd.notna(x) else np.nan)
        out["sic"] = out.get("siccd")
        out = out.drop(columns=["siccd"], errors="ignore")
    return out


def compute_monthly_feature(crsp: pd.DataFrame, stem: str) -> pd.DataFrame:
    """Compute one monthly CRSP characteristic (mom*, dolvol, turn, indmom, mvel1)."""
    crsp = crsp.copy()
    crsp["return_count"] = crsp.groupby("permno").cumcount() + 1
    if stem == "mvel1":
        crsp["me"] = np.log(crsp.groupby("permno")["market_equity"].shift(1))
        crsp[stem] = crsp["me"]
    elif stem == "mom1m":
        crsp[stem] = crsp.groupby("permno")["ret"].shift(1)
        crsp.loc[crsp["return_count"] == 1, stem] = np.nan
    elif stem == "mom6m":
        crsp[stem] = rolling_return_product(crsp, 2, 6)
        crsp.loc[crsp["return_count"] < 7, stem] = np.nan
    elif stem == "mom12m":
        crsp[stem] = rolling_return_product(crsp, 2, 12)
        crsp.loc[crsp["return_count"] < 13, stem] = np.nan
    elif stem == "mom36m":
        crsp[stem] = rolling_return_product(crsp, 13, 36)
        crsp.loc[crsp["return_count"] < 37, stem] = np.nan
    elif stem == "chmom":
        crsp[stem] = rolling_return_product(crsp, 1, 6) - rolling_return_product(crsp, 7, 12)
        crsp.loc[crsp["return_count"] < 13, stem] = np.nan
    elif stem == "dolvol":
        crsp[stem] = np.log(
            crsp.groupby("permno")["vol"].shift(2) * crsp.groupby("permno")["prc_abs"].shift(2)
        )
    elif stem == "turn":
        vol_lags = [crsp.groupby("permno")["vol"].shift(i) for i in range(1, 4)]
        crsp[stem] = pd.concat(vol_lags, axis=1).mean(axis=1) / crsp["shrout"]
    elif stem == "indmom":
        if "mom12m" not in crsp.columns:
            crsp["mom12m"] = rolling_return_product(crsp, 2, 12)
            crsp.loc[crsp["return_count"] < 13, "mom12m"] = np.nan
        crsp[stem] = crsp.groupby(["sic2", "date"])["mom12m"].transform("mean")
    else:
        raise KeyError(stem)
    return crsp


def write_monthly(crsp: pd.DataFrame, stem: str) -> None:
    """Finalize and write one monthly character parquet."""
    out = finalize_monthly(crsp, stem)
    write_character(out, stem, SINGLE_CHARACTERS_DIR)


def monthly_alignment_frame(crsp: pd.DataFrame) -> pd.DataFrame:
    """Return deduplicated monthly rows with standard output ID columns only."""
    cols = [c for c in MONTHLY_OUTPUT_COLUMNS if c in crsp.columns]
    return crsp[cols].drop_duplicates(["permno", "date"])
