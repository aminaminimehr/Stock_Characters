import argparse
from pathlib import Path

import pandas as pd
import wrds


WRDS_USER = None
OUTPUT_FILE = "operating_profitability.csv"


def load_compustat(db):
    comp = db.raw_sql("""
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

    company = db.raw_sql("""
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
    comp["operating_profitability"] = operating_profit / comp["book_equity"]
    comp.loc[~expense_available, "operating_profitability"] = pd.NA
    comp = comp[comp["operating_profitability"].notna()].copy()

    # This is the actual Compustat fiscal-year-end calendar year. The raw
    # output intentionally does not shift dates. For prediction or portfolio
    # formation, make this character available in June of calendar_year + 1.
    # Example: datadate in 2004 is used for June 2005 portfolios /
    # July 2005-June 2006 returns.
    comp["calendar_year"] = comp["datadate"].dt.year

    # If a firm changes fiscal year end and has multiple records in the same
    # calendar year, keep the most recent report for that firm-year.
    return (
        comp.sort_values(["gvkey", "calendar_year", "datadate"])
        .drop_duplicates(["gvkey", "calendar_year"], keep="last")
    )


def load_ccm_links(db):
    link = db.raw_sql("""
        SELECT gvkey, lpermno AS permno, lpermco AS permco,
               linkdt, linkenddt
        FROM crsp.ccmxpf_linktable
        WHERE linktype IN ('LU', 'LC')
          AND linkprim = 'P'
    """)
    link["linkdt"] = pd.to_datetime(link["linkdt"])
    link["linkenddt"] = pd.to_datetime(link["linkenddt"])

    return link


def build_operating_profitability(comp, link):
    comp_linked = comp.merge(link, on="gvkey", how="inner")
    comp_linked = comp_linked[
        (comp_linked["datadate"] >= comp_linked["linkdt"])
        & (
            (comp_linked["datadate"] <= comp_linked["linkenddt"])
            | comp_linked["linkenddt"].isna()
        )
    ].copy()

    comp_linked = (
        comp_linked.sort_values(["permno", "datadate"])
        .drop_duplicates(["permno", "datadate"], keep="last")
    )

    return comp_linked[
        [
            "permno",
            "permco",
            "gvkey",
            "datadate",
            "sic",
            "fyear",
            "operating_profitability",
        ]
    ]


def main():
    parser = argparse.ArgumentParser(
        description="Build operating profitability to equity using actual Compustat datadates."
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
        comp = load_compustat(db)
        link = load_ccm_links(db)
    finally:
        db.close()

    ope = build_operating_profitability(comp, link)
    output_path = Path(args.output)
    if not output_path.is_absolute():
        output_path = Path(__file__).resolve().parents[2] / "outputs" / output_path
    output_path.parent.mkdir(parents=True, exist_ok=True)
    ope.to_csv(output_path, index=False)

    print(f"Saved operating profitability character to: {output_path.resolve()}")
    print(f"Rows: {len(ope):,}")
    print("datadate is the actual Compustat datadate; no return-prediction shift is applied.")


if __name__ == "__main__":
    main()
