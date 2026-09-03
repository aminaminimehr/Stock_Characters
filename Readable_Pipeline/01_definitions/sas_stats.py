"""SAS-compatible rolling statistics."""
from __future__ import annotations

import numpy as np
import pandas as pd


def sas_std_row(values: np.ndarray) -> float:
    """Sample std (ddof=1) of finite values; NaN if fewer than 2 observations."""
    row = values[np.isfinite(values)]
    if len(row) < 2:
        return np.nan
    return float(np.std(row, ddof=1))


def rolling_sas_std(frame: pd.DataFrame, col: str, lags: list[int]) -> pd.Series:
    """Rolling SAS-compatible std of ``col`` and its per-gvkey lags."""
    parts = [frame[col].to_numpy(dtype=float)]
    grouped = frame.groupby("gvkey", sort=False)
    for lag_n in lags:
        parts.append(grouped[col].shift(lag_n).to_numpy(dtype=float))
    mat = np.column_stack(parts)
    return pd.Series([sas_std_row(mat[i]) for i in range(len(mat))], index=frame.index)
