#!/usr/bin/env python3
"""Remaining bm_ia blocker tests: why does the monthly benchmark move, when is it
computed, and over what universe?

Test J (skepticism check): each firm's bm is annual, so why does a monthly
    (sic2, month) mean move? Decompose consecutive-month benchmark changes into
    (a) some member's bm refreshed, (b) membership churn (entry/exit), (c) both,
    (d) neither (benchmark should be CONSTANT then - key falsification test).

Test F (benchmark timing): compare recovered modal benchmark(t) against the
    in-cell mean of published bm at months t-2..t+2. If exactness peaks off
    k=0, the benchmark is computed on a shifted universe.

Test G (benchmark universe):
    G1: row-wise null asymmetry between bm and bm_ia.
    G2: in cells where benchmark != in-cell mean, do winsorized/trimmed means
        explain the benchmark better?
    G3: how much of the paired-obs mass sits in exact-match cells vs not; and
        the naive-mean reconstruction quality WITHIN exact cells vs mismatch
        cells (upper bound for a real builder on a matching universe).
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
    return df


def month_index(m: pd.Series) -> pd.Series:
    return ((m // 100) * 12 + (m % 100)).astype("int64")


def recovered_benchmarks(d: pd.DataFrame) -> pd.DataFrame:
    d = d.copy()
    d["implied_r"] = (d["bm"] - d["bm_ia"]).round(6)
    mode_map = (
        d.groupby(["month", "sic2", "implied_r"]).size().rename("cnt").reset_index()
        .sort_values(["month", "sic2", "cnt"], ascending=[True, True, False])
        .drop_duplicates(["month", "sic2"])
        .rename(columns={"implied_r": "bench"})[["month", "sic2", "bench", "cnt"]]
    )
    return mode_map


def main() -> None:
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

    print("Loading datashare...", flush=True)
    raw = load()

    # ---------------- Test G1: null asymmetry ----------------
    print("=" * 88)
    print("TEST G1: row-wise null asymmetry between bm and bm_ia")
    print("=" * 88)
    both = (raw["bm"].notna() & raw["bm_ia"].notna()).sum()
    bm_only = (raw["bm"].notna() & raw["bm_ia"].isna()).sum()
    ia_only = (raw["bm"].isna() & raw["bm_ia"].notna()).sum()
    print(f"bm & bm_ia both non-null: {both:,}")
    print(f"bm non-null, bm_ia null : {bm_only:,}")
    print(f"bm null, bm_ia non-null : {ia_only:,}")

    d = raw.dropna(subset=["bm", "bm_ia", "sic2"]).copy()
    d["sic2"] = d["sic2"].astype(int)
    d["midx"] = month_index(d["month"])
    cell_sizes = d.groupby(["month", "sic2"])["bm"].transform("size")
    d = d[cell_sizes >= MIN_CELL].copy()

    bench = recovered_benchmarks(d)
    bench["midx"] = month_index(bench["month"])

    # ---------------- Test J ----------------
    print()
    print("=" * 88)
    print("TEST J: why does the (sic2, month) benchmark move month-over-month?")
    print("        decomposition over consecutive-month cell pairs")
    print("=" * 88)
    # per (sic2, month): membership set hash and per-firm bm
    d = d.sort_values(["sic2", "permno", "midx"])
    d["bm_prev"] = d.groupby(["sic2", "permno"])["bm"].shift()
    d["midx_prev"] = d.groupby(["sic2", "permno"])["midx"].shift()
    d["stayed"] = d["midx_prev"] == d["midx"] - 1
    d["refreshed"] = d["stayed"] & (d["bm"] != d["bm_prev"])

    cellstat = d.groupby(["sic2", "midx"]).agg(
        n=("permno", "size"),
        n_stayed=("stayed", "sum"),
        n_refreshed=("refreshed", "sum"),
        month=("month", "first"),
    ).reset_index().sort_values(["sic2", "midx"])
    cellstat["n_prev"] = cellstat.groupby("sic2")["n"].shift()
    cellstat["midx_prev"] = cellstat.groupby("sic2")["midx"].shift()
    consec = cellstat[cellstat["midx_prev"] == cellstat["midx"] - 1].copy()
    # membership churn: entrants = n - n_stayed; exits = n_prev - n_stayed
    consec["entrants"] = consec["n"] - consec["n_stayed"]
    consec["exits"] = consec["n_prev"] - consec["n_stayed"]
    consec["churn"] = (consec["entrants"] > 0) | (consec["exits"] > 0)
    consec["any_refresh"] = consec["n_refreshed"] > 0

    bench_l = bench.set_index(["sic2", "midx"])["bench"]
    consec = consec.set_index(["sic2", "midx"])
    consec["bench"] = bench_l
    consec = consec.reset_index()
    consec["bench_prev"] = consec.groupby("sic2")["bench"].shift()
    # only rows where both benchmarks known and months consecutive already ensured
    cc = consec.dropna(subset=["bench", "bench_prev"]).copy()
    cc["bench_moved"] = (cc["bench"] - cc["bench_prev"]).abs() > TOL

    n = len(cc)
    print(f"consecutive-month cell pairs analyzed: {n:,}")
    print(f"benchmark moved: {100*cc['bench_moved'].mean():.1f}% of pairs")
    print()
    grp = cc.groupby([cc["any_refresh"], cc["churn"]])["bench_moved"].agg(["size", "mean"])
    grp.index.names = ["member_bm_refreshed", "membership_churned"]
    grp["share_of_pairs_pct"] = 100 * grp["size"] / n
    grp["bench_moved_pct"] = 100 * grp["mean"]
    print(grp[["size", "share_of_pairs_pct", "bench_moved_pct"]].to_string(
        float_format=lambda v: f"{v:.1f}"))
    quiet = cc[~cc["any_refresh"] & ~cc["churn"]]
    print(f"\nKEY falsification cell-pairs (NO refresh, NO churn): {len(quiet):,} "
          f"-> benchmark moved in {100*quiet['bench_moved'].mean():.2f}% of them "
          f"(should be ~0 if grouping+universe are right)")

    # ---------------- Test F ----------------
    print()
    print("=" * 88)
    print("TEST F: recovered benchmark(t) vs in-cell mean(published bm) at t+k")
    print("=" * 88)
    means = d.groupby(["sic2", "midx"])["bm"].mean().rename("cellmean").reset_index()
    for k in (-2, -1, 0, 1, 2):
        m = bench.merge(
            means.assign(midx=(means["midx"] - k).astype("int64")),
            on=["sic2", "midx"], how="inner")
        diff = (m["bench"] - m["cellmean"]).abs()
        print(f"k={k:+d}: cells={len(m):>7,}  exact(<1e-4): {100*(diff<1e-4).mean():5.1f}%  "
              f"median|diff|={diff.median():.4f}  corr={m['bench'].corr(m['cellmean']):.4f}")

    # ---------------- Test G2: robust-mean variants in mismatch cells ----------
    print()
    print("=" * 88)
    print("TEST G2: winsorized/trimmed in-cell means vs benchmark (mismatch cells only)")
    print("=" * 88)
    d = d.merge(bench[["sic2", "midx", "bench"]], on=["sic2", "midx"], how="left")
    cellkey = ["sic2", "midx"]
    plain = d.groupby(cellkey)["bm"].mean().rename("mean_plain")
    q = d.groupby("midx")["bm"].quantile([0.01, 0.99]).unstack()
    d = d.join(q, on="midx")
    d["bm_w"] = d["bm"].clip(d[0.01], d[0.99])
    wins = d.groupby(cellkey)["bm_w"].mean().rename("mean_winsor_1_99_month")

    def trimmed(s: pd.Series) -> float:
        if len(s) < 5:
            return np.nan
        lo, hi = s.quantile(0.01), s.quantile(0.99)
        return s[(s >= lo) & (s <= hi)].mean()

    trim = d.groupby(cellkey)["bm"].apply(trimmed).rename("mean_trim_cell_1_99")
    tests = pd.concat([plain, wins, trim], axis=1).reset_index().merge(
        bench[["sic2", "midx", "bench"]], on=cellkey)
    mismatch = tests[(tests["bench"] - tests["mean_plain"]).abs() >= 1e-4]
    print(f"mismatch cells (benchmark != plain mean): {len(mismatch):,} of {len(tests):,}")
    for col in ["mean_plain", "mean_winsor_1_99_month", "mean_trim_cell_1_99"]:
        diff = (mismatch["bench"] - mismatch[col]).abs()
        print(f"  {col:26s}: exact(<1e-4): {100*(diff<1e-4).mean():5.1f}%  "
              f"median|diff|={diff.median():.4f}")

    # ---------------- Test G3: reconstruction quality split ----------
    print()
    print("=" * 88)
    print("TEST G3: naive-mean reconstruction quality, exact-benchmark cells vs mismatch")
    print("=" * 88)
    d["cellmean"] = d.groupby(cellkey)["bm"].transform("mean")
    d["hat"] = d["bm"] - d["cellmean"]
    d["cell_exact"] = (d["bench"] - d["cellmean"]).abs() < 1e-4
    for flag, label in [(True, "cells where benchmark == plain mean"),
                        (False, "cells where benchmark != plain mean")]:
        sub = d[d["cell_exact"] == flag]
        rho = sub["bm_ia"].corr(sub["hat"], method="spearman")
        ex = 100 * ((sub["bm_ia"] - sub["hat"]).abs() <= 1e-4).mean()
        print(f"{label}: firm-months={len(sub):,} ({100*len(sub)/len(d):.1f}%)  "
              f"pooled rho={rho:.4f}  exact={ex:.1f}%")

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    cc.to_csv(OUT_DIR / "bmia_benchmark_movement_decomposition.csv", index=False)
    print(f"\nWrote {OUT_DIR / 'bmia_benchmark_movement_decomposition.csv'}")


if __name__ == "__main__":
    main()
