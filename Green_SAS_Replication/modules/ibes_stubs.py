"""IBES column stubs and post-merge cleanup (Greens_code.sas L810-924, excluded data)."""
from __future__ import annotations

import numpy as np
import pandas as pd

from config import IBES_COLUMNS


def apply_ibes_stubs(df: pd.DataFrame) -> pd.DataFrame:
    """Add IBES columns as missing and apply SAS missing-year cleanup rules."""
    out = df.copy()
    for col in IBES_COLUMNS:
        if col not in out.columns:
            out[col] = np.nan

    out["date"] = pd.to_datetime(out["date"])
    year = out["date"].dt.year

    # SAS L913-923: post-1989 analyst count defaults; LTG indicator from fgr5yr
    out.loc[(year >= 1989) & out["nanalyst"].isna(), "nanalyst"] = 0
    out.loc[(year >= 1989) & out["fgr5yr"].isna(), "ltg"] = 0
    out.loc[(year >= 1989) & out["fgr5yr"].notna(), "ltg"] = 1

    for col in ["disp", "chfeps", "meanest", "nanalyst", "sfe", "ltg", "fgr5yr"]:
        out.loc[year < 1989, col] = np.nan
    for col in ["meanrec", "chrec"]:
        out.loc[year < 1994, col] = np.nan

    if "nanalyst" in out.columns:
        out = out.sort_values(["permno", "date"])
        out["chnanalyst"] = out["nanalyst"] - out.groupby("permno")["nanalyst"].shift(3)

    return out
