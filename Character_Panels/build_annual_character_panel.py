import argparse
from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = PROJECT_ROOT / "outputs"
INPUT_FILES = {
    "book_to_market": OUTPUT_DIR / "book_to_market.csv",
    "book_to_june_market_equity": OUTPUT_DIR / "book_to_june_market_equity.csv",
    "operating_profitability": OUTPUT_DIR / "operating_profitability.csv",
    "cash_flow_to_price": OUTPUT_DIR / "cash_flow_to_price.csv",
}
OUTPUT_FILE = OUTPUT_DIR / "annual_character_panel.csv"
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
        help="Allow building the deprecated annual_character_panel.csv.",
    )
    parser.add_argument("--output", default=OUTPUT_FILE)
    args = parser.parse_args()

    if not args.allow_legacy:
        raise SystemExit(
            "build_annual_character_panel.py is deprecated.\n"
            "Use: python Character_Panels/run_full_pipeline.py --wrds-user YOUR_WRDS_USERNAME --skip-ibes\n"
            "If you truly need the old HXZ-only panel, rerun with --allow-legacy."
        )

    bm, bmj, ope, cfp = load_individual_characters()
    annual_panel = build_annual_character_panel(bm, bmj, ope, cfp)

    output_path = Path(args.output)
    if not output_path.is_absolute():
        output_path = PROJECT_ROOT / output_path
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
