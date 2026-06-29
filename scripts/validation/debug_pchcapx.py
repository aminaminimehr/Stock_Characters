"""Validate pchcapx_ia fix: null pchcapx when lag_capx <= 0.

Compares panel pchcapx_ia against Green SAS for a small window.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "Character_Builders"))
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts" / "validation"))

from green_sas_io import read_green_sas  # noqa: E402
from _shared.green_builders import (  # noqa: E402
    attach_permno,
    compute_annual_characters,
    load_annual_age_lookup,
    load_annual_compustat,
    load_annual_orgcap_lookup,
    load_green_ccm_links,
    connect_wrds,
)
from Character_Panels.timing import expand_annual_file_green  # noqa: E402

GREEN_SAS = ROOT / "Supplementary_assistive_files" / "Output_From_Greens_SAS_code.sas7bdat"
WIN_START, WIN_END = 200901, 201212

CHARS = ["pchcapx", "pchcapx_ia"]


def rho(a: pd.Series, b: pd.Series) -> float:
    m = a.notna() & b.notna()
    n = int(m.sum())
    if n < 50:
        return float("nan"), n
    return float(a[m].corr(b[m], method="spearman")), n


def main() -> None:
    db = connect_wrds(os.environ.get("WRDS_USERNAME"))

    print("Loading annual Compustat...", flush=True)
    raw_comp = load_annual_compustat(db)
    print(f"  Rows: {len(raw_comp):,}", flush=True)

    print("Computing annual characters...", flush=True)
    comp = compute_annual_characters(
        raw_comp,
        age_lookup=load_annual_age_lookup(db),
        orgcap_lookup=load_annual_orgcap_lookup(db),
    )
    link = load_green_ccm_links(db)
    comp = attach_permno(comp, link)
    comp["permno"] = pd.to_numeric(comp["permno"], errors="coerce").astype("Int64")

    # Expand to monthly signals
    annual = comp[comp["permno"].notna()][
        ["permno", "permco", "gvkey", "datadate", "sic", "fyear"] + CHARS
    ].copy()
    expanded = expand_annual_file_green(annual, CHARS)
    expanded = expanded[expanded["signal_yyyymm"].between(WIN_START, WIN_END)].copy()
    expanded["permno"] = pd.to_numeric(expanded["permno"], errors="coerce").astype("Int64")
    print(f"\nExpanded rows in window: {len(expanded):,}", flush=True)

    print("\nLoading Green SAS pchcapx + pchcapx_ia...", flush=True)
    import pyreadstat
    _, meta = pyreadstat.read_sas7bdat(str(GREEN_SAS), row_limit=1)
    available = [c for c in ["permno", "DATE", "pchcapx", "pchcapx_ia"] if c in meta.column_names]
    print(f"  Available Green cols: {available}", flush=True)

    g = read_green_sas(GREEN_SAS, available)
    g = g[g["month"].between(WIN_START, WIN_END)].copy()
    g["permno"] = pd.to_numeric(g["permno"], errors="coerce").astype("Int64")
    print(f"  Green rows in window: {len(g):,}", flush=True)

    for char in CHARS:
        if char not in g.columns:
            print(f"\n{char}: not in Green SAS output, skipping.")
            continue
        mg = expanded.merge(
            g[["permno", "month", char]].rename(columns={char: "g", "month": "signal_yyyymm"}),
            on=["permno", "signal_yyyymm"],
            how="inner",
        ).dropna(subset=[char, "g"])
        r, n = rho(mg[char], mg["g"])
        diff = mg[char] - mg["g"]
        print(f"\n{char}:")
        print(f"  Paired obs: {n:,}")
        print(f"  Spearman rho vs Green: {r:.4f}")
        print(f"  Mean diff (panel - green): {diff.mean():.4f}")
        print(f"  Std diff: {diff.std():.4f}")

    # Check how many pchcapx values are NaN due to our fix
    n_nulled = (raw_comp["lag_capx"] <= 0).sum() if "lag_capx" in raw_comp.columns else "N/A"
    print(f"\nRows where lag_capx <= 0 in annual comp: {n_nulled}")
    # Also check from comp directly
    if "pchcapx" in comp.columns and "lag_capx" in comp.columns:
        neg_lag = comp[comp["lag_capx"].notna() & (comp["lag_capx"] <= 0)]
        print(f"Rows with lag_capx <= 0 in computed comp: {len(neg_lag):,}")
        print(f"  Of those, pchcapx is NaN: {neg_lag['pchcapx'].isna().sum():,} (should equal above)")

    db.close()


if __name__ == "__main__":
    main()
