import argparse
import sys
from pathlib import Path

import pandas as pd
import wrds

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from _shared.ccm import attach_ccm_links, load_ccm_links
from output_paths import crsp_universe_filter, read_wrds_sql, resolve_output_path  # noqa: E402

OUTPUT_FILE = "bm.csv"


def load_compustat(db):
    """Pull Compustat annual fundamentals and book equity (Davis-Fama-French)."""
    comp = read_wrds_sql(db, """
        SELECT gvkey, datadate, fyear,
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
        comp["ceq"] + comp["preferred_stock"]
    )
    comp.loc[comp["stockholders_equity"].isna(), "stockholders_equity"] = (
        comp["at"] - comp["lt"]
    )

    comp["txditc"] = comp["txditc"].fillna(0)
    comp["book_equity"] = (
        comp["stockholders_equity"] + comp["txditc"] - comp["preferred_stock"]
    )
    comp = comp[comp["book_equity"] > 0].copy()
    comp["book_equity"] = comp["book_equity"] * 1000
    comp["calendar_year"] = comp["datadate"].dt.year

    return (
        comp.sort_values(["gvkey", "calendar_year", "datadate"])
        .drop_duplicates(["gvkey", "calendar_year"], keep="last")
    )


def load_crsp_monthly(db):
    """CRSP monthly prices for December firm market equity (all share codes)."""
    crsp = read_wrds_sql(db, f"""
        SELECT m.permno, m.permco, m.date, m.prc, m.shrout,
               n.exchcd, n.shrcd
        FROM crsp.msf AS m
        JOIN crsp.msenames AS n
          ON m.permno = n.permno
         AND n.namedt <= m.date
         AND m.date <= COALESCE(n.nameendt, DATE '9999-12-31')
        WHERE {crsp_universe_filter("n")}
    """)
    crsp["date"] = pd.to_datetime(crsp["date"])
    crsp["year"] = crsp["date"].dt.year
    crsp["month"] = crsp["date"].dt.month
    crsp = crsp.sort_values(["permno", "date"])
    crsp["market_equity"] = crsp["prc"].abs() * crsp["shrout"]
    return crsp[crsp["market_equity"].notna() & (crsp["market_equity"] > 0)].copy()


def december_firm_market_equity(crsp):
    """Sum December CRSP market equity to permco x calendar_year."""
    december = crsp[crsp["month"] == 12].copy()
    return (
        december.groupby(["permco", "year"], as_index=False)["market_equity"]
        .sum()
        .rename(columns={"year": "calendar_year"})
    )


def build_bm(comp, crsp_december_me, link):
    """Book equity / December market equity, one row per permno x datadate."""
    comp_linked = attach_ccm_links(comp, link)
    bm = comp_linked.merge(crsp_december_me, on=["permco", "calendar_year"], how="inner")
    bm["bm"] = bm["book_equity"] / bm["market_equity"]
    bm = bm[bm["bm"] > 0].copy()
    bm = (
        bm.sort_values(["permno", "datadate", "market_equity"], ascending=[True, True, False])
        .drop_duplicates(["permno", "datadate"], keep="first")
    )
    return bm[["permno", "permco", "gvkey", "datadate", "sic", "fyear", "bm"]]


def main():
    parser = argparse.ArgumentParser(description="Build bm (book-to-market) from WRDS.")
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
        crsp = load_crsp_monthly(db)
        link = load_ccm_links(db)
    finally:
        db.close()

    bm = build_bm(comp, december_firm_market_equity(crsp), link)
    output_path = resolve_output_path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    bm.to_csv(output_path, index=False)

    print(f"Saved bm to: {output_path.resolve()}")
    print(f"Rows: {len(bm):,}")


if __name__ == "__main__":
    main()
