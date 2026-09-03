"""Shared math helpers (copied from green_builders)."""
from __future__ import annotations

import numpy as np
import pandas as pd


def safe_divide(numerator, denominator):
    """Divide returning NaN where denominator is zero."""
    return numerator / denominator.replace(0, np.nan)


def lag(df: pd.DataFrame, column: str, periods: int = 1) -> pd.Series:
    """Per-gvkey lag of a Compustat column."""
    return df.groupby("gvkey")[column].shift(periods)


def indicator(condition) -> pd.Series:
    """Convert boolean condition to 0/1, treating NaN as False."""
    return condition.fillna(False).astype(int)


def add_one_month(yyyymm: int) -> int:
    """Advance yyyymm integer by one calendar month."""
    year = yyyymm // 100
    month = yyyymm % 100
    next_month = month + 1
    next_year = year + (next_month == 13)
    next_month = 1 if next_month == 13 else next_month
    return next_year * 100 + next_month
