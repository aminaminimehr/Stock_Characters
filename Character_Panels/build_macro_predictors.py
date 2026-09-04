#!/usr/bin/env python3
"""Build 8 monthly macro predictors from Amit Goyal PredictorData -> parquet.

Raw, unstandardized output. Expanding-window standardization is done later
inside each train/val window by the interaction-panel builder.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_GOYAL = (
    PROJECT_ROOT
    / "Supplementary_assistive_files"
    / "PredictorData2025_Monthly_from_Amit_Goyal.csv"
)
DEFAULT_OUT = PROJECT_ROOT / "outputs" / "panels" / "macro_predictors_monthly.parquet"

MACRO_COLUMNS: tuple[str, ...] = ("dp", "ep", "bm", "tms", "dfy", "ntis", "tbl", "svar")


def resolve_path(path: Path) -> Path:
    """Resolve a path relative to the repo root when not absolute."""
    return path if path.is_absolute() else PROJECT_ROOT / path


def build_macro_predictors(goyal_path: Path) -> pd.DataFrame:
    """Read Goyal CSV and compute the 8 raw macro predictors keyed by yyyymm."""
    raw = pd.read_csv(goyal_path, thousands=",")
    if "yyyymm" not in raw.columns:
        raise ValueError(f"Goyal file missing yyyymm column: {goyal_path}")

    index = pd.to_numeric(raw["Index"], errors="coerce")
    d12 = pd.to_numeric(raw["D12"], errors="coerce")
    e12 = pd.to_numeric(raw["E12"], errors="coerce")
    bm_ratio = pd.to_numeric(raw["b/m"], errors="coerce")
    tbl = pd.to_numeric(raw["tbl"], errors="coerce")
    aaa = pd.to_numeric(raw["AAA"], errors="coerce")
    baa = pd.to_numeric(raw["BAA"], errors="coerce")
    lty = pd.to_numeric(raw["lty"], errors="coerce")

    macro = pd.DataFrame(
        {"yyyymm": pd.to_numeric(raw["yyyymm"], errors="coerce").astype("Int64")}
    )
    macro["dp"] = np.log(d12 / index)
    macro["ep"] = np.log(e12 / index)
    macro["bm"] = np.log(bm_ratio)
    macro["tms"] = lty - tbl
    macro["dfy"] = baa - aaa
    macro["ntis"] = pd.to_numeric(raw["ntis"], errors="coerce")
    macro["tbl"] = tbl
    macro["svar"] = pd.to_numeric(raw["svar"], errors="coerce")

    return macro[["yyyymm", *MACRO_COLUMNS]].sort_values("yyyymm").reset_index(drop=True)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Build 8 Goyal macro predictors -> parquet (raw, unstandardized)."
    )
    parser.add_argument("--goyal", type=Path, default=DEFAULT_GOYAL)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()

    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

    goyal_path = resolve_path(args.goyal)
    out_path = resolve_path(args.out)

    if not goyal_path.exists():
        raise FileNotFoundError(f"Goyal PredictorData not found: {goyal_path}")

    macro = build_macro_predictors(goyal_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    macro.to_parquet(out_path, index=False, engine="pyarrow", compression="snappy")

    print(f"Saved {len(macro):,} rows x {len(macro.columns)} cols -> {out_path.resolve()}")
    print(f"  yyyymm: {int(macro['yyyymm'].min())} to {int(macro['yyyymm'].max())}")
    print(f"  columns: {', '.join(macro.columns)}")
    print(f"  size: {out_path.stat().st_size / 1024:.1f} KB")


if __name__ == "__main__":
    main()
