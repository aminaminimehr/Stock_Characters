#!/usr/bin/env python3
"""Final validation: reconstruct datashare bm_ia as bm - benchmark(sic2, month).

Two reconstructions of the industry benchmark, per (sic2, month) cell:
  1. cell MEAN of published bm  (the naive replication formula)
  2. cell MODE of implied (bm - bm_ia)  (the recovered construction benchmark;
     robust to the ~3% of firms whose construction-time SIC differs)

Reports the five required metrics for each: median monthly Spearman, pooled
Spearman, exact rate, paired N, unique permnos.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
DATASHARE = ROOT / "Supplementary_assistive_files" / "datashare.csv"
OUT_DIR = ROOT / "outputs" / "diagnostics"
MIN_CELL = 5
MIN_PAIRS = 50


def monthly_median_spearman(df: pd.DataFrame, a: str, b: str) -> float:
    vals = []
    for _, grp in df.groupby("month", sort=True):
        sub = grp[[a, b]].dropna()
        if len(sub) < MIN_PAIRS:
            continue
        r = sub[a].corr(sub[b], method="spearman")
        if pd.notna(r):
            vals.append(r)
    return float(np.median(vals)) if vals else np.nan


def report(df: pd.DataFrame, hat_col: str, label: str) -> dict:
    sub = df.dropna(subset=["bm_ia", hat_col])
    diff = (sub["bm_ia"] - sub[hat_col]).abs()
    return {
        "candidate": label,
        "median_monthly_spearman": monthly_median_spearman(sub, "bm_ia", hat_col),
        "pooled_spearman": float(sub["bm_ia"].corr(sub[hat_col], method="spearman")),
        "exact_rate_1e-4_pct": 100 * float((diff <= 1e-4).mean()),
        "paired_N": len(sub),
        "unique_permnos": int(sub["permno"].nunique()),
    }


def main() -> None:
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

    print("Loading datashare...", flush=True)
    df = pd.read_csv(DATASHARE, usecols=["permno", "DATE", "bm", "bm_ia", "sic2"])
    df["month"] = (df["DATE"] // 100).astype("int32")
    df = df.dropna(subset=["bm", "bm_ia", "sic2"]).reset_index(drop=True)
    df["sic2"] = df["sic2"].astype(int)
    df["implied_r"] = (df["bm"] - df["bm_ia"]).round(6)

    cell = df.groupby(["month", "sic2"])
    df["cell_n"] = cell["bm"].transform("size")
    df = df[df["cell_n"] >= MIN_CELL].copy()

    # candidate 1: in-cell mean of published bm
    df["bench_mean"] = df.groupby(["month", "sic2"])["bm"].transform("mean")
    df["hat_mean"] = df["bm"] - df["bench_mean"]

    # candidate 2: modal implied benchmark
    mode_map = (
        df.groupby(["month", "sic2", "implied_r"]).size().rename("cnt").reset_index()
        .sort_values(["month", "sic2", "cnt"], ascending=[True, True, False])
        .drop_duplicates(["month", "sic2"])
        .rename(columns={"implied_r": "bench_mode"})[["month", "sic2", "bench_mode"]]
    )
    df = df.merge(mode_map, on=["month", "sic2"], how="left")
    df["hat_mode"] = df["bm"] - df["bench_mode"]

    rows = [
        report(df, "hat_mean", "bm - mean(published bm) by (sic2, month)"),
        report(df, "hat_mode", "bm - modal implied benchmark by (sic2, month)"),
    ]
    res = pd.DataFrame(rows)
    print()
    print(res.to_string(index=False, float_format=lambda v: f"{v:.4f}"))

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    res.to_csv(OUT_DIR / "bmia_reconstruction_check.csv", index=False)
    print(f"\nWrote {OUT_DIR / 'bmia_reconstruction_check.csv'}")


if __name__ == "__main__":
    main()
