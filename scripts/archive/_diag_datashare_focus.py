"""Compare datashare bm/bm_ia/operprof/cfp against ALL candidate panel columns.

Goal: find whether an existing repo column (Green-style `bm` vs HXZ-style
`book_to_market`, etc.) already replicates datashare, and quantify the gap.
"""
from pathlib import Path
import sys

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
PANEL = ROOT / "outputs" / "panels" / "all_character_signal_panel_final.csv"
DATASHARE = ROOT / "Supplementary_assistive_files" / "datashare.csv"

# datashare focus col -> candidate panel columns to test
CANDIDATES = {
    "bm": ["bm", "book_to_market", "bmj"],
    "bm_ia": ["bm_ia"],
    "operprof": ["operprof", "operating_profitability", "op"],
    "cfp": ["cfp", "cash_flow_to_price"],
}


def load_panel(cols):
    usecols = ["permno", "signal_yyyymm"] + cols
    frames = []
    for ch in pd.read_csv(PANEL, usecols=usecols, chunksize=1_000_000):
        ch["permno"] = pd.to_numeric(ch["permno"], errors="coerce").astype("Int64")
        ch["month"] = pd.to_numeric(ch["signal_yyyymm"], errors="coerce").astype("Int64")
        frames.append(ch.drop(columns=["signal_yyyymm"]))
    return pd.concat(frames, ignore_index=True)


def load_datashare(cols):
    usecols = ["permno", "DATE"] + cols
    frames = []
    for ch in pd.read_csv(DATASHARE, usecols=usecols, chunksize=500_000):
        ch["permno"] = pd.to_numeric(ch["permno"], errors="coerce").astype("Int64")
        ch["month"] = (pd.to_numeric(ch["DATE"], errors="coerce") // 100).astype("Int64")
        frames.append(ch.drop(columns=["DATE"]))
    return pd.concat(frames, ignore_index=True)


def monthly_spearman(m, a, b):
    vals = []
    for _, g in m.groupby("month", sort=True):
        sub = g[[a, b]].dropna()
        if len(sub) < 50:
            continue
        r = sub[a].corr(sub[b], method="spearman")
        if pd.notna(r):
            vals.append(r)
    return (float(np.median(vals)), len(vals)) if vals else (np.nan, 0)


def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    panel_cols = sorted({c for v in CANDIDATES.values() for c in v})
    ds_cols = sorted(CANDIDATES.keys())
    print("Loading panel...", flush=True)
    panel = load_panel(panel_cols)
    print("Loading datashare...", flush=True)
    ds = load_datashare(ds_cols)
    print(f"panel rows={len(panel):,} datashare rows={len(ds):,}\n")

    print(f"{'datashare':<10}{'panel_cand':<22}{'med_monthly_rho':>16}{'pooled_rho':>12}{'exact%':>9}{'paired':>12}{'panelN':>12}{'dsN':>12}")
    print("-" * 105)
    for dscol, cands in CANDIDATES.items():
        dsN = int(ds[dscol].notna().sum())
        for pcol in cands:
            sp = panel[["permno", "month", pcol]].dropna(subset=[pcol]).rename(columns={pcol: "pv"})
            sg = ds[["permno", "month", dscol]].dropna(subset=[dscol]).rename(columns={dscol: "gv"})
            m = sp.merge(sg, on=["permno", "month"], how="inner").dropna(subset=["pv", "gv"])
            if len(m) >= 2:
                pooled = m["pv"].corr(m["gv"], method="spearman")
                diff = (m["pv"].astype("float64") - m["gv"].astype("float64")).abs()
                exact = float((diff <= 1e-4).mean()) * 100
                mm, _ = monthly_spearman(m, "pv", "gv")
            else:
                pooled = exact = mm = np.nan
            print(f"{dscol:<10}{pcol:<22}{mm:>16.4f}{pooled:>12.4f}{exact:>9.2f}{len(m):>12,}{int(panel[pcol].notna().sum()):>12,}{dsN:>12,}")
        print()


if __name__ == "__main__":
    main()
