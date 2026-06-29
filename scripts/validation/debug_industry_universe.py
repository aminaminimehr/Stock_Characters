"""Verify hypothesis: repo uses full Compustat universe for industry means;
Green SAS uses only CCM-linked (CRSP-filtered) firms."""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "validation"))
from green_sas_io import read_green_sas  # noqa: E402

MONTH = 200001  # Jan 2000 – a year where divergence has started

def main() -> None:
    # Panel counts for year 2000
    parts = []
    for chunk in pd.read_csv(
        ROOT / "outputs/panels/all_character_signal_panel_for_GKX_comparison.csv",
        usecols=["permno", "signal_yyyymm", "sic2", "chpmia"],
        chunksize=400_000,
    ):
        chunk = chunk[chunk["signal_yyyymm"].between(200001, 200012)]
        parts.append(chunk)
    p = pd.concat(parts)
    p["permno"] = pd.to_numeric(p["permno"], errors="coerce").astype("Int64")
    print(f"Panel permnos in 2000: {p['permno'].nunique():,}")

    g = read_green_sas(
        ROOT / "Supplementary_assistive_files" / "Output_From_Greens_SAS_code.sas7bdat",
        ["permno", "DATE", "sic2", "chpm", "chpmia"],
    )
    g = g[g["month"].between(200001, 200012)].copy()
    g["permno"] = pd.to_numeric(g["permno"], errors="coerce").astype("Int64")
    print(f"Green permnos in 2000: {g['permno'].nunique():,}")

    common = set(p["permno"].dropna()) & set(g["permno"].dropna())
    print(f"Common permnos: {len(common):,}")

    # For sic2=73, compare how many firms go into each group's industry mean
    sic73_g = g[g["sic2"].astype(str).str.strip() == "73"]
    sic73_p = p[pd.to_numeric(p["sic2"], errors="coerce") == 73]
    print(f"\nGreen sic2=73 firms (200001): {sic73_g['permno'].nunique():,}, mean chpm={sic73_g['chpm'].mean():.4f}")
    print(f"Panel sic2=73 firms (200001): {sic73_p['permno'].nunique():,}")

    # Show the correlation between chpmia in panel vs green – are the means different?
    mx = g[["permno", "month", "chpm", "chpmia"]].rename(
        columns={"month": "signal_yyyymm", "chpm": "g_chpm", "chpmia": "g_chpmia"}
    ).merge(
        p[["permno", "signal_yyyymm", "chpmia"]].rename(columns={"chpmia": "p_chpmia"}),
        on=["permno", "signal_yyyymm"],
        how="inner",
    ).dropna()
    r = mx["p_chpmia"].corr(mx["g_chpmia"], method="spearman")
    print(f"\nPanel chpmia vs Green chpmia (2000): rho={r:.3f} n={len(mx):,}")

    # Compute what the industry mean SHOULD be (Green universe) and what repo uses
    # Estimate by checking whether chpm - chpmia is consistent between the two
    mx["g_ind_mean"] = mx["g_chpm"] - mx["g_chpmia"]
    mx_sic73 = mx.merge(
        p[["permno", "signal_yyyymm", "sic2"]],
        on=["permno", "signal_yyyymm"],
    ).dropna()
    mx_sic73_subset = mx_sic73[pd.to_numeric(mx_sic73["sic2"], errors="coerce") == 73]
    if not mx_sic73_subset.empty:
        print(f"\nFor sic2=73 firms:")
        print(f"  Green industry mean: {mx_sic73_subset['g_ind_mean'].mean():.4f} (should be same for all in group)")
        print(f"  Green industry mean std (should be ~0): {mx_sic73_subset['g_ind_mean'].std():.6f}")
        # Compute panel implied industry mean = chpm - chpmia
        p_with_chpm = p[["permno", "signal_yyyymm", "sic2", "chpmia"]].merge(
            g[["permno", "month", "chpm"]].rename(columns={"month": "signal_yyyymm"}),
            on=["permno", "signal_yyyymm"],
        ).dropna()
        p_with_chpm["p_ind_mean"] = p_with_chpm["chpm"] - p_with_chpm["chpmia"]
        p_sic73 = p_with_chpm[pd.to_numeric(p_with_chpm["sic2"], errors="coerce") == 73]
        if not p_sic73.empty:
            print(f"  Panel implied industry mean: {p_sic73['p_ind_mean'].mean():.4f}")
            print(f"  Panel implied industry mean std (should be ~0): {p_sic73['p_ind_mean'].std():.6f}")

    # Year by year: how many firms are in Green vs panel
    print("\nYear-by-year universe sizes (full sample, annual):")
    for yr in range(1975, 2022, 5):
        g_yr = read_green_sas(
            ROOT / "Supplementary_assistive_files" / "Output_From_Greens_SAS_code.sas7bdat",
            ["permno", "DATE"],
        )
        g_yr = g_yr[(g_yr["month"] // 100) == yr]
        p_yr = []
        for chunk in pd.read_csv(
            ROOT / "outputs/panels/all_character_signal_panel_for_GKX_comparison.csv",
            usecols=["permno", "signal_yyyymm"],
            chunksize=400_000,
        ):
            chunk = chunk[(chunk["signal_yyyymm"] // 100) == yr]
            if len(chunk):
                p_yr.append(chunk)
        if not p_yr:
            continue
        p_yr_df = pd.concat(p_yr)
        print(f"  {yr}: Green={g_yr['permno'].nunique():,}, Panel={p_yr_df['permno'].nunique():,}")


if __name__ == "__main__":
    main()
