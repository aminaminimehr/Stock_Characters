import argparse
import os
import time
from pathlib import Path

import numpy as np
import pandas as pd
import wrds

from _shared.ccm import (
    add_ccm_arguments,
    attach_ccm_links,
    attach_ccm_links_green,
    load_ccm_links,
    load_ccm_links_green,
)


PROJECT_ROOT = Path(__file__).resolve().parents[2]
import sys

sys.path.insert(0, str(PROJECT_ROOT))
from output_paths import (  # noqa: E402
    CACHE_DIR,
    CHARACTER_INDIVIDUAL_DIR,
    MONTHLY_ALIGNMENT_STEMS,
    OUTPUT_DIR,
    ensure_output_tree,
    resolve_output_path,
    sql_date_filter,
)


ANNUAL_CHARACTER_INFO = {
    "absacc": "Absolute accruals",
    "acc": "Operating accruals",
    "adm": "Advertising expense-to-market",
    "age": "Years since first Compustat coverage",
    "agr": "Asset growth",
    "alm": "Asset liquidity",
    "ato": "Asset turnover",
    "bm": "Book-to-market equity",
    "bm_ia": "Industry-adjusted book-to-market",
    "cashdebt": "Cash to debt",
    "cashpr": "Cash productivity",
    "cfp": "Cash-flow-to-price",
    "cfp_ia": "Industry-adjusted cash-flow-to-price",
    "chcsho": "Change in shares outstanding",
    "chobklg": "Change in order backlog scaled by assets",
    "chinv": "Change in inventory",
    "chpm": "Industry-adjusted change in profit margin",
    "chpmia": "Industry-adjusted change in profit margin (GKX name)",
    "chatoia": "Industry-adjusted change in asset turnover",
    "chempia": "Industry-adjusted employee growth",
    "convind": "Convertible debt indicator",
    "currat": "Current ratio",
    "depr": "Depreciation / PP&E",
    "dy": "Dividend yield",
    "divi": "Dividend initiation",
    "divo": "Dividend omission",
    "egr": "Growth in common shareholder equity",
    "ep": "Earnings-to-price",
    "gma": "Gross profitability",
    "grcapx": "Growth in capital expenditures",
    "grltnoa": "Growth in long-term net operating assets",
    "herf": "Industry sales concentration",
    "hire": "Employee growth rate",
    "invest": "Capital expenditures and inventory",
    "lev": "Leverage",
    "lgr": "Growth in long-term debt",
    "me_ia": "Industry-adjusted size",
    "noa": "Net operating assets",
    "obklg": "Order backlog scaled by assets",
    "op": "Operating profitability",
    "operprof": "Operating profitability (datashare name)",
    "orgcap": "Organizational capital",
    "pctacc": "Percent operating accruals",
    "pchcurrat": "Change in current ratio",
    "pchdepr": "Change in depreciation rate",
    "pchcapx": "Change in capital expenditures",
    "pchcapx_ia": "Industry-adjusted change in capital expenditures",
    "pchgm_pchsale": "Change in gross margin minus change in sales",
    "pchquick": "Change in quick ratio",
    "pchsale_pchinvt": "Change in sales minus change in inventory",
    "pchsale_pchrect": "Change in sales minus change in receivables",
    "pchsale_pchxsga": "Change in sales minus change in SG&A",
    "pchsaleinv": "Change in sales-to-inventory",
    "pm": "Profit margin",
    "ps": "Performance score",
    "quick": "Quick ratio",
    "rd": "R&D increase indicator",
    "rd_sale": "R&D to sales",
    "rdm": "R&D expense-to-market",
    "realestate": "Real-estate holdings",
    "roe": "Return on equity",
    "roic": "Return on invested capital",
    "sgr": "Sales growth",
    "salecash": "Sales-to-cash",
    "saleinv": "Sales-to-inventory",
    "salerec": "Sales-to-receivables",
    "secured": "Secured debt",
    "securedind": "Secured debt indicator",
    "sic2": "Two-digit SIC code",
    "sin": "Sin stocks indicator",
    "sp": "Sales-to-price",
    "tb": "Industry-adjusted tax income to book income",
    "tang": "Tangibility",
}

MONTHLY_CHARACTER_INFO = {
    "chmom": "Change in six-month momentum",
    "dolvol": "Dollar trading volume",
    "indmom": "Industry momentum",
    "me": "Market equity",
    "mvel1": "Log lagged market equity",
    "mom1m": "One-month momentum",
    "mom6m": "Six-month momentum",
    "mom12m": "Twelve-month momentum",
    "mom36m": "Thirty-six-month momentum",
    "mom60m": "Sixty-month momentum",
    "seas1a": "Seasonality (lagged 11-month return)",
    "turn": "Share turnover",
}

DAILY_MONTHLY_CHARACTER_INFO = {
    "baspread": "Bid-ask spread, rolling month",
    "ill": "Illiquidity, rolling month",
    "maxret": "Maximum daily return, rolling month",
    "rvar_mean": "Daily return variance, rolling month",
    "std_dolvol": "Standard deviation of dollar trading volume, rolling month",
    "std_turn": "Standard deviation of share turnover, rolling month",
    "zerotrade": "Zero-trading days, rolling month",
}

SUPPORTED_CHARACTERS = {
    **ANNUAL_CHARACTER_INFO,
    **MONTHLY_CHARACTER_INFO,
    **DAILY_MONTHLY_CHARACTER_INFO,
}

PLANNED_CHARACTERS = {}

GREEN_SIN_NAICS = {
    "7132", "71312", "713210", "71329", "713290", "72112", "721120",
}


def _normalize_naics(naics):
    if pd.isna(naics):
        return ""
    value = pd.to_numeric(naics, errors="coerce")
    if pd.isna(value):
        return str(naics).strip()
    if float(value).is_integer():
        return str(int(value))
    return str(value).strip()


def compute_sin(comp):
    sic = pd.to_numeric(comp["sic"], errors="coerce")
    sic_sin = ((sic >= 2100) & (sic <= 2199)) | ((sic >= 2080) & (sic <= 2085))
    naics_str = comp["naics"].map(_normalize_naics)
    naics_sin = naics_str.isin(GREEN_SIN_NAICS)
    return indicator(sic_sin | naics_sin)


def safe_divide(numerator, denominator):
    return numerator / denominator.replace(0, np.nan)


def lag(df, column, periods=1):
    return df.groupby("gvkey")[column].shift(periods)


def indicator(condition):
    return condition.fillna(False).astype(int)


def add_one_month(yyyymm):
    year = yyyymm // 100
    month = yyyymm % 100
    next_month = month + 1
    next_year = year + (next_month == 13)
    next_month = 1 if next_month == 13 else next_month
    return next_year * 100 + next_month


def connect_wrds(wrds_user):
    """Connect to WRDS with explicit user or common env var fallbacks.

    Fallback order when --wrds-user is not provided:
    1) WRDS_USERNAME
    2) WRDS_USER
    """
    if not wrds_user:
        wrds_user = os.environ.get("WRDS_USERNAME") or os.environ.get("WRDS_USER")
    return wrds.Connection(wrds_username=wrds_user) if wrds_user else wrds.Connection()


def attach_permno(comp, link, green_ccm: bool = True):
  if green_ccm:
    return attach_ccm_links_green(comp, link)
  return attach_ccm_links(comp, link)


def load_green_ccm_links(db, ccm_linktypes=None, ccm_linkprim=None):
  _ = ccm_linktypes, ccm_linkprim
  return load_ccm_links_green(db)


ANNUAL_COMPUSTAT_WHERE = """
          f.indfmt = 'INDL'
          AND f.datafmt = 'STD'
          AND f.popsrc = 'D'
          AND f.consol = 'C'
          AND f.at IS NOT NULL
          AND f.prcc_f IS NOT NULL
          AND f.ni IS NOT NULL
"""

# Green SAS CPI table (1974-2015) plus BLS CPI-U annual averages for later fiscal years.
GREEN_CPI_BY_FYEAR = {
    1974: 49.3,
    1975: 53.8,
    1976: 56.9,
    1977: 60.6,
    1978: 65.2,
    1979: 72.6,
    1980: 82.4,
    1981: 90.9,
    1982: 96.5,
    1983: 99.6,
    1984: 103.9,
    1985: 107.6,
    1986: 109.6,
    1987: 113.6,
    1988: 118.3,
    1989: 124.0,
    1990: 130.7,
    1991: 136.2,
    1992: 140.3,
    1993: 144.5,
    1994: 148.2,
    1995: 152.4,
    1996: 156.9,
    1997: 160.5,
    1998: 163.0,
    1999: 166.6,
    2000: 172.2,
    2001: 177.1,
    2002: 179.88,
    2003: 183.96,
    2004: 188.9,
    2005: 195.3,
    2006: 201.6,
    2007: 207.342,
    2008: 215.303,
    2009: 214.537,
    2010: 218.056,
    2011: 224.939,
    2012: 229.594,
    2013: 229.17,
    2014: 229.91,
    2015: 236.53,
    2016: 240.007,
    2017: 245.120,
    2018: 251.107,
    2019: 255.657,
    2020: 258.811,
    2021: 270.970,
    2022: 292.655,
    2023: 304.702,
}

GREEN_TAX_RATE_BY_FYEAR = {
    year: rate
    for year, rate in [
        *((y, 0.48) for y in range(1900, 1979)),
        *((y, 0.46) for y in range(1979, 1987)),
        (1987, 0.40),
        *((y, 0.34) for y in range(1988, 1993)),
        *((y, 0.35) for y in range(1993, 2100)),
    ]
}


def _dedupe_annual_compustat(comp):
    comp["datadate"] = pd.to_datetime(comp["datadate"])
    if "sic" in comp.columns:
        sic_str = pd.to_numeric(comp["sic"], errors="coerce").astype("Int64").astype(str).str.replace("<NA>", "", regex=False)
        comp["sic2"] = sic_str.str[:2].replace("", np.nan)
    if "datadate" in comp.columns:
        comp["calendar_year"] = comp["datadate"].dt.year
    return (
        comp.sort_values(["gvkey", "datadate"])
        .drop_duplicates(["gvkey", "datadate"], keep="last")
        .sort_values(["gvkey", "datadate"])
    )


def load_annual_age_lookup(db):
    """Green age from full annual Compustat history (sample window ignored)."""
    age = raw_sql_with_retry(db, f"""
        SELECT c.gvkey, f.datadate
        FROM comp.company AS c
        JOIN comp.funda AS f
          ON c.gvkey = f.gvkey
        WHERE {ANNUAL_COMPUSTAT_WHERE}
    """)
    age = _dedupe_annual_compustat(age)
    age["age"] = age.groupby("gvkey").cumcount() + 1
    return age[["gvkey", "datadate", "age"]]


def load_annual_orgcap_lookup(db):
    """Green orgcap from full annual Compustat history (sample window ignored)."""
    comp = raw_sql_with_retry(db, f"""
        SELECT c.gvkey, f.datadate, f.fyear, f.xsga, f.at
        FROM comp.company AS c
        JOIN comp.funda AS f
          ON c.gvkey = f.gvkey
        WHERE {ANNUAL_COMPUSTAT_WHERE}
    """)
    comp = _dedupe_annual_compustat(comp)
    comp["lag_at"] = lag(comp, "at")
    comp["avg_at"] = (comp["at"] + comp["lag_at"]) / 2
    comp["cpi"] = comp["fyear"].map(GREEN_CPI_BY_FYEAR)
    comp["xsga_cpi"] = safe_divide(comp["xsga"], comp["cpi"])
    orgcap_vals = []
    for _, group in comp.groupby("gvkey", sort=False):
        orgcap_vals.append(_accumulate_orgcap(group))
    comp = pd.concat(orgcap_vals, ignore_index=True)
    comp["orgcap"] = safe_divide(comp["_orgcap_1"], comp["avg_at"])
    comp.loc[comp.groupby("gvkey").cumcount() == 0, "orgcap"] = np.nan
    return comp[["gvkey", "datadate", "orgcap"]]


def load_annual_compustat(db):
    comp = raw_sql_with_retry(db, f"""
        SELECT c.gvkey, f.datadate, f.fyear, c.sic, c.naics,
               f.sale, f.revt, f.cogs, f.xsga, f.dp, f.xrd, f.xad,
               f.ebit, f.nopi, f.txt, f.txfo, f.txfed, f.txdi,
               f.ib, f.oancf, f.dvt, f.ni, f.txp, f.xint, f.capx, f.ob,
               f.rect, f.act, f.che, f.ppegt, f.invt, f.at, f.aco,
               f.intan, f.ao, f.ppent, f.fatb, f.fatl,
               f.lct, f.dlc, f.dltt, f.lt, f.dm, f.dcvt, f.dcpstk, f.cshrc, f.ap, f.lco, f.lo,
               f.ceq, f.seq, f.pstk, f.pstkl, f.pstkrv, f.txditc,
               f.scstkc, f.emp, f.csho, ABS(f.prcc_f) AS prcc_f
        FROM comp.company AS c
        JOIN comp.funda AS f
          ON c.gvkey = f.gvkey
        WHERE {ANNUAL_COMPUSTAT_WHERE}
          AND {sql_date_filter("f.datadate")}
    """)
    return _dedupe_annual_compustat(comp)


def add_book_equity(comp):
    preferred = comp["pstkrv"].fillna(comp["pstkl"]).fillna(comp["pstk"]).fillna(0)
    stockholders_equity = comp["seq"].copy()
    stockholders_equity = stockholders_equity.fillna(comp["ceq"] + preferred)
    stockholders_equity = stockholders_equity.fillna(comp["at"] - comp["lt"])
    comp["book_equity"] = stockholders_equity + comp["txditc"].fillna(0) - preferred
    return comp


def _accumulate_orgcap(group):
    orgcap_1 = np.nan
    values = []
    for xsga_cpi in group["xsga_cpi"]:
        if pd.isna(xsga_cpi):
            values.append(np.nan)
            continue
        if pd.isna(orgcap_1):
            orgcap_1 = xsga_cpi / 0.25
        else:
            orgcap_1 = orgcap_1 * 0.85 + xsga_cpi
        values.append(orgcap_1)
    group = group.copy()
    group["_orgcap_1"] = values
    return group


def compute_annual_characters(comp, age_lookup=None, orgcap_lookup=None):
    comp = comp.copy()
    comp = add_book_equity(comp)
    comp["mve_f"] = comp["prcc_f"] * comp["csho"]
    comp["xsga0"] = comp["xsga"].fillna(0)
    comp["xint0"] = comp["xint"].fillna(0)

    for col in [
        "at", "act", "che", "lct", "dlc", "txp", "dp", "ib", "csho", "lt",
        "sale", "revt", "cogs", "emp", "rect", "invt", "ppent", "ppegt", "aco",
        "intan", "ao", "ap", "lco", "lo", "ceq", "dltt", "ni", "capx", "ob",
        "dvt", "xrd", "xsga",
    ]:
        if col in comp:
            comp[f"lag_{col}"] = lag(comp, col)
            comp[f"lag2_{col}"] = lag(comp, col, 2)

    avg_at = (comp["at"] + comp["lag_at"]) / 2
    avg_lt = (comp["lt"] + comp["lag_lt"]) / 2
    working_capital_accrual = (
        (comp["act"] - comp["lag_act"] - (comp["che"] - comp["lag_che"]))
        - (
            (comp["lct"] - comp["lag_lct"])
            - (comp["dlc"] - comp["lag_dlc"])
            - (comp["txp"] - comp["lag_txp"])
            - comp["dp"]
        )
    )

    comp["bm"] = safe_divide(comp["ceq"], comp["mve_f"])
    comp["ep"] = safe_divide(comp["ib"], comp["mve_f"])
    comp["adm"] = safe_divide(comp["xad"], comp["mve_f"])
    comp["rdm"] = safe_divide(comp["xrd"], comp["mve_f"])
    comp["lev"] = safe_divide(comp["lt"], comp["mve_f"])
    comp["dy"] = safe_divide(comp["dvt"], comp["mve_f"])
    comp["sp"] = safe_divide(comp["sale"], comp["mve_f"])
    comp["rd_sale"] = safe_divide(comp["xrd"], comp["sale"])
    comp["agr"] = safe_divide(comp["at"], comp["lag_at"]) - 1
    comp["gma"] = safe_divide(comp["revt"] - comp["cogs"], comp["lag_at"])
    comp["chcsho"] = safe_divide(comp["csho"], comp["lag_csho"]) - 1
    comp["lgr"] = safe_divide(comp["lt"], comp["lag_lt"]) - 1
    comp["acc"] = safe_divide(comp["ib"] - comp["oancf"], avg_at)
    comp.loc[comp["oancf"].isna(), "acc"] = safe_divide(working_capital_accrual, avg_at)
    comp["pctacc"] = safe_divide(comp["ib"] - comp["oancf"], comp["ib"].abs().replace(0, 0.01))
    comp.loc[comp["oancf"].isna(), "pctacc"] = safe_divide(
        working_capital_accrual, comp["ib"].abs().replace(0, 0.01)
    )
    comp["cfp"] = safe_divide(comp["ib"] - working_capital_accrual, comp["mve_f"])
    comp.loc[comp["oancf"].notna(), "cfp"] = safe_divide(comp["oancf"], comp["mve_f"])
    comp["hire"] = safe_divide(comp["emp"] - comp["lag_emp"], comp["lag_emp"]).fillna(0)
    comp["sgr"] = safe_divide(comp["sale"], comp["lag_sale"]) - 1
    comp["chpm"] = safe_divide(comp["ib"], comp["sale"]) - safe_divide(comp["lag_ib"], comp["lag_sale"])
    comp["ato"] = safe_divide(comp["sale"], avg_at)
    comp["depr"] = safe_divide(comp["dp"], comp["ppent"])
    depr_rate = safe_divide(comp["dp"], comp["ppent"])
    lag_depr_rate = safe_divide(comp["lag_dp"], comp["lag_ppent"])
    comp["pchdepr"] = safe_divide(depr_rate - lag_depr_rate, lag_depr_rate)
    comp["cashdebt"] = safe_divide(comp["ib"] + comp["dp"], avg_lt)
    comp["cashpr"] = safe_divide(comp["mve_f"] + comp["dltt"] - comp["at"], comp["che"])
    comp["pm"] = safe_divide(comp["ib"], comp["sale"])
    comp["roe"] = safe_divide(comp["ib"], comp["lag_ceq"])
    # Green SAS L206: operprof = (revt-cogs-xsga0-xint0)/lag(ceq). NOTE: Green's published
    # benchmark output (Output_From_Greens_SAS_code.sas7bdat) omits xsga0 -- it computes
    # (revt-cogs-xint0)/lag(ceq) -- which is a known TYPO in Green's run, not the intended
    # definition. The SAS code is authoritative, so we keep the full -xsga0-xint0 formula.
    # (Verified the typo via raw comp.funda; see docs/gkx/green_universe_and_mismatch_audit.md.)
    comp["op"] = safe_divide(comp["revt"] - comp["cogs"] - comp["xsga0"] - comp["xint0"], comp["lag_ceq"])
    comp["operprof"] = comp["op"]
    comp["noa"] = safe_divide(
        (comp["at"] - comp["che"]) - (comp["at"] - comp["dlc"] - comp["dltt"] - comp["pstk"] - comp["ceq"]),
        comp["lag_at"],
    )
    comp["alm"] = safe_divide(
        comp["che"] + 0.75 * (comp["act"] - comp["che"]) + 0.5 * (comp["at"] - comp["act"]),
        comp["at"],
    )
    comp["grltnoa"] = safe_divide(
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
        avg_at,
    )
    ppegt_delta = comp["ppegt"] - comp["lag_ppegt"]
    ppent_delta = comp["ppent"] - comp["lag_ppent"]
    invt_delta = comp["invt"] - comp["lag_invt"]
    comp["invest"] = safe_divide(ppegt_delta + invt_delta, comp["lag_at"])
    comp.loc[comp["ppegt"].isna(), "invest"] = safe_divide(
        ppent_delta + invt_delta, comp["lag_at"]
    )
    comp["egr"] = safe_divide(comp["ceq"] - comp["lag_ceq"], comp["lag_ceq"])
    comp["chinv"] = safe_divide(comp["invt"] - comp["lag_invt"], avg_at)
    comp["absacc"] = comp["acc"].abs()
    currat = safe_divide(comp["act"], comp["lct"])
    lag_currat = safe_divide(comp["lag_act"], comp["lag_lct"])
    comp["pchcurrat"] = safe_divide(currat - lag_currat, lag_currat)
    firm_count = comp.groupby("gvkey").cumcount()
    impute_capx = comp["capx"].isna() & (firm_count >= 1)
    comp.loc[impute_capx, "capx"] = (
        comp.loc[impute_capx, "ppent"] - comp.loc[impute_capx, "lag_ppent"]
    )
    comp["grcapx"] = safe_divide(comp["capx"] - comp["lag2_capx"], comp["lag2_capx"])
    # Green SAS treats non-positive lag_capx as missing (denominator must be > 0
    # for a growth rate to be meaningful).  Using negative denominators would
    # sign-reverse pchcapx and contaminate the SIC2×fyear industry mean used in
    # pchcapx_ia, causing a large divergence vs Green even though the base
    # pchcapx values look similar at the permno level.
    valid_lag_capx = comp["lag_capx"].where(comp["lag_capx"] > 0)
    comp["pchcapx"] = safe_divide(comp["capx"] - valid_lag_capx, valid_lag_capx)
    act_i = comp["act"].where(comp["act"].notna(), comp["che"] + comp["rect"] + comp["invt"])
    lct_i = comp["lct"].where(comp["lct"].notna(), comp["ap"])
    lag_act_i = comp["lag_act"].where(
        comp["lag_act"].notna(),
        comp["lag_che"] + comp["lag_rect"] + comp["lag_invt"],
    )
    lag_lct_i = comp["lag_lct"].where(comp["lag_lct"].notna(), comp["lag_ap"])
    comp["currat"] = safe_divide(act_i, lct_i)
    sale_invt = safe_divide(comp["sale"], comp["invt"])
    lag_sale_invt = safe_divide(comp["lag_sale"], comp["lag_invt"])
    comp["pchsaleinv"] = safe_divide(sale_invt - lag_sale_invt, lag_sale_invt)
    quick = safe_divide(act_i - comp["invt"], lct_i)
    lag_quick = safe_divide(lag_act_i - comp["lag_invt"], lag_lct_i)
    comp["pchquick"] = safe_divide(quick - lag_quick, lag_quick)
    comp["quick"] = quick
    comp["salecash"] = safe_divide(comp["sale"], comp["che"])
    comp["saleinv"] = safe_divide(comp["sale"], comp["invt"])
    comp["salerec"] = safe_divide(comp["sale"], comp["rect"])
    comp["tang"] = safe_divide(
        comp["che"] + comp["rect"] * 0.715 + comp["invt"] * 0.547 + comp["ppent"] * 0.535,
        comp["at"],
    )
    comp["roic"] = safe_divide(
        comp["ebit"] - comp["nopi"], comp["ceq"] + comp["lt"] - comp["che"]
    )
    sale_growth = safe_divide(comp["sale"] - comp["lag_sale"], comp["lag_sale"])
    invt_growth = safe_divide(comp["invt"] - comp["lag_invt"], comp["lag_invt"])
    rect_growth = safe_divide(comp["rect"] - comp["lag_rect"], comp["lag_rect"])
    xsga_growth = safe_divide(comp["xsga"] - comp["lag_xsga"], comp["lag_xsga"])
    gross_margin = comp["sale"] - comp["cogs"]
    lag_gross_margin = comp["lag_sale"] - comp["lag_cogs"]
    gross_margin_growth = safe_divide(gross_margin - lag_gross_margin, lag_gross_margin)
    comp["pchsale_pchinvt"] = sale_growth - invt_growth
    comp["pchsale_pchrect"] = sale_growth - rect_growth
    comp["pchgm_pchsale"] = gross_margin_growth - sale_growth
    comp["pchsale_pchxsga"] = sale_growth - xsga_growth
    comp["divi"] = (
        comp["dvt"].notna()
        & (comp["dvt"] > 0)
        & (comp["lag_dvt"].isna() | (comp["lag_dvt"] == 0))
    ).astype(float)
    comp["divo"] = (
        (comp["dvt"].isna() | (comp["dvt"] == 0))
        & comp["lag_dvt"].notna()
        & (comp["lag_dvt"] > 0)
    ).astype(float)
    xrd_at = safe_divide(comp["xrd"], comp["at"])
    lag_xrd_at = safe_divide(comp["lag_xrd"], comp["lag2_at"])
    rd_growth = safe_divide(xrd_at - lag_xrd_at, lag_xrd_at).astype(float)
    comp["rd"] = np.nan
    valid_rd = rd_growth.notna()
    comp.loc[valid_rd, "rd"] = np.where(rd_growth.loc[valid_rd] > 0.05, 1.0, 0.0)
    comp["dc"] = np.nan
    dc_mask1 = (
        comp["dcvt"].isna()
        & comp["dcpstk"].notna()
        & comp["pstk"].notna()
        & (comp["dcpstk"] > comp["pstk"])
    )
    comp.loc[dc_mask1, "dc"] = comp.loc[dc_mask1, "dcpstk"] - comp.loc[dc_mask1, "pstk"]
    dc_mask2 = comp["dcvt"].isna() & comp["dcpstk"].notna() & comp["pstk"].isna()
    comp.loc[dc_mask2, "dc"] = comp.loc[dc_mask2, "dcpstk"]
    comp["dc"] = comp["dc"].combine_first(pd.to_numeric(comp["dcvt"], errors="coerce"))
    comp["convind"] = (
        (comp["dc"].notna() & (comp["dc"] != 0))
        | (comp["cshrc"].notna() & (comp["cshrc"] != 0))
    ).astype(float)
    comp["securedind"] = (comp["dm"].notna() & (comp["dm"] != 0)).astype(float)
    comp["secured"] = safe_divide(comp["dm"], comp["dltt"])
    tax_rate = comp["fyear"].map(GREEN_TAX_RATE_BY_FYEAR)
    tb_primary = safe_divide(comp["txfo"] + comp["txfed"], tax_rate)
    tb_fallback = safe_divide(comp["txt"] - comp["txdi"], tax_rate)
    tb_numerator = tb_primary.where(
        comp["txfo"].notna() & comp["txfed"].notna(), tb_fallback
    )
    comp["tb_1"] = safe_divide(tb_numerator, comp["ib"])
    tb_special = (
        (comp["txfo"].fillna(0) + comp["txfed"].fillna(0) > 0)
        | (comp["txt"] > comp["txdi"])
    ) & (comp["ib"] <= 0)
    comp.loc[tb_special, "tb_1"] = 1.0
    comp["sin"] = compute_sin(comp)
    comp["realestate"] = safe_divide(comp["fatb"] + comp["fatl"], comp["ppegt"])
    comp.loc[comp["ppegt"].isna(), "realestate"] = safe_divide(
        comp["fatb"] + comp["fatl"], comp["ppent"]
    )
    comp["obklg"] = safe_divide(comp["ob"], avg_at)
    comp["chobklg"] = safe_divide(comp["ob"] - comp["lag_ob"], avg_at)

    grouped = comp.groupby(["sic2", "fyear"], dropna=False)
    comp["chato"] = safe_divide(comp["sale"], avg_at) - safe_divide(
        comp["lag_sale"], (comp["lag_at"] + comp["lag2_at"]) / 2
    )
    comp["cfp_ia"] = comp["cfp"] - grouped["cfp"].transform("mean")
    comp["chatoia"] = comp["chato"] - grouped["chato"].transform("mean")
    comp["chempia"] = comp["hire"] - grouped["hire"].transform("mean")
    chpm_group_mean = grouped["chpm"].transform("mean")
    comp["chpmia"] = comp["chpm"] - chpm_group_mean
    comp["pchcapx_ia"] = comp["pchcapx"] - grouped["pchcapx"].transform("mean")
    comp["bm_ia"] = comp["bm"] - grouped["bm"].transform("mean")
    comp["me_ia"] = comp["mve_f"] - grouped["mve_f"].transform("mean")
    comp["tb"] = comp["tb_1"] - grouped["tb_1"].transform("mean")
    industry_sales = grouped["sale"].transform("sum")
    comp["sales_share_sq"] = (comp["sale"] / industry_sales.replace(0, np.nan)) ** 2
    comp["herf"] = grouped["sales_share_sq"].transform("sum")

    comp.loc[comp.groupby("gvkey").cumcount() < 2, ["chato", "chatoia"]] = np.nan
    comp.loc[comp.groupby("gvkey").cumcount() == 0, [
        "agr", "gma", "chcsho", "lgr", "acc", "pctacc", "hire", "sgr",
        "chpm", "ato", "cashdebt", "roe", "noa", "grltnoa",
        "invest", "egr", "chinv", "absacc", "pchdepr", "pchcurrat",
        "pchcapx", "pchsaleinv", "pchquick", "obklg", "chobklg",
        "pchsale_pchinvt", "pchsale_pchrect", "pchgm_pchsale", "pchsale_pchxsga",
        "divi", "divo", "rd", "chpmia", "chempia", "pchcapx_ia",
    ]] = np.nan
    comp.loc[comp.groupby("gvkey").cumcount() < 2, "grcapx"] = np.nan

    if orgcap_lookup is not None:
        orgcap_lookup = orgcap_lookup.drop_duplicates(["gvkey", "datadate"], keep="last")
        comp = comp.merge(orgcap_lookup, on=["gvkey", "datadate"], how="left")
        comp.loc[comp.groupby("gvkey").cumcount() == 0, "orgcap"] = np.nan
    else:
        comp["cpi"] = comp["fyear"].map(GREEN_CPI_BY_FYEAR)
        comp["xsga_cpi"] = safe_divide(comp["xsga"], comp["cpi"])
        # Use a loop instead of groupby().apply() to avoid pandas 3.0 include_groups
        # behaviour where the group-key column is excluded from the sub-DataFrame,
        # causing gvkey to land in the index rather than the columns after apply().
        comp["_orgcap_1"] = np.nan
        for _, grp in comp.groupby("gvkey"):
            result = _accumulate_orgcap(grp)
            comp.loc[grp.index, "_orgcap_1"] = result["_orgcap_1"].values
        comp["orgcap"] = safe_divide(comp["_orgcap_1"], avg_at)
        comp = comp.drop(columns=["_orgcap_1"], errors="ignore")
        comp.loc[comp.groupby("gvkey").cumcount() == 0, "orgcap"] = np.nan
    if age_lookup is not None:
        age_lookup = age_lookup.drop_duplicates(["gvkey", "datadate"], keep="last")
        comp = comp.merge(age_lookup, on=["gvkey", "datadate"], how="left")
    else:
        comp["age"] = comp.groupby("gvkey").cumcount() + 1
    comp["ps"] = (
        indicator(comp["ni"] > 0)
        + indicator(comp["oancf"] > 0)
        + indicator(safe_divide(comp["ni"], comp["at"]) > safe_divide(comp["lag_ni"], comp["lag_at"]))
        + indicator(comp["oancf"] > comp["ni"])
        + indicator(safe_divide(comp["dltt"], comp["at"]) < safe_divide(comp["lag_dltt"], comp["lag_at"]))
        + indicator(safe_divide(comp["act"], comp["lct"]) > safe_divide(comp["lag_act"], comp["lag_lct"]))
        + indicator(safe_divide(comp["sale"] - comp["cogs"], comp["sale"]) > safe_divide(comp["lag_sale"] - comp["lag_cogs"], comp["lag_sale"]))
        + indicator(safe_divide(comp["sale"], comp["at"]) > safe_divide(comp["lag_sale"], comp["lag_at"]))
        + indicator(comp["scstkc"].fillna(0) == 0)
    )
    comp.loc[comp.groupby("gvkey").cumcount() == 0, "ps"] = np.nan

    # Mohanram annual signals m1-m6 (Greens_code.sas L261-285) for ms score.
    comp["_roa_ms"] = safe_divide(comp["ni"], avg_at)
    comp["_cfroa_ms"] = safe_divide(comp["oancf"], avg_at)
    comp.loc[comp["oancf"].isna(), "_cfroa_ms"] = safe_divide(comp["ib"] + comp["dp"], avg_at)
    # Green SAS treats missing xrd and xad as 0 (non-disclosing firms assumed to
    # spend nothing), so the industry medians for m4/m6 include those zeros and
    # are near-zero in non-R&D-intensive industries.  Using NaN (the Python default)
    # would exclude non-reporters from the median, producing artificially high
    # medians and far fewer m4=1 and m6=1 flags.
    comp["_xrdint_ms"] = safe_divide(comp["xrd"].fillna(0), avg_at)
    comp["_capxint_ms"] = safe_divide(comp["capx"], avg_at)
    comp["_xadint_ms"] = safe_divide(comp["xad"].fillna(0), avg_at)
    med_ms = comp.groupby(["fyear", "sic2"], dropna=False)[
        ["_roa_ms", "_cfroa_ms", "_xrdint_ms", "_capxint_ms", "_xadint_ms"]
    ].transform("median")
    med_ms.columns = ["md_roa", "md_cfroa", "md_xrdint", "md_capxint", "md_xadint"]
    comp = pd.concat([comp, med_ms], axis=1)
    comp["m1"] = (comp["_roa_ms"] > comp["md_roa"]).fillna(False).astype(int)
    comp["m2"] = (comp["_cfroa_ms"] > comp["md_cfroa"]).fillna(False).astype(int)
    comp["m3"] = (comp["oancf"] > comp["ni"]).fillna(False).astype(int)
    comp["m4"] = (comp["_xrdint_ms"] > comp["md_xrdint"]).fillna(False).astype(int)
    comp["m5"] = (comp["_capxint_ms"] > comp["md_capxint"]).fillna(False).astype(int)
    comp["m6"] = (comp["_xadint_ms"] > comp["md_xadint"]).fillna(False).astype(int)
    comp = comp.drop(
        columns=[
            "_roa_ms", "_cfroa_ms", "_xrdint_ms", "_capxint_ms", "_xadint_ms",
            "md_roa", "md_cfroa", "md_xrdint", "md_capxint", "md_xadint",
        ],
        errors="ignore",
    )

    return comp


def write_character(df, character, output_dir):
    out = df.copy()
    out = out[out[character].replace([np.inf, -np.inf], np.nan).notna()].copy()
    output_path = Path(output_dir) / f"{character}.csv"
    out.to_csv(output_path, index=False)
    print(f"{character}: {len(out):,} rows -> {output_path}")


def build_annual_character(db, character, ccm_linktypes=None, ccm_linkprim=None):
    comp = compute_annual_characters(
        load_annual_compustat(db),
        age_lookup=load_annual_age_lookup(db),
        orgcap_lookup=load_annual_orgcap_lookup(db),
    )
    link = load_green_ccm_links(db, ccm_linktypes, ccm_linkprim)
    comp = attach_permno(comp, link)
    comp = comp.rename(columns={character: "character_value"})
    comp = comp[comp["character_value"].replace([np.inf, -np.inf], np.nan).notna()].copy()
    return comp[
        ["permno", "permco", "gvkey", "datadate", "sic", "fyear", "character_value"]
    ].rename(columns={"character_value": character})


def _reset_wrds_connection(db):
    """Rollback and reconnect after a failed WRDS query."""
    try:
        conn = getattr(db, "connection", None)
        if conn is not None and hasattr(conn, "rollback"):
            conn.rollback()
    except Exception:
        pass
    try:
        db.close()
        db.connect()
    except Exception as exc:
        print(f"Warning: could not reset WRDS connection: {exc}", flush=True)


def raw_sql_with_retry(db, sql, attempts=5, pause_seconds=120):
    """Retry WRDS queries that fail from transient connection timeouts."""
    last_exc = None
    for attempt in range(1, attempts + 1):
        try:
            return db.raw_sql(sql)
        except Exception as exc:
            last_exc = exc
            msg = str(exc).lower()
            retryable = any(
                token in msg
                for token in (
                    "timeout",
                    "timed out",
                    "connection",
                    "ssl",
                    "closed",
                    "reset",
                    "rollback",
                    "invalid transaction",
                )
            )
            if attempt == attempts or not retryable:
                raise
            print(
                f"WRDS query failed (attempt {attempt}/{attempts}): {exc}; "
                f"retrying in {pause_seconds}s...",
                flush=True,
            )
            _reset_wrds_connection(db)
            time.sleep(pause_seconds)
    raise last_exc


MONTHLY_ALIGNMENT_COLUMNS = [
    "permno",
    "permco",
    "date",
    "signal_yyyymm",
    "target_yyyymm",
    "sic",
    "exchcd",
    "shrcd",
    "source_yyyymm",
]


def load_monthly_alignment_frame(output_dir=OUTPUT_DIR, db=None):
    """
    Reuse monthly CRSP timing from an existing monthly character CSV when possible.
    Avoids re-querying crsp.msf during resume runs.
    """
    from output_paths import character_csv_path

    for stem in MONTHLY_ALIGNMENT_STEMS:
        path = character_csv_path(stem)
        if not path.exists():
            continue
        monthly = pd.read_csv(path)
        required = {
            "permno",
            "permco",
            "date",
            "signal_yyyymm",
            "target_yyyymm",
            "sic",
            "exchcd",
            "shrcd",
        }
        if not required.issubset(monthly.columns):
            continue
        monthly["date"] = pd.to_datetime(monthly["date"])
        if "source_yyyymm" not in monthly.columns:
            monthly["source_yyyymm"] = monthly.groupby("permno")["signal_yyyymm"].shift(1)
        print(
            f"Monthly alignment loaded from local {path.name} ({len(monthly):,} rows)",
            flush=True,
        )
        return monthly[MONTHLY_ALIGNMENT_COLUMNS].copy()

    if db is None:
        raise FileNotFoundError(
            "No monthly character CSV found for alignment and no WRDS connection supplied."
        )
    from _shared.quarterly_builders import get_monthly_crsp_panel

    monthly = get_monthly_crsp_panel(db).copy()
    monthly["source_yyyymm"] = monthly.groupby("permno")["signal_yyyymm"].shift(1)
    print(f"Monthly alignment loaded from WRDS ({len(monthly):,} rows)", flush=True)
    return monthly[MONTHLY_ALIGNMENT_COLUMNS].copy()


_MONTHLY_CRSP_CACHE = None


def clear_monthly_crsp_cache():
    global _MONTHLY_CRSP_CACHE
    _MONTHLY_CRSP_CACHE = None


def load_crsp_monthly(db, use_cache=True):
    """
    Load filtered CRSP monthly stock file + msenames once per process.

    Xin He / GKX reference scripts (e.g. Rvar_ff3.py, maxret_d.py) typically
    pull crsp.dsf only and never touch crsp.msf. Our Green-style panel needs msf for
    permco/sic/exchcd timing, but it must be queried once—not once per characteristic.
    """
    global _MONTHLY_CRSP_CACHE
    if use_cache and _MONTHLY_CRSP_CACHE is not None:
        return _MONTHLY_CRSP_CACHE

    crsp = raw_sql_with_retry(
        db,
        f"""
        SELECT m.permno, m.permco, m.date, m.ret, m.retx, m.prc, m.shrout, m.vol,
               n.exchcd, n.shrcd, n.siccd
        FROM crsp.msf AS m
        JOIN crsp.msenames AS n
          ON m.permno = n.permno
         AND n.namedt <= m.date
         AND m.date <= COALESCE(n.nameendt, DATE '9999-12-31')
        WHERE n.shrcd IN (10, 11)
          AND n.exchcd IN (1, 2, 3)
          AND {sql_date_filter("date", "m")}
    """,
    )
    crsp["date"] = pd.to_datetime(crsp["date"])
    crsp = crsp.sort_values(["permno", "date"])
    crsp["ret"] = pd.to_numeric(crsp["ret"], errors="coerce")
    crsp["prc_abs"] = crsp["prc"].abs()
    crsp["market_equity"] = crsp["prc_abs"] * crsp["shrout"]
    crsp["signal_yyyymm"] = crsp["date"].dt.year * 100 + crsp["date"].dt.month
    crsp["target_yyyymm"] = crsp["signal_yyyymm"].map(add_one_month)
    if use_cache:
        _MONTHLY_CRSP_CACHE = crsp
    return crsp


def rolling_return_product(crsp, start_lag, end_lag):
    lagged_returns = pd.concat(
        [crsp.groupby("permno")["ret"].shift(period) for period in range(start_lag, end_lag + 1)],
        axis=1,
    )
    return (1 + lagged_returns).prod(axis=1, min_count=end_lag - start_lag + 1) - 1


def _compustat_sic2_monthly_map(db, crsp: pd.DataFrame) -> pd.DataFrame:
    """Map permno x signal month to Compustat sic2 via Green annual timing."""
    import sys
    from pathlib import Path

    project_root = Path(__file__).resolve().parents[2]
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))
    from Character_Panels.timing import expand_annual_file_green  # noqa: WPS433

    comp = compute_annual_characters(load_annual_compustat(db))
    comp = attach_permno(comp, load_green_ccm_links(db))
    annual = comp[comp["permno"].notna()][
        ["permno", "permco", "gvkey", "datadate", "sic", "fyear", "sic2"]
    ].copy()
    crsp_idx = crsp[["permno", "signal_yyyymm"]].drop_duplicates()
    expanded = expand_annual_file_green(annual, ["sic2"], crsp_month_index=crsp_idx)
    return expanded[["permno", "signal_yyyymm", "sic2"]].drop_duplicates().rename(columns={"sic2": "sic2_comp"})


def prepare_monthly_crsp_features(crsp, db=None):
    """Compute all shared monthly CRSP characteristics on one loaded panel."""
    crsp = crsp[crsp["ret"].notna()].copy()
    crsp["return_count"] = crsp.groupby("permno").cumcount() + 1
    sic_num = pd.to_numeric(crsp["siccd"], errors="coerce")
    crsp["sic2_crsp"] = sic_num.apply(lambda x: f"{int(x):04d}"[:2] if pd.notna(x) else np.nan)
    if db is not None:
        sic2_map = _compustat_sic2_monthly_map(db, crsp)
        crsp = crsp.merge(sic2_map, on=["permno", "signal_yyyymm"], how="left")
        crsp["sic2"] = crsp["sic2_comp"].fillna(crsp["sic2_crsp"])
    else:
        crsp["sic2"] = crsp["sic2_crsp"]
    crsp["me"] = np.log(crsp.groupby("permno")["market_equity"].shift(1))
    crsp["mvel1"] = crsp["me"]
    crsp["mom1m"] = crsp.groupby("permno")["ret"].shift(1)
    crsp["mom6m"] = rolling_return_product(crsp, 2, 6)
    crsp["mom12m"] = rolling_return_product(crsp, 2, 12)
    crsp["mom36m"] = rolling_return_product(crsp, 13, 36)
    crsp["mom60m"] = rolling_return_product(crsp, 13, 60)
    crsp["chmom"] = rolling_return_product(crsp, 1, 6) - rolling_return_product(crsp, 7, 12)
    crsp["seas1a"] = crsp.groupby("permno")["ret"].shift(11)
    crsp.loc[crsp["return_count"] == 1, "mom1m"] = np.nan
    crsp.loc[crsp["return_count"] < 7, "mom6m"] = np.nan
    crsp.loc[crsp["return_count"] < 13, ["mom12m", "chmom"]] = np.nan
    crsp.loc[crsp["return_count"] < 37, "mom36m"] = np.nan
    crsp.loc[crsp["return_count"] < 61, "mom60m"] = np.nan
    crsp.loc[crsp["return_count"] < 12, "seas1a"] = np.nan
    crsp["dolvol"] = np.log(
        crsp.groupby("permno")["vol"].shift(2) * crsp.groupby("permno")["prc_abs"].shift(2)
    )
    vol_lags = [crsp.groupby("permno")["vol"].shift(i) for i in range(1, 4)]
    crsp["turn"] = pd.concat(vol_lags, axis=1).mean(axis=1) / crsp["shrout"]
    # Green SAS L992-997: indmom = mean(mom12m) by sic2 x date, broadcast to every
    # firm in the industry-month (equal-weighted industry momentum), NOT the firm's
    # deviation from the industry mean.
    crsp["indmom"] = crsp.groupby(["sic2", "date"])["mom12m"].transform("mean")
    return crsp.rename(columns={"siccd": "sic"})


def finalize_monthly_character(crsp, character):
    out = crsp[crsp[character].replace([np.inf, -np.inf], np.nan).notna()].copy()
    if character in {"mom36m", "mom60m"} and out[character].nunique(dropna=True) == 1:
        only_value = out[character].dropna().iloc[0]
        if np.isclose(only_value, -1):
            raise ValueError(
                f"{character} is degenerate at -1. Recheck the long-horizon momentum input returns."
            )
    return out[
        ["permno", "permco", "date", "signal_yyyymm", "target_yyyymm", "sic", "exchcd", "shrcd", character]
    ]


def build_monthly_character(db, character, monthly_panel=None):
    if monthly_panel is None:
        monthly_panel = prepare_monthly_crsp_features(load_crsp_monthly(db), db=db)
    return finalize_monthly_character(monthly_panel, character)


def build_all_monthly_characters(db, characters=None):
    """One WRDS monthly pull for all Green monthly characteristics (Xiu-style batching)."""
    characters = characters or list(MONTHLY_CHARACTER_INFO)
    if not characters:
        return {}
    print("Loading CRSP monthly panel once for all monthly characters...", flush=True)
    monthly_panel = prepare_monthly_crsp_features(load_crsp_monthly(db), db=db)
    return {character: finalize_monthly_character(monthly_panel, character) for character in characters}


def _daily_monthly_sql() -> str:
    return f"""
        SELECT permno,
               DATE_TRUNC('month', date)::date AS month_start,
               MAX(ret) AS maxret,
               STDDEV_SAMP(ret) AS rvar_mean,
               AVG((askhi - bidlo) / NULLIF(((askhi + bidlo) / 2), 0)) AS baspread,
               STDDEV_SAMP(LOG(NULLIF(ABS(prc * vol), 0))) AS std_dolvol,
               STDDEV_SAMP(vol / NULLIF(shrout, 0)) AS std_turn,
               AVG(ABS(ret) / NULLIF(ABS(prc) * vol, 0)) AS ill,
               SUM(CASE WHEN vol = 0 THEN 1 ELSE 0 END)::double precision AS countzero,
               COUNT(*)::double precision AS ndays,
               SUM(vol / NULLIF(shrout, 0))::double precision AS turn_sum
        FROM crsp.dsf
        WHERE {sql_date_filter("date")}
        GROUP BY permno, DATE_TRUNC('month', date)::date
    """


def _finalize_daily_monthly_frame(daily: pd.DataFrame) -> pd.DataFrame:
    daily["month_start"] = pd.to_datetime(daily["month_start"])
    daily["source_yyyymm"] = daily["month_start"].dt.year * 100 + daily["month_start"].dt.month
    daily["zerotrade"] = (daily["countzero"] + ((1 / daily["turn_sum"]) / 480000)) * 21 / daily["ndays"]
    return daily


def load_daily_monthly(db, workers: int | None = None):
    _ = workers  # daily-monthly uses one server-side SQL aggregation (formulas unchanged)
    daily = raw_sql_with_retry(db, _daily_monthly_sql())
    return _finalize_daily_monthly_frame(daily)


def build_daily_monthly_character(db, character):
    daily = load_daily_monthly(db)
    monthly = load_crsp_monthly(db)[
        ["permno", "permco", "date", "signal_yyyymm", "target_yyyymm", "siccd", "exchcd", "shrcd"]
    ].rename(columns={"siccd": "sic"})
    monthly["source_yyyymm"] = monthly.groupby("permno")["signal_yyyymm"].shift(1)
    out = monthly.merge(daily[["permno", "source_yyyymm", character]], on=["permno", "source_yyyymm"], how="left")
    out = out[out[character].replace([np.inf, -np.inf], np.nan).notna()].copy()
    return out[["permno", "permco", "date", "signal_yyyymm", "target_yyyymm", "sic", "exchcd", "shrcd", character]]


def build_character(db, character, ccm_linktypes=None, ccm_linkprim=None):
    if character in ANNUAL_CHARACTER_INFO:
        return build_annual_character(db, character, ccm_linktypes, ccm_linkprim)
    if character in MONTHLY_CHARACTER_INFO:
        return build_monthly_character(db, character)
    if character in DAILY_MONTHLY_CHARACTER_INFO:
        return build_daily_monthly_character(db, character)

    from _shared.quarterly_builders import QUARTERLY_CHARACTER_INFO, build_quarterly_character

    if character in QUARTERLY_CHARACTER_INFO:
        return build_quarterly_character(db, character, ccm_linktypes, ccm_linkprim)
    if character == "beta":
        from _shared.beta_builder import build_beta_character

        return build_beta_character(db)
    if character == "ear":
        from _shared.event_builders import build_ear_character

        return build_ear_character(db, ccm_linktypes, ccm_linkprim)
    if character == "abr":
        from _shared.event_builders import build_abr_character

        return build_abr_character(db, ccm_linktypes, ccm_linkprim)
    if character == "re":
        from _shared.ibes_builders import build_re_character

        return build_re_character(db)
    if character in PLANNED_CHARACTERS:
        raise NotImplementedError(
            f"{character} needs an additional specialized data source or event-time routine. "
            f"Note: {PLANNED_CHARACTERS[character]}"
        )
    raise ValueError(f"Unknown character: {character}")


def run_character_cli(character, description):
    parser = argparse.ArgumentParser(description=f"Build {character}: {description}.")
    parser.add_argument("--wrds-user", default=None)
    parser.add_argument("--output", default=f"{character}.csv")
    add_ccm_arguments(parser)
    args = parser.parse_args()

    db = connect_wrds(args.wrds_user)
    try:
        out = build_character(db, character, args.ccm_linktypes, args.ccm_linkprim)
    finally:
        db.close()

    output_path = Path(args.output)
    if not output_path.is_absolute():
        output_path = OUTPUT_DIR / output_path
    output_path.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(output_path, index=False)
    print(f"Saved {character} to: {output_path.resolve()}")
    print(f"Rows: {len(out):,}")
