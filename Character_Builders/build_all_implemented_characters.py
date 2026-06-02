import argparse
from pathlib import Path

import numpy as np

from _shared.beta_builder import build_beta_character
from _shared.event_builders import build_abr_character
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
    write_character,
)
from _shared.ibes_builders import build_re_character
from _shared.quarterly_builders import (
    QUARTERLY_CHARACTER_INFO,
    build_quarterly_character,
    prepare_quarterly_compustat_panel,
)
from _shared.rvar_factor_builders import build_factor_rvar


PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = PROJECT_ROOT / "outputs"
ANNUAL_ID_COLUMNS = ["permno", "permco", "gvkey", "datadate", "sic", "fyear"]


def build_annual_characters(
    db, output_dir, ccm_linktypes=None, ccm_linkprim=None, skip_existing=False
):
    comp = compute_annual_characters(load_annual_compustat(db))
    comp = attach_permno(comp, load_ccm_links(db, ccm_linktypes, ccm_linkprim))

    for character in ANNUAL_CHARACTER_INFO:
        if skip_existing and (output_dir / f"{character}.csv").exists():
            print(f"{character}: skipped (already exists)")
            continue
        write_character(comp[ANNUAL_ID_COLUMNS + [character]], character, output_dir)


def build_monthly_characters(db, output_dir, skip_existing=False):
    for character in MONTHLY_CHARACTER_INFO:
        if skip_existing and (output_dir / f"{character}.csv").exists():
            print(f"{character}: skipped (already exists)")
            continue
        out = build_monthly_character(db, character)
        write_character(out, character, output_dir)


def build_quarterly_characters(
    db,
    output_dir,
    ccm_linktypes=None,
    ccm_linkprim=None,
    skip_ibes=False,
    skip_existing=False,
):
    quarterly_chars = [
        character
        for character in QUARTERLY_CHARACTER_INFO
        if not (skip_existing and (output_dir / f"{character}.csv").exists())
    ]
    if quarterly_chars:
        print("Loading quarterly Compustat panel once for all quarterly characters...")
        quarterly_comp = prepare_quarterly_compustat_panel(
            db, ccm_linktypes, ccm_linkprim, use_ibes=not skip_ibes
        )
        for character in quarterly_chars:
            out = build_quarterly_character(
                db,
                character,
                ccm_linktypes,
                ccm_linkprim,
                use_ibes=not skip_ibes,
                comp=quarterly_comp,
            )
            write_character(out, character, output_dir)


def build_special_characters(
    db,
    output_dir,
    ccm_linktypes=None,
    ccm_linkprim=None,
    skip_ibes=False,
    skip_existing=False,
):
    special_jobs = [
        ("beta", lambda: build_beta_character(db)),
        ("abr", lambda: build_abr_character(db, ccm_linktypes, ccm_linkprim)),
        ("rvar_capm", lambda: build_factor_rvar(db, "rvar_capm", ["mktrf"])),
        (
            "rvar_ff3",
            lambda: build_factor_rvar(db, "rvar_ff3", ["mktrf", "smb", "hml"]),
        ),
    ]
    if not skip_ibes:
        special_jobs.insert(2, ("re", lambda: build_re_character(db)))

    for name, builder in special_jobs:
        if skip_existing and (output_dir / f"{name}.csv").exists():
            print(f"{name}: skipped (already exists)")
            continue
        write_character(builder(), name, output_dir)


def build_daily_monthly_characters(db, output_dir, skip_existing=False):
    daily = load_daily_monthly(db)
    monthly = load_crsp_monthly(db)[
        ["permno", "permco", "date", "signal_yyyymm", "target_yyyymm", "siccd", "exchcd", "shrcd"]
    ].rename(columns={"siccd": "sic"})
    monthly["source_yyyymm"] = monthly.groupby("permno")["signal_yyyymm"].shift(1)

    for character in DAILY_MONTHLY_CHARACTER_INFO:
        if skip_existing and (output_dir / f"{character}.csv").exists():
            print(f"{character}: skipped (already exists)")
            continue
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
    parser.add_argument(
        "--skip-special",
        action="store_true",
        help="Skip beta, abr, re, and residual-variance characters.",
    )
    parser.add_argument(
        "--skip-annual-monthly",
        action="store_true",
        help="Skip annual and monthly blocks (use after a partial run that already wrote those CSVs).",
    )
    parser.add_argument(
        "--skip-ibes",
        action="store_true",
        help="Skip IBES tables (no re; sue uses Compustat-only surprise).",
    )
    parser.add_argument(
        "--skip-existing",
        action="store_true",
        help="Skip characters whose CSV already exists in the output directory.",
    )
    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    if not output_dir.is_absolute():
        output_dir = PROJECT_ROOT / output_dir
    output_dir.mkdir(parents=True, exist_ok=True)

    db = connect_wrds(args.wrds_user)
    try:
        if not args.only_daily:
            if not args.skip_annual_monthly:
                build_annual_characters(
                    db,
                    output_dir,
                    args.ccm_linktypes,
                    args.ccm_linkprim,
                    skip_existing=args.skip_existing,
                )
                build_monthly_characters(
                    db, output_dir, skip_existing=args.skip_existing
                )
            build_quarterly_characters(
                db,
                output_dir,
                args.ccm_linktypes,
                args.ccm_linkprim,
                skip_ibes=args.skip_ibes,
                skip_existing=args.skip_existing,
            )
            if not args.skip_special:
                build_special_characters(
                    db,
                    output_dir,
                    args.ccm_linktypes,
                    args.ccm_linkprim,
                    skip_ibes=args.skip_ibes,
                    skip_existing=args.skip_existing,
                )
        if args.only_daily or not args.skip_daily:
            build_daily_monthly_characters(
                db, output_dir, skip_existing=args.skip_existing
            )
    finally:
        db.close()


if __name__ == "__main__":
    main()
