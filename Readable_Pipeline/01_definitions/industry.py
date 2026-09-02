"""Industry-adjusted annual characteristics (copied from green_builders)."""
from __future__ import annotations

import numpy as np
import pandas as pd

from config import INDUSTRY_AGG
from constants import GREEN_TAX_RATE_BY_FYEAR
from math_ops import indicator, safe_divide


def apply_industry_adjusted_annual(comp: pd.DataFrame, character: str | None = None) -> pd.DataFrame:
    comp = comp.copy()
    grouped = comp.groupby(["sic2", "fyear"], dropna=False)
    ia_map = {
        "cfp_ia":      ("cfp",     "cfp_ia"),
        "chatoia":     ("chato",   "chatoia"),
        "chempia":     ("hire",    "chempia"),
        "chpmia":      ("chpm",    "chpmia"),
        "pchcapx_ia":  ("pchcapx", "pchcapx_ia"),
        "mve_ia":      ("mve_f",   "mve_ia"),
        "tb":          ("tb_1",    "tb"),
    }
    if character == "herf":
        industry_sales = grouped["sale"].transform("sum")
        comp["sales_share_sq"] = (comp["sale"] / industry_sales.replace(0, np.nan)) ** 2
        comp["herf"] = grouped["sales_share_sq"].transform("sum")
        return comp
    if character is not None and character in ia_map:
        base, out = ia_map[character]
        comp[out] = comp[base] - grouped[base].transform("mean")
        return comp
    # Fallback (production-style): compute all whose base columns exist
    for base, out in ia_map.values():
        if base in comp.columns:
            comp[out] = comp[base] - grouped[base].transform("mean")
    if "sale" in comp.columns:
        industry_sales = grouped["sale"].transform("sum")
        comp["sales_share_sq"] = (comp["sale"] / industry_sales.replace(0, np.nan)) ** 2
        comp["herf"] = grouped["sales_share_sq"].transform("sum")
    return comp


def apply_ia_lag_nulling(comp: pd.DataFrame, character: str) -> pd.DataFrame:
    comp = comp.copy()
    if character in ("chato", "chatoia"):
        comp.loc[comp.groupby("gvkey").cumcount() < 2, character] = np.nan
    if character in ("chpmia", "chempia", "pchcapx_ia"):
        comp.loc[comp.groupby("gvkey").cumcount() == 0, character] = np.nan
    return comp


def apply_mohanram_m1_m6(comp: pd.DataFrame, avg_at: pd.Series) -> pd.DataFrame:
    comp = comp.copy()
    roa_ms = safe_divide(comp["ni"], avg_at)
    cfroa_ms = safe_divide(comp["oancf"], avg_at)
    cfroa_ms = cfroa_ms.where(comp["oancf"].notna(), safe_divide(comp["ib"] + comp["dp"], avg_at))
    xrdint_ms = safe_divide(comp["xrd"].fillna(0), avg_at)
    capxint_ms = safe_divide(comp["capx"], avg_at)
    xadint_ms = safe_divide(comp["xad"].fillna(0), avg_at)
    med = comp.assign(
        _roa_ms=roa_ms, _cfroa_ms=cfroa_ms, _xrdint_ms=xrdint_ms,
        _capxint_ms=capxint_ms, _xadint_ms=xadint_ms,
    ).groupby(["fyear", "sic2"], dropna=False)[
        ["_roa_ms", "_cfroa_ms", "_xrdint_ms", "_capxint_ms", "_xadint_ms"]
    ].transform("median")
    med.columns = ["md_roa", "md_cfroa", "md_xrdint", "md_capxint", "md_xadint"]
    comp["m1"] = (roa_ms > med["md_roa"]).fillna(False).astype(int)
    comp["m2"] = (cfroa_ms > med["md_cfroa"]).fillna(False).astype(int)
    comp["m3"] = (comp["oancf"] > comp["ni"]).fillna(False).astype(int)
    comp["m4"] = (xrdint_ms > med["md_xrdint"]).fillna(False).astype(int)
    comp["m5"] = (capxint_ms > med["md_capxint"]).fillna(False).astype(int)
    comp["m6"] = (xadint_ms > med["md_xadint"]).fillna(False).astype(int)
    return comp


def compute_tb_1(comp: pd.DataFrame) -> pd.Series:
    tax_rate = comp["fyear"].map(GREEN_TAX_RATE_BY_FYEAR)
    tb_primary = safe_divide(comp["txfo"] + comp["txfed"], tax_rate)
    tb_fallback = safe_divide(comp["txt"] - comp["txdi"], tax_rate)
    tb_numerator = tb_primary.where(comp["txfo"].notna() & comp["txfed"].notna(), tb_fallback)
    tb_1 = safe_divide(tb_numerator, comp["ib"])
    tb_special = (
        (comp["txfo"].fillna(0) + comp["txfed"].fillna(0) > 0) | (comp["txt"] > comp["txdi"])
    ) & (comp["ib"] <= 0)
    tb_1 = tb_1.copy()
    tb_1.loc[tb_special] = 1.0
    return tb_1


def should_apply_post_ccm_ia() -> bool:
    return INDUSTRY_AGG == "post_ccm"
