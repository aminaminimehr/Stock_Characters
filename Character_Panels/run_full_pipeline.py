"""Run character builds (resume-friendly) and rebuild monthly panels."""
import argparse
import subprocess
import sys
from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = PROJECT_ROOT / "outputs"
PYTHON = sys.executable

NON_CHARACTER_FILES = {
    "all_character_signal_panel",
    "annual_character_panel",
    "complete_all_character_prediction_panel",
    "complete_prediction_panel",
    "complete_prediction_panel_imputed",
    "excess_returns",
    "green_comparable_temp",
    "green_comparable_temp2_winsorized",
    "green_comparable_validation_summary",
    "green_comparable_winsorized_validation_summary",
    "green_comparable_winsorized_validation_summary_fresh",
    "green_missing_character_inventory",
    "monthly_character_panel",
    "research_panel_1957_ranked",
}

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


def list_character_csvs():
    return sorted(
        p.stem
        for p in OUTPUT_DIR.glob("*.csv")
        if p.stem not in NON_CHARACTER_FILES
    )


def count_panel_characters(path):
    df = pd.read_csv(path, nrows=0)
    return [c for c in df.columns if c not in PANEL_META]


def build_all_characters(wrds_user, skip_ibes=False, resume=False):
    cmd = [
        PYTHON,
        "Character_Builders/build_all_implemented_characters.py",
        "--wrds-user",
        wrds_user,
    ]
    if skip_ibes:
        cmd.append("--skip-ibes")
    if resume:
        cmd.extend(["--skip-existing", "--skip-annual-monthly"])
    run(cmd)


def build_hxz_characters(wrds_user):
    for stem, script, extra in HXZ_JOBS:
        out = OUTPUT_DIR / f"{stem}.csv"
        if out.exists():
            print(f"{stem}: skipped (already exists)")
            continue
        run([PYTHON, script, "--wrds-user", wrds_user, *extra])


def build_excess_returns(wrds_user):
    if (OUTPUT_DIR / "excess_returns.csv").exists():
        print("excess_returns: skipped (already exists)")
        return
    run([PYTHON, "Return_Builders/build_excess_returns.py", "--wrds-user", wrds_user])


def build_panels():
    run([PYTHON, "Character_Panels/build_all_character_panel.py"])
    run(
        [
            PYTHON,
            "Character_Panels/build_complete_prediction_panel.py",
            "--characters",
            "outputs/all_character_signal_panel.csv",
            "--returns",
            "outputs/excess_returns.csv",
            "--output",
            "outputs/complete_all_character_prediction_panel.csv",
        ]
    )
    run([PYTHON, "Character_Panels/build_research_panel_1957.py"])


def print_summary():
    chars = list_character_csvs()
    signal_cols = count_panel_characters(OUTPUT_DIR / "all_character_signal_panel.csv")
    pred_cols = count_panel_characters(
        OUTPUT_DIR / "complete_all_character_prediction_panel.csv"
    )
    research_cols = count_panel_characters(OUTPUT_DIR / "research_panel_1957_ranked.csv")

    print("\n=== Pipeline summary ===")
    print(f"Individual character CSV files: {len(chars)}")
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
        help="Only rebuild panels from existing character CSVs in outputs/.",
    )
    parser.add_argument(
        "--skip-ibes",
        action="store_true",
        help="Skip IBES tables (no re; sue uses Compustat-only surprise).",
    )
    parser.add_argument(
        "--resume",
        action="store_true",
        help=(
            "Resume a partial build: skip existing character CSVs and skip the "
            "annual/monthly block in build_all_implemented_characters.py."
        ),
    )
    args = parser.parse_args()

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    if not args.skip_build:
        build_all_characters(args.wrds_user, skip_ibes=args.skip_ibes, resume=args.resume)
        build_hxz_characters(args.wrds_user)
        build_excess_returns(args.wrds_user)

    build_panels()
    print_summary()


if __name__ == "__main__":
    main()
