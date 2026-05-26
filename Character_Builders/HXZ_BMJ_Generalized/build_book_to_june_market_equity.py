import argparse
import sys
from pathlib import Path

import pandas as pd
import wrds

sys.path.append(str(Path(__file__).resolve().parents[1]))

from _shared.ccm import add_ccm_arguments, attach_ccm_links, load_ccm_links


WRDS_USER = None
OUTPUT_FILE = "book_to_june_market_equity.csv"


def load_compustat(db):
    comp = db.raw_sql("""
        SELECT gvkey, datadate, fyear,
               seq, ceq, at, lt,
               pstk, pstkl, pstkrv,
               txditc, csho
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
        comp["ceq"] + comp["preferred_stock"]
    )
    comp.loc[comp["stockholders_equity"].isna(), "stockholders_equity"] = (
        comp["at"] - comp["lt"]
    )

    comp["txditc"] = comp["txditc"].fillna(0)
    comp["book_equity"] = (
        comp["stockholders_equity"] + comp["txditc"] - comp["preferred_stock"]
    )
    comp = comp[
        comp["book_equity"].notna()
        & (comp["book_equity"] > 0)
        & comp["csho"].notna()
        & (comp["csho"] > 0)
    ].copy()

    comp["book_equity_per_share"] = comp["book_equity"] / comp["csho"]
    comp["calendar_year"] = comp["datadate"].dt.year
    comp["formation_year"] = comp["calendar_year"] + 1
    comp["fiscal_yyyymm"] = comp["datadate"].dt.year * 100 + comp["datadate"].dt.month

    # If fiscal year-end changes create multiple reports in the same calendar
    # year, keep the most recent fiscal-year-end report.
    return (
        comp.sort_values(["gvkey", "calendar_year", "datadate"])
        .drop_duplicates(["gvkey", "calendar_year"], keep="last")
    )


def load_crsp_monthly(db):
    crsp = db.raw_sql("""
        SELECT m.permno, m.permco, m.date, m.prc, m.cfacpr,
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
    crsp["yyyymm"] = crsp["year"] * 100 + crsp["month"]
    crsp["price"] = crsp["prc"].abs()
    return crsp[
        crsp["price"].notna()
        & (crsp["price"] > 0)
        & crsp["cfacpr"].notna()
        & (crsp["cfacpr"] > 0)
    ].copy()


def build_book_to_june_market_equity(comp, crsp, link):
    comp_linked = attach_ccm_links(comp, link)

    fiscal_factor = crsp[["permno", "yyyymm", "cfacpr"]].rename(
        columns={"yyyymm": "fiscal_yyyymm", "cfacpr": "cfacpr_fiscal"}
    )
    june_price = crsp[crsp["month"] == 6][
        ["permno", "year", "date", "price", "cfacpr", "exchcd", "shrcd"]
    ].rename(
        columns={
            "year": "formation_year",
            "date": "june_date",
            "price": "june_price",
            "cfacpr": "cfacpr_june",
        }
    )

    bmj = comp_linked.merge(
        fiscal_factor,
        on=["permno", "fiscal_yyyymm"],
        how="inner",
    ).merge(
        june_price,
        on=["permno", "formation_year"],
        how="inner",
    )

    bmj["split_adjustment"] = bmj["cfacpr_june"] / bmj["cfacpr_fiscal"]
    bmj["book_equity_per_share_june_basis"] = (
        bmj["book_equity_per_share"] * bmj["split_adjustment"]
    )
    bmj["bmj"] = bmj["book_equity_per_share_june_basis"] / bmj["june_price"]
    bmj = bmj[bmj["bmj"].notna() & (bmj["bmj"] > 0)].copy()

    bmj = (
        bmj.sort_values(["permno", "datadate", "june_price"], ascending=[True, True, False])
        .drop_duplicates(["permno", "datadate"], keep="first")
    )

    return bmj[
        [
            "permno",
            "permco",
            "gvkey",
            "datadate",
            "sic",
            "fyear",
            "june_date",
            "book_equity_per_share",
            "split_adjustment",
            "june_price",
            "bmj",
        ]
    ]


def main():
    parser = argparse.ArgumentParser(
        description="Build HXZ Bmj, book-to-June-end market equity."
    )
    parser.add_argument("--wrds-user", default=WRDS_USER)
    parser.add_argument("--output", default=OUTPUT_FILE)
    add_ccm_arguments(parser)
    args = parser.parse_args()

    db = (
        wrds.Connection(wrds_username=args.wrds_user)
        if args.wrds_user
        else wrds.Connection()
    )
    try:
        comp = load_compustat(db)
        crsp = load_crsp_monthly(db)
        link = load_ccm_links(db, args.ccm_linktypes, args.ccm_linkprim)
    finally:
        db.close()

    bmj = build_book_to_june_market_equity(comp, crsp, link)
    output_path = Path(args.output)
    if not output_path.is_absolute():
        output_path = Path(__file__).resolve().parents[2] / "outputs" / output_path
    output_path.parent.mkdir(parents=True, exist_ok=True)
    bmj.to_csv(output_path, index=False)

    print(f"Saved Bmj character to: {output_path.resolve()}")
    print(f"Rows: {len(bmj):,}")
    print("datadate is the actual Compustat datadate; june_date is the June formation date.")


if __name__ == "__main__":
    main()
