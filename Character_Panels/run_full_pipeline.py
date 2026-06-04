"""Run character builds (resume-friendly) and rebuild monthly panels."""
import argparse
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


def run(cmd):
    print("\n>>", " ".join(cmd), flush=True)
    subprocess.run(cmd, check=True, cwd=PROJECT_ROOT)


def count_panel_characters(path):
    df = pd.read_csv(path, nrows=0)
    return [c for c in df.columns if c not in PANEL_META]


def build_all_characters(wrds_user, skip_ibes=False, resume=False, sample_start=None, sample_end=None):
    cmd = [
        PYTHON,
        "Character_Builders/build_all_implemented_characters.py",
        "--wrds-user",
        wrds_user,
        "--output-dir",
        str(CHARACTER_INDIVIDUAL_DIR),
    ]
    if skip_ibes:
        cmd.append("--skip-ibes")
    if resume:
        cmd.extend(["--skip-existing", "--skip-annual-monthly"])
    if sample_start:
        cmd.extend(["--sample-start", sample_start])
    if sample_end:
        cmd.extend(["--sample-end", sample_end])
    run(cmd)


def build_hxz_characters(wrds_user, output_dir):
    for stem, script, extra in HXZ_JOBS:
        out = output_dir / f"{stem}.csv"
        if out.exists():
            print(f"{stem}: skipped (already exists)")
            continue
        run(
            [
                PYTHON,
                script,
                "--wrds-user",
                wrds_user,
                "--output",
                str(out),
                *extra,
            ]
        )


def build_excess_returns(wrds_user, sample_start=None, sample_end=None):
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
    if sample_start:
        cmd.extend(["--sample-start", sample_start])
    if sample_end:
        cmd.extend(["--sample-end", sample_end])
    run(cmd)


def build_panels():
    run(
        [
            PYTHON,
            "Character_Panels/build_all_character_panel.py",
            "--input-dir",
            str(CHARACTER_INDIVIDUAL_DIR),
            "--output",
            str(SIGNAL_PANEL_FILE),
        ]
    )
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


def print_summary():
    chars = list_character_stems()
    signal_cols = count_panel_characters(SIGNAL_PANEL_FILE)
    pred_cols = count_panel_characters(COMPLETE_ALL_PANEL_FILE)
    research_cols = count_panel_characters(RESEARCH_PANEL_FILE)

    print("\n=== Pipeline summary ===")
    print(f"Individual character CSV files: {len(chars)}")
    print(f"Signal panel: {SIGNAL_PANEL_FILE}")
    print(f"Complete panel: {COMPLETE_ALL_PANEL_FILE}")
    print(f"all_character_signal_panel predictors: {len(signal_cols)}")
    print(f"complete_all_character_prediction_panel predictors: {len(pred_cols)}")
    print(f"research_panel_1957_ranked predictors: {len(research_cols)}")
    print("\nPredictor columns in monthly signal panel:")
    print(", ".join(signal_cols))


def main():
    parser = argparse.ArgumentParser(
        description=(
            "Build all implemented characters from WRDS, then merge monthly panels. "
            "Run from the repository root."
        )
    )
    parser.add_argument("--wrds-user", required=True, help="WRDS PostgreSQL username.")
    parser.add_argument(
        "--skip-build",
        action="store_true",
        help="Only rebuild panels from existing character CSVs.",
    )
    parser.add_argument(
        "--skip-ibes",
        action="store_true",
        help="Skip IBES tables (no re; sue uses Compustat-only surprise).",
    )
    parser.add_argument(
        "--resume",
        action="store_true",
        help="Resume a partial build with --skip-existing.",
    )
    parser.add_argument(
        "--sample-start",
        default=None,
        help="Optional WRDS lower date bound (YYYY-MM-DD) for validation runs.",
    )
    parser.add_argument(
        "--sample-end",
        default=None,
        help="Optional WRDS upper date bound (YYYY-MM-DD) for validation runs.",
    )
    args = parser.parse_args()

    ensure_output_tree()

    if not args.skip_build:
        build_all_characters(
            args.wrds_user,
            skip_ibes=args.skip_ibes,
            resume=args.resume,
            sample_start=args.sample_start,
            sample_end=args.sample_end,
        )
        build_hxz_characters(args.wrds_user, CHARACTER_INDIVIDUAL_DIR)
        build_excess_returns(
            args.wrds_user,
            sample_start=args.sample_start,
            sample_end=args.sample_end,
        )

    build_panels()
    print_summary()


if __name__ == "__main__":
    main()
