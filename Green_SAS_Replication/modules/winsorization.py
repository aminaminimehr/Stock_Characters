"""Monthly winsorization by date (Greens_code.sas L1160-1240)."""
from __future__ import annotations

import pandas as pd

from config import HILOTRIM_VARS, HITRIM_VARS


def _normalize_col(name: str) -> str:
    return name.lower()


def winsorize_green(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out["date"] = pd.to_datetime(out["date"])
    colmap = {_normalize_col(c): c for c in out.columns}

    # One-sided p99 for hitrim
    hitrim = [_normalize_col(v) for v in HITRIM_VARS]
    for date, grp in out.groupby("date", sort=False):
        idx = grp.index
        for var in hitrim:
            if var not in colmap:
                continue
            col = colmap[var]
            series = out.loc[idx, col]
            p99 = series.quantile(0.99)
            if pd.isna(p99):
                out.loc[idx, col] = pd.NA
            else:
                out.loc[idx, col] = series.where(series.isna() | (series <= p99), p99)

    # Two-sided p1/p99 for hilotrim
    hilotrim = [_normalize_col(v) for v in HILOTRIM_VARS]
    for date, grp in out.groupby("date", sort=False):
        idx = grp.index
        for var in hilotrim:
            if var not in colmap:
                continue
            col = colmap[var]
            series = out.loc[idx, col]
            p1 = series.quantile(0.01)
            p99 = series.quantile(0.99)
            if pd.isna(p1) or pd.isna(p99):
                out.loc[idx, col] = pd.NA
            else:
                clipped = series.clip(lower=p1, upper=p99)
                out.loc[idx, col] = clipped

    return out
