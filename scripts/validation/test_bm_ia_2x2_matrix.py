#!/usr/bin/env python3
"""Test 2x2 bm_ia matrix from scratch via WRDS.

Builds book_to_market and bm_ia under four conventions:
  - June expansion vs 6-month per-firm rolling lag
  - CRSP shrcd 10,11 vs ALL

Compares each variant to datashare.csv bm_ia by:
  - cross-sectional Spearman (median monthly + pooled)
  - monthly change frequency
  - distinct bm_ia values per permno

Usage:
  python scripts/validation/test_bm_ia_2x2_matrix.py --wrds-user YOUR_USER
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import wrds
from scipy.stats import spearmanr

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "Character_Builders"))

from Character_Panels.timing import add_one_month, expand_annual_file_june  # noqa: E402
from _shared.bm_ia_builder import demean_by_industry_month  # noqa: E402
from _shared.ccm import attach_ccm_links, load_ccm_links  # noqa: E402
from output_paths import crsp_universe_filter, read_wrds_sql  # noqa: E402

DEFAULT_DATASHARE = ROOT / "Supplementary_assistive_files" / "datashare.csv"
MIN_PAIRS = 50
BM_COLUMN = "book_to_market"
BM_IA_COLUMN = "bm_ia"


def load_compustat(db) -> pd.DataFrame:
    comp = read_wrds_sql(
        db,
        """
        SELECT gvkey, datadate, fyear,
               seq, ceq, at, lt,
               pstk, pstkl, pstkrv,
               txditc
        FROM comp.funda
        WHERE indfmt = 'INDL'
          AND datafmt = 'STD'
          AND popsrc = 'D'
          AND consol = 'C'
        """,
    )
    comp["datadate"] = pd.to_datetime(comp["datadate"])

    company = read_wrds_sql(
        db,
        """
        SELECT gvkey, sic
        FROM comp.company
        """,
    )
    comp = comp.merge(company, on="gvkey", how="left")

    comp["preferred_stock"] = (
        comp["pstkrv"].fillna(comp["pstkl"]).fillna(comp["pstk"]).fillna(0)
    )
    comp["stockholders_equity"] = comp["seq"]
    comp.loc[comp["stockholders_equity"].isna(), "stockholders_equity"] = (
        comp["ceq"] + comp["preferred_stock"]
    )
    comp.loc[comp["stockholders_equity"].isna(), "stockholders_equity"] = (
        comp["at"] - comp["lt"]
    )

    comp["txditc"] = comp["txditc"].fillna(0)
    comp["book_equity"] = (
        comp["stockholders_equity"] + comp["txditc"] - comp["preferred_stock"]
    )
    comp = comp[comp["book_equity"] > 0].copy()
    comp["book_equity"] = comp["book_equity"] * 1000
    comp["calendar_year"] = comp["datadate"].dt.year

    return (
        comp.sort_values(["gvkey", "calendar_year", "datadate"])
        .drop_duplicates(["gvkey", "calendar_year"], keep="last")
    )


def load_crsp_monthly(db) -> pd.DataFrame:
    crsp = read_wrds_sql(
        db,
        f"""
        SELECT m.permno, m.permco, m.date, m.prc, m.shrout,
               n.exchcd, n.shrcd
        FROM crsp.msf AS m
        JOIN crsp.msenames AS n
          ON m.permno = n.permno
         AND n.namedt <= m.date
         AND m.date <= COALESCE(n.nameendt, DATE '9999-12-31')
        WHERE {crsp_universe_filter("n")}
        """,
    )
    crsp["date"] = pd.to_datetime(crsp["date"])
    crsp["year"] = crsp["date"].dt.year
    crsp["month"] = crsp["date"].dt.month
    crsp = crsp.sort_values(["permno", "date"])
    crsp["market_equity"] = crsp["prc"].abs() * crsp["shrout"]
    return crsp[crsp["market_equity"].notna() & (crsp["market_equity"] > 0)].copy()


def december_firm_market_equity(crsp: pd.DataFrame) -> pd.DataFrame:
    december = crsp[crsp["month"] == 12].copy()
    return (
        december.groupby(["permco", "year"], as_index=False)["market_equity"]
        .sum()
        .rename(columns={"year": "calendar_year"})
    )


def build_book_to_market(comp: pd.DataFrame, crsp_december_me: pd.DataFrame, link: pd.DataFrame) -> pd.DataFrame:
    comp_linked = attach_ccm_links(comp, link)
    bm = comp_linked.merge(
        crsp_december_me,
        on=["permco", "calendar_year"],
        how="inner",
    )
    bm[BM_COLUMN] = bm["book_equity"] / bm["market_equity"]
    bm = bm[bm[BM_COLUMN] > 0].copy()
    bm = (
        bm.sort_values(
            ["permno", "datadate", "market_equity"],
            ascending=[True, True, False],
        )
        .drop_duplicates(["permno", "datadate"], keep="first")
    )
    return bm[
        ["permno", "permco", "gvkey", "datadate", "sic", "fyear", BM_COLUMN]
    ].copy()


def build_crsp_month_index(crsp: pd.DataFrame) -> pd.DataFrame:
    out = crsp[["permno", "date"]].copy()
    out["signal_yyyymm"] = out["date"].dt.year * 100 + out["date"].dt.month
    return out[["permno", "signal_yyyymm"]].drop_duplicates()


def expand_annual_file_6month_rolling(
    df: pd.DataFrame,
    character_columns: list[str],
    crsp_month_index: pd.DataFrame,
) -> pd.DataFrame:
    """6-month per-firm rolling lag with forward-fill until the next FY refresh."""
    df = df.copy()
    df["datadate"] = pd.to_datetime(df["datadate"])
    availability = df["datadate"] + pd.DateOffset(months=6)
    df["availability_yyyymm"] = (
        availability.dt.year * 100 + availability.dt.month
    ).astype("int64")

    id_cols = ["permno", "permco", "gvkey", "datadate", "sic", "fyear"]
    cols = id_cols + list(character_columns) + ["availability_yyyymm"]
    df_sorted = df[cols].copy()
    df_sorted["permno"] = pd.to_numeric(df_sorted["permno"], errors="coerce").astype("int64")
    df_sorted = df_sorted.sort_values(["permno", "availability_yyyymm", "datadate"])

    crsp = crsp_month_index[["permno", "signal_yyyymm"]].drop_duplicates()
    crsp["permno"] = pd.to_numeric(crsp["permno"], errors="coerce").astype("int64")
    crsp["signal_yyyymm"] = pd.to_numeric(crsp["signal_yyyymm"], errors="coerce").astype("int64")
    crsp = crsp.sort_values(["permno", "signal_yyyymm"])

    parts: list[pd.DataFrame] = []
    ann_by_permno = {p: g for p, g in df_sorted.groupby("permno", sort=False)}
    for permno, crsp_grp in crsp.groupby("permno", sort=False):
        ann_grp = ann_by_permno.get(permno)
        if ann_grp is None or ann_grp.empty:
            continue
        merged = pd.merge_asof(
            crsp_grp.sort_values("signal_yyyymm"),
            ann_grp.drop(columns=["permno"]).sort_values("availability_yyyymm"),
            left_on="signal_yyyymm",
            right_on="availability_yyyymm",
            direction="backward",
        )
        merged["permno"] = permno
        parts.append(merged)

    if not parts:
        return pd.DataFrame(
            columns=["permno", "signal_yyyymm", "target_yyyymm", "permco", "gvkey", "sic"]
            + list(character_columns)
        )

    result = pd.concat(parts, ignore_index=True)
    result = result.dropna(subset=character_columns)
    result["target_yyyymm"] = result["signal_yyyymm"].map(add_one_month)
    keep = ["permno", "signal_yyyymm", "target_yyyymm", "permco", "gvkey", "sic"] + list(
        character_columns
    )
    return result[keep]


def build_bm_ia(
    annual_btm: pd.DataFrame,
    *,
    timing: str,
    crsp_month_index: pd.DataFrame | None = None,
) -> pd.DataFrame:
    if timing == "june":
        monthly = expand_annual_file_june(annual_btm, [BM_COLUMN])
    elif timing == "rolling6":
        if crsp_month_index is None:
            raise ValueError("crsp_month_index required for rolling6 timing")
        monthly = expand_annual_file_6month_rolling(
            annual_btm, [BM_COLUMN], crsp_month_index
        )
    else:
        raise ValueError(f"Unknown timing: {timing!r}")

    monthly = monthly[monthly[BM_COLUMN].notna()].copy()
    monthly = demean_by_industry_month(
        monthly,
        value_column=BM_COLUMN,
        industry_digits=2,
        stat="mean",
        output_column=BM_IA_COLUMN,
    )
    return monthly[["permno", "signal_yyyymm", BM_IA_COLUMN]].copy()


def load_datashare_bm_ia(path: Path) -> pd.DataFrame:
    ds = pd.read_csv(path, usecols=["permno", "DATE", BM_IA_COLUMN])
    ds = ds.dropna(subset=[BM_IA_COLUMN])
    ds[BM_IA_COLUMN] = pd.to_numeric(ds[BM_IA_COLUMN], errors="coerce")
    ds = ds.dropna(subset=[BM_IA_COLUMN])
    ds["signal_yyyymm"] = (pd.to_numeric(ds["DATE"], errors="coerce") // 100).astype(int)
    return ds[["permno", "signal_yyyymm", BM_IA_COLUMN]].copy()


def change_frequency(panel: pd.DataFrame, value_col: str) -> dict[str, float]:
    p = panel.sort_values(["permno", "signal_yyyymm"]).copy()
    p["lag"] = p.groupby("permno")[value_col].shift(1)
    c = p.dropna(subset=["lag"])
    if c.empty:
        return {"change_pct": np.nan, "distinct_avg": np.nan, "distinct_median": np.nan}
    changed = c[value_col] != c["lag"]
    distinct = panel.groupby("permno")[value_col].nunique()
    return {
        "change_pct": float(changed.mean() * 100),
        "distinct_avg": float(distinct.mean()),
        "distinct_median": float(distinct.median()),
    }


def compare_to_datashare(panel: pd.DataFrame, ds: pd.DataFrame) -> dict:
    merged = panel.merge(
        ds,
        on=["permno", "signal_yyyymm"],
        how="inner",
        suffixes=("_panel", "_ds"),
    )
    merged = merged.dropna(subset=[f"{BM_IA_COLUMN}_panel", f"{BM_IA_COLUMN}_ds"])
    if merged.empty:
        return {"paired_rows": 0}

    rho_pooled, _ = spearmanr(
        merged[f"{BM_IA_COLUMN}_panel"], merged[f"{BM_IA_COLUMN}_ds"]
    )

    rhos = []
    for _, grp in merged.groupby("signal_yyyymm"):
        if len(grp) < MIN_PAIRS:
            continue
        r, _ = spearmanr(grp[f"{BM_IA_COLUMN}_panel"], grp[f"{BM_IA_COLUMN}_ds"])
        if not np.isnan(r):
            rhos.append(r)
    rhos = np.array(rhos)

    freq = change_frequency(
        panel.rename(columns={BM_IA_COLUMN: BM_IA_COLUMN}),
        BM_IA_COLUMN,
    )

    return {
        "sample_n": int(panel[BM_IA_COLUMN].notna().sum()),
        "unique_permnos": int(panel["permno"].nunique()),
        "paired_rows": int(len(merged)),
        "paired_permnos": int(merged["permno"].nunique()),
        "paired_months": int(merged["signal_yyyymm"].nunique()),
        "pooled_spearman": float(rho_pooled),
        "median_monthly_spearman": float(np.median(rhos)) if len(rhos) else np.nan,
        "mean_monthly_spearman": float(np.mean(rhos)) if len(rhos) else np.nan,
        "share_months_gt_095": float((rhos > 0.95).mean()) if len(rhos) else np.nan,
        "share_months_gt_090": float((rhos > 0.90).mean()) if len(rhos) else np.nan,
        "change_pct": freq["change_pct"],
        "distinct_avg": freq["distinct_avg"],
        "distinct_median": freq["distinct_median"],
    }


def print_row(label: str, metrics: dict) -> None:
    print(f"\n=== {label} ===")
    if metrics.get("paired_rows", 0) == 0:
        print("  No paired rows vs datashare.")
        return
    print(f"  sample_n:              {metrics['sample_n']:,}")
    print(f"  unique_permnos:        {metrics['unique_permnos']:,}")
    print(f"  paired_rows:           {metrics['paired_rows']:,}")
    print(f"  paired_permnos:        {metrics['paired_permnos']:,}")
    print(f"  paired_months:         {metrics['paired_months']:,}")
    print(f"  pooled_spearman:       {metrics['pooled_spearman']:.4f}")
    print(f"  median_monthly_spearman: {metrics['median_monthly_spearman']:.4f}")
    print(f"  mean_monthly_spearman: {metrics['mean_monthly_spearman']:.4f}")
    print(f"  share months > 0.95:   {100 * metrics['share_months_gt_095']:.1f}%")
    print(f"  share months > 0.90:   {100 * metrics['share_months_gt_090']:.1f}%")
    print(f"  change frequency:      {metrics['change_pct']:.1f}%")
    print(f"  distinct bm_ia/permno: avg {metrics['distinct_avg']:.1f}, median {metrics['distinct_median']:.1f}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--wrds-user", default=None, help="WRDS username (optional if configured locally)")
    parser.add_argument("--datashare", type=Path, default=DEFAULT_DATASHARE)
    parser.add_argument("--sample-start", default="1950-01-01")
    parser.add_argument("--ccm-linktypes", default="L*")
    parser.add_argument("--ccm-linkprim", default="P,C")
    parser.add_argument(
        "--save-csvs",
        action="store_true",
        help="Save 4 bm_ia variant CSVs to outputs/panels/bm_ia_2x2/",
    )
    args = parser.parse_args()

    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

    if not args.datashare.exists():
        raise FileNotFoundError(f"datashare not found: {args.datashare}")

    os.environ["STOCK_CHARACTERS_SAMPLE_START"] = args.sample_start
    os.environ["STOCK_CHARACTERS_CRSP_EXCHCD"] = "1,2,3"

    print("Connecting to WRDS...", flush=True)
    db = wrds.Connection(wrds_username=args.wrds_user) if args.wrds_user else wrds.Connection()
    try:
        print("Pulling Compustat + CCM (shared)...", flush=True)
        comp = load_compustat(db)
        link = load_ccm_links(db, args.ccm_linktypes, args.ccm_linkprim)

        crsp_by_shrcd: dict[str, pd.DataFrame] = {}
        dec_me_by_shrcd: dict[str, pd.DataFrame] = {}
        month_index_by_shrcd: dict[str, pd.DataFrame] = {}

        for shrcd_label, shrcd_value in [("10,11", "10,11"), ("ALL", "ALL")]:
            print(f"Pulling CRSP monthly (shrcd={shrcd_label})...", flush=True)
            os.environ["STOCK_CHARACTERS_CRSP_SHRCD"] = shrcd_value
            crsp = load_crsp_monthly(db)
            crsp_by_shrcd[shrcd_label] = crsp
            dec_me_by_shrcd[shrcd_label] = december_firm_market_equity(crsp)
            month_index_by_shrcd[shrcd_label] = build_crsp_month_index(crsp)
            print(f"  CRSP rows: {len(crsp):,}, permnos: {crsp['permno'].nunique():,}", flush=True)

        btm_by_shrcd = {
            shrcd: build_book_to_market(comp, dec_me_by_shrcd[shrcd], link)
            for shrcd in crsp_by_shrcd
        }
        for shrcd, btm in btm_by_shrcd.items():
            print(f"book_to_market ({shrcd}): {len(btm):,} rows, {btm['permno'].nunique():,} permnos", flush=True)
    finally:
        db.close()

    print("Loading datashare bm_ia...", flush=True)
    ds = load_datashare_bm_ia(args.datashare)
    ds_freq = change_frequency(ds.rename(columns={BM_IA_COLUMN: BM_IA_COLUMN}), BM_IA_COLUMN)
    print_row(
        "DATASHARE (reference)",
        {
            "sample_n": int(ds[BM_IA_COLUMN].notna().sum()),
            "unique_permnos": int(ds["permno"].nunique()),
            "paired_rows": int(ds[BM_IA_COLUMN].notna().sum()),
            "paired_permnos": int(ds["permno"].nunique()),
            "paired_months": int(ds["signal_yyyymm"].nunique()),
            "pooled_spearman": 1.0,
            "median_monthly_spearman": 1.0,
            "mean_monthly_spearman": 1.0,
            "share_months_gt_095": 1.0,
            "share_months_gt_090": 1.0,
            "change_pct": ds_freq["change_pct"],
            "distinct_avg": ds_freq["distinct_avg"],
            "distinct_median": ds_freq["distinct_median"],
        },
    )

    variants = [
        ("A: June + shrcd=10,11", "10,11", "june"),
        ("B: June + shrcd=ALL", "ALL", "june"),
        ("C: 6mo rolling + shrcd=10,11", "10,11", "rolling6"),
        ("D: 6mo rolling + shrcd=ALL", "ALL", "rolling6"),
    ]

    save_dir = ROOT / "outputs" / "panels" / "bm_ia_2x2"
    if args.save_csvs:
        save_dir.mkdir(parents=True, exist_ok=True)

    results = []
    for label, shrcd, timing in variants:
        print(f"\nBuilding {label}...", flush=True)
        crsp_idx = month_index_by_shrcd[shrcd] if timing == "rolling6" else None
        panel = build_bm_ia(btm_by_shrcd[shrcd], timing=timing, crsp_month_index=crsp_idx)
        metrics = compare_to_datashare(panel, ds)
        metrics["label"] = label
        results.append(metrics)
        print_row(label, metrics)
        if args.save_csvs:
            slug = label.split(":")[0].strip().lower()
            out = save_dir / f"bm_ia_{slug}.csv"
            panel.to_csv(out, index=False)
            print(f"  saved: {out}", flush=True)

    print("\n=== SUMMARY TABLE ===")
    header = (
        f"{'Variant':<32} {'Med rho':>8} {'Pooled':>8} {'Change%':>8} "
        f"{'Dist/perm':>10} {'Paired N':>12} {'Permnos':>8}"
    )
    print(header)
    print("-" * len(header))
    print(
        f"{'DATASHARE':<32} {'1.0000':>8} {'1.0000':>8} "
        f"{ds_freq['change_pct']:>7.1f}% {ds_freq['distinct_avg']:>10.1f} "
        f"{int(ds[BM_IA_COLUMN].notna().sum()):>12,} {int(ds['permno'].nunique()):>8,}"
    )
    for m in results:
        print(
            f"{m['label']:<32} "
            f"{m.get('median_monthly_spearman', float('nan')):>8.4f} "
            f"{m.get('pooled_spearman', float('nan')):>8.4f} "
            f"{m.get('change_pct', float('nan')):>7.1f}% "
            f"{m.get('distinct_avg', float('nan')):>10.1f} "
            f"{m.get('paired_rows', 0):>12,} "
            f"{m.get('paired_permnos', 0):>8,}"
        )


if __name__ == "__main__":
    main()
