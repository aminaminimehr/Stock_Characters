"""Build the 95-character datashare signal panel from WRDS.

Single entry point: python Character_Panels/run_full_pipeline.py --wrds-user <user>
Optional: --workers for parallel daily-CRSP builders.
"""
import argparse
import subprocess
import sys
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from output_paths import (  # noqa: E402
    CHARACTER_INDIVIDUAL_DIR,
    SIGNAL_PANEL_FILE,
    ensure_output_tree,
    list_character_stems,
)
from pipeline_config import DATASHARE_COLUMNS  # noqa: E402

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
}

# HXZ June annuals built as separate subprocess jobs (bm, operprof).
HXZ_JOBS = [
    ("bm", "Character_Builders/HXZ_BM_Generalized/build_book_to_market.py"),
    ("operprof", "Character_Builders/HXZ_OPE_Generalized/build_operating_profitability.py"),
]

BM_IA_SCRIPT = "Character_Builders/Datashare_BM_IA_Generalized/build_bm_ia.py"


def run(cmd):
    print("\n>>", " ".join(cmd), flush=True)
    subprocess.run(cmd, check=True, cwd=PROJECT_ROOT)


def count_panel_characters(path):
    df = pd.read_csv(path, nrows=0)
    return [c for c in df.columns if c not in PANEL_META]


def build_all_characters(wrds_user, workers=None):
    """Run the bulk Green/shared character builder for all 95 datashare predictors."""
    cmd = [
        PYTHON,
        "Character_Builders/build_all_implemented_characters.py",
        "--wrds-user",
        wrds_user,
        "--output-dir",
        str(CHARACTER_INDIVIDUAL_DIR),
    ]
    if workers is not None:
        cmd.extend(["--workers", str(workers)])
    run(cmd)


def build_hxz_characters(wrds_user, output_dir):
    """Build bm and operprof (HXZ June annuals), then bm_ia."""
    for stem, script in HXZ_JOBS:
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
            ]
        )
    build_bm_ia(output_dir)


def build_bm_ia(output_dir):
    """Build SIC2 x month demeaned bm_ia after bm.csv exists."""
    bm_path = output_dir / "bm.csv"
    out = output_dir / "bm_ia.csv"
    if out.exists():
        print("bm_ia: skipped (already exists)")
        return
    if not bm_path.exists():
        print("bm_ia: skipped (bm.csv missing)")
        return
    run(
        [
            PYTHON,
            BM_IA_SCRIPT,
            "--bm-csv",
            str(bm_path),
            "--output",
            str(out),
        ]
    )


def build_panels():
    """Merge individual character CSVs into the final signal panel."""
    run([PYTHON, "Character_Panels/build_all_character_panel.py"])


def print_summary():
    chars = list_character_stems()
    signal_cols = count_panel_characters(SIGNAL_PANEL_FILE)
    print("\n=== Pipeline summary ===")
    print(f"Individual character CSV files: {len(chars)}")
    print(f"Signal panel: {SIGNAL_PANEL_FILE}")
    print(f"all_character_signal_panel predictors: {len(signal_cols)} (expected {len(DATASHARE_COLUMNS)})")
    print("\nPredictor columns in monthly signal panel:")
    print(", ".join(signal_cols))


def main():
    parser = argparse.ArgumentParser(
        description="Build the 95-character datashare signal panel from WRDS."
    )
    parser.add_argument("--wrds-user", required=True, help="WRDS PostgreSQL username.")
    parser.add_argument(
        "--skip-build",
        action="store_true",
        help="Only rebuild the panel from existing character CSVs.",
    )
    parser.add_argument("--workers", type=int, default=None, help="Parallel workers for daily-CRSP builders.")
    args = parser.parse_args()

    ensure_output_tree()

    if not args.skip_build:
        build_all_characters(args.wrds_user, workers=args.workers)
        build_hxz_characters(args.wrds_user, CHARACTER_INDIVIDUAL_DIR)

    build_panels()
    print_summary()


if __name__ == "__main__":
    main()
