#!/usr/bin/env python3
"""Apply Green winsor to existing panel and recompare four chars vs Green + datashare."""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "Character_Builders"))
sys.path.insert(0, str(ROOT / "scripts" / "validation"))

from green_sas_io import read_green_sas  # noqa: E402
from _shared.green_winsor import apply_green_winsorization  # noqa: E402

PANEL = ROOT / "outputs" / "panels" / "all_character_signal_panel_for_GKX_comparison.csv"
DS = ROOT / "Supplementary_assistive_files" / "datashare.csv"
GREEN = ROOT / "Supplementary_assistive_files" / "Output_From_Greens_SAS_code.sas7bdat"
CHARS = ["ms", "indmom", "chpmia", "pchcapx_ia"]
WIN = (201001, 201512)


def rho(a, b):
    m = a.notna() & b.notna()
    return float(a[m].corr(b[m], method="spearman")) if m.sum() > 50 else float("nan")


def compare(pf: pd.DataFrame, other: pd.DataFrame, char: str, other_col: str) -> float:
    m = pf[["permno", "signal_yyyymm", char]].merge(
        other[["permno", "month", other_col]].rename(columns={"month": "signal_yyyymm"}),
        on=["permno", "signal_yyyymm"],
        how="inner",
    ).dropna()
    return rho(m[char], m[other_col])


def main() -> None:
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    print("Loading panel...", flush=True)
    raw = pd.read_csv(PANEL)
    winsor = apply_green_winsorization(raw.copy(), month_col="signal_yyyymm")

    g = read_green_sas(GREEN, ["permno", "DATE", *CHARS])
    g = g[g["month"].between(*WIN)]
    for c in CHARS:
        g = g.rename(columns={c: f"green_{c}"})

    parts = []
    for chunk in pd.read_csv(DS, usecols=["permno", "DATE", *CHARS], chunksize=500_000):
        chunk["month"] = chunk["DATE"] // 100
        chunk = chunk[chunk["month"].between(*WIN)]
        parts.append(chunk.drop(columns=["DATE"]))
    d = pd.concat(parts, ignore_index=True)
    for c in CHARS:
        d = d.rename(columns={c: f"ds_{c}"})

    print(f"\nWindow {WIN[0]}-{WIN[1]} Spearman\n")
    print(f"{'char':12} {'raw->ds':>8} {'win->ds':>8} {'raw->Gr':>8} {'win->Gr':>8}")
    for char in CHARS:
        gsub = g[["permno", "month", f"green_{char}"]]
        dsub = d[["permno", "month", f"ds_{char}"]]
        r_ds_raw = compare(raw, dsub, char, f"ds_{char}")
        r_ds_win = compare(winsor, dsub, char, f"ds_{char}")
        r_g_raw = compare(raw, gsub, char, f"green_{char}")
        r_g_win = compare(winsor, gsub, char, f"green_{char}")
        print(f"{char:12} {r_ds_raw:8.3f} {r_ds_win:8.3f} {r_g_raw:8.3f} {r_g_win:8.3f}")


if __name__ == "__main__":
    main()
