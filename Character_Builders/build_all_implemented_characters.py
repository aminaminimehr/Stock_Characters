import argparse
import os
from pathlib import Path

import numpy as np

from _shared.beta_builder import (
    build_factor_characters,
    clear_factor_caches,
)
from _shared.event_builders import build_abr_character, build_aeavol_character, build_ear_character
from _shared.ms_builder import build_ms_character
from _shared.green_builders import (
    ANNUAL_CHARACTER_INFO,
    DAILY_MONTHLY_CHARACTER_INFO,
    MONTHLY_CHARACTER_INFO,
    add_ccm_arguments,
    attach_permno,
    build_all_monthly_characters,
    clear_monthly_crsp_cache,
    build_monthly_character,
    compute_annual_characters,
    connect_wrds,
    load_annual_age_lookup,
    load_annual_orgcap_lookup,
    load_annual_compustat,
    load_green_ccm_links,
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
from _shared.rvar_factor_builders import RVAR_SPECS, build_factor_rvar, clear_rvar_caches


PROJECT_ROOT = Path(__file__).resolve().parents[1]
import sys

sys.path.insert(0, str(PROJECT_ROOT))
from output_paths import CHARACTER_INDIVIDUAL_DIR, ensure_output_tree  # noqa: E402

OUTPUT_DIR = CHARACTER_INDIVIDUAL_DIR
ANNUAL_ID_COLUMNS = ["permno", "permco", "gvkey", "datadate", "sic", "fyear"]


def build_annual_characters(
    db, output_dir, ccm_linktypes=None, ccm_linkprim=None, skip_existing=False
):
    comp = compute_annual_characters(
        load_annual_compustat(db),
        age_lookup=load_annual_age_lookup(db),
        orgcap_lookup=load_annual_orgcap_lookup(db),
    )
    comp = attach_permno(comp, load_green_ccm_links(db, ccm_linktypes, ccm_linkprim))

    for character in ANNUAL_CHARACTER_INFO:
        if skip_existing and (output_dir / f"{character}.csv").exists():
            print(f"{character}: skipped (already exists)")
            continue
        write_character(comp[ANNUAL_ID_COLUMNS + [character]], character, output_dir)


def build_monthly_characters(db, output_dir, skip_existing=False):
    pending = [
        character
        for character in MONTHLY_CHARACTER_INFO
        if not (skip_existing and (output_dir / f"{character}.csv").exists())
    ]
    if not pending:
        return
    monthly_outputs = build_all_monthly_characters(db, pending)
    for character, out in monthly_outputs.items():
        write_character(out, character, output_dir)


def build_quarterly_characters(
    db,
    output_dir,
    ccm_linktypes=None,
    ccm_linkprim=None,
    skip_ibes=False,
    skip_existing=False,
):
    """Build Green-style quarterly characters."""
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
    workers=None,
):
    factor_names = [
        name
        for name in ("beta", "betasq", "idiovol", "pricedelay")
        if not (skip_existing and (output_dir / f"{name}.csv").exists())
    ]
    if factor_names:
        clear_factor_caches()
        try:
            factor_outputs = build_factor_characters(
                db, output_dir, workers=workers, names=tuple(factor_names)
            )
            for name, out in factor_outputs.items():
                write_character(out, name, output_dir)
        finally:
            clear_factor_caches()

    other_jobs = [
        ("ear", lambda: build_ear_character(db, ccm_linktypes, ccm_linkprim, workers=workers)),
        ("abr", lambda: build_abr_character(db, ccm_linktypes, ccm_linkprim, workers=workers)),
        ("aeavol", lambda: build_aeavol_character(db, ccm_linktypes, ccm_linkprim, workers=workers)),
        ("ms", lambda: build_ms_character(db, ccm_linktypes, ccm_linkprim, use_ibes=not skip_ibes, workers=workers)),
    ]
    if not skip_ibes:
        other_jobs.insert(0, ("re", lambda: build_re_character(db)))

    for name, builder in other_jobs:
        if skip_existing and (output_dir / f"{name}.csv").exists():
            print(f"{name}: skipped (already exists)")
            continue
        write_character(builder(), name, output_dir)

    rvar_pending = [
        name
        for name in RVAR_SPECS
        if not (skip_existing and (output_dir / f"{name}.csv").exists())
    ]
    if rvar_pending:
        clear_rvar_caches()
        for name in rvar_pending:
            write_character(
                build_factor_rvar(db, name, RVAR_SPECS[name], output_dir, workers=workers),
                name,
                output_dir,
            )
        clear_rvar_caches()


def build_daily_monthly_characters(db, output_dir, skip_existing=False, workers=None):
    from _shared.green_builders import load_monthly_alignment_frame

    _ = workers  # daily-monthly uses server-side SQL aggregation (not parallelized)
    daily = load_daily_monthly(db)
    monthly = load_monthly_alignment_frame(output_dir, db=db)

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
    parser.add_argument(
        "--sample-start",
        default=None,
        help="Optional WRDS lower date (YYYY-MM-DD). Also reads STOCK_CHARACTERS_SAMPLE_START.",
    )
    parser.add_argument(
        "--sample-end",
        default=None,
        help="Optional WRDS upper date (YYYY-MM-DD). Also reads STOCK_CHARACTERS_SAMPLE_END.",
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=None,
        help=(
            "Parallel worker count for beta, rvar_capm, rvar_ff3, and abr/ear builders. "
            "Default: STOCK_CHARACTERS_WORKERS env or min(cpu, 8). Use 1 for debugging."
        ),
    )
    args = parser.parse_args()

    if args.sample_start:
        os.environ["STOCK_CHARACTERS_SAMPLE_START"] = args.sample_start
    if args.sample_end:
        os.environ["STOCK_CHARACTERS_SAMPLE_END"] = args.sample_end

    ensure_output_tree()
    output_dir = Path(args.output_dir)
    if not output_dir.is_absolute():
        output_dir = PROJECT_ROOT / output_dir
    output_dir.mkdir(parents=True, exist_ok=True)

    db = connect_wrds(args.wrds_user)
    try:
        clear_monthly_crsp_cache()
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
                    workers=args.workers,
                )
        if args.only_daily or not args.skip_daily:
            build_daily_monthly_characters(
                db, output_dir, skip_existing=args.skip_existing, workers=args.workers
            )
    finally:
        clear_monthly_crsp_cache()
        db.close()


if __name__ == "__main__":
    main()
