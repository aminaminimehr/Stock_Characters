#!/usr/bin/env python3
"""Internal-consistency audit of datashare industry-adjusted (IA) characters.

Generalizes the bm_ia implied-adjustment recipe to any datashare pair where BOTH
the base and the adjusted column are published. Tests whether the published
adjusted column is cleanly re-derivable from the published base + sic2.

For each (base, adjusted) pair, run four tests:

  1. Constancy test: implied := base - adjusted must be IDENTICAL for all firms
     in a grouping cell if adjusted = base - mean(base) over that cell.
       bm_ia reference (month x sic2): ~44.4% cells constant, R2 ~0.958.

  2. Reconstruction (naive mean): hat_mean = base - groupby.mean(base) vs
     published adjusted. INDEPENDENT ceiling.
       bm_ia reference: ~0.8323 median rho, ~17.5% exact.

  3. Modal benchmark (CIRCULAR ceiling): hat_mode = base - groupby.mode(implied)
     vs published adjusted. Uses info from the adjusted column itself.
       bm_ia reference: ~0.9921 median rho, ~97.1% exact.

  4. Mode dominance + off-mode cross-sic2 matching (SIC-vintage signature).
       bm_ia reference: ~97.09% on-mode, ~19.5% of off-mode match another sic2.

Grouping:
  - bm_ia  : (sic2, calendar month)
  - cfp_ia / chempia : (sic2, fyear). datashare has no fyear column, so fyear
    is inferred per permno from base-value step-change points. A (sic2, year)
    fallback with year = DATE//10000 is also reported.

Usage:
  python scripts/audits/audit_ia_implied_adjustment.py
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
TOL = 1e-6

PAIRS = [
    {"label": "bm_ia", "base": "bm", "adj": "bm_ia",
     "primary_keys": ["month", "sic2"], "fallback_keys": ["year", "sic2"], "period": "month"},
    {"label": "cfp_ia", "base": "cfp", "adj": "cfp_ia",
     "primary_keys": ["fyear", "sic2"], "fallback_keys": ["year", "sic2"], "period": "year"},
    {"label": "chempia", "base": "hire", "adj": "chempia",
     "primary_keys": ["fyear", "sic2"], "fallback_keys": ["year", "sic2"], "period": "year"},
]


def load_pair(base_col, adj_col):
    usecols = ["permno", "DATE", base_col, adj_col, "sic2"]
    df = pd.read_csv(DATASHARE, usecols=usecols)
    df["month"] = (df["DATE"] // 100).astype("int32")
    df["year"] = (df["DATE"] // 10000).astype("int16")
    df = df.drop(columns=["DATE"])
    df = df.sort_values(["permno", "month"]).reset_index(drop=True)
    df["implied"] = df[base_col] - df[adj_col]
    return df


def add_inferred_fyear(df, base_col):
    """Infer fiscal year from June-expansion timing (calendar-aligned).

    datashare applies annual data for fiscal year Y starting June of year Y+1
    (June expansion). So a row at month YYYYMM maps to:
        month-of-year in [6..12] -> fyear = YYYY - 1
        month-of-year in [1..5] -> fyear = YYYY - 2
    This calendar-aligned fyear lets the (sic2, fyear) cohort be recovered from
    datashare alone (which has no fyear column), so the naive-mean
    reconstruction is meaningful rather than pooling firms from different
    true fiscal years.
    """
    d = df.copy()
    moy = d["month"] % 100
    d["fyear"] = d["year"] - np.where(moy >= 6, 1, 2)
    d["fyear"] = d["fyear"].astype("int16")
    return d


def constancy_test(df, keys, label):
    d = df.dropna(subset=["implied"] + keys)
    g = d.groupby(keys, sort=False)["implied"]
    stats = g.agg(["count", "min", "max", "std", "mean"])
    stats = stats[stats["count"] >= MIN_CELL]
    rng = stats["max"] - stats["min"]
    total_var = d["implied"].var()
    cell_mean = g.transform("mean")
    resid_var = (d["implied"] - cell_mean).var()
    r2 = 1.0 - resid_var / total_var if total_var > 0 else np.nan
    return {
        "grouping": label,
        "n_cells": int(len(stats)),
        "pct_cells_range_lt_1e-6": 100 * float((rng < 1e-6).mean()) if len(rng) else np.nan,
        "pct_cells_range_lt_1e-4": 100 * float((rng < 1e-4).mean()) if len(rng) else np.nan,
        "median_cell_std": float(stats["std"].median()) if len(stats) else np.nan,
        "median_cell_range": float(rng.median()) if len(rng) else np.nan,
        "R2_of_cell_means": float(r2),
    }


def _period_spearman(df, a, b, period):
    vals = []
    for _, grp in df.groupby(period, sort=True):
        sub = grp[[a, b]].dropna()
        if len(sub) < MIN_PAIRS:
            continue
        r = sub[a].corr(sub[b], method="spearman")
        if pd.notna(r):
            vals.append(r)
    return float(np.median(vals)) if vals else np.nan


def reconstruction_test(df, base_col, adj_col, keys, period, label):
    d = df.dropna(subset=[base_col, adj_col] + keys).copy()
    d["cell_n"] = d.groupby(keys)[base_col].transform("size")
    d = d[d["cell_n"] >= MIN_CELL].copy()
    d["bench_mean"] = d.groupby(keys)[base_col].transform("mean")
    d["hat_mean"] = d[base_col] - d["bench_mean"]
    sub = d.dropna(subset=[adj_col, "hat_mean"])
    diff = (sub[adj_col] - sub["hat_mean"]).abs()
    return {
        "candidate": label,
        "median_period_spearman": _period_spearman(sub, adj_col, "hat_mean", period),
        "pooled_spearman": float(sub[adj_col].corr(sub["hat_mean"], method="spearman")),
        "exact_rate_1e-4_pct": 100 * float((diff <= 1e-4).mean()),
        "paired_N": int(len(sub)),
        "unique_permnos": int(sub["permno"].nunique()),
    }


def modal_test(df, base_col, adj_col, keys, period, label):
    d = df.dropna(subset=[base_col, adj_col] + keys).copy()
    d["cell_n"] = d.groupby(keys)[base_col].transform("size")
    d = d[d["cell_n"] >= MIN_CELL].copy()
    d["implied_r"] = d["implied"].round(6)
    mode_map = (
        d.groupby(keys + ["implied_r"]).size().rename("cnt").reset_index()
        .sort_values(keys + ["cnt"], ascending=[True] * len(keys) + [False])
        .drop_duplicates(keys)
        .rename(columns={"implied_r": "bench_mode"})
    )
    d = d.merge(mode_map, on=keys, how="left")
    d["on_mode"] = (d["implied_r"] - d["bench_mode"]).abs() <= TOL
    d["hat_mode"] = d[base_col] - d["bench_mode"]
    sub = d.dropna(subset=[adj_col, "hat_mode"])
    diff = (sub[adj_col] - sub["hat_mode"]).abs()
    metrics = {
        "candidate": label,
        "median_period_spearman": _period_spearman(sub, adj_col, "hat_mode", period),
        "pooled_spearman": float(sub[adj_col].corr(sub["hat_mode"], method="spearman")),
        "exact_rate_1e-4_pct": 100 * float((diff <= 1e-4).mean()),
        "paired_N": int(len(sub)),
        "unique_permnos": int(sub["permno"].nunique()),
        "pct_on_mode": 100 * float(d["on_mode"].mean()),
    }
    # off-mode cross-sic2 matching (SIC-vintage signature)
    off = d[~d["on_mode"]].copy()
    cross_pct = np.nan
    if len(off) and "sic2" in mode_map.columns:
        period_col = keys[0]
        lk = mode_map.rename(columns={period_col: "p", "bench_mode": "bench_val"})
        m = off.merge(lk[["p", "bench_val", "sic2"]],
                      left_on=[keys[0], "implied_r"], right_on=["p", "bench_val"], how="left")
        if "sic2_y" in m.columns:
            cross_pct = 100 * float(m["sic2_y"].notna().mean())
    metrics["pct_offmode_cross_sic2_match"] = cross_pct
    return metrics


def run_pair(spec):
    label = spec["label"]
    base_col, adj_col = spec["base"], spec["adj"]
    print(f"\n{'=' * 88}\n  {label}:  base={base_col}  adj={adj_col}\n{'=' * 88}", flush=True)
    df = load_pair(base_col, adj_col)
    n_valid = int(df.dropna(subset=["implied"]).shape[0])
    print(f"rows={len(df):,}  with {base_col}&{adj_col}={n_valid:,}", flush=True)
    if "fyear" in spec["primary_keys"]:
        df = add_inferred_fyear(df, base_col)

    const_rows, rec_rows, mod_rows = [], [], []
    for keys, glabel in [(spec["primary_keys"], "primary"), (spec["fallback_keys"], "fallback")]:
        if not all(k in df.columns for k in keys):
            continue
        r = constancy_test(df, keys, glabel)
        const_rows.append(r)
        print(f"  constancy {glabel:>9}: cells={r['n_cells']:>7,}  "
              f"const<1e-6: {r['pct_cells_range_lt_1e-6']:5.1f}%  R2={r['R2_of_cell_means']:.4f}", flush=True)
    for keys, rlabel in [(spec["primary_keys"], "primary: base-mean(base)"),
                         (spec["fallback_keys"], "fallback: base-mean(base)")]:
        if not all(k in df.columns for k in keys):
            continue
        r = reconstruction_test(df, base_col, adj_col, keys, spec["period"], rlabel)
        rec_rows.append(r)
        print(f"  recon   {rlabel:>22}: med_rho={r['median_period_spearman']:.4f}  "
              f"exact={r['exact_rate_1e-4_pct']:.1f}%  N={r['paired_N']:,}", flush=True)
    for keys, mlabel in [(spec["primary_keys"], "primary: base-mode(impl)"),
                         (spec["fallback_keys"], "fallback: base-mode(impl)")]:
        if not all(k in df.columns for k in keys):
            continue
        r = modal_test(df, base_col, adj_col, keys, spec["period"], mlabel)
        mod_rows.append(r)
        print(f"  modal   {mlabel:>22}: med_rho={r['median_period_spearman']:.4f}  "
              f"exact={r['exact_rate_1e-4_pct']:.1f}%  on_mode={r['pct_on_mode']:.1f}%  "
              f"off_xsic2={r.get('pct_offmode_cross_sic2_match', float('nan')):.1f}%", flush=True)
    return {"label": label, "base": base_col, "adj": adj_col, "n_valid": n_valid,
            "constancy": const_rows, "reconstruction": rec_rows, "modal": mod_rows}


def write_outputs(results):
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for res in results:
        rows = []
        for r in res["constancy"]:
            rows.append({"test": "constancy", **r})
        for r in res["reconstruction"]:
            rows.append({"test": "reconstruction_mean", **r})
        for r in res["modal"]:
            rows.append({"test": "modal", **r})
        pd.DataFrame(rows).to_csv(OUT_DIR / f"ia_implied_audit_{res['label']}.csv", index=False)

    summary_rows = []
    for res in results:
        c = next((r for r in res["constancy"] if r["grouping"].startswith("primary")), {})
        rec = next((r for r in res["reconstruction"] if r["candidate"].startswith("primary")), {})
        mod = next((r for r in res["modal"] if r["candidate"].startswith("primary")), {})
        summary_rows.append({
            "character": res["label"], "base": res["base"], "adj": res["adj"],
            "n_valid": res["n_valid"],
            "pct_cells_constant": c.get("pct_cells_range_lt_1e-6"),
            "R2_cell_means": c.get("R2_of_cell_means"),
            "recon_median_rho": rec.get("median_period_spearman"),
            "recon_exact_pct": rec.get("exact_rate_1e-4_pct"),
            "modal_median_rho": mod.get("median_period_spearman"),
            "modal_exact_pct": mod.get("exact_rate_1e-4_pct"),
            "pct_on_mode": mod.get("pct_on_mode"),
            "pct_offmode_cross_sic2": mod.get("pct_offmode_cross_sic2_match"),
        })
    summary = pd.DataFrame(summary_rows)
    summary.to_csv(OUT_DIR / "ia_implied_audit_summary.csv", index=False)

    lines = ["IA implied-adjustment internal-consistency audit (datashare.csv)",
             "implied := base - adjusted. Clean construction => implied constant per cell.",
             "",
             "Reference (bm_ia): ~44.4% cells constant, R2~0.958, recon rho~0.83, modal rho~0.99, on-mode~97%.",
             "", summary.to_string(index=False, float_format=lambda v: f"{v:.4f}" if pd.notna(v) else "nan")]
    (OUT_DIR / "ia_implied_audit_summary.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"\nWrote {OUT_DIR / 'ia_implied_audit_summary.csv'}")
    print(f"Wrote {OUT_DIR / 'ia_implied_audit_summary.txt'}")


def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    results = [run_pair(spec) for spec in PAIRS]
    write_outputs(results)


if __name__ == "__main__":
    main()
