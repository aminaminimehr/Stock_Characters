import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from _shared.green_builders import connect_wrds, load_crsp_monthly
from output_paths import resolve_output_path  # noqa: E402

DEFAULT_OUTPUT = "zerotrade.csv"


def load_monthly_zerotrade(db):
    daily = db.raw_sql("""
        SELECT permno,
               DATE_TRUNC('month', date)::date AS month_start,
               SUM(CASE WHEN vol = 0 THEN 1 ELSE 0 END)::double precision AS countzero,
               COUNT(*)::double precision AS ndays,
               SUM(vol / NULLIF(shrout, 0))::double precision AS turn_sum
        FROM crsp.dsf
        GROUP BY permno, DATE_TRUNC('month', date)::date
    """)
    daily["month_start"] = pd.to_datetime(daily["month_start"])
    daily["source_yyyymm"] = daily["month_start"].dt.year * 100 + daily["month_start"].dt.month
    daily["zerotrade"] = (daily["countzero"] + ((1 / daily["turn_sum"]) / 480000)) * 21 / daily["ndays"]
    return daily[["permno", "source_yyyymm", "zerotrade"]]


def build_zerotrade(db):
    daily = load_monthly_zerotrade(db)
    monthly = load_crsp_monthly(db)[
        ["permno", "permco", "date", "signal_yyyymm", "target_yyyymm", "siccd", "exchcd", "shrcd"]
    ].rename(columns={"siccd": "sic"})
    monthly["source_yyyymm"] = monthly.groupby("permno")["signal_yyyymm"].shift(1)
    out = monthly.merge(daily, on=["permno", "source_yyyymm"], how="left")
    out = out[out["zerotrade"].replace([np.inf, -np.inf], np.nan).notna()].copy()
    return out[["permno", "permco", "date", "signal_yyyymm", "target_yyyymm", "sic", "exchcd", "shrcd", "zerotrade"]]


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Build zerotrade from daily CRSP.")
    parser.add_argument("--wrds-user", default=None)
    parser.add_argument("--output", default=DEFAULT_OUTPUT)
    args = parser.parse_args()

    output = resolve_output_path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)

    db = connect_wrds(args.wrds_user)
    try:
        zerotrade = build_zerotrade(db)
    finally:
        db.close()

    zerotrade.to_csv(output, index=False)
    print(f"Saved zerotrade to: {output}")
    print(f"Rows: {len(zerotrade):,}")
