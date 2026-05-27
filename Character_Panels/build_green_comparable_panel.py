import argparse
from pathlib import Path

import numpy as np
import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = PROJECT_ROOT / "outputs"
TEMP_OUTPUT = OUTPUT_DIR / "green_comparable_temp.csv"
TEMP2_OUTPUT = OUTPUT_DIR / "green_comparable_temp2_winsorized.csv"

PANEL_KEYS = ["permno", "signal_yyyymm"]
NON_CHARACTER_FILES = {
    "all_character_signal_panel.csv",
    "annual_character_panel.csv",
    "complete_all_character_prediction_panel.csv",
    "complete_prediction_panel.csv",
    "excess_returns.csv",
    "green_comparable_temp.csv",
    "green_comparable_temp2_winsorized.csv",
    "green_comparable_validation_summary.csv",
    "green_sas_validation_summary.csv",
    "monthly_character_panel.csv",
}
NON_CHARACTER_COLUMNS = {
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


def parse_character_list(value):
    if not value:
        return []
    return [item.strip() for item in value.split(",") if item.strip()]


def infer_character_columns(df):
    return [
        column
        for column in df.columns
        if column not in NON_CHARACTER_COLUMNS and pd.api.types.is_numeric_dtype(df[column])
    ]


def month_range_from_green_annual_rule(datadate):
    start = datadate + pd.offsets.MonthBegin(7)
    end = datadate + pd.offsets.MonthBegin(20)
    periods = pd.period_range(start=start.to_period("M"), end=end.to_period("M"), freq="M")
    return periods[:-1]


def expand_annual_with_green_timing(df, character_columns):
    df = df.copy()
    df["datadate"] = pd.to_datetime(df["datadate"])
    id_cols = [column for column in ["permno", "permco", "gvkey", "datadate", "sic", "fyear"] if column in df.columns]
    repeated = df.loc[df.index.repeat(13), id_cols + character_columns].copy()
    month_offsets = np.tile(np.arange(13), len(df))
    start_period = (df["datadate"] + pd.offsets.MonthBegin(7)).dt.to_period("M")
    start_month_index = (start_period.dt.year * 12 + start_period.dt.month - 1).to_numpy().repeat(13)
    month_index = start_month_index + month_offsets
    repeated["signal_yyyymm"] = (month_index // 12) * 100 + (month_index % 12 + 1)
    repeated["target_yyyymm"] = repeated["signal_yyyymm"].map(add_one_month)
    return repeated[PANEL_KEYS + ["target_yyyymm"] + id_cols[1:] + character_columns]


def normalize_character_file(path):
    df = pd.read_csv(path)
    character_columns = infer_character_columns(df)
    if not character_columns:
        return None

    if set(PANEL_KEYS).issubset(df.columns):
        keep = PANEL_KEYS + [
            column
            for column in ["target_yyyymm", "permco", "gvkey", "sic", "exchcd", "shrcd"]
            if column in df.columns
        ] + character_columns
        return df[keep]

    if {"permno", "datadate"}.issubset(df.columns):
        return expand_annual_with_green_timing(df, character_columns)

    return None


def merge_panels(panels):
    final = None
    for panel in panels:
        value_columns = [column for column in panel.columns if column not in set(PANEL_KEYS)]
        panel = panel[PANEL_KEYS + value_columns].drop_duplicates(PANEL_KEYS)
        if final is None:
            final = panel
        else:
            final = final.merge(panel, on=PANEL_KEYS, how="outer", suffixes=("", "_drop"))
            drop_cols = [column for column in final.columns if column.endswith("_drop")]
            if drop_cols:
                final = final.drop(columns=drop_cols)
    return final


def build_green_temp(input_dir=OUTPUT_DIR):
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
        raise FileNotFoundError(f"No compatible character CSV files found in {Path(input_dir).resolve()}.")

    panel = merge_panels(panels)
    if "target_yyyymm" not in panel.columns:
        panel["target_yyyymm"] = panel["signal_yyyymm"].map(add_one_month)

    size_col = "me" if "me" in panel.columns else "mvel1" if "mvel1" in panel.columns else None
    required = [column for column in [size_col, "mom1m", "bm"] if column]
    missing_required = [column for column in ["bm", "mom1m"] if column not in panel.columns]
    if size_col is None:
        missing_required.append("me or mvel1")
    if missing_required:
        raise ValueError(
            "Cannot apply Green temp filter because required columns are missing: "
            + ", ".join(missing_required)
        )

    temp = panel.dropna(subset=required).copy()
    if "eamonth" in temp.columns:
        temp["eamonth"] = temp["eamonth"].fillna(0)
    if "IPO" in temp.columns:
        temp["IPO"] = temp["IPO"].fillna(0)
    return temp, skipped


def winsorize_by_month(panel, hitrim=None, hilotrim=None):
    hitrim = [column for column in (hitrim or []) if column in panel.columns]
    hilotrim = [column for column in (hilotrim or []) if column in panel.columns]
    out = panel.copy()

    for column in hitrim:
        p99 = out.groupby("signal_yyyymm")[column].transform(lambda x: x.quantile(0.99))
        out[column] = out[column].where(out[column].isna() | (out[column] <= p99), p99)

    for column in hilotrim:
        p01 = out.groupby("signal_yyyymm")[column].transform(lambda x: x.quantile(0.01))
        p99 = out.groupby("signal_yyyymm")[column].transform(lambda x: x.quantile(0.99))
        out[column] = out[column].where(out[column].isna() | (out[column] >= p01), p01)
        out[column] = out[column].where(out[column].isna() | (out[column] <= p99), p99)

    return out


def main():
    parser = argparse.ArgumentParser(
        description=(
            "Build a Green-SAS-comparable temp panel from generated character CSVs. "
            "Annual variables use intnx('MONTH', datadate, 7) <= date < "
            "intnx('MONTH', datadate, 20)-style timing."
        )
    )
    parser.add_argument("--input-dir", default=OUTPUT_DIR)
    parser.add_argument("--output", default=TEMP_OUTPUT)
    parser.add_argument("--winsorized-output", default=TEMP2_OUTPUT)
    parser.add_argument("--hitrim", default="", help="Comma-separated columns capped at the monthly 99th percentile.")
    parser.add_argument("--hilotrim", default="", help="Comma-separated columns capped at monthly 1st and 99th percentiles.")
    parser.add_argument("--no-winsorized-output", action="store_true")
    args = parser.parse_args()

    temp, skipped = build_green_temp(args.input_dir)

    output_path = Path(args.output)
    if not output_path.is_absolute():
        output_path = PROJECT_ROOT / output_path
    output_path.parent.mkdir(parents=True, exist_ok=True)
    temp.to_csv(output_path, index=False)

    print(f"Saved Green comparable temp panel to: {output_path.resolve()}")
    print(f"Rows after Green temp filter: {len(temp):,}")
    print("Filter applied: nonmissing size (`me` or `mvel1`), `mom1m`, and `bm`.")

    hitrim = parse_character_list(args.hitrim)
    hilotrim = parse_character_list(args.hilotrim)
    if not args.no_winsorized_output and (hitrim or hilotrim):
        temp2 = winsorize_by_month(temp, hitrim=hitrim, hilotrim=hilotrim)
        winsorized_path = Path(args.winsorized_output)
        if not winsorized_path.is_absolute():
            winsorized_path = PROJECT_ROOT / winsorized_path
        winsorized_path.parent.mkdir(parents=True, exist_ok=True)
        temp2.to_csv(winsorized_path, index=False)
        print(f"Saved winsorized Green comparable temp2 panel to: {winsorized_path.resolve()}")
        print(f"High-only trimmed columns: {', '.join(hitrim) if hitrim else '(none)'}")
        print(f"Two-sided trimmed columns: {', '.join(hilotrim) if hilotrim else '(none)'}")

    if skipped:
        print("Skipped incompatible files:")
        for name in skipped:
            print(f"- {name}")


if __name__ == "__main__":
    main()
