import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import wrds

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from output_paths import resolve_output_path  # noqa: E402

WRDS_USER = None
OUTPUT_FILE = "mvel1.csv"


def add_one_month(yyyymm):
    year = yyyymm // 100
    month = yyyymm % 100
    next_month = month + 1
    next_year = year + (next_month == 13)
    next_month = 1 if next_month == 13 else next_month
    return next_year * 100 + next_month


def load_crsp_monthly(db, use_imputed_market_equity):
    crsp = db.raw_sql("""
        SELECT m.permno, m.permco, m.date, m.prc, m.shrout,
               n.exchcd, n.shrcd, n.siccd
        FROM crsp.msf AS m
        JOIN crsp.msenames AS n
          ON m.permno = n.permno
         AND n.namedt <= m.date
         AND m.date <= COALESCE(n.nameendt, DATE '9999-12-31')
        WHERE n.shrcd IN (10, 11)
          AND n.exchcd IN (1, 2, 3)
    """)
    crsp["date"] = pd.to_datetime(crsp["date"])
    crsp = crsp.sort_values(["permno", "date"])

    if use_imputed_market_equity:
        crsp[["price_for_me", "shrout_for_me"]] = (
            crsp.groupby("permno")[["prc", "shrout"]].ffill()
        )
    else:
        crsp["price_for_me"] = crsp["prc"]
        crsp["shrout_for_me"] = crsp["shrout"]

    crsp["market_equity"] = crsp["price_for_me"].abs() * crsp["shrout_for_me"]
    crsp = crsp[crsp["market_equity"].notna() & (crsp["market_equity"] > 0)].copy()

    return crsp


def build_mvel1(crsp):
    mvel1 = crsp.sort_values(["permno", "date"]).copy()
    mvel1["lagged_market_equity"] = mvel1.groupby("permno")["market_equity"].shift(1)
    mvel1["source_date"] = mvel1.groupby("permno")["date"].shift(1)
    mvel1 = mvel1[
        mvel1["lagged_market_equity"].notna() & (mvel1["lagged_market_equity"] > 0)
    ].copy()

    mvel1["mvel1"] = np.log(mvel1["lagged_market_equity"])
    mvel1["source_yyyymm"] = (
        mvel1["source_date"].dt.year * 100 + mvel1["source_date"].dt.month
    )
    mvel1["signal_yyyymm"] = mvel1["date"].dt.year * 100 + mvel1["date"].dt.month
    mvel1["target_yyyymm"] = mvel1["signal_yyyymm"].map(add_one_month)
    mvel1 = mvel1.rename(columns={"siccd": "sic"})

    return mvel1[
        [
            "permno",
            "permco",
            "source_date",
            "source_yyyymm",
            "date",
            "signal_yyyymm",
            "target_yyyymm",
            "sic",
            "exchcd",
            "shrcd",
            "lagged_market_equity",
            "mvel1",
        ]
    ]


def main():
    parser = argparse.ArgumentParser(
        description="Build monthly mvel1 as log lagged CRSP market equity."
    )
    parser.add_argument("--wrds-user", default=WRDS_USER)
    parser.add_argument("--output", default=OUTPUT_FILE)
    parser.add_argument(
        "--use-imputed-market-equity",
        action="store_true",
        help=(
            "Forward-fill CRSP price and shares outstanding within permno before "
            "constructing market equity."
        ),
    )
    args = parser.parse_args()

    db = (
        wrds.Connection(wrds_username=args.wrds_user)
        if args.wrds_user
        else wrds.Connection()
    )
    try:
        crsp = load_crsp_monthly(db, args.use_imputed_market_equity)
    finally:
        db.close()

    mvel1 = build_mvel1(crsp)
    output_path = resolve_output_path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    mvel1.to_csv(output_path, index=False)

    print(f"Saved mvel1 character to: {output_path.resolve()}")
    print(f"Rows: {len(mvel1):,}")
    print(f"Used imputed CRSP price/shareout: {args.use_imputed_market_equity}")


if __name__ == "__main__":
    main()
