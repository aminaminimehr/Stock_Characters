#!/usr/bin/env python3
"""Compare rebuilt bm_ia.csv against datashare.csv bm_ia.

Reports Spearman (pooled + median monthly), paired N, unique permnos, and
exact/round4 rates. Month alignment picks signal_yyyymm vs target_yyyymm
(whichever yields higher median monthly Spearman).

Expected ceiling ~0.83–0.85 median monthly Spearman due to construction-SIC
vintage (~3% of cells); see docs/gkx/datashare_reverse_engineering.md.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_BM_IA = ROOT / "outputs" / "characteristics" / "individual" / "bm_ia.csv"
DEFAULT_DATASHARE = ROOT / "Supplementary_assistive_files" / "datashare.csv"
MIN_PAIRS = 50


def monthly_spearman_values(df: pd.DataFrame, a: str, b: str) -> list[float]:
    vals = []
    for _, grp in df.groupby("month", sort=True):
        sub = grp[[a, b]].dropna()
        if len(sub) < MIN_PAIRS:
            continue
        r = sub[a].corr(sub[b], method="spearman")
        if pd.notna(r):
            vals.append(r)
    return vals


def compare(panel: pd.DataFrame, ds: pd.DataFrame, month_col: str) -> dict:
    ps = panel.rename(columns={month_col: "month"})[["permno", "month", "bm_ia"]]
    m = ds.merge(ps, on=["permno", "month"], how="inner", suffixes=("_ds", "_panel"))
    m = m.dropna(subset=["bm_ia_ds", "bm_ia_panel"])
    n = len(m)
    if n < 2:
        return {"month_align": month_col, "paired_obs": 0}

    pv = m["bm_ia_panel"].astype("float64")
    dv = m["bm_ia_ds"].astype("float64")
    diff = (pv - dv).abs()
    vals = monthly_spearman_values(m.rename(columns={"bm_ia_panel": "a", "bm_ia_ds": "b"}), "a", "b")
    return {
        "month_align": month_col,
        "paired_obs": n,
        "pooled_spearman": float(pv.corr(dv, method="spearman")),
        "median_monthly_spearman": float(np.median(vals)) if vals else np.nan,
        "mean_monthly_spearman": float(np.mean(vals)) if vals else np.nan,
        "spearman_months": len(vals),
        "exact_rate": float((diff <= 1e-4).mean()),
        "round4_rate": float((np.round(pv, 4) == np.round(dv, 4)).mean()),
        "permno_panel": int(ps.loc[ps["bm_ia"].notna(), "permno"].nunique()),
        "permno_datashare": int(ds.loc[ds["bm_ia"].notna(), "permno"].nunique()),
        "permno_both": int(m["permno"].nunique()),
        "panel_nonnull": int(ps["bm_ia"].notna().sum()),
        "datashare_nonnull": int(ds["bm_ia"].notna().sum()),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bm-ia", type=Path, default=DEFAULT_BM_IA)
    parser.add_argument("--datashare", type=Path, default=DEFAULT_DATASHARE)
    args = parser.parse_args()

    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

    if not args.bm_ia.exists():
        raise FileNotFoundError(f"{args.bm_ia} not found. Build with Datashare_BM_IA_Generalized/build_bm_ia.py")

    print(f"Loading panel bm_ia: {args.bm_ia}", flush=True)
    panel = pd.read_csv(args.bm_ia)
    panel["permno"] = pd.to_numeric(panel["permno"], errors="coerce").astype("Int64")
    panel["signal_yyyymm"] = pd.to_numeric(panel["signal_yyyymm"], errors="coerce").astype("Int64")
    panel["target_yyyymm"] = pd.to_numeric(panel["target_yyyymm"], errors="coerce").astype("Int64")
    panel["bm_ia"] = pd.to_numeric(panel["bm_ia"], errors="coerce")

    print(f"Loading datashare: {args.datashare}", flush=True)
    frames = []
    for chunk in pd.read_csv(args.datashare, usecols=["permno", "DATE", "bm_ia"], chunksize=500_000):
        chunk["permno"] = pd.to_numeric(chunk["permno"], errors="coerce").astype("Int64")
        chunk["month"] = (pd.to_numeric(chunk["DATE"], errors="coerce") // 100).astype("Int64")
        chunk["bm_ia"] = pd.to_numeric(chunk["bm_ia"], errors="coerce")
        frames.append(chunk[["permno", "month", "bm_ia"]])
    ds = pd.concat(frames, ignore_index=True)

    best = None
    for month_col in ("signal_yyyymm", "target_yyyymm"):
        row = compare(panel, ds, month_col)
        print(
            f"  align={month_col}: paired={row.get('paired_obs', 0):,} "
            f"median_rho={row.get('median_monthly_spearman', float('nan')):.4f} "
            f"pooled={row.get('pooled_spearman', float('nan')):.4f}",
            flush=True,
        )
        if best is None or (
            pd.notna(row.get("median_monthly_spearman"))
            and (
                pd.isna(best.get("median_monthly_spearman"))
                or row["median_monthly_spearman"] > best["median_monthly_spearman"]
            )
        ):
            best = row

    print()
    print("=== bm_ia vs datashare (best month alignment) ===")
    print(f"  month align              : {best['month_align']}")
    print(f"  median monthly Spearman  : {best['median_monthly_spearman']:.4f}  ({best['spearman_months']} months)")
    print(f"  mean monthly Spearman    : {best['mean_monthly_spearman']:.4f}")
    print(f"  pooled Spearman          : {best['pooled_spearman']:.4f}")
    print(f"  exact (|Δ|≤1e-4)         : {100 * best['exact_rate']:.2f}%")
    print(f"  round-4 match            : {100 * best['round4_rate']:.2f}%")
    print(f"  paired N                 : {best['paired_obs']:,}")
    print(f"  panel non-null           : {best['panel_nonnull']:,}")
    print(f"  datashare non-null       : {best['datashare_nonnull']:,}")
    print(f"  unique permnos (panel)   : {best['permno_panel']:,}")
    print(f"  unique permnos (datashare): {best['permno_datashare']:,}")
    print(f"  unique permnos (both)    : {best['permno_both']:,}")
    print()
    print(
        "Note: realistic ceiling is ~0.83–0.85 median monthly Spearman "
        "(construction-SIC vintage residual); see datashare_reverse_engineering.md."
    )


if __name__ == "__main__":
    main()
