"""Beta, betasq, idiovol, pricedelay from weekly CRSP regressions."""
from __future__ import annotations

import pickle
from pathlib import Path

import numpy as np
import pandas as pd

from constants import QUARTERLY_MONTH_END_LAG, QUARTERLY_MONTH_START_LAG
from monthly_runner import fetch_crsp_msf, monthly_alignment_frame
from paths import CACHE_DIR, SINGLE_CHARACTERS_DIR
from wrds_io import get_sample_bounds, raw_sql_with_retry, sql_date_filter
from writers import write_character

_WEEKLY_CACHE: pd.DataFrame | None = None
FACTOR_COLUMNS = ("beta", "betasq", "idiovol", "pricedelay")


def intnx_month(ts: pd.Series, n: int, alignment: str = "end") -> pd.Series:
    shifted = pd.to_datetime(ts) + pd.DateOffset(months=n)
    if alignment == "beg":
        return shifted.dt.to_period("M").dt.to_timestamp("s")
    return shifted.dt.to_period("M").dt.to_timestamp("h")


def _ols_beta(y: np.ndarray, x: np.ndarray) -> tuple[float, float]:
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


def _weekly_cache_path() -> Path:
    start, end = get_sample_bounds()
    end_tag = end or "open"
    return CACHE_DIR / f"weekly_returns_{start}_{end_tag}.pkl"


def get_weekly_returns(db, permnos: list[int], use_cache: bool = True) -> pd.DataFrame:
    global _WEEKLY_CACHE
    if use_cache and _WEEKLY_CACHE is not None:
        return _WEEKLY_CACHE
    cache_path = _weekly_cache_path()
    if use_cache and cache_path.exists():
        with cache_path.open("rb") as handle:
            _WEEKLY_CACHE = pickle.load(handle)
        return _WEEKLY_CACHE
    if not permnos:
        return pd.DataFrame(columns=["permno", "wkdt", "wkret", "ewret"])
    permno_list = ",".join(str(int(p)) for p in permnos)
    dsf = raw_sql_with_retry(
        db,
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
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    with cache_path.open("wb") as handle:
        pickle.dump(wk, handle, protocol=pickle.HIGHEST_PROTOCOL)
    _WEEKLY_CACHE = wk
    return wk


def estimate_factor_panel(db, use_cache: bool = True) -> pd.DataFrame:
    monthly = monthly_alignment_frame(fetch_crsp_msf(db, "beta", use_cache=use_cache))
    monthly["date"] = pd.to_datetime(monthly["date"])
    monthly["permno"] = pd.to_numeric(monthly["permno"], errors="coerce").astype("int64")
    permnos = monthly["permno"].dropna().astype(int).unique().tolist()
    wk = get_weekly_returns(db, permnos, use_cache=use_cache)
    rows = []
    for permno, m_grp in monthly.groupby("permno", sort=False):
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
            pricedelay = 1 - (rsq1 / adj_multi) if np.isfinite(rsq1) and np.isfinite(adj_multi) and adj_multi != 0 else np.nan
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
    factors = pd.DataFrame(rows)
    out = monthly.merge(factors, on=["permno", "date"], how="left")
    return out[out["date"].dt.year >= 1980]


def build_factor_stem(db, stem: str, use_cache: bool = True) -> pd.DataFrame:
    panel = estimate_factor_panel(db, use_cache=use_cache)
    if stem == "betasq":
        panel["betasq"] = panel["beta"] ** 2
    out = panel[panel[stem].replace([np.inf, -np.inf], np.nan).notna()].copy()
    cols = ["permno", "permco", "date", "signal_yyyymm", "target_yyyymm", "sic", "exchcd", "shrcd", stem]
    return out[[c for c in cols if c in out.columns]]


def write_factor(out: pd.DataFrame, stem: str) -> None:
    write_character(out, stem, SINGLE_CHARACTERS_DIR)
