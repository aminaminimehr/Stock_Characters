import argparse
from pathlib import Path

import numpy as np
import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = PROJECT_ROOT / "outputs"
INPUT_FILE = OUTPUT_DIR / "complete_all_character_prediction_panel.csv"
OUTPUT_FILE = OUTPUT_DIR / "research_panel_1957_ranked.csv"

try:
    from Imputation.industry_codes import add_fama_french_industry_code
except ImportError:
    import sys

    sys.path.append(str(PROJECT_ROOT))
    from Imputation.industry_codes import add_fama_french_industry_code


IDENTIFIER_COLUMNS = {
    "permno",
    "permco",
    "gvkey",
    "sic",
    "ffi49",
    "date",
    "datadate",
    "availability_date",
    "source_date",
    "source_yyyymm",
    "signal_yyyymm",
    "target_yyyymm",
    "yyyymm",
    "exchcd",
    "shrcd",
    "fyear",
    "calendar_year",
}
RETURN_COLUMNS = {
    "ret",
    "retx",
    "dlret",
    "dlstcd",
    "retadj",
    "rf",
    "excess_return",
}
KEEP_COLUMNS = [
    "permno",
    "signal_yyyymm",
    "target_yyyymm",
    "date",
    "sic",
    "ffi49",
    "excess_return",
]


def infer_character_columns(df):
    exclude = IDENTIFIER_COLUMNS | RETURN_COLUMNS
    return [
        column
        for column in df.columns
        if column not in exclude and pd.api.types.is_numeric_dtype(df[column])
    ]


def winsorize_by_month(df, character_cols, time_col, lower=0.01, upper=0.99):
    out = df.copy()
    grouped = out.groupby(time_col, sort=False)
    for column in character_cols:
        lower_bound = grouped[column].transform(lambda s: s.quantile(lower))
        upper_bound = grouped[column].transform(lambda s: s.quantile(upper))
        out[column] = out[column].clip(lower=lower_bound, upper=upper_bound)
    return out


def impute_by_month_industry(df, character_cols, time_col, industry_col):
    out = df.copy()
    monthly_groups = out.groupby(time_col, sort=False)
    industry_groups = out.groupby([time_col, industry_col], sort=False, dropna=False)

    for column in character_cols:
        industry_median = industry_groups[column].transform("median")
        monthly_median = monthly_groups[column].transform("median")
        out[column] = out[column].fillna(industry_median).fillna(monthly_median)
    return out


def rank_to_unit_interval(values):
    nonmissing = values.notna()
    nobs = int(nonmissing.sum())
    ranked = pd.Series(np.nan, index=values.index, dtype="float64")
    if nobs == 0:
        return ranked
    if nobs == 1:
        ranked.loc[nonmissing] = 0.0
        return ranked

    ranks = values.loc[nonmissing].rank(method="average")
    ranked.loc[nonmissing] = 2.0 * (ranks - 1.0) / (nobs - 1.0) - 1.0
    return ranked


def rank_by_month(df, character_cols, time_col):
    out = df.copy()
    grouped = out.groupby(time_col, sort=False)
    for column in character_cols:
        out[column] = grouped[column].transform(rank_to_unit_interval)
        out[column] = out[column].fillna(0.0)
    return out


def build_research_panel(
    input_file=INPUT_FILE,
    start_target_yyyymm=195701,
    industry_scheme=49,
    winsor_lower=0.01,
    winsor_upper=0.99,
):
    input_path = Path(input_file)
    if not input_path.is_absolute():
        input_path = PROJECT_ROOT / input_path

    panel = pd.read_csv(input_path, low_memory=False)
    required = {"permno", "signal_yyyymm", "target_yyyymm", "sic", "excess_return"}
    missing = required.difference(panel.columns)
    if missing:
        missing_text = ", ".join(sorted(missing))
        raise ValueError(
            f"Input panel is missing required columns: {missing_text}. "
            "Rebuild all_character_signal_panel.csv after preserving sic, then rebuild "
            "complete_all_character_prediction_panel.csv."
        )

    panel = panel.loc[panel["target_yyyymm"] >= start_target_yyyymm].copy()
    panel = panel.replace([np.inf, -np.inf], np.nan)

    character_cols = infer_character_columns(panel)
    panel = add_fama_french_industry_code(
        panel,
        scheme=industry_scheme,
        sic_col="sic",
        output_col=f"ffi{industry_scheme}",
    )

    panel = winsorize_by_month(
        panel,
        character_cols,
        time_col="signal_yyyymm",
        lower=winsor_lower,
        upper=winsor_upper,
    )
    panel = impute_by_month_industry(
        panel,
        character_cols,
        time_col="signal_yyyymm",
        industry_col=f"ffi{industry_scheme}",
    )
    panel = rank_by_month(panel, character_cols, time_col="signal_yyyymm")

    keep = [column for column in KEEP_COLUMNS if column in panel.columns]
    panel = panel[keep + character_cols].sort_values(["target_yyyymm", "permno"])
    return panel, character_cols


def main():
    parser = argparse.ArgumentParser(
        description=(
            "Build the 1957+ research-ready monthly panel: winsorized, "
            "industry-median imputed, and cross-sectionally ranked to [-1, 1]."
        )
    )
    parser.add_argument("--input", default=INPUT_FILE)
    parser.add_argument("--output", default=OUTPUT_FILE)
    parser.add_argument("--start-target-yyyymm", type=int, default=195701)
    parser.add_argument("--industry-scheme", type=int, default=49)
    parser.add_argument("--winsor-lower", type=float, default=0.01)
    parser.add_argument("--winsor-upper", type=float, default=0.99)
    args = parser.parse_args()

    research_panel, character_cols = build_research_panel(
        input_file=args.input,
        start_target_yyyymm=args.start_target_yyyymm,
        industry_scheme=args.industry_scheme,
        winsor_lower=args.winsor_lower,
        winsor_upper=args.winsor_upper,
    )

    output_path = Path(args.output)
    if not output_path.is_absolute():
        output_path = PROJECT_ROOT / output_path
    output_path.parent.mkdir(parents=True, exist_ok=True)
    research_panel.to_csv(output_path, index=False)

    print(f"Saved research panel to: {output_path.resolve()}")
    print(f"Rows: {len(research_panel):,}")
    print(f"Character columns: {len(character_cols):,}")
    print(
        "Target months: "
        f"{research_panel['target_yyyymm'].min()} to "
        f"{research_panel['target_yyyymm'].max()}"
    )
    print("Panel operations: monthly 1/99 winsorization, FF49 industry-median imputation, rank map to [-1, 1].")


if __name__ == "__main__":
    main()
