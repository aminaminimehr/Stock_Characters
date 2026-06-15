"""WRDS connection helpers and SAS-compatible date utilities."""
from __future__ import annotations

import time
from typing import Callable

import numpy as np
import pandas as pd
import wrds

from config import GREEN_CCM_LINKTYPES


def connect_wrds(wrds_user: str | None = None) -> wrds.Connection:
    return wrds.Connection(wrds_username=wrds_user) if wrds_user else wrds.Connection()


def sql_date_literal(d: str) -> str:
    return f"'{pd.Timestamp(d).strftime('%Y-%m-%d')}'"


def sql_between_date(col: str, start: str | None, end: str | None) -> str:
    parts = []
    if start:
        parts.append(f"{col} >= {sql_date_literal(start)}")
    if end:
        parts.append(f"{col} <= {sql_date_literal(end)}")
    return " AND ".join(parts) if parts else "1=1"


def retry_wrds_query(db: wrds.Connection, fn: Callable, attempts: int = 3, pause: float = 5.0):
    last_exc = None
    for attempt in range(1, attempts + 1):
        try:
            return fn()
        except Exception as exc:  # noqa: BLE001
            last_exc = exc
            if attempt == attempts:
                break
            time.sleep(pause)
            try:
                db.close()
            except Exception:  # noqa: BLE001
                pass
            db = connect_wrds()
    raise last_exc  # type: ignore[misc]


def month_end(ts: pd.Series | pd.Timestamp) -> pd.Series | pd.Timestamp:
    if isinstance(ts, pd.Timestamp):
        return ts.to_period("M").to_timestamp("h")
    return ts.dt.to_period("M").dt.to_timestamp("h")


def intnx_month(ts: pd.Series, n: int, alignment: str = "end") -> pd.Series:
    """Approximate SAS intnx('MONTH', date, n [, 'beg'|'end'])."""
    shifted = ts + pd.DateOffset(months=n)
    if alignment == "beg":
        return shifted.dt.to_period("M").dt.to_timestamp("s")
    return shifted.dt.to_period("M").dt.to_timestamp("h")


def intnx_weekday(ts: pd.Series, n: int) -> pd.Series:
    """SAS intnx('WEEKDAY', date, n): next weekday if n>=0."""
    out = ts + pd.tseries.offsets.BDay(n)
    return out


def sas_std_row(values: np.ndarray) -> float:
    """SAS std(arg1, arg2, ...) over non-missing arguments (sample std, ddof=1)."""
    row = values[np.isfinite(values)]
    if len(row) < 2:
        return np.nan
    return float(np.std(row, ddof=1))


def rolling_sas_std(frame: pd.DataFrame, col: str, lags: list[int]) -> pd.Series:
    """Row-wise SAS std across col and lagged values within gvkey groups."""
    parts = [frame[col].to_numpy(dtype=float)]
    grouped = frame.groupby("gvkey", sort=False)
    for lag_n in lags:
        parts.append(grouped[col].shift(lag_n).to_numpy(dtype=float))
    mat = np.column_stack(parts)
    return pd.Series([sas_std_row(mat[i]) for i in range(len(mat))], index=frame.index)


def load_ccm_links_green(db: wrds.Connection) -> pd.DataFrame:
    """Green SAS L410-412 link table filter."""
    codes = ", ".join(f"'{c}'" for c in GREEN_CCM_LINKTYPES)
    link = db.raw_sql(f"""
        SELECT gvkey, lpermno AS permno, linkdt, linkenddt, linktype
        FROM crsp.ccmxpf_linktable
        WHERE linktype IN ({codes})
          AND (EXTRACT(YEAR FROM linkdt) <= 2015 OR linkdt IS NULL)
          AND (EXTRACT(YEAR FROM linkenddt) >= 1950 OR linkenddt IS NULL)
          AND lpermno IS NOT NULL
    """)
    link["linkdt"] = pd.to_datetime(link["linkdt"])
    link["linkenddt"] = pd.to_datetime(link["linkenddt"])
    link["permno"] = pd.to_numeric(link["permno"], errors="coerce").astype("Int64")
    return link.sort_values(["gvkey", "linkdt"])


def attach_ccm_links_green(comp: pd.DataFrame, link: pd.DataFrame) -> pd.DataFrame:
    """Green SAS L414-417: date in link window; missing linkdt/linkenddt treated as open."""
    merged = comp.merge(link, on="gvkey", how="inner")
    linkdt_ok = merged["linkdt"].isna() | (merged["linkdt"] <= merged["datadate"])
    linkend_ok = merged["linkenddt"].isna() | (merged["datadate"] <= merged["linkenddt"])
    out = merged[linkdt_ok & linkend_ok & merged["permno"].notna()].copy()
    return out


def save_checkpoint(df: pd.DataFrame, name: str) -> None:
    from config import CHECKPOINT_DIR

    CHECKPOINT_DIR.mkdir(parents=True, exist_ok=True)
    path = CHECKPOINT_DIR / f"{name}.parquet"
    try:
        df.to_parquet(path, index=False)
    except ImportError:
        df.to_pickle(CHECKPOINT_DIR / f"{name}.pkl")


def load_checkpoint(name: str) -> pd.DataFrame:
    from config import CHECKPOINT_DIR

    path = CHECKPOINT_DIR / f"{name}.parquet"
    pkl = CHECKPOINT_DIR / f"{name}.pkl"
    if path.exists():
        return pd.read_parquet(path)
    if pkl.exists():
        return pd.read_pickle(pkl)
    raise FileNotFoundError(f"Checkpoint not found: {path}")
