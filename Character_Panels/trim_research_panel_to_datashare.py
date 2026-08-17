#!/usr/bin/env python3
"""Trim a research panel to datashare-matched character columns only.

Reads a ranked research panel (e.g. Full_research_panel_1957_ranked.csv), keeps
identity columns + excess_return + character columns that map to GKX datashare
signal predictors, and drops all other character columns.

Fully independent: only argparse, pathlib, sys, pandas. No repo imports.
Alias dict and the 95 datashare predictor names are embedded below.

Usage:
  python Character_Panels/trim_research_panel_to_datashare.py \\
      --input  outputs/panels/Full_research_panel_1957_ranked.csv \\
      --output outputs/panels/research_panel_1957_datashare_matched.csv
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))
from pipeline_config import (  # noqa: E402
    DATASHARE_PREDICTORS,
    DATASHARE_PANEL_ALIAS as PANEL_ALIAS,
    panel_column_for_datashare,
)

DEFAULT_INPUT = PROJECT_ROOT / "outputs" / "panels" / "Full_research_panel_1957_ranked.csv"
DEFAULT_OUTPUT = PROJECT_ROOT / "outputs" / "panels" / "research_panel_1957_datashare_matched.csv"
CHUNK_SIZE = 500_000

IDENTITY_COLUMNS: frozenset[str] = frozenset(
    {
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
)

RETURN_COLUMNS: frozenset[str] = frozenset({"excess_return"})


def resolve_path(path: Path) -> Path:
    return path if path.is_absolute() else PROJECT_ROOT / path


def compute_column_plan(input_cols: list[str]) -> dict:
    input_set = set(input_cols)
    keep_chars = {
        panel_column_for_datashare(ds)
        for ds in DATASHARE_PREDICTORS
    } & input_set
    keep_chars -= IDENTITY_COLUMNS

    keep_set = (IDENTITY_COLUMNS | RETURN_COLUMNS | keep_chars) & input_set
    final_cols = [c for c in input_cols if c in keep_set]

    identity_kept = [c for c in final_cols if c in IDENTITY_COLUMNS]
    return_kept = [c for c in final_cols if c in RETURN_COLUMNS]
    chars_kept = [c for c in final_cols if c in keep_chars]

    all_chars = [
        c
        for c in input_cols
        if c not in IDENTITY_COLUMNS
        and c not in RETURN_COLUMNS
    ]
    chars_dropped = [c for c in all_chars if c not in keep_chars]

    missing_from_panel = sorted(
        panel_column_for_datashare(ds)
        for ds in DATASHARE_PREDICTORS
        if panel_column_for_datashare(ds) not in input_set
    )

    return {
        "final_cols": final_cols,
        "identity_kept": identity_kept,
        "return_kept": return_kept,
        "chars_kept": chars_kept,
        "chars_dropped": chars_dropped,
        "missing_from_panel": missing_from_panel,
    }


def trim_panel(input_path: Path, output_path: Path, chunk_size: int = CHUNK_SIZE) -> dict:
    header = pd.read_csv(input_path, nrows=0)
    input_cols = list(header.columns)
    plan = compute_column_plan(input_cols)
    final_cols = plan["final_cols"]

    if not final_cols:
        raise ValueError("No columns selected for output. Check input file header.")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    row_count = 0
    wrote_header = False

    for chunk in pd.read_csv(input_path, usecols=final_cols, chunksize=chunk_size):
        row_count += len(chunk)
        chunk.to_csv(
            output_path,
            mode="w" if not wrote_header else "a",
            header=not wrote_header,
            index=False,
        )
        wrote_header = True

    plan["row_count"] = row_count
    plan["input_path"] = input_path
    plan["output_path"] = output_path
    plan["input_col_count"] = len(input_cols)
    plan["output_col_count"] = len(final_cols)
    return plan


def print_summary(plan: dict) -> None:
    print(f"Input:  {plan['input_path'].resolve()}")
    print(f"Output: {plan['output_path'].resolve()}")
    print(f"Input columns:  {plan['input_col_count']}")
    print(f"Output columns: {plan['output_col_count']}")
    print(f"Rows written:   {plan['row_count']:,}")
    print()
    print(f"Identity columns kept ({len(plan['identity_kept'])}): {', '.join(plan['identity_kept'])}")
    print(f"Return columns kept ({len(plan['return_kept'])}): {', '.join(plan['return_kept'])}")
    print()
    print(f"Character columns kept ({len(plan['chars_kept'])}):")
    for col in plan["chars_kept"]:
        print(f"  + {col}")
    print()
    print(f"Character columns dropped ({len(plan['chars_dropped'])}):")
    for col in plan["chars_dropped"]:
        print(f"  - {col}")
    if plan["missing_from_panel"]:
        print()
        print(
            f"Datashare-mapped panel columns missing from input ({len(plan['missing_from_panel'])}):"
        )
        for col in plan["missing_from_panel"]:
            print(f"  ! {col}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Trim a research panel to identity columns, excess_return, and "
            "character columns that map to GKX datashare predictors."
        )
    )
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--chunk-size", type=int, default=CHUNK_SIZE)
    args = parser.parse_args()

    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

    input_path = resolve_path(args.input)
    output_path = resolve_path(args.output)

    if not input_path.exists():
        raise FileNotFoundError(f"Input panel not found: {input_path}")

    plan = trim_panel(input_path, output_path, chunk_size=args.chunk_size)
    print_summary(plan)


if __name__ == "__main__":
    main()
