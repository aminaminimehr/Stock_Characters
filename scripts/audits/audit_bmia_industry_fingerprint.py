#!/usr/bin/env python3
"""Identify the industry classification behind datashare bm_ia via implied-benchmark clustering.

Building on audit_bmia_implied_adjustment.py (which showed implied := bm - bm_ia
is exactly constant within 44% of month x sic2 cells), this script:

Test C (cluster count fingerprint):
    Within each month, group firms by their implied value (tolerance 1e-5).
    The number of distinct clusters equals the number of industry cells used
    by the true grouping that month: ~49 -> FF49, ~48 -> FF48, ~30 -> FF30,
    ~12/17 -> FF12/FF17, ~60-75 -> SIC2.

Test D (sic2-ambiguity prediction):
    Using the repo FF mappings (Imputation/industry_mappings.py), classify each
    sic2 code as "unambiguous" (every 4-digit SIC in [s*100, s*100+99] maps to
    ONE FF industry) or "ambiguous" (straddles several). If the true grouping is
    month x FFk, then month x sic2 cells should be exactly-constant IF AND ONLY
    IF their sic2 is unambiguous under FFk. We report that contingency for each
    FF scheme; the scheme with the cleanest split is the classification used.

Output: printed report + CSVs in outputs/diagnostics/.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "Imputation"))

from industry_codes import add_fama_french_industry_code  # noqa: E402

DATASHARE = ROOT / "Supplementary_assistive_files" / "datashare.csv"
OUT_DIR = ROOT / "outputs" / "diagnostics"

MIN_CELL = 5
CLUSTER_TOL = 1e-5
FF_SCHEMES = (12, 17, 30, 38, 48, 49)


def load() -> pd.DataFrame:
    df = pd.read_csv(DATASHARE, usecols=["permno", "DATE", "bm", "bm_ia", "sic2"])
    df["month"] = (df["DATE"] // 100).astype("int32")
    df = df.drop(columns=["DATE"])
    df["implied"] = df["bm"] - df["bm_ia"]
    return df.dropna(subset=["implied", "sic2"]).reset_index(drop=True)


def cluster_count_per_month(df: pd.DataFrame) -> pd.DataFrame:
    """Count implied-value clusters per month (tolerance-based, size >= MIN_CELL)."""
    rows = []
    for month, g in df.groupby("month", sort=True):
        v = np.sort(g["implied"].values)
        if len(v) < MIN_CELL:
            continue
        # split sorted values where the gap exceeds tolerance
        breaks = np.where(np.diff(v) > CLUSTER_TOL)[0]
        sizes = np.diff(np.concatenate(([0], breaks + 1, [len(v)])))
        n_all = len(sizes)
        n_big = int((sizes >= MIN_CELL).sum())
        frac_in_big = float(sizes[sizes >= MIN_CELL].sum() / len(v))
        rows.append(
            {"month": month, "n_firms": len(v), "n_clusters_all": n_all,
             "n_clusters_big": n_big, "frac_firms_in_big_clusters": frac_in_big}
        )
    return pd.DataFrame(rows)


def sic2_ambiguity_tables() -> pd.DataFrame:
    """For each FF scheme, mark each sic2 as unambiguous (maps to one FF code)."""
    sic4 = pd.DataFrame({"sic": np.arange(0, 10000)})
    out = pd.DataFrame({"sic2": np.arange(0, 100)})
    for scheme in FF_SCHEMES:
        mapped = add_fama_french_industry_code(sic4, scheme=scheme, sic_col="sic")
        mapped["sic2"] = mapped["sic"] // 100
        # unmatched SICs fall in the FF "other" bucket; treat NA as its own code
        col = f"ffi{scheme}"
        nuniq = mapped.groupby("sic2")[col].nunique(dropna=False)
        out[f"unambig_ff{scheme}"] = out["sic2"].map(nuniq).eq(1)
    return out


def cell_exactness(df: pd.DataFrame) -> pd.DataFrame:
    """Per (month, sic2) cell: is implied exactly constant across firms?"""
    g = df.groupby(["month", "sic2"], sort=False)["implied"]
    stats = g.agg(["count", "min", "max"])
    stats = stats[stats["count"] >= MIN_CELL].reset_index()
    stats["exact"] = (stats["max"] - stats["min"]) < 1e-6
    stats["sic2"] = stats["sic2"].astype(int)
    return stats[["month", "sic2", "count", "exact"]]


def main() -> None:
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

    print("Loading datashare...", flush=True)
    df = load()
    print(f"rows with implied & sic2: {len(df):,}\n")

    # ---------------- Test C ----------------
    print("=" * 88)
    print("TEST C: number of implied-benchmark clusters per month")
    print("        (~12/17/30/38/48/49 -> that FF scheme; ~60-75 -> SIC2)")
    print("=" * 88)
    cc = cluster_count_per_month(df)
    print(cc[["n_clusters_big", "frac_firms_in_big_clusters"]].describe().T.to_string(
        float_format=lambda v: f"{v:.2f}"))
    by_decade = cc.assign(decade=(cc["month"] // 1000) * 10).groupby("decade").agg(
        median_clusters=("n_clusters_big", "median"),
        mean_firms=("n_firms", "mean"),
        frac_in_big=("frac_firms_in_big_clusters", "mean"),
    )
    print("\nBy decade:")
    print(by_decade.to_string(float_format=lambda v: f"{v:.2f}"))

    # ---------------- Test D ----------------
    print()
    print("=" * 88)
    print("TEST D: are exactly-constant (month x sic2) cells the sic2 codes that are")
    print("        UNAMBIGUOUS under each FF scheme? (best-matching scheme = the one used)")
    print("=" * 88)
    amb = sic2_ambiguity_tables()
    cells = cell_exactness(df)
    cells = cells.merge(amb, on="sic2", how="left")

    rows = []
    for scheme in FF_SCHEMES:
        col = f"unambig_ff{scheme}"
        ct = pd.crosstab(cells[col], cells["exact"], normalize="index") * 100
        exact_if_unambig = ct.loc[True, True] if True in ct.index and True in ct.columns else np.nan
        exact_if_ambig = ct.loc[False, True] if False in ct.index and True in ct.columns else np.nan
        # agreement: unambig&exact or ambig&nonexact
        agree = ((cells[col] & cells["exact"]) | (~cells[col] & ~cells["exact"])).mean() * 100
        rows.append({
            "scheme": f"FF{scheme}",
            "pct_sic2_unambiguous": 100 * amb[col].mean(),
            "exact_rate_if_unambiguous": exact_if_unambig,
            "exact_rate_if_ambiguous": exact_if_ambig,
            "overall_agreement_pct": agree,
        })
    res_d = pd.DataFrame(rows)
    print(res_d.to_string(index=False, float_format=lambda v: f"{v:.1f}"))

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    cc.to_csv(OUT_DIR / "bmia_cluster_counts_by_month.csv", index=False)
    res_d.to_csv(OUT_DIR / "bmia_ff_scheme_agreement.csv", index=False)
    cells.to_csv(OUT_DIR / "bmia_cell_exactness.csv", index=False)
    print(f"\nWrote {OUT_DIR / 'bmia_cluster_counts_by_month.csv'}")
    print(f"Wrote {OUT_DIR / 'bmia_ff_scheme_agreement.csv'}")
    print(f"Wrote {OUT_DIR / 'bmia_cell_exactness.csv'}")


if __name__ == "__main__":
    main()
