"""Per-stem annual Green formulas (from green_builders.compute_annual_characters)."""
from __future__ import annotations

import numpy as np
import pandas as pd

from annual_helpers import act_lct_imputed, add_lags, impute_capx, working_capital_accrual
from annual_runner import fetch_age_lookup, fetch_orgcap_lookup
from constants import GREEN_CPI_BY_FYEAR, GREEN_SIN_NAICS
from industry import compute_tb_1
from math_ops import indicator, lag, safe_divide

IA_STEMS = frozenset({"cfp_ia", "chatoia", "chempia", "chpmia", "pchcapx_ia", "mve_ia", "tb", "herf"})


def _normalize_naics(naics):
    """Normalize NAICS codes to comparable string form for sin-industry matching."""
    if pd.isna(naics):
        return ""
    value = pd.to_numeric(naics, errors="coerce")
    if pd.isna(value):
        return str(naics).strip()
    if float(value).is_integer():
        return str(int(value))
    return str(value).strip()


def _compute_sin(comp: pd.DataFrame) -> pd.Series:
    """Sin-stock indicator from SIC ranges or Green NAICS list."""
    sic = pd.to_numeric(comp["sic"], errors="coerce")
    sic_sin = ((sic >= 2100) & (sic <= 2199)) | ((sic >= 2080) & (sic <= 2085))
    naics_str = comp["naics"].map(_normalize_naics)
    naics_sin = naics_str.isin(GREEN_SIN_NAICS)
    return indicator(sic_sin | naics_sin)


def _avg_at(comp: pd.DataFrame) -> pd.Series:
    """Average total assets (current and lagged)."""
    return (comp["at"] + comp["lag_at"]) / 2


def _wca(comp: pd.DataFrame) -> pd.Series:
    """Working-capital accrual component used by acc/cfp family."""
    return working_capital_accrual(comp)


def apply_annual_formula(comp: pd.DataFrame, stem: str, db=None) -> pd.DataFrame:
    """Compute ``stem`` on ``comp`` (post fetch_green_funda, pre CCM)."""
    comp = comp.copy()
    stem = stem.strip()

    if stem == "ep":
        comp["mve_f"] = comp["prcc_f"] * comp["csho"]
        comp[stem] = safe_divide(comp["ib"], comp["mve_f"])
    elif stem == "rd_mve":
        comp["mve_f"] = comp["prcc_f"] * comp["csho"]
        comp[stem] = safe_divide(comp["xrd"], comp["mve_f"])
    elif stem == "lev":
        comp["mve_f"] = comp["prcc_f"] * comp["csho"]
        comp[stem] = safe_divide(comp["lt"], comp["mve_f"])
    elif stem == "dy":
        comp["mve_f"] = comp["prcc_f"] * comp["csho"]
        comp[stem] = safe_divide(comp["dvt"], comp["mve_f"])
    elif stem == "sp":
        comp["mve_f"] = comp["prcc_f"] * comp["csho"]
        comp[stem] = safe_divide(comp["sale"], comp["mve_f"])
    elif stem == "rd_sale":
        comp[stem] = safe_divide(comp["xrd"], comp["sale"])
    elif stem == "agr":
        comp = add_lags(comp, ("at",))
        comp[stem] = safe_divide(comp["at"], comp["lag_at"]) - 1
    elif stem == "gma":
        comp = add_lags(comp, ("at",))
        comp[stem] = safe_divide(comp["revt"] - comp["cogs"], comp["lag_at"])
    elif stem == "chcsho":
        comp = add_lags(comp, ("csho",))
        comp[stem] = safe_divide(comp["csho"], comp["lag_csho"]) - 1
    elif stem == "lgr":
        comp = add_lags(comp, ("lt",))
        comp[stem] = safe_divide(comp["lt"], comp["lag_lt"]) - 1
    elif stem in ("acc", "pctacc", "absacc", "cfp", "cfp_ia"):
        comp = add_lags(comp, ("ib", "oancf", "at", "act", "che", "lct", "dlc", "txp", "dp"))
        avg = _avg_at(comp)
        wca = _wca(comp)
        comp["acc"] = safe_divide(comp["ib"] - comp["oancf"], avg)
        comp.loc[comp["oancf"].isna(), "acc"] = safe_divide(wca, avg)
        comp["pctacc"] = safe_divide(comp["ib"] - comp["oancf"], comp["ib"].abs().replace(0, 0.01))
        comp.loc[comp["oancf"].isna(), "pctacc"] = safe_divide(wca, comp["ib"].abs().replace(0, 0.01))
        comp["absacc"] = comp["acc"].abs()  # runs for acc/pctacc/absacc/cfp/cfp_ia
        if stem in ("cfp", "cfp_ia"):
            comp["mve_f"] = comp["prcc_f"] * comp["csho"]
            comp["cfp"] = safe_divide(comp["ib"] - wca, comp["mve_f"])
            comp.loc[comp["oancf"].notna(), "cfp"] = safe_divide(comp["oancf"], comp["mve_f"])
            if stem == "cfp_ia":
                comp[stem] = comp["cfp"]  # demeaned in finalize
    elif stem == "hire":
        comp = add_lags(comp, ("emp",))
        comp[stem] = safe_divide(comp["emp"] - comp["lag_emp"], comp["lag_emp"]).fillna(0)
    elif stem == "sgr":
        comp = add_lags(comp, ("sale",))
        comp[stem] = safe_divide(comp["sale"], comp["lag_sale"]) - 1
    elif stem == "depr":
        comp[stem] = safe_divide(comp["dp"], comp["ppent"])
    elif stem == "pchdepr":
        comp = add_lags(comp, ("dp", "ppent"))
        depr_rate = safe_divide(comp["dp"], comp["ppent"])
        lag_depr_rate = safe_divide(comp["lag_dp"], comp["lag_ppent"])
        comp[stem] = safe_divide(depr_rate - lag_depr_rate, lag_depr_rate)
    elif stem == "cashdebt":
        comp = add_lags(comp, ("lt",))
        avg_lt = (comp["lt"] + comp["lag_lt"]) / 2
        comp[stem] = safe_divide(comp["ib"] + comp["dp"], avg_lt)
    elif stem == "cashpr":
        comp["mve_f"] = comp["prcc_f"] * comp["csho"]
        comp[stem] = safe_divide(comp["mve_f"] + comp["dltt"] - comp["at"], comp["che"])
    elif stem == "invest":
        comp = add_lags(comp, ("ppegt", "ppent", "invt", "at"))
        ppegt_delta = comp["ppegt"] - comp["lag_ppegt"]
        ppent_delta = comp["ppent"] - comp["lag_ppent"]
        invt_delta = comp["invt"] - comp["lag_invt"]
        comp[stem] = safe_divide(ppegt_delta + invt_delta, comp["lag_at"])
        comp.loc[comp["ppegt"].isna(), stem] = safe_divide(ppent_delta + invt_delta, comp["lag_at"])
    elif stem == "egr":
        comp = add_lags(comp, ("ceq",))
        comp[stem] = safe_divide(comp["ceq"] - comp["lag_ceq"], comp["lag_ceq"])
    elif stem == "chinv":
        comp = add_lags(comp, ("invt", "at"))
        comp[stem] = safe_divide(comp["invt"] - comp["lag_invt"], _avg_at(comp))
    elif stem == "grltnoa":
        comp = add_lags(comp, ("rect", "invt", "ppent", "aco", "intan", "ao", "ap", "lco", "lo", "dp", "at"))
        avg = _avg_at(comp)
        comp[stem] = safe_divide(
            (
                comp["rect"] + comp["invt"] + comp["ppent"] + comp["aco"] + comp["intan"] + comp["ao"]
                - comp["ap"] - comp["lco"] - comp["lo"]
            )
            - (
                comp["lag_rect"] + comp["lag_invt"] + comp["lag_ppent"] + comp["lag_aco"]
                + comp["lag_intan"] + comp["lag_ao"] - comp["lag_ap"] - comp["lag_lco"] - comp["lag_lo"]
            )
            - (
                comp["rect"] - comp["lag_rect"] + comp["invt"] - comp["lag_invt"]
                + comp["aco"] - comp["lag_aco"] - (comp["ap"] - comp["lag_ap"] + comp["lco"] - comp["lag_lco"])
                - comp["dp"]
            ),
            avg,
        )
    elif stem == "pchcurrat":
        comp = add_lags(comp, ("act", "lct"))
        currat = safe_divide(comp["act"], comp["lct"])
        lag_currat = safe_divide(comp["lag_act"], comp["lag_lct"])
        comp[stem] = safe_divide(currat - lag_currat, lag_currat)
    elif stem == "grcapx":
        comp = add_lags(comp, ("capx", "ppent"), periods=(1, 2))
        comp = impute_capx(comp)
        comp[stem] = safe_divide(comp["capx"] - comp["lag2_capx"], comp["lag2_capx"])
    elif stem in ("currat", "quick", "pchquick"):
        comp = add_lags(comp, ("act", "lct", "che", "rect", "invt", "ap"))
        act_i, lct_i, lag_act_i, lag_lct_i = act_lct_imputed(comp)
        comp["currat"] = safe_divide(act_i, lct_i)
        quick = safe_divide(act_i - comp["invt"], lct_i)
        lag_quick = safe_divide(lag_act_i - comp["lag_invt"], lag_lct_i)
        comp["quick"] = quick
        comp["pchquick"] = safe_divide(quick - lag_quick, lag_quick)
        if stem == "currat":
            pass
        elif stem == "quick":
            comp[stem] = comp["quick"]
        else:
            comp[stem] = comp["pchquick"]
    elif stem == "pchsaleinv":
        comp = add_lags(comp, ("sale", "invt"))
        sale_invt = safe_divide(comp["sale"], comp["invt"])
        lag_sale_invt = safe_divide(comp["lag_sale"], comp["lag_invt"])
        comp[stem] = safe_divide(sale_invt - lag_sale_invt, lag_sale_invt)
    elif stem == "salecash":
        comp[stem] = safe_divide(comp["sale"], comp["che"])
    elif stem == "saleinv":
        comp[stem] = safe_divide(comp["sale"], comp["invt"])
    elif stem == "salerec":
        comp[stem] = safe_divide(comp["sale"], comp["rect"])
    elif stem == "tang":
        comp[stem] = safe_divide(
            comp["che"] + comp["rect"] * 0.715 + comp["invt"] * 0.547 + comp["ppent"] * 0.535,
            comp["at"],
        )
    elif stem == "roic":
        comp[stem] = safe_divide(comp["ebit"] - comp["nopi"], comp["ceq"] + comp["lt"] - comp["che"])
    elif stem == "pchsale_pchinvt":
        comp = add_lags(comp, ("sale", "invt"))
        sale_growth = safe_divide(comp["sale"] - comp["lag_sale"], comp["lag_sale"])
        invt_growth = safe_divide(comp["invt"] - comp["lag_invt"], comp["lag_invt"])
        comp[stem] = sale_growth - invt_growth
    elif stem == "pchsale_pchrect":
        comp = add_lags(comp, ("sale", "rect"))
        sale_growth = safe_divide(comp["sale"] - comp["lag_sale"], comp["lag_sale"])
        rect_growth = safe_divide(comp["rect"] - comp["lag_rect"], comp["lag_rect"])
        comp[stem] = sale_growth - rect_growth
    elif stem == "pchgm_pchsale":
        comp = add_lags(comp, ("sale", "cogs"))
        sale_growth = safe_divide(comp["sale"] - comp["lag_sale"], comp["lag_sale"])
        gross_margin = comp["sale"] - comp["cogs"]
        lag_gross_margin = comp["lag_sale"] - comp["lag_cogs"]
        gross_margin_growth = safe_divide(gross_margin - lag_gross_margin, lag_gross_margin)
        comp[stem] = gross_margin_growth - sale_growth
    elif stem == "pchsale_pchxsga":
        comp = add_lags(comp, ("sale", "xsga"))
        sale_growth = safe_divide(comp["sale"] - comp["lag_sale"], comp["lag_sale"])
        xsga_growth = safe_divide(comp["xsga"] - comp["lag_xsga"], comp["lag_xsga"])
        comp[stem] = sale_growth - xsga_growth
    elif stem == "divi":
        comp = add_lags(comp, ("dvt",))
        comp[stem] = (
            comp["dvt"].notna() & (comp["dvt"] > 0) & (comp["lag_dvt"].isna() | (comp["lag_dvt"] == 0))
        ).astype(float)
    elif stem == "divo":
        comp = add_lags(comp, ("dvt",))
        comp[stem] = (
            (comp["dvt"].isna() | (comp["dvt"] == 0)) & comp["lag_dvt"].notna() & (comp["lag_dvt"] > 0)
        ).astype(float)
    elif stem == "rd":
        comp = add_lags(comp, ("xrd", "at"), periods=(1, 2))
        xrd_at = safe_divide(comp["xrd"], comp["at"])
        lag_xrd_at = safe_divide(comp["lag_xrd"], comp["lag2_at"])
        rd_growth = safe_divide(xrd_at - lag_xrd_at, lag_xrd_at).astype(float)
        comp[stem] = np.nan
        valid_rd = rd_growth.notna()
        comp.loc[valid_rd, stem] = np.where(rd_growth.loc[valid_rd] > 0.05, 1.0, 0.0)
    elif stem == "convind":
        comp["dc"] = np.nan
        dc_mask1 = comp["dcvt"].isna() & comp["dcpstk"].notna() & comp["pstk"].notna() & (comp["dcpstk"] > comp["pstk"])
        comp.loc[dc_mask1, "dc"] = comp.loc[dc_mask1, "dcpstk"] - comp.loc[dc_mask1, "pstk"]
        dc_mask2 = comp["dcvt"].isna() & comp["dcpstk"].notna() & comp["pstk"].isna()
        comp.loc[dc_mask2, "dc"] = comp.loc[dc_mask2, "dcpstk"]
        comp["dc"] = comp["dc"].combine_first(pd.to_numeric(comp["dcvt"], errors="coerce"))
        comp[stem] = ((comp["dc"].notna() & (comp["dc"] != 0)) | (comp["cshrc"].notna() & (comp["cshrc"] != 0))).astype(float)
    elif stem == "securedind":
        comp[stem] = (comp["dm"].notna() & (comp["dm"] != 0)).astype(float)
    elif stem == "secured":
        comp[stem] = safe_divide(comp["dm"], comp["dltt"])
    elif stem == "sin":
        comp[stem] = _compute_sin(comp)
    elif stem == "realestate":
        comp[stem] = safe_divide(comp["fatb"] + comp["fatl"], comp["ppegt"])
        comp.loc[comp["ppegt"].isna(), stem] = safe_divide(comp["fatb"] + comp["fatl"], comp["ppent"])
    elif stem == "orgcap":
        lookup = fetch_orgcap_lookup(db, stem)
        comp = comp.merge(lookup.drop_duplicates(["gvkey", "datadate"], keep="last"), on=["gvkey", "datadate"], how="left")
        comp.loc[comp.groupby("gvkey").cumcount() == 0, stem] = np.nan
    elif stem == "age":
        lookup = fetch_age_lookup(db, stem)
        comp = comp.merge(lookup.drop_duplicates(["gvkey", "datadate"], keep="last"), on=["gvkey", "datadate"], how="left")
    elif stem == "sic2":
        comp[stem] = comp["sic2"]
    elif stem == "chatoia":
        comp = add_lags(comp, ("sale", "at"), periods=(1, 2))
        comp["chato"] = safe_divide(comp["sale"], _avg_at(comp)) - safe_divide(
            comp["lag_sale"], (comp["lag_at"] + comp["lag2_at"]) / 2
        )
        comp[stem] = comp["chato"]
    elif stem == "chempia":
        comp = add_lags(comp, ("emp",))
        comp["hire"] = safe_divide(comp["emp"] - comp["lag_emp"], comp["lag_emp"]).fillna(0)
        comp[stem] = comp["hire"]
    elif stem == "chpmia":
        comp = add_lags(comp, ("ib", "sale"))
        comp["chpm"] = safe_divide(comp["ib"], comp["sale"]) - safe_divide(comp["lag_ib"], comp["lag_sale"])
        comp[stem] = comp["chpm"]
    elif stem == "pchcapx_ia":
        comp = add_lags(comp, ("capx", "ppent"))
        comp = impute_capx(comp)
        valid_lag_capx = comp["lag_capx"].where(comp["lag_capx"] > 0)
        comp["pchcapx"] = safe_divide(comp["capx"] - valid_lag_capx, valid_lag_capx)
        comp[stem] = comp["pchcapx"]
    elif stem == "mve_ia":
        comp["mve_f"] = comp["prcc_f"] * comp["csho"]
        comp[stem] = comp["mve_f"]
    elif stem == "tb":
        comp["tb_1"] = compute_tb_1(comp)
        comp[stem] = comp["tb_1"]
    elif stem == "herf":
        comp["sale"] = comp["sale"]
        comp[stem] = np.nan  # computed post-CCM in industry adjustment
    elif stem == "ps":
        comp = add_lags(comp, ("ni", "oancf", "at", "dltt", "act", "lct", "sale", "cogs", "scstkc"))
        comp[stem] = (
            indicator(comp["ni"] > 0)
            + indicator(comp["oancf"] > 0)
            + indicator(safe_divide(comp["ni"], comp["at"]) > safe_divide(comp["lag_ni"], comp["lag_at"]))
            + indicator(comp["oancf"] > comp["ni"])
            + indicator(safe_divide(comp["dltt"], comp["at"]) < safe_divide(comp["lag_dltt"], comp["lag_at"]))
            + indicator(safe_divide(comp["act"], comp["lct"]) > safe_divide(comp["lag_act"], comp["lag_lct"]))
            + indicator(
                safe_divide(comp["sale"] - comp["cogs"], comp["sale"])
                > safe_divide(comp["lag_sale"] - comp["lag_cogs"], comp["lag_sale"])
            )
            + indicator(safe_divide(comp["sale"], comp["at"]) > safe_divide(comp["lag_sale"], comp["lag_at"]))
            + indicator(comp["scstkc"].fillna(0) == 0)
        )
        comp.loc[comp.groupby("gvkey").cumcount() == 0, stem] = np.nan
    else:
        raise KeyError(f"No annual formula registered for {stem!r}")
    return comp


def needs_industry_adjustment(stem: str) -> bool:
    """True if stem requires post-CCM industry demeaning or herf computation."""
    return stem in IA_STEMS
