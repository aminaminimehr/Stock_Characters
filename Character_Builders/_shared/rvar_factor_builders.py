import pickle
from pathlib import Path

import numpy as np
import pandas as pd

from _shared.green_builders import (
    OUTPUT_DIR,
    connect_wrds,
    load_monthly_alignment_frame,
    raw_sql_with_retry,
)


PROJECT_ROOT = Path(__file__).resolve().parents[2]

FF3_FACTORS = ["mktrf", "smb", "hml"]
RVAR_SPECS = {
    "rvar_capm": ["mktrf"],
    "rvar_ff3": ["mktrf", "smb", "hml"],
}

_DAILY_FACTOR_CACHE = None
_MONTHLY_ALIGNMENT_CACHE = None


def _daily_factor_cache_path(output_dir):
    return Path(output_dir) / ".cache" / "daily_ff_factors.pkl"


def clear_rvar_caches():
    global _DAILY_FACTOR_CACHE, _MONTHLY_ALIGNMENT_CACHE
    _DAILY_FACTOR_CACHE = None
    _MONTHLY_ALIGNMENT_CACHE = None


def load_daily_factor_data(db, factors):
    """
    Match Xin He / Dacheng Xiu Rvar_ff3.py: one dsf + factors_daily pull, then merge
    delisting returns in pandas (avoids a heavy per-row SQL join on dsf).
    """
    factor_cols = ", ".join(f"f.{factor}" for factor in factors)
    daily = raw_sql_with_retry(
        db,
        f"""
        SELECT d.permno, d.date, d.ret, f.rf, {factor_cols}
        FROM crsp.dsf AS d
        LEFT JOIN ff.factors_daily AS f
          ON d.date = f.date
        WHERE d.date >= DATE '1959-01-01'
    """,
    )
    dlret = raw_sql_with_retry(
        db,
        """
        SELECT permno, dlret, dlstdt
        FROM crsp.dsedelist
        WHERE dlstdt >= DATE '1959-01-01'
    """,
    )
    daily["date"] = pd.to_datetime(daily["date"])
    daily = daily.sort_values(["permno", "date"])
    dlret["permno"] = pd.to_numeric(dlret["permno"], errors="coerce").astype("int64")
    dlret["dlstdt"] = pd.to_datetime(dlret["dlstdt"])
    dlret = dlret.rename(columns={"dlstdt": "date"})
    daily = daily.merge(dlret[["permno", "date", "dlret"]], on=["permno", "date"], how="left")
    daily["ret"] = pd.to_numeric(daily["ret"], errors="coerce").fillna(0)
    daily["dlret"] = pd.to_numeric(daily["dlret"], errors="coerce").fillna(0)
    daily["retadj"] = (1 + daily["ret"]) * (1 + daily["dlret"]) - 1
    daily["exret"] = daily["retadj"] - daily["rf"]
    daily["source_yyyymm"] = daily["date"].dt.year * 100 + daily["date"].dt.month
    return daily[["permno", "date", "source_yyyymm", "exret", *factors]]


def get_daily_ff_factor_data(db, output_dir=OUTPUT_DIR):
    global _DAILY_FACTOR_CACHE
    if _DAILY_FACTOR_CACHE is not None:
        return _DAILY_FACTOR_CACHE

    cache_path = _daily_factor_cache_path(output_dir)
    if cache_path.exists():
        with cache_path.open("rb") as handle:
            _DAILY_FACTOR_CACHE = pickle.load(handle)
        print(
            f"Loaded daily factor rows from local cache ({len(_DAILY_FACTOR_CACHE):,})",
            flush=True,
        )
        return _DAILY_FACTOR_CACHE

    _DAILY_FACTOR_CACHE = load_daily_factor_data(db, FF3_FACTORS)
    print(f"Loaded daily factor rows from WRDS ({len(_DAILY_FACTOR_CACHE):,})", flush=True)
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    with cache_path.open("wb") as handle:
        pickle.dump(_DAILY_FACTOR_CACHE, handle, protocol=pickle.HIGHEST_PROTOCOL)
    print(f"Saved daily factor cache to {cache_path}", flush=True)
    return _DAILY_FACTOR_CACHE


def get_monthly_alignment(db, output_dir=OUTPUT_DIR):
    global _MONTHLY_ALIGNMENT_CACHE
    if _MONTHLY_ALIGNMENT_CACHE is None:
        _MONTHLY_ALIGNMENT_CACHE = load_monthly_alignment_frame(output_dir, db=db)
    return _MONTHLY_ALIGNMENT_CACHE


def residual_variance(y, x):
    valid = np.isfinite(y)
    for col in range(x.shape[1]):
        valid &= np.isfinite(x[:, col])
    y = y[valid]
    x = x[valid]
    if len(y) < 21:
        return np.nan
    design = np.column_stack([np.ones(len(y)), x])
    try:
        beta, *_ = np.linalg.lstsq(design, y, rcond=None)
    except np.linalg.LinAlgError:
        return np.nan
    resid = y - design @ beta
    return np.var(resid, ddof=1)


def compute_monthly_residual_variance(daily, factors, character):
    rows = []
    factor_array_cols = ["exret", *factors]
    for permno, group in daily.groupby("permno", sort=False):
        group = group.sort_values("date")
        month_codes, month_starts = np.unique(group["source_yyyymm"].to_numpy(), return_index=True)
        month_ends = np.r_[month_starts[1:], len(group)]
        values_all = group[factor_array_cols].to_numpy(dtype=float)
        for index, month in enumerate(month_codes):
            start = month_starts[max(0, index - 2)]
            end = month_ends[index]
            values = values_all[start:end]
            rvar = residual_variance(values[:, 0], values[:, 1:])
            if np.isfinite(rvar):
                rows.append((permno, month, rvar))
    return pd.DataFrame(rows, columns=["permno", "source_yyyymm", character])


def build_factor_rvar(db, character, factors, output_dir=OUTPUT_DIR):
    daily = get_daily_ff_factor_data(db, output_dir)
    rvar = compute_monthly_residual_variance(daily, factors, character)
    print(f"Computed monthly residual-variance rows for {character}: {len(rvar):,}")

    monthly = get_monthly_alignment(db, output_dir)
    out = monthly.merge(rvar, on=["permno", "source_yyyymm"], how="left")
    print(f"Rows after monthly alignment before dropping missing {character}: {len(out):,}")
    out = out[out[character].replace([np.inf, -np.inf], np.nan).notna()].copy()
    return out[
        ["permno", "permco", "date", "signal_yyyymm", "target_yyyymm", "sic", "exchcd", "shrcd", character]
    ]


def run_factor_rvar_cli(character, description, factors):
    import argparse

    parser = argparse.ArgumentParser(description=description)
    parser.add_argument("--wrds-user", default=None)
    parser.add_argument("--output", default=OUTPUT_DIR / f"{character}.csv")
    args = parser.parse_args()

    output = Path(args.output)
    if not output.is_absolute():
        output = PROJECT_ROOT / output
    output_dir = output.parent
    output.parent.mkdir(parents=True, exist_ok=True)

    db = connect_wrds(args.wrds_user)
    try:
        clear_rvar_caches()
        result = build_factor_rvar(db, character, factors, output_dir)
    finally:
        db.close()
        clear_rvar_caches()

    result.to_csv(output, index=False)
    print(f"Saved {character} to: {output}")
    print(f"Rows: {len(result):,}")
