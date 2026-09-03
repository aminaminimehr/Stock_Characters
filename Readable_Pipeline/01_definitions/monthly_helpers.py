"""Monthly CRSP pure helpers (no WRDS)."""
from __future__ import annotations

import numpy as np
import pandas as pd

from math_ops import add_one_month


def rolling_return_product(crsp: pd.DataFrame, start_lag: int, end_lag: int) -> pd.Series:
    """Compound CRSP monthly returns from ``start_lag`` through ``end_lag`` (inclusive)."""
    lagged_returns = pd.concat(
        [crsp.groupby("permno")["ret"].shift(period) for period in range(start_lag, end_lag + 1)],
        axis=1,
    )
    return (1 + lagged_returns).prod(axis=1, min_count=end_lag - start_lag + 1) - 1


def prepare_crsp_base(crsp: pd.DataFrame) -> pd.DataFrame:
    """Sort CRSP msf, compute market equity and signal/target yyyymm columns."""
    crsp = crsp.sort_values(["permno", "date"]).copy()
    crsp["date"] = pd.to_datetime(crsp["date"])
    crsp["ret"] = pd.to_numeric(crsp["ret"], errors="coerce")
    crsp["prc_abs"] = crsp["prc"].abs()
    crsp["market_equity"] = crsp["prc_abs"] * crsp["shrout"]
    crsp["signal_yyyymm"] = crsp["date"].dt.year * 100 + crsp["date"].dt.month
    crsp["target_yyyymm"] = crsp["signal_yyyymm"].map(add_one_month)
    return crsp[crsp["ret"].notna()].copy()


def finalize_monthly(out: pd.DataFrame, character: str) -> pd.DataFrame:
    """Drop rows with missing/inf character values; keep standard monthly output columns."""
    cols = ["permno", "permco", "date", "signal_yyyymm", "target_yyyymm", "sic", "exchcd", "shrcd", character]
    return out[out[character].replace([np.inf, -np.inf], np.nan).notna()][cols]
