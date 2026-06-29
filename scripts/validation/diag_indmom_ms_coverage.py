#!/usr/bin/env python3
"""Year-bucket indmom correlation and ms coverage vs Green."""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import pyreadstat

ROOT = Path(__file__).resolve().parents[2]
GREEN = ROOT / "Supplementary_assistive_files" / "Output_From_Greens_SAS_code.sas7bdat"
PANEL = ROOT / "outputs" / "panels" / "all_character_signal_panel_for_GKX_comparison.csv"
DS = ROOT / "Supplementary_assistive_files" / "datashare.csv"


def rho(a, b):
    m = a.notna() & b.notna()
    return float(a[m].corr(b[m], method="spearman")) if m.sum() > 50 else float("nan")


def main():
    print("Loading Green indmom/ms...", flush=True)
    g, _ = pyreadstat.read_sas7bdat(str(GREEN), usecols=["permno", "DATE", "indmom", "ms"])
    g["month"] = pd.to_datetime(g["DATE"]).dt.year * 100 + pd.to_datetime(g["DATE"]).dt.month
    g["year"] = g["month"] // 100
    g["permno"] = pd.to_numeric(g["permno"], errors="coerce").astype("Int64")

    print("Loading panel...", flush=True)
    parts = []
    for chunk in pd.read_csv(PANEL, usecols=["permno", "signal_yyyymm", "indmom", "ms"], chunksize=400_000):
        parts.append(chunk)
    p = pd.concat(parts, ignore_index=True)
    p["permno"] = pd.to_numeric(p["permno"], errors="coerce").astype("Int64")
    p["year"] = p["signal_yyyymm"] // 100

    print("Loading datashare...", flush=True)
    parts = []
    for chunk in pd.read_csv(DS, usecols=["permno", "DATE", "indmom", "ms"], chunksize=500_000):
        chunk["month"] = chunk["DATE"] // 100
        chunk["year"] = chunk["month"] // 100
        parts.append(chunk.drop(columns=["DATE"]))
    d = pd.concat(parts, ignore_index=True)
    d["permno"] = pd.to_numeric(d["permno"], errors="coerce").astype("Int64")

    print("\n=== indmom median rho by 5-year bucket (panel vs datashare) ===")
    m = p.rename(columns={"signal_yyyymm": "month", "indmom": "panel"}).merge(
        d[["permno", "month", "indmom"]].rename(columns={"indmom": "datashare"}),
        on=["permno", "month"],
        how="inner",
    ).dropna()
    for y0 in range(1960, 2020, 5):
        y1 = y0 + 4
        sub = m[(m["month"] // 100 >= y0) & (m["month"] // 100 <= y1)]
        if len(sub) < 1000:
            continue
        print(f"  {y0}-{y1}: rho={rho(sub['panel'], sub['datashare']):.3f}  n={len(sub):,}")

    print("\n=== ms coverage on permno-month overlap ===")
    gp = g[["permno", "month", "ms"]].rename(columns={"ms": "green_ms"})
    pp = p[["permno", "signal_yyyymm", "ms"]].rename(columns={"signal_yyyymm": "month", "ms": "panel_ms"})
    dp = d[["permno", "month", "ms"]].rename(columns={"ms": "ds_ms"})
    x = gp.merge(pp, on=["permno", "month"], how="outer").merge(dp, on=["permno", "month"], how="outer")
    for col in ["green_ms", "panel_ms", "ds_ms"]:
        print(f"  non-null {col}: {x[col].notna().sum():,}")
    both = x.dropna(subset=["green_ms", "panel_ms"])
    print(f"  panel vs green paired: {len(both):,}, rho={rho(both['panel_ms'], both['green_ms']):.3f}, "
          f"exact={((both['panel_ms'].round()-both['green_ms'].round()).abs()<1e-6).mean()*100:.1f}%")
    both2 = x.dropna(subset=["green_ms", "ds_ms"])
    print(f"  datashare vs green paired: {len(both2):,}, rho={rho(both2['ds_ms'], both2['green_ms']):.3f}, "
          f"exact={((both2['ds_ms'].round()-both2['green_ms'].round()).abs()<1e-6).mean()*100:.1f}%")
    panel_only = x["panel_ms"].notna() & x["green_ms"].isna()
    green_only = x["green_ms"].notna() & x["panel_ms"].isna()
    print(f"  panel has ms, green missing: {panel_only.sum():,}")
    print(f"  green has ms, panel missing: {green_only.sum():,}")


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    main()
