import argparse
from pathlib import Path

import numpy as np
import pandas as pd

from _shared.green_builders import OUTPUT_DIR, connect_wrds, crsp_universe_filter, load_crsp_monthly


PROJECT_ROOT = Path(__file__).resolve().parents[2]


def load_ibes_forecasts(db):
    ibes = db.raw_sql("""
        SELECT ticker, cusip, fpedats, statpers, meanest
        FROM ibes.statsum_epsus
        WHERE fpi = '1'
          AND statpers < anndats_act
          AND measure = 'EPS'
          AND meanest IS NOT NULL
          AND fpedats IS NOT NULL
          AND (fpedats - statpers) >= 0
    """)
    ibes["statpers"] = pd.to_datetime(ibes["statpers"])
    ibes["fpedats"] = pd.to_datetime(ibes["fpedats"])
    ibes["merge_date"] = ibes["statpers"] + pd.offsets.MonthEnd(0)
    ibes = (
        ibes.sort_values(["ticker", "cusip", "statpers", "fpedats"], ascending=[True, True, True, False])
        .drop_duplicates(["ticker", "cusip", "statpers"], keep="first")
    )
    return ibes


def load_crsp_price_history(db):
    crsp = db.raw_sql(f"""
        SELECT m.permno, m.date, m.prc, m.cfacpr, n.ncusip
        FROM crsp.msf AS m
        JOIN crsp.msenames AS n
          ON m.permno = n.permno
         AND n.namedt <= m.date
         AND m.date <= COALESCE(n.nameendt, DATE '9999-12-31')
        WHERE m.date >= DATE '1980-01-01'
          AND {crsp_universe_filter("n")}
    """)
    crsp["date"] = pd.to_datetime(crsp["date"])
    crsp["merge_date"] = crsp["date"] + pd.offsets.MonthEnd(0) + pd.DateOffset(months=1) + pd.offsets.MonthEnd(0)
    crsp["prc_adj"] = crsp["prc"].abs() / crsp["cfacpr"].replace(0, np.nan)
    crsp["cusip6"] = crsp["ncusip"].str[:6]
    return crsp


def build_re_character(db):
    ibes = load_ibes_forecasts(db)
    crsp = load_crsp_price_history(db)

    ibes["cusip6"] = ibes["cusip"].str[:6]
    merged = ibes.merge(
        crsp[["permno", "cusip6", "merge_date", "prc_adj"]],
        on=["cusip6", "merge_date"],
        how="inner",
    )
    merged = merged.sort_values(["permno", "fpedats", "statpers"])
    merged["meanest_last_month"] = merged.groupby(["permno", "fpedats"])["meanest"].shift(1)
    merged = merged[merged["meanest_last_month"].notna()].copy()
    merged = merged[merged["prc_adj"] > 0].copy()
    merged["monthly_revision"] = (merged["meanest"] - merged["meanest_last_month"]) / merged["prc_adj"]

    merged["count"] = merged.groupby(["permno", "fpedats"]).cumcount() + 1
    for lag in range(1, 7):
        merged[f"monthly_revision_l{lag}"] = merged.groupby(["permno"])["monthly_revision"].shift(lag)

    condlist = [
        merged["count"] == 4,
        merged["count"] == 5,
        merged["count"] == 6,
        merged["count"] >= 7,
    ]
    choicelist = [
        merged[["monthly_revision_l1", "monthly_revision_l2", "monthly_revision_l3"]].mean(axis=1),
        merged[["monthly_revision_l1", "monthly_revision_l2", "monthly_revision_l3", "monthly_revision_l4"]].mean(axis=1),
        merged[
            ["monthly_revision_l1", "monthly_revision_l2", "monthly_revision_l3", "monthly_revision_l4", "monthly_revision_l5"]
        ].mean(axis=1),
        merged[
            [
                "monthly_revision_l1",
                "monthly_revision_l2",
                "monthly_revision_l3",
                "monthly_revision_l4",
                "monthly_revision_l5",
                "monthly_revision_l6",
            ]
        ].mean(axis=1),
    ]
    merged["re"] = np.select(condlist, choicelist, default=np.nan)
    merged = merged[merged["count"] >= 4].copy()
    merged = merged.drop_duplicates(["permno", "statpers"], keep="last")
    merged["signal_yyyymm"] = merged["statpers"].dt.year * 100 + merged["statpers"].dt.month

    monthly = load_crsp_monthly(db)[
        ["permno", "permco", "date", "signal_yyyymm", "target_yyyymm", "siccd", "exchcd", "shrcd"]
    ].rename(columns={"siccd": "sic"})
    re_panel = merged[["permno", "signal_yyyymm", "re"]].drop_duplicates(["permno", "signal_yyyymm"], keep="last")
    out = monthly.merge(re_panel, on=["permno", "signal_yyyymm"], how="inner")
    out = out[out["re"].replace([np.inf, -np.inf], np.nan).notna()].copy()
    return out[["permno", "permco", "date", "signal_yyyymm", "target_yyyymm", "sic", "exchcd", "shrcd", "re"]]


def run_re_cli():
    parser = argparse.ArgumentParser(
        description="Build analyst forecast revision character RE from IBES summary history."
    )
    parser.add_argument("--wrds-user", default=None)
    parser.add_argument("--output", default=OUTPUT_DIR / "re.csv")
    args = parser.parse_args()

    output = Path(args.output)
    if not output.is_absolute():
        output = PROJECT_ROOT / output
    output.parent.mkdir(parents=True, exist_ok=True)

    db = connect_wrds(args.wrds_user)
    try:
        result = build_re_character(db)
    finally:
        db.close()

    result.to_csv(output, index=False)
    print(f"Saved re to: {output.resolve()}")
    print(f"Rows: {len(result):,}")
