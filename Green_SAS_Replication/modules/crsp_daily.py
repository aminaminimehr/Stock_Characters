"""Daily CRSP aggregates, beta, idiosyncratic volatility, price delay (Greens_code.sas L1005-1135)."""
from __future__ import annotations

import numpy as np
import pandas as pd
import wrds

from wrds_utils import intnx_month, retry_wrds_query, sql_between_date


def build_daily_monthly_aggregates(db: wrds.Connection, permnos: list[int], sample_start: str | None, sample_end: str | None) -> pd.DataFrame:
    if not permnos:
        return pd.DataFrame()
    date_filter = sql_between_date("date", sample_start, sample_end)
    chunks = []
    for i in range(0, len(permnos), 3000):
        ids = ",".join(str(p) for p in permnos[i : i + 3000])
        part = retry_wrds_query(
            db,
            lambda conn, id_list=ids: conn.raw_sql(f"""
                SELECT permno, date, ret, vol, shrout, ABS(prc) AS prc, askhi, bidlo
                FROM crsp.dsf
                WHERE permno IN ({id_list})
                  AND EXTRACT(YEAR FROM date) >= 1970
                  AND {date_filter}
            """),
        )
        chunks.append(part)
    dsf = pd.concat(chunks, ignore_index=True)
    dsf["date"] = pd.to_datetime(dsf["date"])
    for col in ("ret", "vol", "shrout", "prc", "askhi", "bidlo"):
        dsf[col] = pd.to_numeric(dsf[col], errors="coerce")
    dsf["yr"] = dsf["date"].dt.year
    dsf["month"] = dsf["date"].dt.month
    dsf["mid"] = (dsf["askhi"] + dsf["bidlo"]) / 2
    dsf["baspread_row"] = (dsf["askhi"] - dsf["bidlo"]) / dsf["mid"]
    dsf["std_dolvol_row"] = np.log((dsf["prc"] * dsf["vol"]).abs())
    dsf["std_turn_row"] = dsf["vol"] / dsf["shrout"]
    dsf["ill_row"] = dsf["ret"].abs() / (dsf["prc"] * dsf["vol"])
    dsf["zero_vol"] = dsf["vol"].eq(0).fillna(False).astype(int)
    dsf["turn_row"] = dsf["vol"] / dsf["shrout"]

    agg = (
        dsf.groupby(["permno", "yr", "month"], as_index=False)
        .agg(
            maxret=("ret", "max"),
            retvol=("ret", "std"),
            baspread=("baspread_row", "mean"),
            std_dolvol=("std_dolvol_row", "std"),
            std_turn=("std_turn_row", "std"),
            ill=("ill_row", "mean"),
            countzero=("zero_vol", "sum"),
            ndays=("permno", "count"),
            turn=("turn_row", "sum"),
        )
    )
    agg["zerotrade"] = (agg["countzero"] + ((1 / agg["turn"]) / 480000)) * 21 / agg["ndays"]
    return agg.drop_duplicates(["permno", "yr", "month"], keep="first")


def merge_lagged_daily_aggregates(panel: pd.DataFrame, dcrsp: pd.DataFrame) -> pd.DataFrame:
    out = panel.copy()
    out["date"] = pd.to_datetime(out["date"])
    lag_date = intnx_month(out["date"], -1, "end")
    out["lag_yr"] = lag_date.dt.year
    out["lag_month"] = lag_date.dt.month
    merged = out.merge(
        dcrsp,
        left_on=["permno", "lag_yr", "lag_month"],
        right_on=["permno", "yr", "month"],
        how="left",
    )
    return merged.drop(columns=["lag_yr", "lag_month", "yr", "month"], errors="ignore")


def _ols_beta(y: np.ndarray, x: np.ndarray) -> tuple[float, float]:
    mask = np.isfinite(y) & np.isfinite(x)
    y, x = y[mask], x[mask]
    if len(y) < 2:
        return np.nan, np.nan
    x_mean = x.mean()
    y_mean = y.mean()
    xc, yc = x - x_mean, y - y_mean
    denom = np.dot(xc, xc)
    if denom == 0:
        return np.nan, np.nan
    beta = np.dot(xc, yc) / denom
    y_hat = beta * xc + y_mean
    ss_res = np.sum((y - y_hat) ** 2)
    ss_tot = np.sum((y - y_mean) ** 2)
    r2 = 1 - ss_res / ss_tot if ss_tot > 0 else np.nan
    n, k = len(y), 1
    adj_r2 = 1 - (1 - r2) * (n - 1) / (n - k - 1) if n > k + 1 and np.isfinite(r2) else np.nan
    return float(beta), float(adj_r2)


def _ols_multi(y: np.ndarray, xcols: list[np.ndarray]) -> float:
    mask = np.isfinite(y)
    for x in xcols:
        mask &= np.isfinite(x)
    y = y[mask]
    xs = [x[mask] for x in xcols]
    if len(y) < len(xcols) + 2:
        return np.nan
    X = np.column_stack(xs)
    X = np.column_stack([np.ones(len(y)), X])
    coef, _, _, _ = np.linalg.lstsq(X, y, rcond=None)
    y_hat = X @ coef
    ss_res = np.sum((y - y_hat) ** 2)
    ss_tot = np.sum((y - y.mean()) ** 2)
    r2 = 1 - ss_res / ss_tot if ss_tot > 0 else np.nan
    n, k = len(y), len(xcols)
    return float(1 - (1 - r2) * (n - 1) / (n - k - 1)) if n > k + 1 and np.isfinite(r2) else np.nan


def estimate_beta_block(db: wrds.Connection, panel: pd.DataFrame, sample_start: str | None, sample_end: str | None) -> pd.DataFrame:
    permnos = panel["permno"].dropna().astype(int).unique().tolist()
    if not permnos:
        return pd.DataFrame(columns=["permno", "date", "beta", "betasq", "rsq1", "pricedelay", "idiovol"])

    date_filter = sql_between_date("date", sample_start, sample_end)
    dsf = []
    for i in range(0, len(permnos), 2000):
        ids = ",".join(str(p) for p in permnos[i : i + 2000])
        part = retry_wrds_query(
            db,
            lambda conn, id_list=ids: conn.raw_sql(f"""
                SELECT permno, date, ret
                FROM crsp.dsf
                WHERE permno IN ({id_list}) AND {date_filter}
            """),
        )
        dsf.append(part)
    dsf = pd.concat(dsf, ignore_index=True)
    dsf["date"] = pd.to_datetime(dsf["date"])
    dsf["ret"] = pd.to_numeric(dsf["ret"], errors="coerce")
    dsf["wkdt"] = dsf["date"] + pd.to_timedelta(4 - dsf["date"].dt.dayofweek, unit="D")
    wk = dsf.groupby(["permno", "wkdt"], as_index=False).agg(wkret=("ret", lambda s: np.exp(np.log1p(s).sum()) - 1))
    wk = wk[wk["wkdt"] >= "1975-01-01"].drop_duplicates(["permno", "wkdt"])
    wk["ewret"] = wk.groupby("wkdt")["wkret"].transform("mean")

    keys = panel[["permno", "date"]].drop_duplicates()
    rows = []
    for _, row in keys.iterrows():
        start = intnx_month(pd.Series([row["date"]]), -36, "end").iloc[0]
        end = intnx_month(pd.Series([row["date"]]), -1, "end").iloc[0]
        sub = wk[(wk["permno"] == row["permno"]) & (wk["wkdt"] >= start) & (wk["wkdt"] <= end)]
        sub = sub[sub["wkret"].notna() & sub["ewret"].notna()]
        if len(sub) < 52:
            continue
        sub = sub.sort_values("wkdt")
        y = sub["wkret"].to_numpy(dtype=float)
        x = sub["ewret"].to_numpy(dtype=float)
        beta, rsq1 = _ols_beta(y, x)
        ew_l1 = sub["ewret"].shift(1).to_numpy(dtype=float)
        ew_l2 = sub["ewret"].shift(2).to_numpy(dtype=float)
        ew_l3 = sub["ewret"].shift(3).to_numpy(dtype=float)
        ew_l4 = sub["ewret"].shift(4).to_numpy(dtype=float)
        adj_multi = _ols_multi(y, [x, ew_l1, ew_l2, ew_l3, ew_l4])
        mask = np.isfinite(y) & np.isfinite(x) & np.isfinite(beta)
        resid = y - (y[mask].mean() - beta * x[mask].mean() + beta * x) if mask.any() else np.full_like(y, np.nan)
        idiovol = float(np.std(resid[np.isfinite(resid)], ddof=1)) if np.isfinite(resid).sum() > 1 else np.nan
        pricedelay = 1 - (rsq1 / adj_multi) if np.isfinite(rsq1) and np.isfinite(adj_multi) and adj_multi != 0 else np.nan
        rows.append(
            {
                "permno": row["permno"],
                "date": row["date"],
                "beta": beta,
                "betasq": beta ** 2 if np.isfinite(beta) else np.nan,
                "rsq1": rsq1,
                "pricedelay": pricedelay,
                "idiovol": idiovol,
            }
        )
    return pd.DataFrame(rows)


def add_crsp_daily_variables(
    db: wrds.Connection,
    panel: pd.DataFrame,
    sample_start: str | None,
    sample_end: str | None,
) -> pd.DataFrame:
    permnos = panel["permno"].dropna().astype(int).unique().tolist()
    dcrsp = build_daily_monthly_aggregates(db, permnos, sample_start, sample_end)
    out = merge_lagged_daily_aggregates(panel, dcrsp)
    beta = estimate_beta_block(db, out, sample_start, sample_end)
    out = out.merge(beta, on=["permno", "date"], how="left")
    out = out[out["date"].dt.year >= 1980].drop_duplicates(["permno", "date"], keep="first")
    return out
