import argparse
from pathlib import Path

import numpy as np
import pandas as pd
import wrds


WRDS_USER = None
PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_FILE = PROJECT_ROOT / "outputs" / "excess_returns.csv"


def load_crsp_monthly_returns(db):
    crsp = db.raw_sql("""
        SELECT m.permno, m.permco, m.date, m.ret, m.retx,
               n.exchcd, n.shrcd
        FROM crsp.msf AS m
        JOIN crsp.msenames AS n
          ON m.permno = n.permno
         AND n.namedt <= m.date
         AND m.date <= COALESCE(n.nameendt, DATE '9999-12-31')
        WHERE n.shrcd IN (10, 11)
          AND n.exchcd IN (1, 2, 3)
    """)
    crsp["date"] = pd.to_datetime(crsp["date"])
    crsp["ret"] = pd.to_numeric(crsp["ret"], errors="coerce")
    crsp["retx"] = pd.to_numeric(crsp["retx"], errors="coerce")
    return crsp


def load_delisting_returns(db):
    dlret = db.raw_sql("""
        SELECT permno, dlstdt, dlret
        FROM crsp.msedelist
        WHERE dlstdt IS NOT NULL
    """)
    dlret["date"] = pd.to_datetime(dlret["dlstdt"]) + pd.offsets.MonthEnd(0)
    dlret["dlret"] = pd.to_numeric(dlret["dlret"], errors="coerce")
    return dlret[["permno", "date", "dlret"]]


def load_risk_free_rate(db):
    factors = db.raw_sql("""
        SELECT date, rf
        FROM ff.factors_monthly
    """)
    factors["date"] = pd.to_datetime(factors["date"]) + pd.offsets.MonthEnd(0)
    factors["rf"] = pd.to_numeric(factors["rf"], errors="coerce")

    # WRDS factor tables are commonly stored in percent units. Convert to
    # decimal units when the scale indicates percentages.
    median_abs_rf = factors["rf"].abs().median()
    if pd.notna(median_abs_rf) and median_abs_rf > 0.02:
        factors["rf"] = factors["rf"] / 100

    return factors


def build_excess_returns(crsp, dlret, rf):
    returns = crsp.merge(dlret, on=["permno", "date"], how="left")
    returns["ret_for_adjustment"] = returns["ret"].fillna(0)
    returns["dlret_for_adjustment"] = returns["dlret"].fillna(0)

    returns["retadj"] = (
        (1 + returns["ret_for_adjustment"])
        * (1 + returns["dlret_for_adjustment"])
        - 1
    )
    returns.loc[returns["ret"].isna() & returns["dlret"].isna(), "retadj"] = np.nan

    returns = returns.merge(rf, on="date", how="left")
    returns["excess_return"] = returns["retadj"] - returns["rf"]
    returns["target_yyyymm"] = returns["date"].dt.year * 100 + returns["date"].dt.month

    returns = returns[
        returns["excess_return"].replace([np.inf, -np.inf], np.nan).notna()
    ].copy()

    return returns[
        [
            "permno",
            "permco",
            "date",
            "target_yyyymm",
            "exchcd",
            "shrcd",
            "ret",
            "dlret",
            "retadj",
            "rf",
            "excess_return",
        ]
    ].sort_values(["permno", "target_yyyymm"])


def main():
    parser = argparse.ArgumentParser(
        description=(
            "Build monthly CRSP excess returns keyed by target_yyyymm. "
            "Merge these returns to character panels on permno and target_yyyymm."
        )
    )
    parser.add_argument("--wrds-user", default=WRDS_USER)
    parser.add_argument("--output", default=OUTPUT_FILE)
    args = parser.parse_args()

    db = (
        wrds.Connection(wrds_username=args.wrds_user)
        if args.wrds_user
        else wrds.Connection()
    )
    try:
        crsp = load_crsp_monthly_returns(db)
        dlret = load_delisting_returns(db)
        rf = load_risk_free_rate(db)
    finally:
        db.close()

    excess_returns = build_excess_returns(crsp, dlret, rf)

    output_path = Path(args.output)
    if not output_path.is_absolute():
        output_path = PROJECT_ROOT / output_path
    output_path.parent.mkdir(parents=True, exist_ok=True)
    excess_returns.to_csv(output_path, index=False)

    print(f"Saved excess returns to: {output_path.resolve()}")
    print(f"Rows: {len(excess_returns):,}")
    print("Return month key: target_yyyymm")
    print("Use this file by merging on ['permno', 'target_yyyymm'].")


if __name__ == "__main__":
    main()
