"""Hardcoded lookup tables: CPI, tax rates, sin NAICS, winsor lists, FF49."""
from __future__ import annotations

import pandas as pd

from config.conventions import DATASHARE_PREDICTORS
from config.ff49_ranges import FF49_RANGES

GREEN_SIN_NAICS = {
    "7132", "71312", "713210", "71329", "713290", "72112", "721120",
}

GREEN_CPI_BY_FYEAR = {
    1974: 49.3, 1975: 53.8, 1976: 56.9, 1977: 60.6, 1978: 65.2, 1979: 72.6,
    1980: 82.4, 1981: 90.9, 1982: 96.5, 1983: 99.6, 1984: 103.9, 1985: 107.6,
    1986: 109.6, 1987: 113.6, 1988: 118.3, 1989: 124.0, 1990: 130.7, 1991: 136.2,
    1992: 140.3, 1993: 144.5, 1994: 148.2, 1995: 152.4, 1996: 156.9, 1997: 160.5,
    1998: 163.0, 1999: 166.6, 2000: 172.2, 2001: 177.1, 2002: 179.88, 2003: 183.96,
    2004: 188.9, 2005: 195.3, 2006: 201.6, 2007: 207.342, 2008: 215.303, 2009: 214.537,
    2010: 218.056, 2011: 224.939, 2012: 229.594, 2013: 229.17, 2014: 229.91,
    2015: 236.53, 2016: 240.007, 2017: 245.120, 2018: 251.107, 2019: 255.657,
    2020: 258.811, 2021: 270.970, 2022: 292.655, 2023: 304.702,
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

HITRIM_VARS = [
    "betasq", "mvel1", "dy", "lev", "baspread", "depr", "sp", "turn", "dolvol",
    "std_dolvol", "std_turn", "idiovol", "roavol", "ill", "age", "rd_sale", "rd_mve",
    "retvol", "zerotrade", "stdcf", "tang", "absacc", "stdacc", "cash", "orgcap",
    "salecash", "salerec", "saleinv", "pchsaleinv", "cashdebt", "realestate", "secured",
]
HILOTRIM_VARS = [
    "beta", "ep", "mom12m", "mom1m", "mom6m", "mom36m", "indmom", "agr", "maxret", "bm",
    "currat", "pchcurrat", "quick", "pchquick", "pchdepr", "sgr", "chempia", "acc",
    "pchsale_pchinvt", "pchsale_pchrect", "pchcapx_ia", "pchgm_pchsale", "pchsale_pchxsga",
    "mve_ia", "cfp_ia", "bm_ia", "chinv", "grltnoa", "cinvest", "tb", "cfp", "lgr", "egr",
    "pricedelay", "grcapx", "chmom", "roic", "aeavol", "chcsho", "chpmia", "chatoia", "ear",
    "rsup", "hire", "cashpr", "roaq", "roeq", "invest", "chtx", "pctacc", "gma", "operprof",
]
HITRIM_VARS = [v for v in HITRIM_VARS if v in DATASHARE_PREDICTORS]
HILOTRIM_VARS = [v for v in HILOTRIM_VARS if v in DATASHARE_PREDICTORS]


def assign_ff49(sic_series: pd.Series) -> pd.Series:
    """Map SIC codes to Fama-French 49 industry codes."""
    sic = pd.to_numeric(sic_series, errors="coerce")
    out = pd.Series(pd.NA, index=sic_series.index, dtype="Int64")
    for sic_s, sic_e, ffi in FF49_RANGES:
        mask = sic.between(sic_s, sic_e)
        out.loc[mask] = int(ffi)
    return out


def apply_winsorization(df: pd.DataFrame, month_col: str = "signal_yyyymm") -> pd.DataFrame:
    """Cross-sectionally winsorize character columns by month (Green SAS rules)."""
    out = df.copy()
    for var in HITRIM_VARS:
        if var not in out.columns:
            continue
        vals = pd.to_numeric(out[var], errors="coerce")
        p99 = vals.groupby(out[month_col], sort=False).transform(lambda s: s.quantile(0.99))
        keep = vals.isna() | (vals <= p99).fillna(False)
        out[var] = vals.where(keep, p99)
        out.loc[p99.isna(), var] = float("nan")
    for var in HILOTRIM_VARS:
        if var not in out.columns:
            continue
        vals = pd.to_numeric(out[var], errors="coerce")
        g = vals.groupby(out[month_col], sort=False)
        p1 = g.transform(lambda s: s.quantile(0.01))
        p99 = g.transform(lambda s: s.quantile(0.99))
        valid = p1.notna() & p99.notna()
        out[var] = vals.clip(lower=p1, upper=p99).where(valid, float("nan"))
    return out
