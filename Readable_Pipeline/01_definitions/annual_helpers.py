"""Shared annual data-prep helpers (not character formulas)."""
from __future__ import annotations

import numpy as np
import pandas as pd

from constants import GREEN_CPI_BY_FYEAR
from math_ops import lag, safe_divide


def add_lags(comp: pd.DataFrame, columns: tuple[str, ...], periods: tuple[int, ...] = (1, 2)) -> pd.DataFrame:
    comp = comp.copy()
    for col in columns:
        if col not in comp.columns:
            continue
        if 1 in periods:
            comp[f"lag_{col}"] = lag(comp, col, 1)
        if 2 in periods:
            comp[f"lag2_{col}"] = lag(comp, col, 2)
    return comp


def working_capital_accrual(comp: pd.DataFrame) -> pd.Series:
    return (
        (comp["act"] - comp["lag_act"] - (comp["che"] - comp["lag_che"]))
        - (
            (comp["lct"] - comp["lag_lct"])
            - (comp["dlc"] - comp["lag_dlc"])
            - (comp["txp"] - comp["lag_txp"])
            - comp["dp"]
        )
    )


def impute_capx(comp: pd.DataFrame) -> pd.DataFrame:
    comp = comp.copy()
    firm_count = comp.groupby("gvkey").cumcount()
    impute_mask = comp["capx"].isna() & (firm_count >= 1)
    comp.loc[impute_mask, "capx"] = comp.loc[impute_mask, "ppent"] - comp.loc[impute_mask, "lag_ppent"]
    return comp


def act_lct_imputed(comp: pd.DataFrame):
    act_i = comp["act"].where(comp["act"].notna(), comp["che"] + comp["rect"] + comp["invt"])
    lct_i = comp["lct"].where(comp["lct"].notna(), comp["ap"])
    lag_act_i = comp["lag_act"].where(
        comp["lag_act"].notna(),
        comp["lag_che"] + comp["lag_rect"] + comp["lag_invt"],
    )
    lag_lct_i = comp["lag_lct"].where(comp["lag_lct"].notna(), comp["lag_ap"])
    return act_i, lct_i, lag_act_i, lag_lct_i


def accumulate_orgcap(group: pd.DataFrame) -> pd.DataFrame:
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
