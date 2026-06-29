#!/usr/bin/env python3
"""Three-way Spearman: panel vs Green SAS vs datashare (narrow window)."""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "validation"))
from green_sas_io import read_green_sas  # noqa: E402
GREEN = ROOT / "Supplementary_assistive_files" / "Output_From_Greens_SAS_code.sas7bdat"
PANEL = ROOT / "outputs" / "panels" / "all_character_signal_panel_for_GKX_comparison.csv"
DS = ROOT / "Supplementary_assistive_files" / "datashare.csv"
MONTH_MIN, MONTH_MAX = 201001, 201512
CHARS = ["chpmia", "indmom", "ms", "pchcapx_ia"]


def rho(a: pd.Series, b: pd.Series) -> float:
    m = a.notna() & b.notna()
    return float(a[m].corr(b[m], method="spearman")) if m.sum() > 10 else float("nan")


def main() -> None:
    cols = ["permno", "DATE", *CHARS, "chpm", "pchcapx", "mom12m", "sic2"]
    print("Reading Green SAS...", flush=True)
    g = read_green_sas(GREEN, cols)
    g = g[g["month"].between(MONTH_MIN, MONTH_MAX)].copy()
    g["permno"] = pd.to_numeric(g["permno"], errors="coerce").astype("Int64")

    pcols = ["permno", "signal_yyyymm", *CHARS, "chpm", "pchcapx", "mom12m", "sic2"]
    parts = []
    for chunk in pd.read_csv(PANEL, usecols=pcols, chunksize=300_000):
        chunk = chunk[chunk["signal_yyyymm"].between(MONTH_MIN, MONTH_MAX)]
        parts.append(chunk)
    p = pd.concat(parts, ignore_index=True)
    p["permno"] = pd.to_numeric(p["permno"], errors="coerce").astype("Int64")

    ds_cols = ["permno", "DATE", *CHARS, "mom12m", "sic2"]
    parts = []
    for chunk in pd.read_csv(DS, usecols=ds_cols, chunksize=500_000):
        chunk["month"] = chunk["DATE"] // 100
        chunk = chunk[chunk["month"].between(MONTH_MIN, MONTH_MAX)]
        parts.append(chunk.drop(columns=["DATE"]))
    d = pd.concat(parts, ignore_index=True)
    d["permno"] = pd.to_numeric(d["permno"], errors="coerce").astype("Int64")

    print(f"\nThree-way comparison {MONTH_MIN}-{MONTH_MAX}\n")
    for char in CHARS:
        gp = g[["permno", "month", char]].rename(columns={char: "green"}).merge(
            p[["permno", "signal_yyyymm", char]].rename(columns={"signal_yyyymm": "month", char: "panel"}),
            on=["permno", "month"],
            how="inner",
        )
        gd = g[["permno", "month", char]].rename(columns={char: "green"}).merge(
            d[["permno", "month", char]].rename(columns={char: "datashare"}),
            on=["permno", "month"],
            how="inner",
        )
        pd_pair = p[["permno", "signal_yyyymm", char]].rename(
            columns={"signal_yyyymm": "month", char: "panel"}
        ).merge(
            d[["permno", "month", char]].rename(columns={char: "datashare"}),
            on=["permno", "month"],
            how="inner",
        )

        print(f"{char}:")
        print(f"  panel vs Green:     rho={rho(gp['panel'], gp['green']):.3f}  paired={gp.dropna().shape[0]:,}")
        print(f"  datashare vs Green: rho={rho(gd['datashare'], gd['green']):.3f}  paired={gd.dropna().shape[0]:,}")
        print(f"  panel vs datashare: rho={rho(pd_pair['panel'], pd_pair['datashare']):.3f}  paired={pd_pair.dropna().shape[0]:,}")


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    main()
