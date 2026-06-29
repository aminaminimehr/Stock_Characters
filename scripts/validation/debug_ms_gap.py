"""
Deep diagnostic for ms discrepancy.
1. Build ms fresh from WRDS (small window).
2. Compare ms distribution: repo - green.
3. Compare roavol/sgrvol between Green and repo quarterly panel.
4. For a sample of disagreeing permnos, show which component (m1-m6 vs m7/m8) is wrong.
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
    attach_permno, compute_annual_characters,
    load_annual_age_lookup, load_annual_compustat,
    load_annual_orgcap_lookup, load_green_ccm_links,
    load_crsp_monthly, connect_wrds,
)
from _shared.quarterly_builders import prepare_quarterly_compustat_panel, expand_quarterly_columns_to_monthly  # noqa: E402
from _shared.ms_builder import build_ms_character, _expand_annual_m_signals  # noqa: E402

GREEN_SAS = ROOT / "Supplementary_assistive_files" / "Output_From_Greens_SAS_code.sas7bdat"
WIN_START, WIN_END = 200901, 201012

def rho(a, b):
    m = a.notna() & b.notna()
    return float(a[m].corr(b[m], method="spearman")) if m.sum() > 20 else float("nan")


def main():
    db = connect_wrds(os.environ.get("WRDS_USERNAME"))

    print("Building ms...", flush=True)
    ms = build_ms_character(db, use_ibes=False)
    ms_win = ms[ms["signal_yyyymm"].between(WIN_START, WIN_END)].copy()
    ms_win["permno"] = pd.to_numeric(ms_win["permno"], errors="coerce").astype("Int64")

    print("Loading Green SAS ms + roavol + sgrvol...", flush=True)
    g = read_green_sas(GREEN_SAS, ["permno", "DATE", "ms", "roavol", "sgrvol"])
    g = g[g["month"].between(WIN_START, WIN_END)].copy()
    g["permno"] = pd.to_numeric(g["permno"], errors="coerce").astype("Int64")

    paired = ms_win.merge(
        g[["permno", "month", "ms", "roavol", "sgrvol"]].rename(
            columns={"ms": "g_ms", "month": "signal_yyyymm",
                     "roavol": "g_roavol", "sgrvol": "g_sgrvol"}
        ),
        on=["permno", "signal_yyyymm"],
        how="inner",
    ).dropna(subset=["ms", "g_ms"])

    print(f"\nPaired non-null ms: {len(paired):,}")
    print(f"Spearman rho(ms, g_ms) = {rho(paired['ms'], paired['g_ms']):.4f}")
    diff = paired["ms"] - paired["g_ms"]
    print(f"Difference (repo - green): mean={diff.mean():.3f}, std={diff.std():.3f}")
    print("Distribution of (repo_ms - green_ms):")
    print(diff.value_counts().sort_index())

    # How many have ms=0 in repo but Green has ms>0? (false-zero problem)
    false_zero = paired[(paired["ms"] == 0) & (paired["g_ms"] > 0)]
    print(f"\nFalse zeros (repo=0, green>0): {len(false_zero):,} ({100*len(false_zero)/len(paired):.1f}%)")
    over_repo = paired[(paired["ms"] > paired["g_ms"])]
    under_repo = paired[(paired["ms"] < paired["g_ms"])]
    print(f"Repo > Green: {len(over_repo):,}  |  Repo < Green: {len(under_repo):,}")

    # Compare roavol/sgrvol between Green and repo quarterly panel
    print("\n--- roavol / sgrvol comparison ---")
    quarterly = prepare_quarterly_compustat_panel(db)

    q_monthly_rv = expand_quarterly_columns_to_monthly(db, quarterly, ["roavol", "sgrvol", "m7", "m8"],
                                                        require_rdq=False, require_values=False)
    q_monthly_rv["permno"] = pd.to_numeric(q_monthly_rv["permno"], errors="coerce").astype("Int64")
    q_monthly_rv = q_monthly_rv[q_monthly_rv["signal_yyyymm"].between(WIN_START, WIN_END)]

    # Green has roavol/sgrvol columns (renamed below for clarity)
    g_rv = g[["permno", "month", "roavol", "sgrvol"]].rename(
        columns={"month": "signal_yyyymm", "roavol": "g_roavol", "sgrvol": "g_sgrvol"}
    ).dropna(subset=["g_roavol", "g_sgrvol"])

    paired_rv = q_monthly_rv.merge(
        g_rv,
        on=["permno", "signal_yyyymm"],
        how="inner",
    ).dropna(subset=["roavol", "g_roavol"])
    print(f"Paired roavol obs: {len(paired_rv):,}")
    print(f"Spearman rho(roavol, g_roavol) = {rho(paired_rv['roavol'], paired_rv['g_roavol']):.4f}")
    print(f"Spearman rho(sgrvol, g_sgrvol) = {rho(paired_rv['sgrvol'], paired_rv['g_sgrvol']):.4f}")

    # m7/m8 agreement
    paired_m78 = paired_rv.dropna(subset=["m7", "m8"])
    # Infer Green m7/m8 from Green roavol vs md_roavol
    # We can't directly, but let's look at ms disagrement breakdown
    # For permnos where ms disagrees, how many have m7/m8 = 1 in repo?
    disagree = paired[paired["ms"] != paired["g_ms"]].copy()
    # Get m7/m8 for disagree permnos from quarterly monthly lookup
    disagree_q = disagree.merge(
        q_monthly_rv[["permno", "signal_yyyymm", "m7", "m8"]],
        on=["permno", "signal_yyyymm"],
        how="left",
    )
    print(f"\nDisagreeing ms permnos: {disagree['permno'].nunique():,}")
    print(f"  Of those, repo has m7=1: {(disagree_q['m7']==1).sum():,}")
    print(f"  Of those, repo has m8=1: {(disagree_q['m8']==1).sum():,}")

    # Look at a sample where repo > green (repo likely has extra 1s)
    over = disagree_q[disagree_q["ms"] > disagree_q["g_ms"]].head(10)
    print("\nSample where repo_ms > green_ms (extra ones in repo):")
    print(over[["permno", "signal_yyyymm", "ms", "g_ms", "m7", "m8"]].to_string(index=False))

    db.close()


if __name__ == "__main__":
    main()
