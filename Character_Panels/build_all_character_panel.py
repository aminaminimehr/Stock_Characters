import argparse
from pathlib import Path

import numpy as np
import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = PROJECT_ROOT / "outputs"
OUTPUT_FILE = OUTPUT_DIR / "all_character_signal_panel.csv"

MONTHLY_KEYS = ["permno", "signal_yyyymm", "target_yyyymm"]
ANNUAL_ID_COLUMNS = ["permno", "permco", "gvkey", "datadate", "sic", "fyear"]
NON_CHARACTER_FILES = {
    "all_character_signal_panel.csv",
    "annual_character_panel.csv",
    "complete_all_character_prediction_panel.csv",
    "complete_prediction_panel.csv",
    "complete_prediction_panel_imputed.csv",
    "excess_returns.csv",
    "green_comparable_temp.csv",
    "green_comparable_temp2_winsorized.csv",
    "green_comparable_validation_summary.csv",
    "green_comparable_winsorized_validation_summary.csv",
    "green_comparable_winsorized_validation_summary_fresh.csv",
    "green_missing_character_inventory.csv",
    "monthly_character_panel.csv",
    "research_panel_1957_ranked.csv",
}
KNOWN_NON_CHARACTER_COLUMNS = {
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
    "lagged_market_equity",
    "june_date",
    "book_equity_per_share",
    "split_adjustment",
    "june_price",
}


def add_one_month(yyyymm):
    year = yyyymm // 100
    month = yyyymm % 100
    next_month = month + 1
    next_year = year + (next_month == 13)
    next_month = 1 if next_month == 13 else next_month
    return next_year * 100 + next_month


def infer_character_columns(df):
    return [
        column
        for column in df.columns
        if column not in KNOWN_NON_CHARACTER_COLUMNS
        and pd.api.types.is_numeric_dtype(df[column])
    ]


def expand_annual_file(df, character_columns):
    df = df.copy()
    df["datadate"] = pd.to_datetime(df["datadate"])
    availability_year = df["datadate"].dt.year + 1

    repeated = df.loc[df.index.repeat(12), ANNUAL_ID_COLUMNS + character_columns].copy()
    month_offsets = np.tile(np.arange(12), len(df))
    first_signal_month = availability_year.to_numpy().repeat(12) * 12 + 5
    month_index = first_signal_month + month_offsets
    repeated["signal_yyyymm"] = (month_index // 12) * 100 + (month_index % 12 + 1)
    repeated["target_yyyymm"] = repeated["signal_yyyymm"].map(add_one_month)
    repeated = (
        repeated.sort_values(["permno", "signal_yyyymm", "datadate"])
        .drop_duplicates(["permno", "signal_yyyymm"], keep="last")
    )

    keep = MONTHLY_KEYS + ["permco", "gvkey", "sic"] + character_columns
    return repeated[keep]


def normalize_character_file(path):
    df = pd.read_csv(path)
    character_columns = infer_character_columns(df)
    if not character_columns:
        return None

    if set(MONTHLY_KEYS).issubset(df.columns):
        keep = MONTHLY_KEYS + [
            column for column in ["permco", "gvkey", "sic"] if column in df.columns
        ] + character_columns
        return df[keep]

    if {"permno", "datadate"}.issubset(df.columns):
        return expand_annual_file(df, character_columns)

    return None


def coalesce_metadata(panels):
    metadata = None
    for panel in panels:
        meta_cols = [
            column
            for column in ["sic"]
            if column in panel.columns
        ]
        if not meta_cols:
            continue

        one_meta = (
            panel[MONTHLY_KEYS + meta_cols]
            .sort_values(MONTHLY_KEYS)
            .drop_duplicates(MONTHLY_KEYS)
        )
        if metadata is None:
            metadata = one_meta
            continue

        metadata = metadata.merge(
            one_meta,
            on=MONTHLY_KEYS,
            how="outer",
            suffixes=("", "_new"),
        )
        for column in meta_cols:
            new_column = f"{column}_new"
            if new_column in metadata.columns:
                metadata[column] = metadata[column].combine_first(metadata[new_column])
                metadata = metadata.drop(columns=[new_column])

    return metadata


def merge_panels(panels):
    final = None
    for panel in panels:
        value_columns = [
            column
            for column in panel.columns
            if column not in set(MONTHLY_KEYS + ["permco", "gvkey", "sic"])
        ]
        panel = panel[MONTHLY_KEYS + value_columns].drop_duplicates(MONTHLY_KEYS)
        if final is None:
            final = panel
        else:
            final = final.merge(panel, on=MONTHLY_KEYS, how="outer")

    metadata = coalesce_metadata(panels)
    if metadata is not None:
        final = metadata.merge(final, on=MONTHLY_KEYS, how="right")

    return final


def build_all_character_panel(input_dir=OUTPUT_DIR):
    paths = sorted(Path(input_dir).glob("*.csv"))
    panels = []
    skipped = []
    for path in paths:
        if path.name in NON_CHARACTER_FILES:
            continue
        panel = normalize_character_file(path)
        if panel is None:
            skipped.append(path.name)
            continue
        panels.append(panel)

    if not panels:
        raise FileNotFoundError(
            f"No compatible character CSV files found in {Path(input_dir).resolve()}."
        )

    return merge_panels(panels), skipped


def main():
    parser = argparse.ArgumentParser(
        description="Combine local character CSVs into one signal-month panel."
    )
    parser.add_argument("--input-dir", default=OUTPUT_DIR)
    parser.add_argument("--output", default=OUTPUT_FILE)
    args = parser.parse_args()

    panel, skipped = build_all_character_panel(args.input_dir)

    output_path = Path(args.output)
    if not output_path.is_absolute():
        output_path = PROJECT_ROOT / output_path
    output_path.parent.mkdir(parents=True, exist_ok=True)
    panel.to_csv(output_path, index=False)

    print(f"Saved all-character signal panel to: {output_path.resolve()}")
    print(f"Rows: {len(panel):,}")
    metadata_columns = {"sic"}
    character_count = len(
        [
            column
            for column in panel.columns
            if column not in set(MONTHLY_KEYS) | metadata_columns
        ]
    )
    print(f"Character columns: {character_count:,}")
    if skipped:
        print("Skipped incompatible files:")
        for name in skipped:
            print(f"- {name}")


if __name__ == "__main__":
    main()
