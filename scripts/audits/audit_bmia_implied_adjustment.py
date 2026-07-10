#!/usr/bin/env python3
"""Diagnose how datashare.csv bm_ia was constructed (Dr. Qin's implied-adjustment test).

Facts this script tests, using only the published datashare.csv:

Test A (implied industry mean constancy):
    If bm_ia = bm - mean(bm) over some (industry, period) grouping of the SAME
    published bm column, then implied := bm - bm_ia equals that group mean and
    must be IDENTICAL for all firms in the same cell. We measure within-cell
    dispersion of `implied` under candidate groupings (month, month x sic2,
    year x sic2, ...). If no grouping gives ~zero dispersion, the published bm
    is NOT the input to bm_ia.

Test B (monthly market-equity mechanism):
    The GKX/Xiu accounting_60.py source constructs bm_ia from an INTERNAL
    monthly bm = be / me(current month CRSP), then subtracts a benchmark that
    is constant per (datadate, ffi49) cohort:
        bm_ia_t = be / me_t - bm_ind(cohort)
    Within a window where the published (annual) bm is constant, be and
    bm_ind are constant, so bm_ia_t must be LINEAR in 1/me_t with slope be>0.
    datashare's mvel1 is lagged market equity, so we test bm_ia_t against
    1/mvel1_t and 1/mvel1_{t+1} (= 1/me_t) and report per-window R^2.

Output: printed report + CSV summary in outputs/diagnostics/.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
DATASHARE = ROOT / "Supplementary_assistive_files" / "datashare.csv"
OUT_DIR = ROOT / "outputs" / "diagnostics"

MIN_CELL = 5          # min firms per cell for Test A
MIN_WINDOW = 8        # min months per constant-bm window for Test B


def load() -> pd.DataFrame:
    usecols = ["permno", "DATE", "bm", "bm_ia", "mvel1", "sic2"]
    df = pd.read_csv(DATASHARE, usecols=usecols)
    df["month"] = (df["DATE"] // 100).astype("int32")
    df["year"] = (df["DATE"] // 10000).astype("int16")
    df = df.drop(columns=["DATE"])
    df = df.sort_values(["permno", "month"]).reset_index(drop=True)
    df["implied"] = df["bm"] - df["bm_ia"]
    return df


def constancy_test(df: pd.DataFrame, keys: list[str], label: str) -> dict:
    """Within-cell dispersion of implied adjustment under a candidate grouping."""
    d = df.dropna(subset=["implied"] + keys)
    g = d.groupby(keys, sort=False)["implied"]
    stats = g.agg(["count", "min", "max", "std", "mean"])
    stats = stats[stats["count"] >= MIN_CELL]
    rng = stats["max"] - stats["min"]

    # share of total variance explained by cell means (1 = perfectly grouped)
    total_var = d["implied"].var()
    d2 = d.join(g.transform("mean").rename("cell_mean"))
    resid_var = (d2["implied"] - d2["cell_mean"]).var()
    r2 = 1.0 - resid_var / total_var if total_var > 0 else np.nan

    out = {
        "grouping": label,
        "n_cells": len(stats),
        "pct_cells_range_lt_1e-6": 100 * (rng < 1e-6).mean(),
        "pct_cells_range_lt_1e-4": 100 * (rng < 1e-4).mean(),
        "pct_cells_range_lt_1e-2": 100 * (rng < 1e-2).mean(),
        "median_cell_std": float(stats["std"].median()),
        "median_cell_range": float(rng.median()),
        "R2_of_cell_means": float(r2),
    }
    return out


def window_linearity_test(df: pd.DataFrame) -> pd.DataFrame:
    """Test bm_ia_t = slope * (1/me_t) + const within constant-published-bm windows."""
    d = df.dropna(subset=["bm", "bm_ia"]).copy()
    # windows of constant published bm within a permno over consecutive months
    new_win = (
        (d["permno"] != d["permno"].shift())
        | (d["bm"] != d["bm"].shift())
        | (d["month"] - d["month"].shift() != 1)
    )
    d["win"] = new_win.cumsum()

    results = {}
    # candidate x: 1/mvel1 aligned same-month, and shifted so x_t = 1/me_t
    d["inv_mvel1"] = 1.0 / d["mvel1"].replace(0, np.nan)
    d["inv_me_curr"] = d.groupby("permno")["inv_mvel1"].shift(-1)  # mvel1_{t+1} = me_t

    for xcol, label in [("inv_mvel1", "1/mvel1_t (me_{t-1})"),
                        ("inv_me_curr", "1/mvel1_{t+1} (me_t)")]:
        sub = d.dropna(subset=[xcol, "bm_ia"])
        g = sub.groupby("win")
        n = g.size()
        ok = n[n >= MIN_WINDOW].index
        sub = sub[sub["win"].isin(ok)]
        g = sub.groupby("win")

        x, y = sub[xcol], sub["bm_ia"]
        mx, my = g[xcol].transform("mean"), g["bm_ia"].transform("mean")
        dx, dy = x - mx, y - my
        sxx = dx.pow(2).groupby(sub["win"]).sum()
        syy = dy.pow(2).groupby(sub["win"]).sum()
        sxy = (dx * dy).groupby(sub["win"]).sum()
        slope = sxy / sxx.replace(0, np.nan)
        r2 = (sxy.pow(2) / (sxx * syy)).replace([np.inf, -np.inf], np.nan)

        results[label] = {
            "n_windows": len(r2.dropna()),
            "median_R2": float(r2.median()),
            "p25_R2": float(r2.quantile(0.25)),
            "p75_R2": float(r2.quantile(0.75)),
            "pct_R2_gt_0.9": 100 * float((r2 > 0.9).mean()),
            "pct_R2_gt_0.99": 100 * float((r2 > 0.99).mean()),
            "pct_slope_positive": 100 * float((slope > 0).mean()),
        }
    return pd.DataFrame(results).T


def main() -> None:
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

    print("Loading datashare (bm, bm_ia, mvel1, sic2)...", flush=True)
    df = load()
    d_valid = df.dropna(subset=["implied"])
    print(f"rows={len(df):,}  with bm & bm_ia={len(d_valid):,}\n")

    # ---------------- Test A ----------------
    print("=" * 88)
    print("TEST A: is implied adjustment (bm - bm_ia) constant within candidate cells?")
    print("        (it MUST be, if bm_ia = published bm - group mean of published bm)")
    print("=" * 88)
    rows = []
    for keys, label in [
        (["month"], "month only"),
        (["month", "sic2"], "month x sic2"),
        (["year", "sic2"], "year x sic2"),
        (["year"], "year only"),
    ]:
        r = constancy_test(df, keys, label)
        rows.append(r)
        print(
            f"{label:>14}: cells={r['n_cells']:>7,}  "
            f"range<1e-6: {r['pct_cells_range_lt_1e-6']:5.1f}%  "
            f"range<1e-4: {r['pct_cells_range_lt_1e-4']:5.1f}%  "
            f"range<1e-2: {r['pct_cells_range_lt_1e-2']:5.1f}%  "
            f"med_cell_std={r['median_cell_std']:.4f}  R2={r['R2_of_cell_means']:.4f}",
            flush=True,
        )
    res_a = pd.DataFrame(rows)

    # ---------------- Test B ----------------
    print()
    print("=" * 88)
    print("TEST B: within windows where published bm is CONSTANT, is bm_ia linear in 1/ME?")
    print("        (accounting_60.py implies bm_ia_t = be/me_t - const, i.e. R2 ~ 1, slope>0)")
    print("=" * 88)
    res_b = window_linearity_test(df)
    print(res_b.to_string(float_format=lambda v: f"{v:.3f}"))

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    res_a.to_csv(OUT_DIR / "bmia_implied_constancy.csv", index=False)
    res_b.to_csv(OUT_DIR / "bmia_window_linearity.csv")
    print(f"\nWrote {OUT_DIR / 'bmia_implied_constancy.csv'}")
    print(f"Wrote {OUT_DIR / 'bmia_window_linearity.csv'}")


if __name__ == "__main__":
    main()
