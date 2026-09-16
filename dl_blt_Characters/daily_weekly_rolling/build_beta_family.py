"""Flat procedural builder: beta, betasq, idiovol, pricedelay from weekly CRSP regressions."""
from __future__ import annotations

import os
import pickle
import sys
import time
from pathlib import Path

import multiprocessing as mp

import numpy as np
import pandas as pd
import wrds

PIPELINE_ROOT = Path(__file__).resolve().parents[1]
if str(PIPELINE_ROOT) not in sys.path:
    sys.path.insert(0, str(PIPELINE_ROOT))

from config.conventions import (  # noqa: E402
    CACHE_DIR,
    CHARACTERS_DIR,
    CRSP_EXCHCD,
    SAMPLE_END,
    SAMPLE_START,
)

BETA_FAMILY_COLUMNS = ("beta", "betasq", "idiovol", "pricedelay")

# Module globals populated before parallel main(); read inside worker processes.
_WEEKLY_RETURNS: pd.DataFrame | None = None
_MONTHLY_PANEL: pd.DataFrame | None = None


#######################################################################################################################
#                                                    Helper functions                                                 #
#######################################################################################################################


def wrds_query(conn, sql: str) -> pd.DataFrame:
    """Execute SQL on WRDS; one retry after 120 seconds on failure (with connection reset)."""
    last_exc = None
    for attempt in range(2):
        try:
            return conn.raw_sql(sql)
        except Exception as exc:
            last_exc = exc
            if attempt == 0:
                print(f"WRDS query failed: {exc}; resetting connection and retrying in 120s...", flush=True)
                try:
                    conn.connection.rollback()
                except Exception:
                    pass
                try:
                    conn.close(); conn.connect()
                except Exception as e2:
                    print(f"  reconnect failed: {e2}", flush=True)
                time.sleep(120)
            else:
                raise
    raise last_exc


def add_one_month(yyyymm: int) -> int:
    year = yyyymm // 100
    month = yyyymm % 100
    next_month = month + 1
    next_year = year + (next_month == 13)
    next_month = 1 if next_month == 13 else next_month
    return next_year * 100 + next_month


def sql_date_filter(column: str, table_alias: str | None = None) -> str:
    col = f"{table_alias}.{column}" if table_alias else column
    parts = []
    if SAMPLE_START:
        parts.append(f"{col} >= DATE '{SAMPLE_START}'")
    if SAMPLE_END:
        parts.append(f"{col} <= DATE '{SAMPLE_END}'")
    return " AND ".join(parts) if parts else "TRUE"


def crsp_exchcd_filter(table_alias: str = "n") -> str:
    codes = ", ".join(v.strip() for v in str(CRSP_EXCHCD).split(",") if v.strip())
    return f"{table_alias}.exchcd IN ({codes})"


def crsp_msf_sql() -> str:
    return f"""
        SELECT m.permno, m.permco, m.date, m.ret,
               n.exchcd, n.shrcd
        FROM crsp.msf AS m
        JOIN crsp.msenames AS n
          ON m.permno = n.permno
         AND n.namedt <= m.date
         AND m.date <= COALESCE(n.nameendt, DATE '9999-12-31')
        WHERE {crsp_exchcd_filter("n")}
          AND {sql_date_filter("date", "m")}
    """


def intnx_month(ts: pd.Series, n: int, alignment: str = "end") -> pd.Series:
    """Shift dates by n months; align to month start (``beg``) or end (``end``)."""
    shifted = pd.to_datetime(ts) + pd.DateOffset(months=n)
    if alignment == "beg":
        return shifted.dt.to_period("M").dt.to_timestamp("s")
    return shifted.dt.to_period("M").dt.to_timestamp("h")


def _ols_beta(y: np.ndarray, x: np.ndarray) -> tuple[float, float]:
    """OLS slope of y on x and adjusted R-squared (single-factor)."""
    mask = np.isfinite(y) & np.isfinite(x)
    y, x = y[mask], x[mask]
    if len(y) < 2:
        return np.nan, np.nan
    x_mean, y_mean = x.mean(), y.mean()
    xc, yc = x - x_mean, y - y_mean
    denom = np.dot(xc, xc)
    if denom == 0:
        return np.nan, np.nan
    beta = float(np.dot(xc, yc) / denom)
    y_hat = beta * xc + y_mean
    ss_res = np.sum((y - y_hat) ** 2)
    ss_tot = np.sum((y - y_mean) ** 2)
    r2 = 1 - ss_res / ss_tot if ss_tot > 0 else np.nan
    n, k = len(y), 1
    adj_r2 = 1 - (1 - r2) * (n - 1) / (n - k - 1) if n > k + 1 and np.isfinite(r2) else np.nan
    return beta, float(adj_r2)


def _ols_multi_adj_r2(y: np.ndarray, xcols: list[np.ndarray]) -> float:
    """Adjusted R-squared from multivariate OLS (pricedelay denominator)."""
    mask = np.isfinite(y)
    for x in xcols:
        mask &= np.isfinite(x)
    y = y[mask]
    xs = [x[mask] for x in xcols]
    if len(y) < len(xcols) + 2:
        return np.nan
    x_mat = np.column_stack([np.ones(len(y)), *xs])
    coef, _, _, _ = np.linalg.lstsq(x_mat, y, rcond=None)
    y_hat = x_mat @ coef
    ss_res = np.sum((y - y_hat) ** 2)
    ss_tot = np.sum((y - y.mean()) ** 2)
    r2 = 1 - ss_res / ss_tot if ss_tot > 0 else np.nan
    n, k = len(y), len(xcols)
    return float(1 - (1 - r2) * (n - 1) / (n - k - 1)) if n > k + 1 and np.isfinite(r2) else np.nan


def _weekly_cache_paths() -> tuple[Path, Path]:
    end_tag = SAMPLE_END or "open"
    stem = f"weekly_returns_{SAMPLE_START}_{end_tag}"
    return CACHE_DIR / f"{stem}.pkl", CACHE_DIR / f"{stem}.parquet"


def prepare_monthly(crsp: pd.DataFrame) -> pd.DataFrame:
    crsp = crsp.sort_values(["permno", "date"]).copy()
    crsp["date"] = pd.to_datetime(crsp["date"])
    crsp["ret"] = pd.to_numeric(crsp["ret"], errors="coerce")
    crsp["signal_yyyymm"] = crsp["date"].dt.year * 100 + crsp["date"].dt.month
    crsp["target_yyyymm"] = crsp["signal_yyyymm"].map(add_one_month)
    return crsp[crsp["ret"].notna()].copy()


def get_weekly_returns(conn, permnos: list[int]) -> pd.DataFrame:
    """Aggregate daily CRSP to week-ending Friday returns plus equal-weight market return."""
    pkl_path, parquet_path = _weekly_cache_paths()
    if pkl_path.exists():
        print(f"Loading cached weekly returns from {pkl_path}", flush=True)
        with pkl_path.open("rb") as handle:
            return pickle.load(handle)
    if parquet_path.exists():
        print(f"Loading cached weekly returns from {parquet_path}", flush=True)
        return pd.read_parquet(parquet_path)

    if not permnos:
        return pd.DataFrame(columns=["permno", "wkdt", "wkret", "ewret"])

    print(f"Pulling crsp.dsf daily returns for {len(permnos):,} permnos...", flush=True)
    permno_list = ",".join(str(int(p)) for p in permnos)
    dsf = wrds_query(
        conn,
        f"""
        SELECT permno, date, ret
        FROM crsp.dsf
        WHERE permno IN ({permno_list})
          AND {sql_date_filter("date")}
        """,
    )
    dsf["date"] = pd.to_datetime(dsf["date"])
    dsf["ret"] = pd.to_numeric(dsf["ret"], errors="coerce")
    dsf["wkdt"] = dsf["date"] + pd.to_timedelta(4 - dsf["date"].dt.dayofweek, unit="D")

    log_ret = np.log1p(dsf["ret"])
    wk = log_ret.groupby([dsf["permno"], dsf["wkdt"]], sort=False).sum(min_count=1).reset_index(name="log_wkret")
    wk["wkret"] = np.expm1(wk["log_wkret"])
    wk = wk.drop(columns=["log_wkret"])
    wk = wk[wk["wkdt"] >= "1975-01-01"].drop_duplicates(["permno", "wkdt"])
    wk["ewret"] = wk.groupby("wkdt")["wkret"].transform("mean")

    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    with pkl_path.open("wb") as handle:
        pickle.dump(wk, handle, protocol=pickle.HIGHEST_PROTOCOL)
    wk.to_parquet(parquet_path, index=False)
    print(f"Cached weekly returns -> {pkl_path} and {parquet_path}", flush=True)
    return wk


def _load_weekly_returns_cache() -> pd.DataFrame:
    """Load weekly returns from disk (required in spawned worker processes on Windows)."""
    global _WEEKLY_RETURNS
    if _WEEKLY_RETURNS is not None:
        return _WEEKLY_RETURNS
    pkl_path, parquet_path = _weekly_cache_paths()
    if pkl_path.exists():
        with pkl_path.open("rb") as handle:
            _WEEKLY_RETURNS = pickle.load(handle)
    elif parquet_path.exists():
        _WEEKLY_RETURNS = pd.read_parquet(parquet_path)
    else:
        raise RuntimeError("Weekly returns cache not found; run the main process pull first.")
    return _WEEKLY_RETURNS


def get_beta_family(monthly_df: pd.DataFrame, firm_list: pd.DataFrame) -> pd.DataFrame:
    """Compute beta-family characteristics for firms in firm_list (maxret_d worker style)."""
    wk = _load_weekly_returns_cache()
    rows = []
    n_firms = len(firm_list)
    for prog, permno in enumerate(firm_list["permno"], start=1):
        if prog == 1 or prog % 50 == 0 or prog == n_firms:
            print(
                f"processing permno {int(permno)} / finished {100.0 * prog / n_firms:.2f}%",
                flush=True,
            )
        m_grp = monthly_df[monthly_df["permno"] == permno]
        if m_grp.empty:
            continue
        w_grp = wk[wk["permno"] == permno].sort_values("wkdt")
        if w_grp.empty:
            continue
        wk_dates = w_grp["wkdt"].to_numpy(dtype="datetime64[ns]")
        wkret = w_grp["wkret"].to_numpy(dtype=float)
        ewret = w_grp["ewret"].to_numpy(dtype=float)
        for date in m_grp["date"]:
            end = intnx_month(pd.Series([date]), -1, "end").iloc[0]
            start = intnx_month(pd.Series([date]), -36, "end").iloc[0]
            i0 = wk_dates.searchsorted(np.datetime64(start), side="left")
            i1 = wk_dates.searchsorted(np.datetime64(end), side="right")
            if i1 - i0 < 52:
                continue
            y = wkret[i0:i1]
            x = ewret[i0:i1]
            beta, rsq1 = _ols_beta(y, x)
            if not np.isfinite(beta):
                continue
            sub_ew = ewret[i0:i1]
            ew_l1 = np.roll(sub_ew, 1)
            ew_l2 = np.roll(sub_ew, 2)
            ew_l3 = np.roll(sub_ew, 3)
            ew_l4 = np.roll(sub_ew, 4)
            ew_l1[:1] = ew_l2[:2] = ew_l3[:3] = ew_l4[:4] = np.nan
            adj_multi = _ols_multi_adj_r2(y, [x, ew_l1, ew_l2, ew_l3, ew_l4])
            mask = np.isfinite(y) & np.isfinite(x)
            resid = y - (y[mask].mean() - beta * x[mask].mean() + beta * x) if mask.any() else np.full_like(y, np.nan)
            idiovol = float(np.std(resid[np.isfinite(resid)], ddof=1)) if np.isfinite(resid).sum() > 1 else np.nan
            pricedelay = (
                1 - (rsq1 / adj_multi)
                if np.isfinite(rsq1) and np.isfinite(adj_multi) and adj_multi != 0
                else np.nan
            )
            rows.append(
                {
                    "permno": int(permno),
                    "date": date,
                    "beta": beta,
                    "betasq": beta ** 2,
                    "idiovol": idiovol,
                    "pricedelay": pricedelay,
                }
            )
    return pd.DataFrame(rows)


def sub_df(start: float, end: float, step: float) -> dict:
    """Split monthly panel and firm list into quantile chunks (maxret_d style)."""
    temp: dict = {}
    monthly = _MONTHLY_PANEL
    df_firm = (
        monthly[["permno"]]
        .drop_duplicates()
        .reset_index(drop=True)
        .reset_index()
        .rename(columns={"index": "count"})
    )
    n_chunks = int((end - start) / step)
    for i, h in zip(np.arange(start, end, step), range(n_chunks)):
        print(f"processing splitting dataframe: {round(i, 2)} to {round(i + step, 2)}", flush=True)
        if i == 0:
            firm_chunk = df_firm[df_firm["count"] <= df_firm["count"].quantile(i + step)]
        else:
            firm_chunk = df_firm[
                (df_firm["count"].quantile(i) < df_firm["count"])
                & (df_firm["count"] <= df_firm["count"].quantile(i + step))
            ]
        permnos = firm_chunk["permno"].astype(int).tolist()
        temp[f"firm{h}"] = firm_chunk
        temp[f"monthly{h}"] = monthly[monthly["permno"].isin(permnos)].copy()
    return temp


def main(start: float = 0.0, end: float = 1.0, step: float = 0.05) -> pd.DataFrame:
    """Run get_beta_family in parallel across quantile-split firm chunks."""
    chunks = sub_df(start, end, step)
    n_chunks = int((end - start) / step)
    pool = mp.Pool()
    pending = {}
    for i in range(n_chunks):
        pending[f"p{i}"] = pool.apply_async(
            get_beta_family,
            (chunks[f"monthly{i}"], chunks[f"firm{i}"]),
        )
    pool.close()
    pool.join()
    result = pd.DataFrame()
    print("processing pd.concat", flush=True)
    for h in range(n_chunks):
        chunk_result = pending[f"p{h}"].get()
        if not chunk_result.empty:
            result = pd.concat([result, chunk_result], ignore_index=True)
    return result


if __name__ == "__main__":
    ###################################################################################################################
    #                                                Connect to WRDS                                                  #
    ###################################################################################################################

    _wrds_user = os.environ.get("WRDS_USERNAME") or os.environ.get("WRDS_USER")
    conn = wrds.Connection(wrds_username=_wrds_user) if _wrds_user else wrds.Connection()

    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    CHARACTERS_DIR.mkdir(parents=True, exist_ok=True)

    ###################################################################################################################
    #                                              CRSP monthly grid                                                  #
    ###################################################################################################################

    msf_cache = CACHE_DIR / "beta_family_msf.parquet"
    if msf_cache.exists():
        print(f"Loading cached msf grid from {msf_cache}", flush=True)
        monthly = pd.read_parquet(msf_cache)
    else:
        print("Pulling crsp.msf + msenames monthly grid...", flush=True)
        monthly = wrds_query(conn, crsp_msf_sql())
        monthly = prepare_monthly(monthly)
        monthly.to_parquet(msf_cache, index=False)
        print(f"Cached msf grid -> {msf_cache}", flush=True)

    monthly["date"] = pd.to_datetime(monthly["date"])
    monthly["permno"] = pd.to_numeric(monthly["permno"], errors="coerce").astype("int64")
    _MONTHLY_PANEL = monthly[["permno", "date"]].drop_duplicates().copy()

    ###################################################################################################################
    #                                              Weekly CRSP returns                                                #
    ###################################################################################################################

    permnos = monthly["permno"].dropna().astype(int).unique().tolist()
    _WEEKLY_RETURNS = get_weekly_returns(conn, permnos)

    ###################################################################################################################
    #                                       Parallel beta-family estimation                                           #
    ###################################################################################################################

    print("Estimating beta-family characteristics (parallel quantile split)...", flush=True)
    factors = main(0, 1, 0.05)

    ###################################################################################################################
    #                                Merge onto monthly alignment and write output                                    #
    ###################################################################################################################

    print("Merging factors onto monthly alignment frame...", flush=True)
    panel = monthly.merge(factors, on=["permno", "date"], how="left")
    panel = panel[panel["date"].dt.year >= 1980].copy()

    valid_mask = panel[list(BETA_FAMILY_COLUMNS)].replace([np.inf, -np.inf], np.nan).notna().any(axis=1)
    panel = panel[valid_mask].copy()

    out_cols = [
        "permno", "permco", "date", "signal_yyyymm", "target_yyyymm",
        "exchcd", "shrcd", *BETA_FAMILY_COLUMNS,
    ]
    out_path = CHARACTERS_DIR / "beta_family.parquet"
    panel[out_cols].to_parquet(out_path, index=False)
    print(f"Wrote {len(panel):,} rows -> {out_path}", flush=True)
