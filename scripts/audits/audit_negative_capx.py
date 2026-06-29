#!/usr/bin/env python3
"""Count gvkeys/permnos with negative Compustat capx under Green annual filters."""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "Character_Builders"))

from _shared.ccm import attach_ccm_links_green  # noqa: E402
from _shared.green_builders import (  # noqa: E402
    connect_wrds,
    load_annual_compustat,
    load_green_ccm_links,
)


def main() -> None:
    print("Connecting to WRDS...", flush=True)
    db = connect_wrds(None)

    print("Loading annual Compustat (Green filters)...", flush=True)
    comp = load_annual_compustat(db)
    comp["datadate"] = pd.to_datetime(comp["datadate"])
    comp = comp.sort_values(["gvkey", "datadate"])

    capx = comp["capx"]
    nonmiss = capx.notna()
    neg = nonmiss & (capx < 0)

    print("\n=== Raw Compustat CAPX (Green annual universe) ===")
    print(f"Annual rows: {len(comp):,}")
    print(f"Non-missing capx rows: {nonmiss.sum():,} ({100 * nonmiss.mean():.2f}%)")
    print(f"Negative capx rows: {neg.sum():,} ({100 * neg.sum() / nonmiss.sum():.2f}% of non-missing)")

    gv_any_neg = comp.groupby("gvkey")["capx"].apply(lambda s: (s < 0).any())
    gv_all_neg = comp.groupby("gvkey")["capx"].apply(
        lambda s: s.notna().any() and (s.dropna() < 0).all()
    )
    print(f"\nUnique gvkeys: {comp['gvkey'].nunique():,}")
    print(f"Gvkeys with any negative capx: {gv_any_neg.sum():,} ({100 * gv_any_neg.mean():.2f}%)")
    print(f"Gvkeys where ALL non-missing capx are negative: {gv_all_neg.sum():,}")

    comp["lag_ppent"] = comp.groupby("gvkey")["ppent"].shift(1)
    comp["gvkey_count"] = comp.groupby("gvkey").cumcount() + 1
    comp["imputed_capx"] = comp["capx"].copy()
    impute_mask = (
        comp["capx"].isna()
        & comp["gvkey_count"].ge(2)
        & comp["lag_ppent"].notna()
        & comp["ppent"].notna()
    )
    comp.loc[impute_mask, "imputed_capx"] = comp.loc[impute_mask, "ppent"] - comp.loc[impute_mask, "lag_ppent"]

    imp = comp["imputed_capx"]
    imp_nonmiss = imp.notna()
    imp_neg = imp_nonmiss & (imp < 0)
    print("\n=== After Green capx imputation (capx or ppent - lag(ppent)) ===")
    print(f"Non-missing imputed capx rows: {imp_nonmiss.sum():,}")
    print(f"Negative imputed capx rows: {imp_neg.sum():,} ({100 * imp_neg.sum() / imp_nonmiss.sum():.2f}% of non-missing)")
    gv_imp_any_neg = comp.groupby("gvkey")["imputed_capx"].apply(lambda s: (s < 0).any())
    print(f"Gvkeys with any negative imputed capx: {gv_imp_any_neg.sum():,}")

    print("\nLinking CCM (Green)...", flush=True)
    link = load_green_ccm_links(db)
    linked = attach_ccm_links_green(comp, link)
    linked = linked[linked["permno"].notna()].copy()
    linked["permno"] = pd.to_numeric(linked["permno"], errors="coerce").astype("Int64")

    print("\n=== Permno level (CCM-linked annual rows) ===")
    print(f"Linked annual rows: {len(linked):,}")
    print(f"Unique permnos: {linked['permno'].nunique():,}")

    pm_any_neg = linked.groupby("permno")["capx"].apply(lambda s: (s < 0).any())
    pm_all_neg = linked.groupby("permno")["capx"].apply(
        lambda s: s.notna().any() and (s.dropna() < 0).all()
    )
    print(f"Permnos with ANY negative raw capx: {pm_any_neg.sum():,} ({100 * pm_any_neg.mean():.2f}% of linked permnos)")
    print(f"Permnos where ALL non-missing raw capx are negative: {pm_all_neg.sum():,}")

    pm_imp_any_neg = linked.groupby("permno")["imputed_capx"].apply(lambda s: (s < 0).any())
    print(f"Permnos with ANY negative imputed capx: {pm_imp_any_neg.sum():,}")

    linked = linked.sort_values(["permno", "datadate"])
    linked["lag_capx"] = linked.groupby("permno")["imputed_capx"].shift(1)
    lag_neg = linked["lag_capx"].notna() & (linked["lag_capx"] < 0)
    print("\n=== Denominator for pchcapx (lag imputed capx < 0) ===")
    denom_rows = linked["imputed_capx"].notna().sum()
    print(f"Linked rows with negative lag capx: {lag_neg.sum():,} ({100 * lag_neg.sum() / denom_rows:.2f}% of rows with capx)")
    print(f"Permnos with any negative lag imputed capx: {linked.loc[lag_neg, 'permno'].nunique():,}")

    db.close()
    print("\nDone.", flush=True)


if __name__ == "__main__":
    main()
