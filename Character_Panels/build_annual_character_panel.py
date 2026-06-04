import argparse
import sys
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from output_paths import (  # noqa: E402
    LEGACY_ANNUAL_PANEL_FILE,
    character_csv_path,
    resolve_legacy_panel_path,
)

INPUT_STEMS = (
    "book_to_market",
    "book_to_june_market_equity",
    "operating_profitability",
    "cash_flow_to_price",
)
INPUT_FILES = {stem: character_csv_path(stem) for stem in INPUT_STEMS}
OUTPUT_FILE = LEGACY_ANNUAL_PANEL_FILE
MERGE_KEYS = ["permno", "permco", "gvkey", "datadate", "sic", "fyear"]


def require_input_files(input_files=INPUT_FILES):
    missing = [path for path in input_files.values() if not path.exists()]
    if not missing:
        return

    missing_text = "\n".join(f"- {path}" for path in missing)
    raise FileNotFoundError(
        "Missing individual character files.\n\n"
        "Run the individual character builders first:\n\n"
        "python Character_Builders/HXZ_BM_Generalized/build_book_to_market.py --wrds-user YOUR_WRDS_USERNAME\n"
        "python Character_Builders/HXZ_BMJ_Generalized/build_book_to_june_market_equity.py --wrds-user YOUR_WRDS_USERNAME\n"
        "python Character_Builders/HXZ_OPE_Generalized/build_operating_profitability.py --wrds-user YOUR_WRDS_USERNAME\n"
        "python Character_Builders/HXZ_CFP_Generalized/build_cash_flow_to_price.py --wrds-user YOUR_WRDS_USERNAME --use-imputed-market-equity\n\n"
        f"Missing files:\n{missing_text}"
    )


def load_individual_characters(input_files=INPUT_FILES):
    require_input_files(input_files)

    bm = pd.read_csv(input_files["book_to_market"], parse_dates=["datadate"])
    bmj = pd.read_csv(
        input_files["book_to_june_market_equity"],
        parse_dates=["datadate"],
        usecols=MERGE_KEYS + ["bmj"],
    )
    ope = pd.read_csv(input_files["operating_profitability"], parse_dates=["datadate"])
    cfp = pd.read_csv(input_files["cash_flow_to_price"], parse_dates=["datadate"])

    return bm, bmj, ope, cfp


def build_annual_character_panel(bm, bmj, ope, cfp):
    return (
        bm.merge(bmj, on=MERGE_KEYS, how="inner")
        .merge(ope, on=MERGE_KEYS, how="inner")
        .merge(cfp, on=MERGE_KEYS, how="inner")
    )


def main():
    parser = argparse.ArgumentParser(
        description=(
            "DEPRECATED narrow HXZ annual panel. Use run_full_pipeline.py for the "
            "full all-character workflow."
        )
    )
    parser.add_argument(
        "--allow-legacy",
        action="store_true",
        help="Allow building the deprecated annual_character_panel.csv under panels/legacy/.",
    )
    parser.add_argument("--output", default=str(OUTPUT_FILE))
    args = parser.parse_args()

    if not args.allow_legacy:
        raise SystemExit(
            "build_annual_character_panel.py is deprecated.\n"
            "Use: python Character_Panels/run_full_pipeline.py --wrds-user YOUR_WRDS_USERNAME --skip-ibes\n"
            "If you truly need the old HXZ-only panel, rerun with --allow-legacy."
        )

    bm, bmj, ope, cfp = load_individual_characters()
    annual_panel = build_annual_character_panel(bm, bmj, ope, cfp)

    output_path = resolve_legacy_panel_path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    annual_panel.to_csv(output_path, index=False)

    print(f"Saved annual character panel to: {output_path.resolve()}")
    print(f"B/M rows: {len(bm):,}")
    print(f"BMJ rows: {len(bmj):,}")
    print(f"OPE rows: {len(ope):,}")
    print(f"CFP rows: {len(cfp):,}")
    print(f"Combined rows: {len(annual_panel):,}")


if __name__ == "__main__":
    main()
