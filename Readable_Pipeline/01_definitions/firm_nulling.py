"""Firm-lag nulling rules (copied from green_builders._apply_firm_lag_nulling)."""
from __future__ import annotations

import numpy as np
import pandas as pd


FIRST_YEAR_NULL = [
    "agr", "gma", "chcsho", "lgr", "acc", "pctacc", "hire", "sgr",
    "chpm", "ato", "cashdebt", "roe", "noa", "grltnoa",
    "invest", "egr", "chinv", "absacc", "pchdepr", "pchcurrat",
    "pchcapx", "pchsaleinv", "pchquick", "obklg", "chobklg",
    "pchsale_pchinvt", "pchsale_pchrect", "pchgm_pchsale", "pchsale_pchxsga",
    "divi", "divo", "rd",
]

IA_FIRST_YEAR_NULL = ["chpmia", "chempia", "pchcapx_ia"]


def apply_firm_lag_nulling(comp: pd.DataFrame, character: str) -> pd.DataFrame:
    comp = comp.copy()
    if character in ("chato", "chatoia"):
        comp.loc[comp.groupby("gvkey").cumcount() < 2, character] = np.nan
    if character in FIRST_YEAR_NULL:
        comp.loc[comp.groupby("gvkey").cumcount() == 0, character] = np.nan
    if character == "grcapx":
        comp.loc[comp.groupby("gvkey").cumcount() < 2, character] = np.nan
    if character in IA_FIRST_YEAR_NULL:
        comp.loc[comp.groupby("gvkey").cumcount() == 0, character] = np.nan
    if character == "ps":
        comp.loc[comp.groupby("gvkey").cumcount() == 0, character] = np.nan
    if character == "orgcap":
        comp.loc[comp.groupby("gvkey").cumcount() == 0, character] = np.nan
    return comp


def dedupe_annual_compustat(comp: pd.DataFrame) -> pd.DataFrame:
    comp = comp.copy()
    comp["datadate"] = pd.to_datetime(comp["datadate"])
    if "sic" in comp.columns:
        sic_str = (
            pd.to_numeric(comp["sic"], errors="coerce")
            .astype("Int64")
            .astype(str)
            .str.replace("<NA>", "", regex=False)
        )
        comp["sic2"] = sic_str.str[:2].replace("", np.nan)
    return (
        comp.sort_values(["gvkey", "datadate"])
        .drop_duplicates(["gvkey", "datadate"], keep="last")
        .sort_values(["gvkey", "datadate"])
    )
