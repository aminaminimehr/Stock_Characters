from pathlib import Path

import numpy as np
import pandas as pd

from _shared.green_builders import connect_wrds, load_crsp_monthly


PROJECT_ROOT = Path(__file__).resolve().parents[2]
OUTPUT_DIR = PROJECT_ROOT / "outputs"


def load_daily_factor_data(db, factors):
    factor_cols = ", ".join(f"f.{factor}" for factor in factors)
    daily = db.raw_sql(f"""
        SELECT d.permno, d.date, d.ret, f.rf, {factor_cols},
               dl.dlret
        FROM crsp.dsf AS d
        LEFT JOIN ff.factors_daily AS f
          ON d.date = f.date
        LEFT JOIN crsp.dsedelist AS dl
          ON d.permno = dl.permno
         AND d.date = dl.dlstdt
        WHERE d.date >= DATE '1959-01-01'
    """)
    daily["date"] = pd.to_datetime(daily["date"])
    daily = daily.sort_values(["permno", "date"])
    daily["ret"] = pd.to_numeric(daily["ret"], errors="coerce").fillna(0)
    daily["dlret"] = pd.to_numeric(daily["dlret"], errors="coerce").fillna(0)
    daily["retadj"] = (1 + daily["ret"]) * (1 + daily["dlret"]) - 1
    daily["exret"] = daily["retadj"] - daily["rf"]
    daily["source_yyyymm"] = daily["date"].dt.year * 100 + daily["date"].dt.month
    return daily[["permno", "date", "source_yyyymm", "exret", *factors]]


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


def build_factor_rvar(db, character, factors):
    daily = load_daily_factor_data(db, factors)
    print(f"Loaded daily factor rows: {len(daily):,}")
    rvar = compute_monthly_residual_variance(daily, factors, character)
    print(f"Computed monthly residual-variance rows: {len(rvar):,}")

    monthly = load_crsp_monthly(db)[
        ["permno", "permco", "date", "signal_yyyymm", "target_yyyymm", "siccd", "exchcd", "shrcd"]
    ].rename(columns={"siccd": "sic"})
    monthly["source_yyyymm"] = monthly.groupby("permno")["signal_yyyymm"].shift(1)
    out = monthly.merge(rvar, on=["permno", "source_yyyymm"], how="left")
    print(f"Rows after monthly alignment before dropping missing {character}: {len(out):,}")
    out = out[out[character].replace([np.inf, -np.inf], np.nan).notna()].copy()
    return out[["permno", "permco", "date", "signal_yyyymm", "target_yyyymm", "sic", "exchcd", "shrcd", character]]


def run_factor_rvar_cli(character, description, factors):
    import argparse

    parser = argparse.ArgumentParser(description=description)
    parser.add_argument("--wrds-user", default=None)
    parser.add_argument("--output", default=OUTPUT_DIR / f"{character}.csv")
    args = parser.parse_args()

    output = Path(args.output)
    if not output.is_absolute():
        output = PROJECT_ROOT / output
    output.parent.mkdir(parents=True, exist_ok=True)

    db = connect_wrds(args.wrds_user)
    try:
        result = build_factor_rvar(db, character, factors)
    finally:
        db.close()

    result.to_csv(output, index=False)
    print(f"Saved {character} to: {output}")
    print(f"Rows: {len(result):,}")
