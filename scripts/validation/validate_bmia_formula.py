#!/usr/bin/env python3
"""Validate the bm_ia builder's demeaning function against datashare bm_ia.

Feeds the builder's own demean_by_industry_month() the published datashare bm
and sic2 (the best-case inputs) and reports the five required metrics vs the
published bm_ia. This is the formula ceiling: a WRDS rebuild inherits our
book_to_market quality (rho ~0.971 vs datashare bm) on top of this.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "Character_Builders"))

from _shared.bm_ia_builder import demean_by_industry_month  # noqa: E402

DATASHARE = ROOT / "Supplementary_assistive_files" / "datashare.csv"
MIN_PAIRS = 50


def main() -> None:
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

    print("Loading datashare bm / bm_ia / sic2...", flush=True)
    df = pd.read_csv(DATASHARE, usecols=["permno", "DATE", "bm", "bm_ia", "sic2"])
    df["signal_yyyymm"] = (df["DATE"] // 100).astype("int64")
    df = df.dropna(subset=["bm", "sic2"]).copy()
    # builder expects 4-digit SIC; datashare publishes 2-digit -> scale up
    df["sic"] = df["sic2"].astype(int) * 100

    out = demean_by_industry_month(
        df,
        value_column="bm",
        industry_column="sic",
        industry_digits=2,
        time_column="signal_yyyymm",
        stat="mean",
        output_column="bm_ia_hat",
    )

    sub = out.dropna(subset=["bm_ia", "bm_ia_hat"])
    diff = (sub["bm_ia"] - sub["bm_ia_hat"]).abs()

    monthly = []
    for _, grp in sub.groupby("signal_yyyymm", sort=True):
        g = grp[["bm_ia", "bm_ia_hat"]].dropna()
        if len(g) < MIN_PAIRS:
            continue
        r = g["bm_ia"].corr(g["bm_ia_hat"], method="spearman")
        if pd.notna(r):
            monthly.append(r)

    print()
    print("builder demean function on datashare's own bm/sic2 vs published bm_ia:")
    print(f"  median monthly Spearman : {np.median(monthly):.4f}  ({len(monthly)} months)")
    print(f"  pooled Spearman         : {sub['bm_ia'].corr(sub['bm_ia_hat'], method='spearman'):.4f}")
    print(f"  exact (|diff|<=1e-4)    : {100 * (diff <= 1e-4).mean():.2f}%")
    print(f"  paired N                : {len(sub):,}")
    print(f"  unique permnos          : {sub['permno'].nunique():,}")


if __name__ == "__main__":
    main()
