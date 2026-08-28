import argparse
import sys
from pathlib import Path

import pandas as pd
import wrds

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from _shared.ccm import attach_ccm_links, load_ccm_links
from output_paths import read_wrds_sql, resolve_output_path  # noqa: E402

OUTPUT_FILE = "operprof.csv"


def load_compustat(db):
    """Pull Compustat annual fundamentals for operating profitability."""
    comp = read_wrds_sql(db, """
        SELECT gvkey, datadate, fyear,
               revt, cogs, xsga, xint,
               seq, ceq, at, lt,
               pstk, pstkl, pstkrv,
               txditc
        FROM comp.funda
        WHERE indfmt = 'INDL'
          AND datafmt = 'STD'
          AND popsrc = 'D'
          AND consol = 'C'
    """)
    comp["datadate"] = pd.to_datetime(comp["datadate"])

    company = read_wrds_sql(db, """
        SELECT gvkey, sic
        FROM comp.company
    """)
    comp = comp.merge(company, on="gvkey", how="left")

    comp["preferred_stock"] = (
        comp["pstkrv"].fillna(comp["pstkl"]).fillna(comp["pstk"]).fillna(0)
    )
    comp["stockholders_equity"] = comp["seq"]
    comp.loc[comp["stockholders_equity"].isna(), "stockholders_equity"] = (
        comp["ceq"] + comp["pstk"].fillna(0)
    )
    comp.loc[comp["stockholders_equity"].isna(), "stockholders_equity"] = (
        comp["at"] - comp["lt"]
    )

    comp["txditc"] = comp["txditc"].fillna(0)
    comp["book_equity"] = (
        comp["stockholders_equity"] + comp["txditc"] - comp["preferred_stock"]
    )
    comp = comp[comp["book_equity"] > 0].copy()

    expense_available = comp[["cogs", "xsga", "xint"]].notna().any(axis=1)
    operating_profit = (
        comp["revt"]
        - comp["cogs"].fillna(0)
        - comp["xsga"].fillna(0)
        - comp["xint"].fillna(0)
    )
    comp["operprof"] = operating_profit / comp["book_equity"]
    comp.loc[~expense_available, "operprof"] = pd.NA
    comp = comp[comp["operprof"].notna()].copy()
    comp["calendar_year"] = comp["datadate"].dt.year

    return (
        comp.sort_values(["gvkey", "calendar_year", "datadate"])
        .drop_duplicates(["gvkey", "calendar_year"], keep="last")
    )


def build_operprof(comp, link):
    """Operating profitability to equity, one row per permno x datadate."""
    comp_linked = attach_ccm_links(comp, link)
    comp_linked = (
        comp_linked.sort_values(["permno", "datadate"])
        .drop_duplicates(["permno", "datadate"], keep="last")
    )
    return comp_linked[
        ["permno", "permco", "gvkey", "datadate", "sic", "fyear", "operprof"]
    ]


def main():
    parser = argparse.ArgumentParser(description="Build operprof from WRDS.")
    parser.add_argument("--wrds-user", default=None)
    parser.add_argument("--output", default=OUTPUT_FILE)
    args = parser.parse_args()

    db = (
        wrds.Connection(wrds_username=args.wrds_user)
        if args.wrds_user
        else wrds.Connection()
    )
    try:
        comp = load_compustat(db)
        link = load_ccm_links(db)
    finally:
        db.close()

    ope = build_operprof(comp, link)
    output_path = resolve_output_path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    ope.to_csv(output_path, index=False)

    print(f"Saved operprof to: {output_path.resolve()}")
    print(f"Rows: {len(ope):,}")


if __name__ == "__main__":
    main()
