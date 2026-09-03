"""Monthly winsorization (copied from green_winsor.py)."""
from __future__ import annotations

import pandas as pd

from config import DATASHARE_PREDICTORS

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


def _resolve_col(name: str, columns: list[str]) -> str | None:
    """Case-insensitive column name lookup."""
    lower = name.lower()
    for col in columns:
        if col.lower() == lower:
            return col
    return None


def apply_green_winsorization(df: pd.DataFrame, month_col: str = "signal_yyyymm") -> pd.DataFrame:
    """Cross-sectionally winsorize character columns by month (Green SAS rules)."""
    if month_col not in df.columns:
        raise KeyError(f"Winsorization requires {month_col!r} on the panel.")
    out = df.copy()
    cols = list(out.columns)
    for var in HITRIM_VARS:
        col = _resolve_col(var, cols)
        if col is None:
            continue
        # Cap at 99th percentile only (one-sided winsorization).
        p99 = out.groupby(month_col, sort=False)[col].transform(lambda s: s.quantile(0.99))
        out[col] = out[col].where(out[col].isna() | (out[col] <= p99), p99)
        out.loc[p99.isna(), col] = pd.NA
    for var in HILOTRIM_VARS:
        col = _resolve_col(var, cols)
        if col is None:
            continue
        # Clip at 1st and 99th percentiles (two-sided winsorization).
        g = out.groupby(month_col, sort=False)[col]
        p1 = g.transform(lambda s: s.quantile(0.01))
        p99 = g.transform(lambda s: s.quantile(0.99))
        clipped = out[col].clip(lower=p1, upper=p99)
        out[col] = clipped.where(p1.notna() & p99.notna(), pd.NA)
    return out
