import argparse
from pathlib import Path

import numpy as np

from _shared.green_builders import (
    ANNUAL_CHARACTER_INFO,
    DAILY_MONTHLY_CHARACTER_INFO,
    MONTHLY_CHARACTER_INFO,
    add_ccm_arguments,
    attach_permno,
    build_monthly_character,
    compute_annual_characters,
    connect_wrds,
    load_annual_compustat,
    load_ccm_links,
    load_crsp_monthly,
    load_daily_monthly,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = PROJECT_ROOT / "outputs"
ANNUAL_ID_COLUMNS = ["permno", "permco", "gvkey", "datadate", "sic", "fyear"]


def write_character(df, character, output_dir):
    out = df.copy()
    out = out[out[character].replace([np.inf, -np.inf], np.nan).notna()].copy()
    output_path = output_dir / f"{character}.csv"
    out.to_csv(output_path, index=False)
    print(f"{character}: {len(out):,} rows -> {output_path}")


def build_annual_characters(db, output_dir, ccm_linktypes=None, ccm_linkprim=None):
    comp = compute_annual_characters(load_annual_compustat(db))
    comp = attach_permno(comp, load_ccm_links(db, ccm_linktypes, ccm_linkprim))

    for character in ANNUAL_CHARACTER_INFO:
        write_character(comp[ANNUAL_ID_COLUMNS + [character]], character, output_dir)


def build_monthly_characters(db, output_dir):
    for character in MONTHLY_CHARACTER_INFO:
        out = build_monthly_character(db, character)
        write_character(out, character, output_dir)


def build_daily_monthly_characters(db, output_dir):
    daily = load_daily_monthly(db)
    monthly = load_crsp_monthly(db)[
        ["permno", "permco", "date", "signal_yyyymm", "target_yyyymm", "siccd", "exchcd", "shrcd"]
    ].rename(columns={"siccd": "sic"})
    monthly["source_yyyymm"] = monthly.groupby("permno")["signal_yyyymm"].shift(1)

    for character in DAILY_MONTHLY_CHARACTER_INFO:
        out = monthly.merge(
            daily[["permno", "source_yyyymm", character]],
            on=["permno", "source_yyyymm"],
            how="left",
        )
        out = out[
            ["permno", "permco", "date", "signal_yyyymm", "target_yyyymm", "sic", "exchcd", "shrcd", character]
        ]
        write_character(out, character, output_dir)


def main():
    parser = argparse.ArgumentParser(
        description="Build every implemented Green-style character into outputs/."
    )
    parser.add_argument("--wrds-user", default=None)
    parser.add_argument("--output-dir", default=OUTPUT_DIR)
    add_ccm_arguments(parser)
    parser.add_argument(
        "--skip-daily",
        action="store_true",
        help="Skip daily-CRSP based monthly characters, which are slower to query.",
    )
    parser.add_argument(
        "--only-daily",
        action="store_true",
        help="Build only daily-CRSP based monthly characters.",
    )
    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    if not output_dir.is_absolute():
        output_dir = PROJECT_ROOT / output_dir
    output_dir.mkdir(parents=True, exist_ok=True)

    db = connect_wrds(args.wrds_user)
    try:
        if not args.only_daily:
            build_annual_characters(
                db, output_dir, args.ccm_linktypes, args.ccm_linkprim
            )
            build_monthly_characters(db, output_dir)
        if args.only_daily or not args.skip_daily:
            build_daily_monthly_characters(db, output_dir)
    finally:
        db.close()


if __name__ == "__main__":
    main()
