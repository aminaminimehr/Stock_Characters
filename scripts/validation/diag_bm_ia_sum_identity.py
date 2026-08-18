#!/usr/bin/env python3
"""Test sum(bm) = mean(bm) x n universe identity for datashare bm_ia.

For each (sic2, month) cell, if bm_ia = bm - mean(bm) over the construction
universe, then sum(published bm) must equal n x recovered_mean where
recovered_mean := modal(bm - bm_ia) and n is the published cell size.

A systematic gap localizes whether the published universe differs from the
benchmark construction universe (firms screened in/out before publication).

Outputs:
  outputs/diagnostics/bmia_sum_identity_cell.csv
  outputs/diagnostics/bmia_sum_identity_summary.txt
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
DATASHARE = ROOT / "Supplementary_assistive_files" / "datashare.csv"
OUT_DIR = ROOT / "outputs" / "diagnostics"

MIN_CELL = 5
TOL = 1e-6
IDENTITY_TOL = 1e-4


def load_datashare(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path, usecols=["permno", "DATE", "bm", "bm_ia", "sic2"])
    df["month"] = (df["DATE"] // 100).astype("int32")
    df = df.drop(columns=["DATE"])
    df["implied"] = df["bm"] - df["bm_ia"]
    df = df.dropna(subset=["implied", "bm", "sic2"]).reset_index(drop=True)
    df["sic2"] = df["sic2"].astype(int)
    df["implied_r"] = df["implied"].round(6)
    return df


def recover_cell_benchmarks(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Attach modal implied benchmark per (month, sic2); return firm-level + cell stats."""
    cell = df.groupby(["month", "sic2"], sort=False)
    d = df.assign(cell_n=cell["implied"].transform("size"))
    d = d[d["cell_n"] >= MIN_CELL].copy()

    mode_map = (
        d.groupby(["month", "sic2", "implied_r"]).size().rename("cnt").reset_index()
        .sort_values(["month", "sic2", "cnt"], ascending=[True, True, False])
        .drop_duplicates(["month", "sic2"])
        .rename(columns={"implied_r": "bench", "cnt": "mode_n"})
    )
    d = d.merge(mode_map, on=["month", "sic2"], how="left")
    d["on_mode"] = (d["implied_r"] - d["bench"]).abs() <= TOL

    cell_stats = d.groupby(["month", "sic2"], as_index=False).agg(
        n_pub=("bm", "size"),
        sum_bm_pub=("bm", "sum"),
        bench=("bench", "first"),
        bm_mean_pub=("bm", "mean"),
        frac_on_mode=("on_mode", "mean"),
        mode_n=("mode_n", "first"),
    )
    cell_stats["identity_lhs"] = cell_stats["n_pub"] * cell_stats["bench"]
    cell_stats["gap_abs"] = cell_stats["sum_bm_pub"] - cell_stats["identity_lhs"]
    denom = cell_stats["identity_lhs"].replace(0, np.nan)
    cell_stats["gap_rel"] = cell_stats["gap_abs"] / denom
    cell_stats["identity_holds"] = cell_stats["gap_abs"].abs() <= IDENTITY_TOL

    near_zero_bench = cell_stats["bench"].abs() <= TOL
    cell_stats["n_construction_implied"] = np.where(
        near_zero_bench,
        np.nan,
        cell_stats["sum_bm_pub"] / cell_stats["bench"],
    )
    cell_stats["delta_n"] = cell_stats["n_construction_implied"] - cell_stats["n_pub"]
    cell_stats["delta_n_rel"] = cell_stats["delta_n"] / cell_stats["n_pub"]
    cell_stats["decade"] = (cell_stats["month"] // 1000) * 10
    cell_stats["size_bin"] = pd.cut(
        cell_stats["n_pub"],
        [4, 10, 25, 50, 100, 10_000],
        labels=["5-10", "11-25", "26-50", "51-100", ">100"],
    )
    cell_stats["mean_gap_abs"] = (cell_stats["bm_mean_pub"] - cell_stats["bench"]).abs()
    cell_stats["mean_matches_bench"] = cell_stats["mean_gap_abs"] <= IDENTITY_TOL

    return d, cell_stats


def summarize_cells(cell_stats: pd.DataFrame) -> dict:
    n = len(cell_stats)
    holds = cell_stats["identity_holds"]
    gap = cell_stats["gap_abs"]
    return {
        "n_cells": n,
        "pct_identity_holds": 100 * holds.mean(),
        "pct_gap_negative": 100 * (gap < -IDENTITY_TOL).mean(),
        "pct_gap_positive": 100 * (gap > IDENTITY_TOL).mean(),
        "median_gap_rel": float(cell_stats["gap_rel"].median()),
        "mean_gap_rel": float(cell_stats["gap_rel"].mean()),
        "median_gap_abs": float(gap.median()),
        "mean_gap_abs": float(gap.mean()),
        "median_delta_n": float(cell_stats["delta_n"].median()),
        "mean_delta_n": float(cell_stats["delta_n"].mean()),
        "pct_mean_matches_bench": 100 * cell_stats["mean_matches_bench"].mean(),
    }


def cross_check_residual(d: pd.DataFrame, cell_stats: pd.DataFrame) -> pd.DataFrame:
    """Tabulate overlap: identity-hold cells vs on-mode fraction / mean-match."""
    merged = cell_stats.merge(
        d.groupby(["month", "sic2"], as_index=False).agg(
            firm_months=("on_mode", "size"),
            firm_on_mode=("on_mode", "sum"),
        ),
        on=["month", "sic2"],
        how="left",
    )
    merged["all_firms_on_mode"] = merged["frac_on_mode"] >= 0.999
    merged["residual_bucket"] = np.select(
        [
            merged["identity_holds"] & merged["all_firms_on_mode"],
            merged["identity_holds"] & ~merged["all_firms_on_mode"],
            ~merged["identity_holds"] & merged["all_firms_on_mode"],
            ~merged["identity_holds"] & ~merged["all_firms_on_mode"],
        ],
        [
            "identity_holds_and_all_on_mode",
            "identity_holds_but_off_mode_firms",
            "identity_fails_all_on_mode",
            "identity_fails_with_off_mode",
        ],
        default="other",
    )
    return merged


def delta_n_histogram(cell_stats: pd.DataFrame) -> pd.Series:
    """Round delta_n to nearest integer for histogram of implied extra/missing firms."""
    valid = cell_stats.dropna(subset=["delta_n"]).copy()
    valid["delta_n_round"] = valid["delta_n"].round().astype("Int64")
    return valid.groupby("delta_n_round").size().sort_index()


def format_summary(
    overall: dict,
    by_decade: pd.DataFrame,
    by_size: pd.DataFrame,
    cross: pd.DataFrame,
    delta_hist: pd.Series,
) -> str:
    lines = [
        "=== bm_ia sum(bm) = mean x n universe identity test ===",
        "",
        "Per (sic2, month) cell with n >= 5:",
        f"  cells tested                 : {overall['n_cells']:,}",
        f"  identity holds (|gap|<=1e-4)  : {overall['pct_identity_holds']:.2f}%",
        f"  gap < 0 (construction larger): {overall['pct_gap_negative']:.2f}%",
        f"  gap > 0 (publication larger) : {overall['pct_gap_positive']:.2f}%",
        f"  median gap_rel               : {overall['median_gap_rel']:+.6f}",
        f"  mean gap_rel                 : {overall['mean_gap_rel']:+.6f}",
        f"  median gap_abs               : {overall['median_gap_abs']:+.6f}",
        f"  median delta_n (implied n - pub n): {overall['median_delta_n']:+.4f}",
        f"  mean delta_n                 : {overall['mean_delta_n']:+.4f}",
        f"  cells where mean(bm)==bench  : {overall['pct_mean_matches_bench']:.2f}%",
        "",
        "Interpretation:",
        "  gap = sum(bm) - n_pub * recovered_bench",
        "  delta_n = sum(bm)/bench - n_pub  (implied construction universe size)",
        "",
        "--- By decade ---",
        by_decade.to_string(float_format=lambda v: f"{v:.3f}"),
        "",
        "--- By cell size ---",
        by_size.to_string(float_format=lambda v: f"{v:.3f}"),
        "",
        "--- Residual cross-check (identity vs on-mode firms) ---",
        cross.groupby("residual_bucket").size().to_string(),
        "",
        "--- delta_n histogram (rounded to nearest integer) ---",
        delta_hist.head(20).to_string(),
    ]
    if len(delta_hist) > 20:
        lines.append(f"  ... ({len(delta_hist)} distinct values total)")
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--datashare", type=Path, default=DATASHARE)
    args = parser.parse_args()

    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

    print(f"Loading datashare: {args.datashare}", flush=True)
    df = load_datashare(args.datashare)
    print(f"rows with bm, bm_ia, sic2: {len(df):,}", flush=True)

    d, cell_stats = recover_cell_benchmarks(df)
    overall = summarize_cells(cell_stats)

    by_decade = cell_stats.groupby("decade").agg(
        cells=("identity_holds", "size"),
        pct_identity_holds=("identity_holds", lambda s: 100 * s.mean()),
        median_gap_rel=("gap_rel", "median"),
        median_delta_n=("delta_n", "median"),
        pct_mean_matches=("mean_matches_bench", lambda s: 100 * s.mean()),
    )

    by_size = cell_stats.groupby("size_bin", observed=True).agg(
        cells=("identity_holds", "size"),
        pct_identity_holds=("identity_holds", lambda s: 100 * s.mean()),
        median_gap_rel=("gap_rel", "median"),
        median_delta_n=("delta_n", "median"),
    )

    cross = cross_check_residual(d, cell_stats)
    delta_hist = delta_n_histogram(cell_stats)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    cell_out = OUT_DIR / "bmia_sum_identity_cell.csv"
    summary_out = OUT_DIR / "bmia_sum_identity_summary.txt"
    cross_out = OUT_DIR / "bmia_sum_identity_crosscheck.csv"

    cell_stats.to_csv(cell_out, index=False)
    cross[["month", "sic2", "n_pub", "bench", "sum_bm_pub", "identity_lhs", "gap_abs",
           "gap_rel", "identity_holds", "delta_n", "frac_on_mode", "residual_bucket"]].to_csv(
        cross_out, index=False
    )

    text = format_summary(overall, by_decade, by_size, cross, delta_hist)
    summary_out.write_text(text, encoding="utf-8")
    print("\n" + text)
    print(f"\nWrote {cell_out}")
    print(f"Wrote {cross_out}")
    print(f"Wrote {summary_out}")


if __name__ == "__main__":
    main()
