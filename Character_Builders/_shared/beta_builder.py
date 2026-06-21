import argparse
import os
import pickle
from pathlib import Path

import numpy as np
import pandas as pd

from _shared.green_builders import OUTPUT_DIR, connect_wrds, load_monthly_alignment_frame
from _shared.wrds_chunk_download import fetch_dsf_by_permno_batches
from output_paths import CACHE_DIR, get_sample_bounds
from _shared.parallel_daily_windows import run_permno_parallel

PROJECT_ROOT = Path(__file__).resolve().parents[2]

DAILY_FACTOR_COLUMNS = ("beta", "betasq", "idiovol", "pricedelay")
FACTOR_CHARACTER_NAMES = ("beta", "betasq", "idiovol", "pricedelay")

_WEEKLY_RETURNS_CACHE: pd.DataFrame | None = None
_FACTOR_PANEL_CACHE: pd.DataFrame | None = None


def clear_factor_caches() -> None:
    global _WEEKLY_RETURNS_CACHE, _FACTOR_PANEL_CACHE
    _WEEKLY_RETURNS_CACHE = None
    _FACTOR_PANEL_CACHE = None


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
    x_mean = x.mean()
    y_mean = y.mean()
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
    x_mat = np.column_stack(xs)
    x_mat = np.column_stack([np.ones(len(y)), x_mat])
    coef, _, _, _ = np.linalg.lstsq(x_mat, y, rcond=None)
    y_hat = x_mat @ coef
    ss_res = np.sum((y - y_hat) ** 2)
    ss_tot = np.sum((y - y.mean()) ** 2)
    r2 = 1 - ss_res / ss_tot if ss_tot > 0 else np.nan
    n, k = len(y), len(xcols)
    return float(1 - (1 - r2) * (n - 1) / (n - k - 1)) if n > k + 1 and np.isfinite(r2) else np.nan


def _weekly_compound(ret_series: pd.Series) -> float:
    vals = pd.to_numeric(ret_series, errors="coerce").dropna()
    if vals.empty:
        return np.nan
    return float(np.exp(np.log1p(vals).sum()) - 1)


def _weekly_cache_path() -> Path:
    start, end = get_sample_bounds()
    end_tag = end or "open"
    return CACHE_DIR / f"weekly_returns_{start}_{end_tag}.pkl"


def _load_weekly_returns_from_wrds(db, permnos: list[int]) -> pd.DataFrame:
    dsf = fetch_dsf_by_permno_batches(
        permnos,
        db=db,
        select_cols="permno, date, ret",
        label="weekly returns",
    )
    dsf["date"] = pd.to_datetime(dsf["date"])
    dsf["ret"] = pd.to_numeric(dsf["ret"], errors="coerce")
    dsf["wkdt"] = dsf["date"] + pd.to_timedelta(4 - dsf["date"].dt.dayofweek, unit="D")
    wk = dsf.groupby(["permno", "wkdt"], as_index=False).agg(wkret=("ret", _weekly_compound))
    wk = wk[wk["wkdt"] >= "1975-01-01"].drop_duplicates(["permno", "wkdt"])
    wk["ewret"] = wk.groupby("wkdt")["wkret"].transform("mean")
    return wk


def get_weekly_returns(db, permnos: list[int]) -> pd.DataFrame:
    """Load weekly CRSP returns once; reuse disk cache across factor characters."""
    global _WEEKLY_RETURNS_CACHE
    if _WEEKLY_RETURNS_CACHE is not None:
        return _WEEKLY_RETURNS_CACHE

    cache_path = _weekly_cache_path()
    if cache_path.exists():
        with cache_path.open("rb") as handle:
            _WEEKLY_RETURNS_CACHE = pickle.load(handle)
        print(
            f"Loaded weekly returns from cache ({len(_WEEKLY_RETURNS_CACHE):,} rows): {cache_path}",
            flush=True,
        )
        return _WEEKLY_RETURNS_CACHE

    print(f"Loading weekly returns for {len(permnos):,} permnos from WRDS...", flush=True)
    wk = _load_weekly_returns_from_wrds(db, permnos)
    print("Weekly returns WRDS download complete; aggregating to weeks...", flush=True)
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    with cache_path.open("wb") as handle:
        pickle.dump(wk, handle, protocol=pickle.HIGHEST_PROTOCOL)
    print(f"Saved weekly returns cache ({len(wk):,} rows): {cache_path}", flush=True)
    _WEEKLY_RETURNS_CACHE = wk
    return wk


def _factor_chunk_worker(args: tuple) -> pd.DataFrame:
    permno_chunk, wk, panel_dates = args
    rows = []
    wk_sub = wk[wk["permno"].isin(permno_chunk)]
    panel_sub = panel_dates[panel_dates["permno"].isin(permno_chunk)]
    for permno, m_grp in panel_sub.groupby("permno", sort=False):
        w_grp = wk_sub[wk_sub["permno"] == permno].sort_values("wkdt")
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
            ew_l1[:1] = np.nan
            ew_l2[:2] = np.nan
            ew_l3[:3] = np.nan
            ew_l4[:4] = np.nan
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


def estimate_daily_factors(
    panel_dates: pd.DataFrame, db, workers: int | None = None
) -> pd.DataFrame:
    permnos = panel_dates["permno"].dropna().astype(int).unique().tolist()
    if not permnos:
        return pd.DataFrame(columns=["permno", "date", *DAILY_FACTOR_COLUMNS])

    wk = get_weekly_returns(db, permnos)
    panel_dates = panel_dates.drop_duplicates(["permno", "date"]).copy()
    panel_dates["date"] = pd.to_datetime(panel_dates["date"])

    frames = run_permno_parallel(
        permnos,
        _factor_chunk_worker,
        lambda chunk: (
            chunk,
            wk[wk["permno"].isin(chunk)],
            panel_dates[panel_dates["permno"].isin(chunk)],
        ),
        workers=workers,
        label="Green daily factors",
    )
    if not frames:
        return pd.DataFrame(columns=["permno", "date", *DAILY_FACTOR_COLUMNS])
    return pd.concat(frames, ignore_index=True)


def _build_factor_panel(
    db, output_dir=OUTPUT_DIR, workers: int | None = None, monthly_panel: pd.DataFrame | None = None
) -> pd.DataFrame:
    global _FACTOR_PANEL_CACHE
    if _FACTOR_PANEL_CACHE is not None:
        return _FACTOR_PANEL_CACHE

    monthly = monthly_panel.copy() if monthly_panel is not None else load_monthly_alignment_frame(output_dir, db=db)
    monthly["date"] = pd.to_datetime(monthly["date"])
    monthly["permno"] = pd.to_numeric(monthly["permno"], errors="coerce").astype("int64")
    factors = estimate_daily_factors(monthly[["permno", "date"]], db, workers=workers)
    out = monthly.merge(factors, on=["permno", "date"], how="left")
    out = out[out["date"].dt.year >= 1980]
    _FACTOR_PANEL_CACHE = out
    return out


def _finalize_factor_character(df: pd.DataFrame, column: str) -> pd.DataFrame:
    out = df[df[column].replace([np.inf, -np.inf], np.nan).notna()].copy()
    return out[
        ["permno", "permco", "date", "signal_yyyymm", "target_yyyymm", "sic", "exchcd", "shrcd", column]
    ]


def build_factor_characters(
    db, output_dir=OUTPUT_DIR, workers: int | None = None, names: tuple[str, ...] = FACTOR_CHARACTER_NAMES
) -> dict[str, pd.DataFrame]:
    """Build beta/betasq/idiovol/pricedelay from one WRDS weekly pull + one parallel pass."""
    names = tuple(dict.fromkeys(names))
    if not names:
        return {}

    if names == ("betasq",):
        beta_path = Path(output_dir) / "beta.csv"
        if beta_path.exists():
            out = pd.read_csv(beta_path)
            out["betasq"] = out["beta"] ** 2
            return {"betasq": out.drop(columns=["beta"], errors="ignore")}

    panel = _build_factor_panel(db, output_dir, workers=workers)
    results: dict[str, pd.DataFrame] = {}
    for name in names:
        if name == "betasq":
            tmp = panel.copy()
            tmp["betasq"] = tmp["beta"] ** 2
            results[name] = _finalize_factor_character(tmp, "betasq")
        else:
            results[name] = _finalize_factor_character(panel, name)
    return results


def build_beta_character(db, output_dir=OUTPUT_DIR, workers: int | None = None):
    return build_factor_characters(db, output_dir, workers=workers, names=("beta",))["beta"]


def build_betasq_character(db, output_dir=OUTPUT_DIR, workers: int | None = None):
    return build_factor_characters(db, output_dir, workers=workers, names=("betasq",))["betasq"]


def build_idiovol_character(db, output_dir=OUTPUT_DIR, workers: int | None = None):
    return build_factor_characters(db, output_dir, workers=workers, names=("idiovol",))["idiovol"]


def build_pricedelay_character(db, output_dir=OUTPUT_DIR, workers: int | None = None):
    return build_factor_characters(db, output_dir, workers=workers, names=("pricedelay",))["pricedelay"]


def run_beta_cli():
    parser = argparse.ArgumentParser(
        description="Build beta from Green SAS weekly rolling market regressions."
    )
    parser.add_argument("--wrds-user", default=None)
    parser.add_argument("--output", default=OUTPUT_DIR / "beta.csv")
    parser.add_argument("--workers", type=int, default=None)
    args = parser.parse_args()

    output = Path(args.output)
    if not output.is_absolute():
        output = PROJECT_ROOT / output
    output.parent.mkdir(parents=True, exist_ok=True)

    db = connect_wrds(args.wrds_user)
    try:
        clear_factor_caches()
        result = build_beta_character(db, workers=args.workers)
    finally:
        db.close()
        clear_factor_caches()

    result.to_csv(output, index=False)
    print(f"Saved beta to: {output.resolve()}")
    print(f"Rows: {len(result):,}")
