"""TEMPORARY standalone book_to_market builder with corrected (July) signal-month alignment.
Identical to HXZ_BM_Generalized/build_book_to_market.py for the Compustat /
CRSP / CCM loading and the bm ratio, but June-expands with a JULY start (one
month later than the repo's June start) so the emitted signal_yyyymm matches
datashare's DATE (see docs/gkx/panel_gkx_datashare_full_comparison.md: bm
aligns to `target`, i.e. datashare DATE = repo signal_yyyymm + 1).
Output is a MONTHLY-NATIVE book_to_market.csv (carries signal_yyyymm /
target_yyyymm), so build_all_character_panel.py takes it as-is and does
NOT re-expand it. Dropping this file into outputs/characteristics/individual/
OVERRIDES the annual book_to_market.csv. Not wired into run_full_pipeline;
run directly. Untracked for now.
"""
import argparse
import sys
from pathlib import Path
import numpy as np
import pandas as pd
import wrds
PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "Character_Builders"))
from _shared.ccm import add_ccm_arguments, attach_ccm_links, load_ccm_links
from output_paths import crsp_universe_filter, read_wrds_sql, resolve_output_path
# Reuse the HXZ builder's data loaders and bm-ratio logic verbatim.
from Character_Builders.HXZ_BM_Generalized.build_book_to_market import (
    load_compustat,
    load_crsp_monthly,
    december_firm_market_equity,
    build_book_to_market,
)
ANNUAL_ID_COLUMNS = ["permno", "permco", "gvkey", "datadate", "sic", "fyear"]
MONTHLY_KEYS = ["permno", "signal_yyyymm", "target_yyyymm"]
def add_one_month(yyyymm: int) -> int:
    year, month = yyyymm // 100, yyyymm % 100
    next_month = month + 1
    next_year = year + (next_month == 13)
    next_month = 1 if next_month == 13 else next_month
    return next_year * 100 + next_month
def expand_annual_file_july(df, character_columns):
    """HXZ June availability shifted +1 month: FY ending calendar year y -> Jul y+1 .. Jun y+2.
    This is the ONLY change vs expand_annual_file_june (timing.py): the first
    signal month is July (index +6) instead of June (index +5). Everything
    else is identical, so the 12-month window and the latest-datadate dedup are preserved.
    """
    df = df.copy()
    df["datadate"] = pd.to_datetime(df["datadate"])
    availability_year = df["datadate"].dt.year + 1
    repeated = df.loc[df.index.repeat(12), list(ANNUAL_ID_COLUMNS) + list(character_columns)].copy()
    month_offsets = np.tile(np.arange(12), len(df))
    first_signal_month = availability_year.to_numpy().repeat(12) * 12 + 6  # July (was +5 = June)
    month_index = first_signal_month + month_offsets
    repeated["signal_yyyymm"] = (month_index // 12) * 100 + (month_index % 12 + 1)
    repeated["target_yyyymm"] = repeated["signal_yyyymm"].map(add_one_month)
    repeated = (
        repeated.sort_values(["permno", "signal_yyyymm", "datadate"])
        .drop_duplicates(["permno", "signal_yyyymm"], keep="last")
    )
    keep = MONTHLY_KEYS + ["permco", "gvkey", "sic"] + list(character_columns)
    return repeated[keep]
def main():
    parser = argparse.ArgumentParser(
        description="Build book_to_market with July signal-month alignment (temp alignment fix)."
    )
    parser.add_argument("--wrds-user", default=None)
    parser.add_argument("--output", default="book_to_market.csv")
    add_ccm_arguments(parser)
    parser.add_argument(
        "--use-imputed-market-equity",
        action="store_true",
        help="Forward-fill CRSP price/shrout within permno before December ME.",
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
    bm = build_book_to_market(comp, december_firm_market_equity(crsp), link)
    # The fix: expand with July start instead of June start.
    monthly = expand_annual_file_july(bm, ["book_to_market"])
    output_path = resolve_output_path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    monthly.to_csv(output_path, index=False)
    print(f"Saved (July-aligned) book_to_market to: {output_path.resolve()}")
    print(f"Rows: {len(monthly):,}  permnos: {monthly['permno'].nunique():,}")
    print("signal_yyyymm is July-start (one month later than the repo default June start).")
if __name__ == "__main__":
    main()