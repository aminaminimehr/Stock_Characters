#!/usr/bin/env python3
"""Build monthly macro predictors and a macro-interaction research panel.

Step 1: Read Amit Goyal PredictorData CSV and compute 8 macro predictors:
  dp = ln(D12/Index), ep = ln(E12/Index), bm = ln(b/m), tms = lty - tbl,
  dfy = BAA - AAA, plus direct copies ntis, tbl, svar.

Step 2: Blend into the research panel:
  identity + excess_return + 94 base characters (excl. ranked sic2)
  + 8x94 interaction columns (<char>_x_<macro>)
  + 2-digit SIC one-hot dummies (sic2d_<code> from raw sic // 100).

Fully independent: only argparse, pathlib, sys, numpy, pandas. No repo imports.

Usage:
  python Character_Panels/build_macro_interaction_panel.py
"""
from __future__ import annotations

import argparse
import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore", category=pd.errors.PerformanceWarning)

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_GOYAL = (
    PROJECT_ROOT
    / "Supplementary_assistive_files"
    / "PredictorData2025_Monthly_from_Amit_Goyal.csv"
)
DEFAULT_PANEL = (
    PROJECT_ROOT / "outputs" / "panels" / "research_panel_1957_ranked.csv"
)
DEFAULT_MACRO_OUT = PROJECT_ROOT / "outputs" / "panels" / "macro_predictors_monthly.csv"
DEFAULT_BLENDED_OUT = PROJECT_ROOT / "outputs" / "panels" / "macro_interaction_panel.csv"
CHUNK_SIZE = 200_000

IDENTITY_COLUMNS: tuple[str, ...] = (
    "permno",
    "signal_yyyymm",
    "target_yyyymm",
    "date",
    "sic",
    "ffi49",
)
RETURN_COLUMN = "excess_return"
RANKED_SIC_COLUMN = "sic2"
MACRO_COLUMNS: tuple[str, ...] = (
    "dp",
    "ep",
    "bm",
    "tms",
    "dfy",
    "ntis",
    "tbl",
    "svar",
)
MACRO_OUTPUT_COLUMNS: tuple[str, ...] = ("yyyymm",) + MACRO_COLUMNS


def resolve_path(path: Path) -> Path:
    return path if path.is_absolute() else PROJECT_ROOT / path


def build_macro_predictors(goyal_path: Path) -> pd.DataFrame:
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

    macro = pd.DataFrame({"yyyymm": pd.to_numeric(raw["yyyymm"], errors="coerce").astype("Int64")})
    macro["dp"] = np.log(d12 / index)
    macro["ep"] = np.log(e12 / index)
    macro["bm"] = np.log(bm_ratio)
    macro["tms"] = lty - tbl
    macro["dfy"] = baa - aaa
    macro["ntis"] = pd.to_numeric(raw["ntis"], errors="coerce")
    macro["tbl"] = tbl
    macro["svar"] = pd.to_numeric(raw["svar"], errors="coerce")

    return macro[list(MACRO_OUTPUT_COLUMNS)].sort_values("yyyymm").reset_index(drop=True)


def standardize_macros(
    macro: pd.DataFrame, mode: str, min_periods: int
) -> pd.DataFrame:
    """Standardize macro columns over the time series before interaction.

    mode='none'      -> raw macros (original behavior, for backward compatibility)
    mode='full'      -> full-sample z-score (uses future data; in-sample only)
    mode='expanding' -> expanding-window z-score using only data up to each
                        month (no look-ahead; correct for pooled OOS protocols)
    Months with fewer than `min_periods` of prior history produce NaN, so the
    earliest months lose interaction features (standard and expected).
    """
    if mode == "none":
        return macro
    out = macro.copy()
    for col in MACRO_COLUMNS:
        s = out[col].astype("float64")
        if mode == "full":
            out[col] = (s - s.mean()) / s.std()
        elif mode == "expanding":
            mean = s.expanding(min_periods=min_periods).mean()
            std = s.expanding(min_periods=min_periods).std()
            out[col] = (s - mean) / std
        else:
            raise ValueError(f"Unknown macro-standardize mode: {mode}")
    return out


def infer_panel_schema(panel_path: Path) -> tuple[list[str], list[str]]:
    header = list(pd.read_csv(panel_path, nrows=0).columns)
    identity_set = set(IDENTITY_COLUMNS)
    missing_identity = identity_set.difference(header)
    if missing_identity:
        missing_text = ", ".join(sorted(missing_identity))
        raise ValueError(f"Panel missing identity columns: {missing_text}")

    if RETURN_COLUMN not in header:
        raise ValueError(f"Panel missing {RETURN_COLUMN!r}")

    char_cols = [
        col
        for col in header
        if col not in identity_set and col != RETURN_COLUMN
    ]
    if RANKED_SIC_COLUMN not in char_cols:
        raise ValueError(
            f"Panel missing ranked {RANKED_SIC_COLUMN!r}; expected among character columns."
        )

    base_chars = [col for col in char_cols if col != RANKED_SIC_COLUMN]
    return header, base_chars


def collect_sic2_codes(panel_path: Path, chunk_size: int) -> list[int]:
    codes: set[int] = set()
    for chunk in pd.read_csv(panel_path, usecols=["sic"], chunksize=chunk_size):
        sic = pd.to_numeric(chunk["sic"], errors="coerce").dropna()
        if len(sic):
            codes.update((sic // 100).astype(int).unique().tolist())
    return sorted(codes)


def interaction_column_names(base_chars: list[str]) -> list[str]:
    names: list[str] = []
    for char in base_chars:
        for macro in MACRO_COLUMNS:
            names.append(f"{char}_x_{macro}")
    return names


def dummy_column_names(sic_codes: list[int]) -> list[str]:
    return [f"sic2d_{code}" for code in sic_codes]


def macro_merge_frame(macro: pd.DataFrame) -> pd.DataFrame:
    """Rename macro value columns to avoid collisions with panel character names (e.g. ep)."""
    rename_map = {"yyyymm": "signal_yyyymm"}
    rename_map.update({col: f"__macro_{col}" for col in MACRO_COLUMNS})
    return macro.rename(columns=rename_map)


def add_interactions(chunk: pd.DataFrame, base_chars: list[str]) -> pd.DataFrame:
    interaction_data: dict[str, np.ndarray] = {}
    for macro in MACRO_COLUMNS:
        macro_vals = chunk[f"__macro_{macro}"].to_numpy(dtype=np.float64)
        for char in base_chars:
            interaction_data[f"{char}_x_{macro}"] = macro_vals * chunk[char].to_numpy(
                dtype=np.float64
            )
    if not interaction_data:
        return chunk
    interactions = pd.DataFrame(interaction_data, index=chunk.index)
    return pd.concat([chunk, interactions], axis=1)


def add_sic_dummies(
    chunk: pd.DataFrame,
    sic_codes: list[int],
    dummy_cols: list[str],
) -> pd.DataFrame:
    sic = pd.to_numeric(chunk["sic"], errors="coerce")
    sic2_raw = (sic // 100).astype("Int64")
    dummies = pd.get_dummies(sic2_raw, prefix="sic2d", dtype=np.float32)
    dummies = dummies.reindex(columns=dummy_cols, fill_value=0.0)
    return pd.concat([chunk, dummies], axis=1)


def build_blended_panel(
    panel_path: Path,
    macro: pd.DataFrame,
    blended_out: Path,
    base_chars: list[str],
    sic_codes: list[int],
    chunk_size: int,
) -> int:
    interaction_cols = interaction_column_names(base_chars)
    dummy_cols = dummy_column_names(sic_codes)
    identity_cols = list(IDENTITY_COLUMNS)
    read_cols = identity_cols + [RETURN_COLUMN] + base_chars

    macro_merge = macro_merge_frame(macro)
    final_cols = (
        identity_cols
        + [RETURN_COLUMN]
        + base_chars
        + interaction_cols
        + dummy_cols
    )

    blended_out.parent.mkdir(parents=True, exist_ok=True)
    row_count = 0
    wrote_header = False

    for chunk in pd.read_csv(panel_path, usecols=read_cols, chunksize=chunk_size):
        chunk = chunk.merge(
            macro_merge,
            on="signal_yyyymm",
            how="left",
        )
        chunk = add_interactions(chunk, base_chars)
        chunk = add_sic_dummies(chunk, sic_codes, dummy_cols)
        chunk = chunk[final_cols]
        row_count += len(chunk)
        chunk.to_csv(
            blended_out,
            mode="w" if not wrote_header else "a",
            header=not wrote_header,
            index=False,
        )
        wrote_header = True

    return row_count


def print_summary(
    macro: pd.DataFrame,
    macro_out: Path,
    blended_out: Path,
    base_chars: list[str],
    sic_codes: list[int],
    panel_rows: int,
) -> None:
    interaction_cols = interaction_column_names(base_chars)
    dummy_cols = dummy_column_names(sic_codes)
    identity_cols = list(IDENTITY_COLUMNS)
    total_cols = len(identity_cols) + 1 + len(base_chars) + len(interaction_cols) + len(dummy_cols)

    print(f"Macro file: {macro_out.resolve()}")
    print(f"  rows: {len(macro):,}")
    print(
        f"  yyyymm: {int(macro['yyyymm'].min())} to {int(macro['yyyymm'].max())}"
    )
    print(f"  columns ({len(MACRO_COLUMNS)}): {', '.join(MACRO_COLUMNS)}")
    print()
    print(f"Blended panel: {blended_out.resolve()}")
    print(f"  rows written: {panel_rows:,}")
    print(f"  total columns: {total_cols}")
    print(f"  identity columns ({len(identity_cols)}): {', '.join(identity_cols)}")
    print(f"  return column: {RETURN_COLUMN}")
    print(f"  base character columns: {len(base_chars)} (excludes ranked {RANKED_SIC_COLUMN})")
    print(f"  interaction columns: {len(interaction_cols)} ({len(base_chars)} x {len(MACRO_COLUMNS)})")
    print(f"  SIC dummy columns: {len(dummy_cols)}")
    print()
    print(f"Unique 2-digit SIC codes = {len(sic_codes)}")
    print(f"  codes: {sic_codes}")
    if blended_out.exists():
        size_mb = blended_out.stat().st_size / (1024 * 1024)
        print(f"  output size: {size_mb:,.1f} MB")


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Build 8 monthly macro predictors from Amit Goyal PredictorData and "
            "blend them into the research panel as macro x character interactions "
            "plus 2-digit SIC one-hot dummies."
        )
    )
    parser.add_argument("--goyal", type=Path, default=DEFAULT_GOYAL)
    parser.add_argument("--panel", type=Path, default=DEFAULT_PANEL)
    parser.add_argument("--macro-out", type=Path, default=DEFAULT_MACRO_OUT)
    parser.add_argument("--blended-out", type=Path, default=DEFAULT_BLENDED_OUT)
    parser.add_argument("--chunk-size", type=int, default=CHUNK_SIZE)
    parser.add_argument(
        "--macro-standardize",
        choices=("none", "full", "expanding"),
        default="expanding",
        help="Standardize macros over the time series before forming interactions. "
        "'expanding' (default) uses only data up to each month (no look-ahead). "
        "'none' reproduces the original raw-macro behavior.",
    )
    parser.add_argument(
        "--macro-min-periods",
        type=int,
        default=60,
        help="Minimum prior months required before expanding z-score is defined.",
    )
    args = parser.parse_args()

    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

    goyal_path = resolve_path(args.goyal)
    panel_path = resolve_path(args.panel)
    macro_out = resolve_path(args.macro_out)
    blended_out = resolve_path(args.blended_out)

    for path, label in (
        (goyal_path, "Goyal PredictorData"),
        (panel_path, "research panel"),
    ):
        if not path.exists():
            raise FileNotFoundError(f"{label} not found: {path}")

    print("Building macro predictors...", flush=True)
    macro = build_macro_predictors(goyal_path)
    macro = standardize_macros(macro, args.macro_standardize, args.macro_min_periods)
    macro_out.parent.mkdir(parents=True, exist_ok=True)
    macro.to_csv(macro_out, index=False)
    print(f"Saved macro predictors: {macro_out.resolve()}", flush=True)

    print("Inferring panel schema...", flush=True)
    _, base_chars = infer_panel_schema(panel_path)
    if len(base_chars) != 94:
        print(
            f"WARNING: expected 94 base character columns, found {len(base_chars)}",
            flush=True,
        )

    print("Collecting 2-digit SIC codes from panel...", flush=True)
    sic_codes = collect_sic2_codes(panel_path, args.chunk_size)

    print("Building blended macro-interaction panel (chunked)...", flush=True)
    panel_rows = build_blended_panel(
        panel_path=panel_path,
        macro=macro,
        blended_out=blended_out,
        base_chars=base_chars,
        sic_codes=sic_codes,
        chunk_size=args.chunk_size,
    )

    print()
    print_summary(
        macro=macro,
        macro_out=macro_out,
        blended_out=blended_out,
        base_chars=base_chars,
        sic_codes=sic_codes,
        panel_rows=panel_rows,
    )


if __name__ == "__main__":
    main()
