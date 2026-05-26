import argparse
import sys
from pathlib import Path

import pandas as pd
import wrds

sys.path.append(str(Path(__file__).resolve().parents[1]))

from _shared.ccm import add_ccm_arguments, attach_ccm_links, load_ccm_links


WRDS_USER = None
OUTPUT_FILE = "cash_flow_to_price.csv"


def load_compustat(db):
    comp = db.raw_sql("""
        SELECT gvkey, datadate, fyear,
               ib, dp
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

    comp["cash_flow"] = comp["ib"] + comp["dp"]
    comp = comp[comp["cash_flow"] > 0].copy()

    # This is the actual Compustat fiscal-year-end calendar year. The raw
    # output intentionally does not shift dates. For prediction or portfolio
    # formation, make this character available in June of calendar_year + 1.
    # Example: datadate in 2004 uses December 2004 market equity and is used
    # for June 2005 portfolios / July 2005-June 2006 returns.
    comp["calendar_year"] = comp["datadate"].dt.year

    # If a firm changes fiscal year end and has multiple records in the same
    # calendar year, keep the most recent report for that firm-year.
    return (
        comp.sort_values(["gvkey", "calendar_year", "datadate"])
        .drop_duplicates(["gvkey", "calendar_year"], keep="last")
    )


def load_crsp_monthly(db, use_imputed_market_equity):
    crsp = db.raw_sql("""
        SELECT m.permno, m.permco, m.date, m.prc, m.shrout,
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
    crsp["year"] = crsp["date"].dt.year
    crsp["month"] = crsp["date"].dt.month
    crsp = crsp.sort_values(["permno", "date"])

    if use_imputed_market_equity:
        crsp[["price_for_me", "shrout_for_me"]] = (
            crsp.groupby("permno")[["prc", "shrout"]].ffill()
        )
    else:
        crsp["price_for_me"] = crsp["prc"]
        crsp["shrout_for_me"] = crsp["shrout"]

    crsp["market_equity"] = crsp["price_for_me"].abs() * crsp["shrout_for_me"]

    return crsp[crsp["market_equity"].notna() & (crsp["market_equity"] > 0)].copy()


def december_firm_market_equity(crsp):
    december = crsp[crsp["month"] == 12].copy()

    return (
        december.groupby(["permco", "year"], as_index=False)["market_equity"]
        .sum()
        .rename(columns={"year": "calendar_year"})
    )


def build_cash_flow_to_price(comp, crsp_december_me, link):
    comp_linked = attach_ccm_links(comp, link)

    cfp = comp_linked.merge(
        crsp_december_me,
        on=["permco", "calendar_year"],
        how="inner",
    )
    cfp["cash_flow_to_price"] = cfp["cash_flow"] / cfp["market_equity"]
    cfp = cfp[cfp["cash_flow_to_price"] > 0].copy()

    cfp = (
        cfp.sort_values(
            ["permno", "datadate", "market_equity"],
            ascending=[True, True, False],
        )
        .drop_duplicates(["permno", "datadate"], keep="first")
    )

    return cfp[
        ["permno", "permco", "gvkey", "datadate", "sic", "fyear", "cash_flow_to_price"]
    ]


def main():
    parser = argparse.ArgumentParser(
        description="Build cash-flow-to-price using actual Compustat datadates."
    )
    parser.add_argument("--wrds-user", default=WRDS_USER)
    parser.add_argument("--output", default=OUTPUT_FILE)
    add_ccm_arguments(parser)
    parser.add_argument(
        "--use-imputed-market-equity",
        action="store_true",
        help=(
            "Forward-fill CRSP price and shares outstanding within permno before "
            "constructing December market equity."
        ),
    )
    args = parser.parse_args()

    db = (
        wrds.Connection(wrds_username=args.wrds_user)
        if args.wrds_user
        else wrds.Connection()
    )
    try:
        comp = load_compustat(db)
        crsp = load_crsp_monthly(db, args.use_imputed_market_equity)
        link = load_ccm_links(db, args.ccm_linktypes, args.ccm_linkprim)
    finally:
        db.close()

    cfp = build_cash_flow_to_price(comp, december_firm_market_equity(crsp), link)
    output_path = Path(args.output)
    if not output_path.is_absolute():
        output_path = Path(__file__).resolve().parents[2] / "outputs" / output_path
    output_path.parent.mkdir(parents=True, exist_ok=True)
    cfp.to_csv(output_path, index=False)

    print(f"Saved cash-flow-to-price character to: {output_path.resolve()}")
    print(f"Rows: {len(cfp):,}")
    print(f"Used imputed CRSP price/shareout: {args.use_imputed_market_equity}")
    print("datadate is the actual Compustat datadate; no return-prediction shift is applied.")


if __name__ == "__main__":
    main()
