import argparse
from pathlib import Path

import numpy as np
import pandas as pd
import pyreadstat


PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = PROJECT_ROOT / "outputs"
DEFAULT_PANEL = OUTPUT_DIR / "green_comparable_temp.csv"
DEFAULT_GREEN = PROJECT_ROOT / "Supplementary_assistive_files" / "Output_From_Greens_SAS_code.sas7bdat"
DEFAULT_SUMMARY = OUTPUT_DIR / "green_comparable_validation_summary.csv"
DEFAULT_REPORT = OUTPUT_DIR / "green_comparable_validation_report.md"


COLUMN_MAP = {
    "acc": "acc",
    "agr": "agr",
    "baspread": "baspread",
    "bm": "bm",
    "bm_ia": "bm_ia",
    "cash": "cash",
    "cashdebt": "cashdebt",
    "cfp": "cfp",
    "chcsho": "chcsho",
    "chpm": "chpmia",
    "depr": "depr",
    "dolvol": "dolvol",
    "ep": "ep",
    "gma": "gma",
    "grltnoa": "grltnoa",
    "herf": "herf",
    "hire": "hire",
    "ill": "ill",
    "lev": "lev",
    "lgr": "lgr",
    "maxret": "maxret",
    "me": "mve",
    "me_ia": "mve_ia",
    "mom1m": "mom1m",
    "mom6m": "mom6m",
    "mom12m": "mom12m",
    "mom36m": "mom36m",
    "mom60m": "mom60m",
    "mvel1": "mve",
    "op": "operprof",
    "pctacc": "pctacc",
    "ps": "ps",
    "rd_sale": "rd_sale",
    "rdm": "rd_mve",
    "roe": "roe",
    "rvar_mean": "retvol",
    "sgr": "sgr",
    "sp": "sp",
    "std_dolvol": "std_dolvol",
    "std_turn": "std_turn",
    "turn": "turn",
    "zerotrade": "zerotrade",
}


UNMAPPED_LOCAL_COLUMNS = {
    "adm": "No `adm` column exists in the supplied Green SAS output.",
    "alm": "No `alm` column exists in the supplied Green SAS output.",
    "ato": "No direct `ato` column exists in the supplied Green SAS output.",
    "bmj": "HXZ-specific book-to-June-market-equity variable, not a Green output column.",
    "book_to_market": "HXZ-specific duplicate construction; compare `bm` for Green-style book-to-market.",
    "cash_flow_to_price": "HXZ-specific duplicate construction; compare `cfp` for Green-style cash-flow-to-price.",
    "noa": "No `noa` column exists in the supplied Green SAS output.",
    "operating_profitability": "HXZ-specific duplicate construction; compare `op` to Green's `operprof`.",
    "pm": "No `pm` column exists in the supplied Green SAS output.",
}


def yyyymm_from_date(series):
    dt = pd.to_datetime(series)
    return dt.dt.year * 100 + dt.dt.month


def exact_match_rates(left, right):
    rates = {}
    for decimals in (4, 3, 2):
        rates[f"exact_{decimals}dp"] = float((left.round(decimals) == right.round(decimals)).mean()) if len(left) else np.nan
    return rates


def cross_sectional_correlations(data):
    corrs = []
    for _, group in data.groupby("signal_yyyymm"):
        pair = group[["python_value", "green_value"]].dropna()
        if len(pair) >= 5 and pair["python_value"].nunique() > 1 and pair["green_value"].nunique() > 1:
            corrs.append(pair["python_value"].corr(pair["green_value"]))
    if not corrs:
        return {
            "xs_periods": 0,
            "mean_xs_corr": np.nan,
            "median_xs_corr": np.nan,
            "min_xs_corr": np.nan,
        }
    corrs = pd.Series(corrs, dtype="float64")
    return {
        "xs_periods": int(corrs.notna().sum()),
        "mean_xs_corr": float(corrs.mean()),
        "median_xs_corr": float(corrs.median()),
        "min_xs_corr": float(corrs.min()),
    }


def summarize_column(merged, local_col, green_col):
    merged_green_col = f"{green_col}_green" if local_col == green_col else green_col
    pair = merged[["signal_yyyymm", local_col, merged_green_col]].replace([np.inf, -np.inf], np.nan).dropna()
    pair = pair.rename(columns={local_col: "python_value", merged_green_col: "green_value"})
    row = {
        "character": local_col,
        "green_column": green_col,
        "matched_nonmissing_pairs": int(len(pair)),
        "overall_corr": float(pair["python_value"].corr(pair["green_value"])) if len(pair) >= 2 else np.nan,
        "mean_abs_diff": float((pair["python_value"] - pair["green_value"]).abs().mean()) if len(pair) else np.nan,
    }
    row.update(cross_sectional_correlations(pair))
    row.update(exact_match_rates(pair["python_value"], pair["green_value"]))
    return row


def read_green_sas(path, columns):
    usecols = ["permno", "DATE", *sorted(set(columns))]
    green, _ = pyreadstat.read_sas7bdat(str(path), usecols=usecols)
    green["permno"] = pd.to_numeric(green["permno"], errors="coerce")
    green["signal_yyyymm"] = yyyymm_from_date(green["DATE"])
    green = green.drop(columns=["DATE"])
    green = green.dropna(subset=["permno", "signal_yyyymm"])
    return green.groupby(["permno", "signal_yyyymm"], as_index=False).last()


def green_columns_available(path):
    _, metadata = pyreadstat.read_sas7bdat(str(path), metadataonly=True)
    return set(metadata.column_names)


def read_python_panel(path, columns):
    usecols = ["permno", "signal_yyyymm", *sorted(set(columns))]
    panel = pd.read_csv(path, usecols=lambda column: column in usecols)
    panel["permno"] = pd.to_numeric(panel["permno"], errors="coerce")
    panel = panel.dropna(subset=["permno", "signal_yyyymm"])
    return panel.groupby(["permno", "signal_yyyymm"], as_index=False).last()


def format_num(value):
    return "" if pd.isna(value) else f"{value:.6f}"


def format_pct(value):
    return "" if pd.isna(value) else f"{100 * value:.2f}%"


def write_outputs(summary, report_path, summary_path, panel_rows, green_rows, common_rows):
    summary = summary.sort_values("character").reset_index(drop=True)
    summary.to_csv(summary_path, index=False)

    display = summary.copy()
    for column in ["overall_corr", "mean_xs_corr", "median_xs_corr", "min_xs_corr", "mean_abs_diff"]:
        display[column] = display[column].map(format_num)
    for column in ["exact_4dp", "exact_3dp", "exact_2dp"]:
        display[column] = display[column].map(format_pct)

    columns = [
        "character",
        "green_column",
        "matched_nonmissing_pairs",
        "overall_corr",
        "mean_xs_corr",
        "median_xs_corr",
        "exact_4dp",
        "exact_3dp",
        "exact_2dp",
        "mean_abs_diff",
    ]
    lines = [
        "# Green Comparable Panel Validation",
        "",
        "This report compares `outputs/green_comparable_temp.csv` against the supplied Green SAS output.",
        "Both datasets are matched on `permno` and month, where the Green SAS month is derived from `DATE`.",
        "",
        f"- Python Green-comparable panel rows: {panel_rows:,}",
        f"- Green SAS output rows: {green_rows:,}",
        f"- Common `permno`-month rows: {common_rows:,}",
        "",
        "## Summary",
        "",
        display[columns].to_markdown(index=False),
        "",
        "## Local Columns Not Compared",
        "",
    ]
    for column, reason in UNMAPPED_LOCAL_COLUMNS.items():
        lines.append(f"- `{column}`: {reason}")
    lines.extend(
        [
            "",
            "## Name Mappings Used",
            "",
            "- `chpm` -> Green `chpmia`.",
            "- `me_ia` -> Green `mve_ia`.",
            "- `op` -> Green `operprof`.",
            "- `rdm` -> Green `rd_mve`.",
            "- `rvar_mean` -> Green `retvol`.",
            "- `me` and `mvel1` -> Green `mve`.",
            "",
        ]
    )
    report_path.write_text("\n".join(lines), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description="Compare the Green-comparable temp panel to Green's SAS output.")
    parser.add_argument("--panel", default=DEFAULT_PANEL)
    parser.add_argument("--green-sas", default=DEFAULT_GREEN)
    parser.add_argument("--summary", default=DEFAULT_SUMMARY)
    parser.add_argument("--report", default=DEFAULT_REPORT)
    args = parser.parse_args()

    panel_path = Path(args.panel)
    green_path = Path(args.green_sas)
    summary_path = Path(args.summary)
    report_path = Path(args.report)
    for path_name, path in [("panel", panel_path), ("green SAS file", green_path)]:
        if not path.exists():
            raise FileNotFoundError(f"Missing {path_name}: {path}")

    panel_columns = set(pd.read_csv(panel_path, nrows=0).columns)
    green_columns = green_columns_available(green_path)
    usable_map = {
        local: green
        for local, green in COLUMN_MAP.items()
        if local in panel_columns and green in green_columns
    }

    print("Reading Python Green-comparable panel...")
    panel = read_python_panel(panel_path, usable_map.keys())
    print("Reading Green SAS output...")
    green = read_green_sas(green_path, usable_map.values())

    print("Merging common permno-month rows...")
    merged = panel.merge(green, on=["permno", "signal_yyyymm"], how="inner", suffixes=("", "_green"))
    rows = [summarize_column(merged, local, green_col) for local, green_col in usable_map.items()]
    summary = pd.DataFrame(rows)

    summary_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    write_outputs(summary, report_path, summary_path, len(panel), len(green), len(merged))
    print(f"Wrote {report_path}")
    print(f"Wrote {summary_path}")


if __name__ == "__main__":
    main()
