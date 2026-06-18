"""CRSP monthly momentum and related variables (Greens_code.sas L931-997)."""
from __future__ import annotations

import numpy as np
import pandas as pd


def _lag_product(group: pd.DataFrame, lags: list[int], col: str = "ret") -> pd.Series:
    factors = pd.concat([(1 + group[col].shift(lag)) for lag in lags], axis=1)
    return factors.prod(axis=1, min_count=len(lags)) - 1


def add_crsp_monthly_variables(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out = out[out["ret"].notna()].sort_values(["permno", "date"])

    g = out.groupby("permno", sort=False)
    out["count"] = g.cumcount() + 1
    out["ewret"] = out.groupby("date")["ret"].transform("mean")

    out = out[out["ret"].notna()].sort_values(["permno", "date"])
    g = out.groupby("permno", sort=False)
    out["count"] = g.cumcount() + 1

    out["mom1m"] = g["ret"].shift(1)
    out["mom6m"] = g.apply(lambda x: _lag_product(x, [2, 3, 4, 5, 6])).reset_index(level=0, drop=True)
    out["mom12m"] = g.apply(lambda x: _lag_product(x, list(range(2, 13)))).reset_index(level=0, drop=True)
    out["mom36m"] = g.apply(lambda x: _lag_product(x, list(range(13, 37)))).reset_index(level=0, drop=True)
    out["dolvol"] = np.log(g["vol"].shift(2) * g["prc"].shift(2))
    out["chmom"] = g.apply(lambda x: _lag_product(x, list(range(1, 7))) - _lag_product(x, list(range(7, 13)))).reset_index(
        level=0, drop=True
    )
    out["turn"] = (g["vol"].shift(1) + g["vol"].shift(2) + g["vol"].shift(3)) / 3 / out["shrout"]

    if "nanalyst" in out.columns:
        out["chnanalyst"] = out["nanalyst"] - g["nanalyst"].shift(3)
    else:
        out["chnanalyst"] = np.nan

    lags6 = pd.concat([g["ret"].shift(i) for i in range(1, 7)], axis=1)
    out["retcons_pos"] = np.where(lags6.gt(0).all(axis=1), 1, 0)
    out["retcons_neg"] = np.where(lags6.lt(0).all(axis=1), 1, 0)

    out.loc[out["count"] == 1, "mom1m"] = np.nan
    out.loc[out["count"] < 13, ["mom12m", "chmom"]] = np.nan
    out.loc[out["count"] < 7, "mom6m"] = np.nan
    out.loc[out["count"] < 37, "mom36m"] = np.nan
    out.loc[out["count"] < 3, "dolvol"] = np.nan
    out.loc[out["count"] < 4, ["turn", "chnanalyst"]] = np.nan
    out.loc[out["count"] < 7, ["retcons_pos", "retcons_neg"]] = np.nan
    out["ipo"] = np.where(out["count"] <= 12, 1, 0)

    if "sic2" in out.columns:
        # Green SAS L992-997: indmom = mean(mom12m) by sic2 x date (industry momentum),
        # broadcast to every firm, not the firm's deviation from the industry mean.
        out["indmom"] = out.groupby(["sic2", "date"])["mom12m"].transform("mean")
    else:
        out["indmom"] = np.nan

    return out
