#!/usr/bin/env python3
"""Recover the actual bm_ia industry benchmark from datashare and characterize it.

Prior findings (audit_bmia_implied_adjustment / audit_bmia_industry_fingerprint):
  - implied := bm - bm_ia is EXACTLY constant within 44% of (month, sic2) cells,
    R2 of cell means = 0.958 -> grouping is monthly x (something sic2-like);
  - ~62-66 distinct benchmark values per month -> SIC2-like granularity,
    NOT FF49 (<=49) nor FF12/17/30/38;
  - year x sic2 and month-only groupings are rejected.

This script answers the remaining questions:

Test E1 (mode dominance): per (month, sic2) cell, what fraction of firms share
    the modal implied value? High dominance -> grouping IS sic2 x month, with a
    minority of firms misaligned (different SIC vintage in construction).

Test E2 (cross-cell matching): do off-mode firms carry the benchmark of a
    DIFFERENT sic2 the same month? If yes, their construction-time SIC differs
    from the published sic2 (header vs historical SIC vintage issue).

Test E3 (benchmark identity): compare the recovered benchmark (cell mode)
    against candidate statistics of the published bm in the same cell:
    mean, median. If benchmark != in-sample mean, the benchmark universe or the
    underlying bm differs from the published rows (e.g. pre-screen universe or
    unwinsorized bm).

Test E4 (exactness by cell size + firm-level dominance rate).

Output: printed report + CSVs in outputs/diagnostics/.
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
TOL = 1e-6


def load() -> pd.DataFrame:
    df = pd.read_csv(DATASHARE, usecols=["permno", "DATE", "bm", "bm_ia", "sic2"])
    df["month"] = (df["DATE"] // 100).astype("int32")
    df = df.drop(columns=["DATE"])
    df["implied"] = df["bm"] - df["bm_ia"]
    df = df.dropna(subset=["implied", "sic2"]).reset_index(drop=True)
    df["sic2"] = df["sic2"].astype(int)
    # round to tolerance grid so exact float ties group cleanly
    df["implied_r"] = df["implied"].round(6)
    return df


def main() -> None:
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

    print("Loading datashare...", flush=True)
    df = load()
    print(f"rows: {len(df):,}\n")

    cell = df.groupby(["month", "sic2"], sort=False)
    df["cell_n"] = cell["implied"].transform("size")
    d = df[df["cell_n"] >= MIN_CELL].copy()

    # modal implied per cell (the recovered benchmark)
    mode_map = (
        d.groupby(["month", "sic2", "implied_r"]).size().rename("cnt").reset_index()
        .sort_values(["month", "sic2", "cnt"], ascending=[True, True, False])
        .drop_duplicates(["month", "sic2"])
        .rename(columns={"implied_r": "cell_mode", "cnt": "mode_n"})
    )
    d = d.merge(mode_map, on=["month", "sic2"], how="left")
    d["on_mode"] = (d["implied_r"] - d["cell_mode"]).abs() <= TOL

    # ---------------- E1: mode dominance ----------------
    print("=" * 88)
    print("TEST E1: fraction of firms sharing the modal implied benchmark per cell")
    print("=" * 88)
    firm_on_mode = d["on_mode"].mean()
    cell_stats = d.groupby(["month", "sic2"]).agg(
        n=("on_mode", "size"), frac_mode=("on_mode", "mean"))
    print(f"firm-months on their cell's modal benchmark: {100*firm_on_mode:.2f}%")
    print("cell-level distribution of frac_mode:")
    print(cell_stats["frac_mode"].describe().to_string(float_format=lambda v: f"{v:.3f}"))

    # dominance by cell size
    cell_stats["size_bin"] = pd.cut(cell_stats["n"], [4, 10, 25, 50, 100, 10_000],
                                    labels=["5-10", "11-25", "26-50", "51-100", ">100"])
    print("\nfrac_mode and exactness by cell size:")
    by_size = cell_stats.groupby("size_bin", observed=True).agg(
        cells=("frac_mode", "size"),
        mean_frac_mode=("frac_mode", "mean"),
        pct_cells_fully_exact=("frac_mode", lambda s: 100 * (s >= 0.999).mean()),
    )
    print(by_size.to_string(float_format=lambda v: f"{v:.3f}"))

    # ---------------- E2: off-mode firms match another sic2's benchmark? ----
    print()
    print("=" * 88)
    print("TEST E2: do off-mode firms carry the benchmark of ANOTHER sic2 that month?")
    print("=" * 88)
    bench_lookup = mode_map[["month", "sic2", "cell_mode"]].rename(
        columns={"sic2": "bench_sic2", "cell_mode": "bench_val"})
    off = d[~d["on_mode"]][["permno", "month", "sic2", "implied_r"]].copy()
    print(f"off-mode firm-months: {len(off):,} ({100*len(off)/len(d):.2f}% of firm-months)")
    m = off.merge(bench_lookup, left_on=["month", "implied_r"],
                  right_on=["month", "bench_val"], how="left")
    matched = m.dropna(subset=["bench_sic2"])
    match_rate = m["bench_sic2"].notna().groupby(m.index).any().mean()
    print(f"off-mode firms whose implied EXACTLY equals another sic2's benchmark "
          f"the same month: {100*match_rate:.2f}%")
    if len(matched):
        same2 = (matched["bench_sic2"].astype(int) == matched["sic2"]).mean()
        ex = matched.groupby(["sic2", "bench_sic2"]).size().sort_values(ascending=False).head(15)
        print(f"(of which pointing back to own sic2 - float ties: {100*same2:.1f}%)")
        print("\ntop published_sic2 -> construction_sic2 reassignments:")
        print(ex.to_string())

    # ---------------- E3: benchmark vs in-cell statistics of published bm ----
    print()
    print("=" * 88)
    print("TEST E3: recovered benchmark vs statistics of PUBLISHED bm in the same cell")
    print("=" * 88)
    stats = d.groupby(["month", "sic2"]).agg(
        bench=("cell_mode", "first"),
        bm_mean=("bm", "mean"),
        bm_median=("bm", "median"),
        n=("bm", "size"),
    ).reset_index()
    for cand in ["bm_mean", "bm_median"]:
        diff = stats["bench"] - stats[cand]
        rel = diff.abs() / stats[cand].abs().replace(0, np.nan)
        print(f"benchmark vs {cand:10s}: exact(<1e-4): {100*(diff.abs()<1e-4).mean():5.1f}%   "
              f"median diff: {diff.median():+.4f}   median |rel diff|: {100*rel.median():.1f}%   "
              f"corr: {stats['bench'].corr(stats[cand]):.4f}")
    ratio = stats["bench"] / stats["bm_mean"].replace(0, np.nan)
    print("\nbenchmark / in-cell mean(published bm) ratio distribution:")
    print(ratio.describe().to_string(float_format=lambda v: f"{v:.3f}"))
    by_dec = stats.assign(decade=(stats["month"] // 1000) * 10).groupby("decade").apply(
        lambda g: pd.Series({
            "median_bench": g["bench"].median(),
            "median_bm_mean": g["bm_mean"].median(),
            "median_ratio": (g["bench"] / g["bm_mean"].replace(0, np.nan)).median(),
        }), include_groups=False)
    print("\nby decade:")
    print(by_dec.to_string(float_format=lambda v: f"{v:.3f}"))

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    stats.to_csv(OUT_DIR / "bmia_recovered_benchmarks.csv", index=False)
    cell_stats.reset_index().to_csv(OUT_DIR / "bmia_cell_mode_dominance.csv", index=False)
    print(f"\nWrote {OUT_DIR / 'bmia_recovered_benchmarks.csv'}")
    print(f"Wrote {OUT_DIR / 'bmia_cell_mode_dominance.csv'}")


if __name__ == "__main__":
    main()
