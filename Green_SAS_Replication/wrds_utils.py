"""WRDS connection helpers and SAS-compatible date utilities."""
from __future__ import annotations

import os
import time
from typing import Callable, TypeVar

import numpy as np
import pandas as pd
import wrds
from sqlalchemy.exc import DBAPIError, OperationalError, ProgrammingError

from config import GREEN_CCM_LINKTYPES

T = TypeVar("T")

_WRDS_SESSION: wrds.Connection | None = None
_WRDS_SESSION_USER: str | None = None
_DEBUG_WRDS = False


def set_wrds_debug(enabled: bool) -> None:
    global _DEBUG_WRDS
    _DEBUG_WRDS = enabled


def _debug(msg: str) -> None:
    if _DEBUG_WRDS:
        print(f"[WRDS DEBUG] {msg}", flush=True)


def _resolve_wrds_user(wrds_user: str | None) -> str | None:
    return wrds_user or os.environ.get("WRDS_USERNAME")


def connect_wrds(wrds_user: str | None = None, *, force_new: bool = False) -> wrds.Connection:
    """Return the process-wide WRDS session (one library-list load per process)."""
    global _WRDS_SESSION, _WRDS_SESSION_USER

    user = _resolve_wrds_user(wrds_user)
    if (
        not force_new
        and _WRDS_SESSION is not None
        and _WRDS_SESSION_USER == user
        and _connection_is_open(_WRDS_SESSION)
    ):
        _debug(f"reusing connection id={id(_WRDS_SESSION)} user={user!r}")
        return _WRDS_SESSION

    if force_new or (_WRDS_SESSION is not None and not _connection_is_open(_WRDS_SESSION)):
        safe_close_wrds(_WRDS_SESSION)

    _debug(f"creating connection user={user!r} force_new={force_new}")
    _WRDS_SESSION = wrds.Connection(wrds_username=user) if user else wrds.Connection()
    _WRDS_SESSION_USER = user
    _debug(f"created connection id={id(_WRDS_SESSION)}")
    return _WRDS_SESSION


def get_wrds_connection(db: wrds.Connection | None = None) -> wrds.Connection:
    """Return the live session; prefer the global singleton over a stale caller reference."""
    global _WRDS_SESSION, _WRDS_SESSION_USER

    if _WRDS_SESSION is not None and _connection_is_open(_WRDS_SESSION):
        return _WRDS_SESSION
    if db is not None and _connection_is_open(db):
        _WRDS_SESSION = db
        return db
    return connect_wrds(_WRDS_SESSION_USER, force_new=True)


def _connection_is_open(db: wrds.Connection | None) -> bool:
    if db is None:
        return False
    conn = getattr(db, "connection", None)
    if conn is None:
        return False
    closed = getattr(conn, "closed", None)
    return not closed if closed is not None else True


def safe_close_wrds(db: wrds.Connection | None = None) -> None:
    """Close WRDS connection without raising if already closed or partially initialized."""
    global _WRDS_SESSION, _WRDS_SESSION_USER

    target = db if db is not None else _WRDS_SESSION
    if target is None:
        return
    _debug(f"closing connection id={id(target)}")
    try:
        if _connection_is_open(target):
            target.close()
    except Exception:  # noqa: BLE001
        pass
    finally:
        if db is None or db is _WRDS_SESSION:
            _WRDS_SESSION = None
            _WRDS_SESSION_USER = None


def run_wrds_smoke_test(wrds_user: str | None = None) -> int:
    """Open one WRDS connection, run a tiny query, close safely. Returns 0 on success."""
    try:
        print("WRDS smoke test: connecting...", flush=True)
        db = connect_wrds(wrds_user, force_new=True)
        print("WRDS smoke test: running query...", flush=True)
        result = retry_wrds_query(db, lambda conn: conn.raw_sql("SELECT 1 AS x"))
        if result is None or len(result) != 1:
            print("WRDS smoke test FAILED: expected 1 row from SELECT 1", flush=True)
            return 1
        value = result.iloc[0]["x"]
        if int(value) != 1:
            print(f"WRDS smoke test FAILED: expected x=1, got {value!r}", flush=True)
            return 1
        print("WRDS smoke test PASSED", flush=True)
        return 0
    except Exception as exc:  # noqa: BLE001
        print(f"WRDS smoke test FAILED: {exc}", flush=True)
        return 1
    finally:
        safe_close_wrds()


def sql_date_literal(d: str) -> str:
    return f"'{pd.Timestamp(d).strftime('%Y-%m-%d')}'"


def sql_between_date(col: str, start: str | None, end: str | None) -> str:
    parts = []
    if start:
        parts.append(f"{col} >= {sql_date_literal(start)}")
    if end:
        parts.append(f"{col} <= {sql_date_literal(end)}")
    return " AND ".join(parts) if parts else "1=1"


def _is_retryable_wrds_error(exc: Exception) -> bool:
    """Retry only transient connection issues, not SQL/schema failures."""
    if isinstance(exc, ProgrammingError):
        return False
    if isinstance(exc, OperationalError):
        return True
    if isinstance(exc, DBAPIError) and exc.connection_invalidated:
        return True
    msg = str(exc).lower()
    if "connection is closed" in msg or "server closed the connection" in msg:
        return True
    if "undefinedcolumn" in msg or "syntax error" in msg:
        return False
    return False


def retry_wrds_query(
    db: wrds.Connection | None,
    fn: Callable[[wrds.Connection], T],
    attempts: int = 3,
    pause: float = 5.0,
) -> T:
    """Run a WRDS query with retries; always passes the live connection into ``fn``."""
    last_exc: Exception | None = None
    conn = get_wrds_connection(db)

    for attempt in range(1, attempts + 1):
        conn = get_wrds_connection(conn)
        try:
            _debug(f"raw_sql via connection id={id(conn)} (attempt {attempt}/{attempts})")
            return fn(conn)
        except Exception as exc:  # noqa: BLE001
            last_exc = exc
            _debug(f"query failed attempt {attempt}/{attempts}: {exc}")
            if attempt == attempts or not _is_retryable_wrds_error(exc):
                break
            time.sleep(pause)
            safe_close_wrds(conn)
            conn = connect_wrds(_WRDS_SESSION_USER, force_new=True)

    assert last_exc is not None
    raise last_exc


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
    link = retry_wrds_query(
        db,
        lambda conn: conn.raw_sql(f"""
        SELECT gvkey, lpermno AS permno, linkdt, linkenddt, linktype
        FROM crsp.ccmxpf_linktable
        WHERE linktype IN ({codes})
          AND (EXTRACT(YEAR FROM linkdt) <= 2015 OR linkdt IS NULL)
          AND (EXTRACT(YEAR FROM linkenddt) >= 1950 OR linkenddt IS NULL)
          AND lpermno IS NOT NULL
    """),
    )
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
