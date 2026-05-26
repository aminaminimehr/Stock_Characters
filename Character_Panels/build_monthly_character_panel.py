import argparse
from pathlib import Path

import numpy as np
import pandas as pd

try:
    from .build_annual_character_panel import (
        OUTPUT_FILE as ANNUAL_OUTPUT_FILE,
        PROJECT_ROOT,
        build_annual_character_panel,
        load_individual_characters,
    )
except ImportError:
    from build_annual_character_panel import (
        OUTPUT_FILE as ANNUAL_OUTPUT_FILE,
        PROJECT_ROOT,
        build_annual_character_panel,
        load_individual_characters,
    )


OUTPUT_FILE = PROJECT_ROOT / "outputs" / "monthly_character_panel.csv"
MVEL1_FILE = PROJECT_ROOT / "outputs" / "mvel1.csv"


def add_one_month(yyyymm):
    year = yyyymm // 100
    month = yyyymm % 100
    next_month = month + 1
    next_year = year + (next_month == 13)
    next_month = 1 if next_month == 13 else next_month
    return next_year * 100 + next_month


def require_mvel1_file():
    if MVEL1_FILE.exists():
        return

    raise FileNotFoundError(
        "Missing monthly mvel1 character file.\n\n"
        "Run the mvel1 builder first:\n\n"
        "python Character_Builders/Green_MVEL1_Generalized/build_mvel1.py --wrds-user YOUR_WRDS_USERNAME\n\n"
        f"Missing file:\n- {MVEL1_FILE}"
    )


def expand_to_monthly_prediction_panel(annual_chars):
    # A fiscal year ending in calendar year y is known for prediction at the
    # end of June y+1. We therefore label the predictor month as June y+1
    # through May y+2 and carry target_yyyymm as the next month's return month.
    monthly = annual_chars.copy()
    monthly["datadate"] = pd.to_datetime(monthly["datadate"])
    monthly["availability_year"] = monthly["datadate"].dt.year + 1
    monthly["availability_date"] = pd.to_datetime(
        monthly["availability_year"].astype(str) + "-06-30"
    )

    monthly = monthly.loc[monthly.index.repeat(12)].copy()
    month_offsets = np.tile(np.arange(12), len(annual_chars))

    first_signal_month = monthly["availability_year"].to_numpy() * 12 + 5
    month_index = first_signal_month + month_offsets
    monthly["signal_yyyymm"] = (month_index // 12) * 100 + (month_index % 12 + 1)
    monthly["target_yyyymm"] = monthly["signal_yyyymm"].map(add_one_month)

    return monthly[
        [
            "permno",
            "permco",
            "gvkey",
            "datadate",
            "availability_date",
            "signal_yyyymm",
            "target_yyyymm",
            "sic",
            "fyear",
            "book_to_market",
            "bmj",
            "operating_profitability",
            "cash_flow_to_price",
        ]
    ]


def load_or_build_annual_panel():
    if Path(ANNUAL_OUTPUT_FILE).exists():
        return pd.read_csv(ANNUAL_OUTPUT_FILE, parse_dates=["datadate"])

    bm, bmj, ope, cfp = load_individual_characters()
    return build_annual_character_panel(bm, bmj, ope, cfp)


def add_mvel1(monthly_chars):
    require_mvel1_file()
    mvel1 = pd.read_csv(MVEL1_FILE)
    required_columns = {"permno", "signal_yyyymm", "mvel1"}
    if not required_columns.issubset(mvel1.columns):
        raise ValueError(
            "outputs/mvel1.csv does not have the current timing columns. "
            "Rerun Character_Builders/Green_MVEL1_Generalized/build_mvel1.py."
        )
    mvel1 = mvel1[["permno", "signal_yyyymm", "mvel1"]]

    return monthly_chars.merge(mvel1, on=["permno", "signal_yyyymm"], how="left")


def main():
    parser = argparse.ArgumentParser(
        description="Create a monthly prediction panel from existing local character files."
    )
    parser.add_argument("--output", default=OUTPUT_FILE)
    args = parser.parse_args()

    annual_chars = load_or_build_annual_panel()
    monthly_chars = expand_to_monthly_prediction_panel(annual_chars)
    monthly_chars = add_mvel1(monthly_chars)

    output_path = Path(args.output)
    if not output_path.is_absolute():
        output_path = PROJECT_ROOT / output_path
    output_path.parent.mkdir(parents=True, exist_ok=True)
    monthly_chars.to_csv(output_path, index=False)

    print(f"Saved monthly character panel to: {output_path.resolve()}")
    print(f"Annual rows: {len(annual_chars):,}")
    print(f"Monthly rows: {len(monthly_chars):,}")
    print(f"Rows with nonmissing mvel1: {monthly_chars['mvel1'].notna().sum():,}")
    print("signal_yyyymm is the predictor month; target_yyyymm is the next-month return month.")


if __name__ == "__main__":
    main()
