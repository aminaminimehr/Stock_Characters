"""Helpers for reading Green SAS benchmark files."""
from __future__ import annotations

from pathlib import Path

import pandas as pd
import pyreadstat

SAS_EPOCH = pd.Timestamp("1960-01-01")


def sas_date_to_month(series: pd.Series) -> pd.Series:
    """Convert Green ``DATE`` column to ``YYYYMM`` int."""
    if pd.api.types.is_datetime64_any_dtype(series):
        ts = pd.to_datetime(series)
    elif pd.api.types.is_numeric_dtype(series):
        ts = SAS_EPOCH + pd.to_timedelta(series, unit="D")
    else:
        ts = pd.to_datetime(series)
    return (ts.dt.year * 100 + ts.dt.month).astype("Int64")


def read_green_sas(path: Path, usecols: list[str]) -> pd.DataFrame:
    df, _ = pyreadstat.read_sas7bdat(str(path), usecols=usecols)
    if "DATE" in df.columns:
        df["month"] = sas_date_to_month(df["DATE"])
    return df
