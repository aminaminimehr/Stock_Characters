"""Monthly cross-sectional winsorization (Greens_code.sas L1160-1240)."""
from __future__ import annotations

import pandas as pd

HITRIM_VARS = [
    "betasq", "mve", "mvel1", "me", "dy", "lev", "baspread", "depr", "sp", "turn", "dolvol",
    "std_dolvol", "std_turn", "disp", "idiovol", "obklg", "roavol", "ill", "age", "rd_sale",
    "rd_mve", "rdm", "retvol", "rvar_mean", "zerotrade", "stdcf", "tang", "absacc", "stdacc",
    "cash", "orgcap", "salecash", "salerec", "saleinv", "pchsaleinv", "cashdebt", "realestate",
    "secured",
]

HILOTRIM_VARS = [
    "beta", "ep", "fgr5yr", "mom12m", "mom1m", "mom6m", "mom36m", "indmom", "sue", "agr", "maxret",
    "chfeps", "bm", "book_to_market", "currat", "pchcurrat", "quick", "pchquick", "pchdepr", "sgr",
    "chempia", "acc", "pchsale_pchinvt", "pchsale_pchrect", "pchcapx_ia", "pchgm_pchsale",
    "pchsale_pchxsga", "mve_ia", "me_ia", "cfp_ia", "bm_ia", "sfe", "chinv", "grltnoa", "cinvest",
    "tb", "cfp", "cash_flow_to_price", "lgr", "egr", "pricedelay", "grcapx", "chmom", "roic",
    "aeavol", "chcsho", "chpmia", "chatoia", "grGW", "ear", "abr", "rsup", "spi", "hire", "chadv",
    "cashpr", "roaq", "roe", "roeq", "invest", "chtx", "pctacc", "gma", "operprof",
    "operating_profitability", "op",
]


def _resolve_col(name: str, columns: list[str]) -> str | None:
    lower = name.lower()
    for col in columns:
        if col.lower() == lower:
            return col
    return None


def apply_green_winsorization(
    df: pd.DataFrame,
    month_col: str = "signal_yyyymm",
) -> pd.DataFrame:
    """Clip cross-sections each month to SAS p99 (hitrim) or p1/p99 (hilotrim)."""
    if month_col not in df.columns:
        raise KeyError(f"Winsorization requires {month_col!r} on the panel.")

    out = df.copy()
    cols = list(out.columns)

    for var in HITRIM_VARS:
        col = _resolve_col(var, cols)
        if col is None:
            continue
        p99 = out.groupby(month_col, sort=False)[col].transform(lambda s: s.quantile(0.99))
        out[col] = out[col].where(out[col].isna() | (out[col] <= p99), p99)
        out.loc[p99.isna(), col] = pd.NA

    for var in HILOTRIM_VARS:
        col = _resolve_col(var, cols)
        if col is None:
            continue
        g = out.groupby(month_col, sort=False)[col]
        p1 = g.transform(lambda s: s.quantile(0.01))
        p99 = g.transform(lambda s: s.quantile(0.99))
        clipped = out[col].clip(lower=p1, upper=p99)
        out[col] = clipped.where(p1.notna() & p99.notna(), pd.NA)

    return out
