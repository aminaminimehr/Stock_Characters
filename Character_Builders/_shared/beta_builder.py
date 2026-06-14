import argparse
from pathlib import Path

import numpy as np
import pandas as pd

from _shared.green_builders import OUTPUT_DIR, connect_wrds, load_monthly_alignment_frame
from _shared.rvar_factor_builders import load_daily_factor_data


PROJECT_ROOT = Path(__file__).resolve().parents[2]


def rolling_beta(y, x):
    valid = np.isfinite(y) & np.isfinite(x)
    y = y[valid]
    x = x[valid]
    if len(y) < 21:
        return np.nan
    x_centered = x - x.mean()
    y_centered = y - y.mean()
    denom = np.dot(x_centered, x_centered)
    if denom == 0:
        return np.nan
    return np.dot(x_centered, y_centered) / denom


def compute_monthly_beta(daily, character="beta"):
    rows = []
    for permno, group in daily.groupby("permno", sort=False):
        group = group.sort_values("date")
        month_codes, month_starts = np.unique(group["source_yyyymm"].to_numpy(), return_index=True)
        month_ends = np.r_[month_starts[1:], len(group)]
        values = group[["exret", "mktrf"]].to_numpy(dtype=float)
        for index, month in enumerate(month_codes):
            start = month_starts[max(0, index - 2)]
            end = month_ends[index]
            window = values[start:end]
            beta = rolling_beta(window[:, 0], window[:, 1])
            if np.isfinite(beta):
                rows.append((permno, month, beta))
    return pd.DataFrame(rows, columns=["permno", "source_yyyymm", character])


def build_beta_character(db, output_dir=OUTPUT_DIR):
    daily = load_daily_factor_data(db, ["mktrf"])
    beta = compute_monthly_beta(daily, "beta")

    monthly = load_monthly_alignment_frame(output_dir, db=db)
    out = monthly.merge(beta, on=["permno", "source_yyyymm"], how="left")
    out = out[out["beta"].replace([np.inf, -np.inf], np.nan).notna()].copy()
    return out[["permno", "permco", "date", "signal_yyyymm", "target_yyyymm", "sic", "exchcd", "shrcd", "beta"]]


def build_betasq_character(db, output_dir=OUTPUT_DIR):
    daily = load_daily_factor_data(db, ["mktrf"])
    beta = compute_monthly_beta(daily, "beta")
    beta["betasq"] = beta["beta"] ** 2

    monthly = load_monthly_alignment_frame(output_dir, db=db)
    out = monthly.merge(beta[["permno", "source_yyyymm", "betasq"]], on=["permno", "source_yyyymm"], how="left")
    out = out[out["betasq"].replace([np.inf, -np.inf], np.nan).notna()].copy()
    return out[
        ["permno", "permco", "date", "signal_yyyymm", "target_yyyymm", "sic", "exchcd", "shrcd", "betasq"]
    ]


def run_beta_cli():
    parser = argparse.ArgumentParser(
        description="Build beta from rolling 3-month daily CAPM regressions."
    )
    parser.add_argument("--wrds-user", default=None)
    parser.add_argument("--output", default=OUTPUT_DIR / "beta.csv")
    args = parser.parse_args()

    output = Path(args.output)
    if not output.is_absolute():
        output = PROJECT_ROOT / output
    output.parent.mkdir(parents=True, exist_ok=True)

    db = connect_wrds(args.wrds_user)
    try:
        result = build_beta_character(db)
    finally:
        db.close()

    result.to_csv(output, index=False)
    print(f"Saved beta to: {output.resolve()}")
    print(f"Rows: {len(result):,}")
