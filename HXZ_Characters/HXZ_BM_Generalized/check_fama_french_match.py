import argparse
import math

import pandas as pd
import wrds

from build_book_to_market import (
    WRDS_USER,
    build_book_to_market,
    december_firm_market_equity,
    load_ccm_links,
    load_compustat,
    load_crsp_monthly,
)


START_YEAR = 1963
END_YEAR = 2005

FF_TARGET = pd.DataFrame(
    {
        "ff_mean": {
            "Market": -0.47,
            "Micro": -0.34,
            "Small": -0.59,
            "Big": -0.70,
            "All but Micro": -0.65,
        },
        "ff_std": {
            "Market": 0.87,
            "Micro": 0.89,
            "Small": 0.77,
            "Big": 0.74,
            "All but Micro": 0.76,
        },
    }
)


def june_firm_market_equity(crsp):
    june = crsp[crsp["month"] == 6].copy()

    firm_exchange = (
        june.sort_values(
            ["permco", "year", "market_equity"],
            ascending=[True, True, False],
        )
        .drop_duplicates(["permco", "year"])
        [["permco", "year", "exchcd"]]
    )

    firm_me = (
        june.groupby(["permco", "year"], as_index=False)["market_equity"]
        .sum()
        .merge(firm_exchange, on=["permco", "year"], how="left")
        .rename(
            columns={
                "year": "portfolio_year",
                "market_equity": "june_market_equity",
                "exchcd": "june_exchcd",
            }
        )
    )

    return firm_me


def add_fama_french_size_groups(bm):
    nyse = bm[bm["june_exchcd"] == 1].copy()
    breakpoints = (
        nyse.groupby("portfolio_year")["june_market_equity"]
        .quantile([0.2, 0.5])
        .unstack()
        .rename(columns={0.2: "nyse_p20", 0.5: "nyse_p50"})
        .reset_index()
    )

    bm = bm.merge(breakpoints, on="portfolio_year", how="left")
    bm["size_group"] = "Big"
    bm.loc[bm["june_market_equity"] < bm["nyse_p20"], "size_group"] = "Micro"
    bm.loc[
        (bm["june_market_equity"] >= bm["nyse_p20"])
        & (bm["june_market_equity"] < bm["nyse_p50"]),
        "size_group",
    ] = "Small"

    return bm


def annual_log_bm_stats(bm, label):
    stats = (
        bm.groupby("portfolio_year")["log_book_to_market"]
        .agg(["mean", "std"])
        .reset_index()
    )
    return pd.Series(
        {
            "mean": stats["mean"].mean(),
            "std": stats["std"].mean(),
        },
        name=label,
    )


def compare_to_fama_french(bm):
    bm["log_book_to_market"] = bm["book_to_market"].map(math.log)

    rows = [
        annual_log_bm_stats(bm, "Market"),
        annual_log_bm_stats(bm[bm["size_group"] == "Micro"], "Micro"),
        annual_log_bm_stats(bm[bm["size_group"] == "Small"], "Small"),
        annual_log_bm_stats(bm[bm["size_group"] == "Big"], "Big"),
        annual_log_bm_stats(bm[bm["size_group"] != "Micro"], "All but Micro"),
    ]

    comparison = pd.DataFrame(rows)
    comparison = comparison.join(FF_TARGET)
    comparison["mean_diff"] = comparison["mean"] - comparison["ff_mean"]
    comparison["std_diff"] = comparison["std"] - comparison["ff_std"]

    return comparison.loc[["Market", "Micro", "Small", "Big", "All but Micro"]]


def main():
    parser = argparse.ArgumentParser(
        description="Check the generalized BM builder against Fama-French 1963-2005 statistics."
    )
    parser.add_argument("--wrds-user", default=WRDS_USER)
    parser.add_argument(
        "--use-imputed-market-equity",
        action="store_true",
        help="Use the builder's forward-filled CRSP price/shareout option.",
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
        link = load_ccm_links(db)
    finally:
        db.close()

    bm = build_book_to_market(comp, december_firm_market_equity(crsp), link)
    bm["portfolio_year"] = pd.to_datetime(bm["datadate"]).dt.year + 1

    june_me = june_firm_market_equity(crsp)
    bm = bm.merge(june_me, on=["permco", "portfolio_year"], how="inner")
    bm = bm[bm["portfolio_year"].between(START_YEAR, END_YEAR)].copy()

    bm = (
        bm.sort_values(
            ["permno", "portfolio_year", "june_market_equity"],
            ascending=[True, True, False],
        )
        .drop_duplicates(["permno", "portfolio_year"], keep="first")
    )
    bm = add_fama_french_size_groups(bm)

    comparison = compare_to_fama_french(bm).round(4)

    print("\nFama-French B/M descriptive-statistics check, 1963-2005")
    print(f"Used imputed CRSP price/shareout: {args.use_imputed_market_equity}")
    print(f"Firm-year observations in check: {len(bm):,}")
    print(comparison)


if __name__ == "__main__":
    main()
