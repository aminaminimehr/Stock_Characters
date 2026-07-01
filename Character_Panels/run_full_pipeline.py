"""Run character builds (resume-friendly) and rebuild monthly panels."""
import argparse
import os
import subprocess
import sys
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from output_paths import (  # noqa: E402
    CHARACTER_INDIVIDUAL_DIR,
    COMPLETE_ALL_PANEL_FILE,
    EXCESS_RETURNS_FILE,
    PIPELINE_LOG_FILE,
    RESEARCH_PANEL_FILE,
    SIGNAL_PANEL_FILE,
    character_csv_path,
    ensure_output_tree,
    iter_character_csv_paths,
    list_character_stems,
)
from pipeline_config import profile_help, resolve_config  # noqa: E402

PYTHON = sys.executable

PANEL_META = {
    "permno",
    "permco",
    "gvkey",
    "date",
    "datadate",
    "source_date",
    "source_yyyymm",
    "signal_yyyymm",
    "target_yyyymm",
    "yyyymm",
    "sic",
    "exchcd",
    "shrcd",
    "fyear",
    "availability_date",
    "calendar_year",
    "excess_return",
    "ffi49",
}

HXZ_JOBS = [
    ("book_to_market", "Character_Builders/HXZ_BM_Generalized/build_book_to_market.py", []),
    (
        "book_to_june_market_equity",
        "Character_Builders/HXZ_BMJ_Generalized/build_book_to_june_market_equity.py",
        [],
    ),
    (
        "operating_profitability",
        "Character_Builders/HXZ_OPE_Generalized/build_operating_profitability.py",
        [],
    ),
    (
        "cash_flow_to_price",
        "Character_Builders/HXZ_CFP_Generalized/build_cash_flow_to_price.py",
        ["--use-imputed-market-equity"],
    ),
]

# Datashare mapping: only these HXZ/Green columns are required for datashare profile.
DATASHARE_HXZ_STEMS = {"book_to_market", "operating_profitability"}


def run(cmd):
    print("\n>>", " ".join(cmd), flush=True)
    subprocess.run(cmd, check=True, cwd=PROJECT_ROOT)


def count_panel_characters(path):
    df = pd.read_csv(path, nrows=0)
    return [c for c in df.columns if c not in PANEL_META]


def build_all_characters(
    wrds_user,
    cfg,
    skip_ibes=False,
    resume=False,
    workers=None,
):
    cmd = [
        PYTHON,
        "Character_Builders/build_all_implemented_characters.py",
        "--wrds-user",
        wrds_user,
        "--output-dir",
        str(CHARACTER_INDIVIDUAL_DIR),
    ]
    if cfg.green_ccm_linktypes:
        cmd.extend(["--ccm-linktypes", cfg.green_ccm_linktypes])
    if cfg.green_ccm_linkprim:
        cmd.extend(["--ccm-linkprim", cfg.green_ccm_linkprim])
    if skip_ibes:
        cmd.append("--skip-ibes")
    if resume:
        cmd.extend(["--skip-existing", "--skip-annual-monthly"])
    if cfg.sample_start:
        cmd.extend(["--sample-start", cfg.sample_start])
    if cfg.sample_end:
        cmd.extend(["--sample-end", cfg.sample_end])
    if cfg.skip_special:
        cmd.append("--skip-special")
    if cfg.skip_daily:
        cmd.append("--skip-daily")
    if workers is not None:
        cmd.extend(["--workers", str(workers)])
    run(cmd)


def build_hxz_characters(wrds_user, output_dir, cfg, profile="green"):
    jobs = HXZ_JOBS

    for stem, script, extra in jobs:
        out = output_dir / f"{stem}.csv"
        if out.exists():
            print(f"{stem}: skipped (already exists)")
            continue
        cmd = [
            PYTHON,
            script,
            "--wrds-user",
            wrds_user,
            "--output",
            str(out),
            "--ccm-linktypes",
            cfg.hxz_ccm_linktypes,
        ]
        if cfg.hxz_ccm_linkprim:
            cmd.extend(["--ccm-linkprim", cfg.hxz_ccm_linkprim])
        cmd.extend(extra)
        run(cmd)


def build_excess_returns(wrds_user, cfg):
    if EXCESS_RETURNS_FILE.exists():
        print("excess_returns: skipped (already exists)")
        return
    cmd = [
        PYTHON,
        "Return_Builders/build_excess_returns.py",
        "--wrds-user",
        wrds_user,
        "--output",
        str(EXCESS_RETURNS_FILE),
    ]
    if cfg.sample_start:
        cmd.extend(["--sample-start", cfg.sample_start])
    if cfg.sample_end:
        cmd.extend(["--sample-end", cfg.sample_end])
    run(cmd)


def build_panels(cfg):
    signal_cmd = [
        PYTHON,
        "Character_Panels/build_all_character_panel.py",
        "--input-dir",
        str(CHARACTER_INDIVIDUAL_DIR),
        "--output",
        str(SIGNAL_PANEL_FILE),
    ]
    if cfg.green_universe:
        signal_cmd.append("--green-universe")
    if cfg.green_winsor:
        signal_cmd.append("--green-winsor")
    run(signal_cmd)

    if not cfg.build_research_panel:
        print("Skipping prediction/research panels (profile setting).")
        return

    run(
        [
            PYTHON,
            "Character_Panels/build_complete_prediction_panel.py",
            "--characters",
            str(SIGNAL_PANEL_FILE),
            "--returns",
            str(EXCESS_RETURNS_FILE),
            "--output",
            str(COMPLETE_ALL_PANEL_FILE),
        ]
    )
    run(
        [
            PYTHON,
            "Character_Panels/build_research_panel_1957.py",
            "--input",
            str(COMPLETE_ALL_PANEL_FILE),
            "--output",
            str(RESEARCH_PANEL_FILE),
        ]
    )


def print_summary(cfg):
    chars = list_character_stems()
    signal_cols = count_panel_characters(SIGNAL_PANEL_FILE)
    print("\n=== Pipeline summary ===")
    print(f"Profile: {cfg.profile}")
    print(f"Individual character CSV files: {len(chars)}")
    print(f"Signal panel: {SIGNAL_PANEL_FILE}")
    if cfg.build_research_panel:
        pred_cols = count_panel_characters(COMPLETE_ALL_PANEL_FILE)
        research_cols = count_panel_characters(RESEARCH_PANEL_FILE)
        print(f"Complete panel: {COMPLETE_ALL_PANEL_FILE}")
        print(f"Research panel: {RESEARCH_PANEL_FILE}")
        print(f"complete_all_character_prediction_panel predictors: {len(pred_cols)}")
        print(f"research_panel_1957_ranked predictors: {len(research_cols)}")
    print(f"all_character_signal_panel predictors: {len(signal_cols)}")
    if cfg.profile == "datashare":
        print("\nDatashare column mapping (bm_ia out of scope):")
        print("  bm -> book_to_market")
        print("  operprof -> operating_profitability")
        print("  cfp -> cfp (Green builder)")
    print("\nPredictor columns in monthly signal panel:")
    print(", ".join(signal_cols))


def main():
    parser = argparse.ArgumentParser(
        description=(
            "Build all implemented characters from WRDS, then merge monthly panels. "
            "Run from the repository root.\n\n"
            + profile_help()
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--wrds-user", required=True, help="WRDS PostgreSQL username.")
    parser.add_argument(
        "--profile",
        choices=("green", "datashare", "research"),
        default=None,
        help="Pipeline preset (overridden by STOCK_CHARACTERS_PROFILE env). Default: green.",
    )
    parser.add_argument(
        "--skip-build",
        action="store_true",
        help="Only rebuild panels from existing character CSVs.",
    )
    parser.add_argument(
        "--skip-ibes",
        action="store_true",
        help="Skip IBES tables (no re; sue uses Compustat-only surprise). Default: skip IBES.",
    )
    parser.add_argument(
        "--resume",
        action="store_true",
        help="Resume a partial build with --skip-existing.",
    )
    parser.add_argument("--sample-start", default=None, help="Override profile sample start (YYYY-MM-DD).")
    parser.add_argument("--sample-end", default=None, help="Override profile sample end (YYYY-MM-DD).")
    parser.add_argument("--workers", type=int, default=None)
    parser.add_argument(
        "--green-universe",
        action="store_true",
        default=None,
        help="Apply Green final sample screen (bm, mom1m, mve non-missing).",
    )
    parser.add_argument(
        "--no-green-universe",
        action="store_false",
        dest="green_universe",
        help="Disable Green universe screen even if profile would enable it.",
    )
    parser.add_argument(
        "--green-winsor",
        action="store_true",
        default=None,
        help="Apply Green SAS monthly winsorization to the signal panel.",
    )
    parser.add_argument(
        "--no-green-winsor",
        action="store_false",
        dest="green_winsor",
        help="Disable Green monthly winsorization even if profile would enable it.",
    )
    parser.add_argument("--ccm-linktypes", default=None, help="Override CCM linktypes for Green + HXZ builders.")
    parser.add_argument("--ccm-linkprim", default=None, help="Override CCM linkprim for HXZ builders.")
    parser.add_argument(
        "--skip-special",
        action="store_true",
        help="Skip beta/rvar/ear/ms and other special builders (debug only).",
    )
    parser.add_argument(
        "--skip-daily",
        action="store_true",
        help="Skip daily-CRSP monthly characters (debug only).",
    )
    args = parser.parse_args()

    cfg = resolve_config(
        args.profile,
        sample_start=args.sample_start,
        sample_end=args.sample_end,
        green_universe=args.green_universe,
        green_winsor=args.green_winsor,
        skip_ibes=True if args.skip_ibes else None,
        skip_special=True if args.skip_special else None,
        skip_daily=True if args.skip_daily else None,
        ccm_linktypes=args.ccm_linktypes,
        ccm_linkprim=args.ccm_linkprim,
    )
    cfg.apply_env()

    ensure_output_tree()
    print(f"Using profile: {cfg.profile}", flush=True)
    if cfg.sample_start:
        print(f"Sample start: {cfg.sample_start}", flush=True)

    if not args.skip_build:
        build_all_characters(
            args.wrds_user,
            cfg,
            skip_ibes=cfg.skip_ibes,
            resume=args.resume,
            workers=args.workers,
        )
        if cfg.build_hxz:
            build_hxz_characters(args.wrds_user, CHARACTER_INDIVIDUAL_DIR, cfg, profile=cfg.profile)
        build_excess_returns(args.wrds_user, cfg)

    build_panels(cfg)
    print_summary(cfg)


if __name__ == "__main__":
    main()
