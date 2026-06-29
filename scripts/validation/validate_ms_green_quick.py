#!/usr/bin/env python3
"""Quick ms vs Green SAS validation after ms_builder fixes."""
from __future__ import annotations

import os
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "Character_Builders"))
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts" / "validation"))

from green_sas_io import read_green_sas  # noqa: E402
from _shared.green_builders import connect_wrds  # noqa: E402
from _shared.ms_builder import build_ms_character  # noqa: E402

GREEN = ROOT / "Supplementary_assistive_files" / "Output_From_Greens_SAS_code.sas7bdat"
WIN_START, WIN_END = 201001, 201112


def rho(a: pd.Series, b: pd.Series) -> float:
    m = a.notna() & b.notna()
    return float(a[m].corr(b[m], method="spearman")) if m.sum() > 50 else float("nan")


def load_green_ms(win_start: int, win_end: int) -> pd.DataFrame:
    g = read_green_sas(GREEN, ["permno", "DATE", "ms"])
    g = g[g["month"].between(win_start, win_end)].copy()
    g["permno"] = pd.to_numeric(g["permno"], errors="coerce").astype("Int64")
    return g


def main() -> None:
    db = connect_wrds(os.environ.get("WRDS_USERNAME"))
    print("Building ms...", flush=True)
    ms = build_ms_character(db, use_ibes=False)
    db.close()

    ms = ms[ms["signal_yyyymm"].between(WIN_START, WIN_END)].copy()
    ms["permno"] = pd.to_numeric(ms["permno"], errors="coerce").astype("Int64")
    g = load_green_ms(WIN_START, WIN_END)

    m = ms.merge(
        g[["permno", "month", "ms"]].rename(columns={"ms": "green"}),
        left_on=["permno", "signal_yyyymm"],
        right_on=["permno", "month"],
        how="inner",
    ).dropna(subset=["ms", "green"])

    print(f"Repo ms rows in window: {len(ms):,}")
    print(f"Green rows in window: {len(g):,} (ms non-null: {g['ms'].notna().sum():,})")
    print(f"Paired non-null: {len(m):,}")
    print(f"Spearman: {rho(m['ms'], m['green']):.4f}")
    exact = ((m["ms"].round() - m["green"].round()).abs() < 1e-6).mean() * 100
    print(f"Exact integer match: {exact:.1f}%")

    outer = ms.merge(
        g[["permno", "month", "ms"]].rename(columns={"ms": "green"}),
        left_on=["permno", "signal_yyyymm"],
        right_on=["permno", "month"],
        how="outer",
    )
    fp = int((outer["ms"].notna() & outer["green"].isna()).sum())
    fn = int((outer["green"].notna() & outer["ms"].isna()).sum())
    print(f"False positive (repo ms, green missing): {fp:,}")
    print(f"False negative (green ms, repo missing): {fn:,}")


if __name__ == "__main__":
    main()
