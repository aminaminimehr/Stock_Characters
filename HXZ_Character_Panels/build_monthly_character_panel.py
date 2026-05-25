import argparse
from pathlib import Path

import numpy as np
import pandas as pd

from build_annual_character_panel import (
    OUTPUT_FILE as ANNUAL_OUTPUT_FILE,
    PROJECT_ROOT,
    build_annual_character_panel,
    load_individual_characters,
)


OUTPUT_FILE = PROJECT_ROOT / "outputs" / "monthly_character_panel.csv"


def expand_to_monthly_prediction_panel(annual_chars):
    monthly = annual_chars.copy()
    monthly["datadate"] = pd.to_datetime(monthly["datadate"])
    monthly["availability_year"] = monthly["datadate"].dt.year + 1
    monthly["availability_date"] = pd.to_datetime(
        monthly["availability_year"].astype(str) + "-06-30"
    )

    monthly = monthly.loc[monthly.index.repeat(12)].copy()
    month_offsets = np.tile(np.arange(12), len(annual_chars))

    first_return_month = monthly["availability_year"].to_numpy() * 12 + 6
    month_index = first_return_month + month_offsets
    monthly["yyyymm"] = (month_index // 12) * 100 + (month_index % 12 + 1)

    return monthly[
        [
            "permno",
            "permco",
            "gvkey",
            "datadate",
            "availability_date",
            "yyyymm",
            "sic",
            "fyear",
            "book_to_market",
            "operating_profitability",
            "cash_flow_to_price",
        ]
    ]


def load_or_build_annual_panel():
    if Path(ANNUAL_OUTPUT_FILE).exists():
        return pd.read_csv(ANNUAL_OUTPUT_FILE, parse_dates=["datadate"])

    bm, ope, cfp = load_individual_characters()
    return build_annual_character_panel(bm, ope, cfp)


def main():
    parser = argparse.ArgumentParser(
        description="Create a monthly prediction panel from existing local HXZ character files."
    )
    parser.add_argument("--output", default=OUTPUT_FILE)
    args = parser.parse_args()

    annual_chars = load_or_build_annual_panel()
    monthly_chars = expand_to_monthly_prediction_panel(annual_chars)

    output_path = Path(args.output)
    if not output_path.is_absolute():
        output_path = PROJECT_ROOT / output_path
    output_path.parent.mkdir(parents=True, exist_ok=True)
    monthly_chars.to_csv(output_path, index=False)

    print(f"Saved monthly character panel to: {output_path.resolve()}")
    print(f"Annual rows: {len(annual_chars):,}")
    print(f"Monthly rows: {len(monthly_chars):,}")
    print("Each annual character is repeated from July of datadate.year + 1 through June of datadate.year + 2.")


if __name__ == "__main__":
    main()
