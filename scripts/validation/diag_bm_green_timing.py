#!/usr/bin/env python3
"""Diagnostic: rebuild bm / bm_ia using firm-specific fiscal-year-end timing.

Tests the hypothesis (confirmed empirically against datashare.csv's own bm
jump months, joined back to fiscal-year-end month) that datashare's bm is
NOT June-of-(fiscal year + 1) for every firm, but datadate + 7 months,
per-firm (the same "Green annual rolling" convention already implemented in
Character_Panels/timing.py for the other Green characteristics, currently
NOT applied to book_to_market / bm / bm_ia).

Variants:
  - june:  expand_annual_file_june  (current book_to_market / bm_ia builder)
  - green: expand_annual_file_green (datadate + 7..19 months, firm-specific)

Compares both variants' bm AND the resulting sic2 x month bm_ia against
published datashare bm / bm_ia.

All local (no WRDS). Read-only on production files.

Outputs under outputs/diagnostics/:
  bm_green_timing_comparison.csv
  bm_green_timing_summary.txt
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "Character_Builders"))

from Character_Builders._shared.bm_ia_builder import demean_by_industry_month  # noqa: E402
from Character_Panels.timing import (  # noqa: E402
    ANNUAL_ID_COLUMNS,
    MONTHLY_KEYS,
    add_one_month,
    expand_annual_file_green,
    expand_annual_file_june,
)

DEFAULT_BM_CSV = PROJECT_ROOT / "outputs" / "characteristics" / "individual" / "book_to_market.csv"
DEFAULT_DATASHARE = PROJECT_ROOT / "Supplementary_assistive_files" / "datashare.csv"
OUT_DIR = PROJECT_ROOT / "outputs" / "diagnostics"

BM_COLUMN = "book_to_market"
MIN_PAIRS = 50
CHUNK_SIZE = 500_000


def expand_annual_file_firmspecific(
    df: pd.DataFrame, character_columns: list[str], *, start_lag: int, end_lag: int
) -> pd.DataFrame:
    """Firm-specific datadate + start_lag..end_lag-1 months (parametrized Green window)."""
    df = df.copy()
    df["datadate"] = pd.to_datetime(df["datadate"])

    chunks = []
    id_cols = list(ANNUAL_ID_COLUMNS) + list(character_columns)
    for month_lag in range(start_lag, end_lag):
        chunk = df[id_cols].copy()
        signal_dates = (chunk["datadate"] + pd.DateOffset(months=month_lag)).dt.to_period("M").dt.to_timestamp("M")
        chunk["signal_yyyymm"] = (signal_dates.dt.year * 100 + signal_dates.dt.month).astype(int)
        chunks.append(chunk)

    expanded = pd.concat(chunks, ignore_index=True)
    expanded = (
        expanded.sort_values(["permno", "signal_yyyymm", "datadate"])
        .drop_duplicates(["permno", "signal_yyyymm"], keep="last")
    )
    expanded["target_yyyymm"] = expanded["signal_yyyymm"].map(add_one_month)
    keep = MONTHLY_KEYS + ["permco", "gvkey", "sic"] + list(character_columns)
    return expanded[keep]


def build_monthly(annual: pd.DataFrame, convention: str) -> pd.DataFrame:
    if convention == "june":
        monthly = expand_annual_file_june(annual, [BM_COLUMN])
    elif convention == "green":
        monthly = expand_annual_file_green(annual, [BM_COLUMN])
    elif convention == "firmspecific_6mo":
        monthly = expand_annual_file_firmspecific(annual, [BM_COLUMN], start_lag=6, end_lag=19)
    else:
        raise ValueError(convention)
    monthly = monthly[monthly[BM_COLUMN].notna()].copy()
    monthly = monthly.rename(columns={BM_COLUMN: "bm"})
    monthly = demean_by_industry_month(
        monthly,
        value_column="bm",
        industry_column="sic",
        industry_digits=2,
        time_column="signal_yyyymm",
        stat="mean",
        output_column="bm_ia",
    )
    return monthly


def load_datashare(datashare_path: Path) -> tuple[pd.DataFrame, int, int]:
    frames = []
    for chunk in pd.read_csv(
        datashare_path,
        usecols=["permno", "DATE", "bm", "bm_ia"],
        chunksize=CHUNK_SIZE,
    ):
        chunk["permno"] = pd.to_numeric(chunk["permno"], errors="coerce").astype("Int64")
        chunk["month"] = (pd.to_numeric(chunk["DATE"], errors="coerce") // 100).astype("Int64")
        chunk["bm"] = pd.to_numeric(chunk["bm"], errors="coerce")
        chunk["bm_ia"] = pd.to_numeric(chunk["bm_ia"], errors="coerce")
        frames.append(chunk.drop(columns=["DATE"]))
    ds = pd.concat(frames, ignore_index=True)
    return ds, int(ds["month"].min()), int(ds["month"].max())


def monthly_spearman_values(df: pd.DataFrame, a: str, b: str) -> list[float]:
    vals = []
    for _, grp in df.groupby("month", sort=True):
        sub = grp[[a, b]].dropna()
        if len(sub) < MIN_PAIRS:
            continue
        r = sub[a].corr(sub[b], method="spearman")
        if pd.notna(r):
            vals.append(float(r))
    return vals


def compare_character(
    panel: pd.DataFrame,
    ds: pd.DataFrame,
    *,
    panel_col: str,
    ds_col: str,
    month_min: int,
    month_max: int,
) -> dict:
    ds_sub = ds[["permno", "month", ds_col]].rename(columns={ds_col: "dv"})
    panel_sub = panel[["permno", "signal_yyyymm", "target_yyyymm", panel_col]].rename(
        columns={panel_col: "pv"}
    )

    best = None
    for month_col in ("signal_yyyymm", "target_yyyymm"):
        ps = panel_sub.rename(columns={month_col: "month"})[["permno", "month", "pv"]]
        ps = ps[ps["month"].between(month_min, month_max)]
        m = ds_sub.merge(ps, on=["permno", "month"], how="inner").dropna(subset=["dv", "pv"])
        n_pair = len(m)
        if n_pair < 2:
            row = {
                "month_align": month_col,
                "paired_obs": 0,
                "pooled_spearman": np.nan,
                "exact_rate_pct": np.nan,
                "median_monthly_spearman": np.nan,
                "mean_monthly_spearman": np.nan,
                "spearman_months": 0,
                "permno_both": 0,
            }
        else:
            pv = m["pv"].astype("float64")
            dv = m["dv"].astype("float64")
            vals = monthly_spearman_values(m.rename(columns={"pv": "a", "dv": "b"}), "a", "b")
            diff = (pv - dv).abs()
            row = {
                "month_align": month_col,
                "paired_obs": int(n_pair),
                "pooled_spearman": float(pv.corr(dv, method="spearman")),
                "exact_rate_pct": 100 * float((diff <= 1e-4).mean()),
                "median_monthly_spearman": float(np.median(vals)) if vals else np.nan,
                "mean_monthly_spearman": float(np.mean(vals)) if vals else np.nan,
                "spearman_months": len(vals),
                "permno_both": int(m["permno"].nunique()),
            }
        if best is None or (
            pd.notna(row["median_monthly_spearman"])
            and (
                pd.isna(best["median_monthly_spearman"])
                or row["median_monthly_spearman"] > best["median_monthly_spearman"]
            )
        ):
            best = row
    return best or {}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bm-csv", type=Path, default=DEFAULT_BM_CSV)
    parser.add_argument("--datashare", type=Path, default=DEFAULT_DATASHARE)
    parser.add_argument("--out-dir", type=Path, default=OUT_DIR)
    args = parser.parse_args()

    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

    if not args.bm_csv.exists():
        raise FileNotFoundError(f"book_to_market CSV not found: {args.bm_csv}")
    if not args.datashare.exists():
        raise FileNotFoundError(f"datashare not found: {args.datashare}")

    args.out_dir.mkdir(parents=True, exist_ok=True)

    print("Loading annual book_to_market...", flush=True)
    annual = pd.read_csv(args.bm_csv)
    print(f"  annual rows={len(annual):,} permnos={annual['permno'].nunique():,}", flush=True)

    print("Loading datashare bm / bm_ia...", flush=True)
    ds, month_min, month_max = load_datashare(args.datashare)
    print(f"  datashare rows={len(ds):,} months={month_min}-{month_max}", flush=True)

    results = []
    monthly_cache = {}
    for convention, label in [
        ("june", "june (current builder)"),
        ("green", "green +7mo firm-specific (candidate)"),
        ("firmspecific_6mo", "firm-specific +6mo (HXZ/FF classic lag)"),
    ]:
        print(f"\nExpanding with {label}...", flush=True)
        monthly = build_monthly(annual, convention)
        monthly_cache[convention] = monthly
        print(f"  monthly rows={len(monthly):,} permnos={monthly['permno'].nunique():,}", flush=True)

        for char_col, ds_col in [("bm", "bm"), ("bm_ia", "bm_ia")]:
            stats = compare_character(
                monthly, ds, panel_col=char_col, ds_col=ds_col,
                month_min=month_min, month_max=month_max,
            )
            print(
                f"  {char_col:6s} vs datashare {ds_col:6s}: "
                f"median rho={stats.get('median_monthly_spearman', float('nan')):.4f}  "
                f"pooled={stats.get('pooled_spearman', float('nan')):.4f}  "
                f"exact%={stats.get('exact_rate_pct', float('nan')):.2f}  "
                f"align={stats.get('month_align')}  paired={stats.get('paired_obs', 0):,}",
                flush=True,
            )
            results.append({
                "convention": convention,
                "label": label,
                "character": char_col,
                "month_align": stats.get("month_align"),
                "median_monthly_spearman": stats.get("median_monthly_spearman"),
                "mean_monthly_spearman": stats.get("mean_monthly_spearman"),
                "pooled_spearman": stats.get("pooled_spearman"),
                "exact_rate_pct": stats.get("exact_rate_pct"),
                "paired_obs": stats.get("paired_obs"),
                "permno_both": stats.get("permno_both"),
            })

    res_df = pd.DataFrame(results)
    cmp_csv = args.out_dir / "bm_green_timing_comparison.csv"
    res_df.to_csv(cmp_csv, index=False)

    def rho(conv, char):
        row = res_df[(res_df["convention"] == conv) & (res_df["character"] == char)]
        return float(row["median_monthly_spearman"].iloc[0]) if len(row) else float("nan")

    summary_lines = [
        "bm / bm_ia timing rebuild: june (uniform) vs green (firm-specific +7mo)",
        f"Source bm CSV: {args.bm_csv}",
        f"Datashare: {args.datashare}",
        f"Comparison window: {month_min}-{month_max}",
        "",
        res_df[
            ["label", "character", "median_monthly_spearman", "mean_monthly_spearman",
             "pooled_spearman", "exact_rate_pct", "paired_obs"]
        ].to_string(index=False),
        "",
        f"bm     median rho: june={rho('june','bm'):.4f}  green={rho('green','bm'):.4f}  "
        f"delta={rho('green','bm') - rho('june','bm'):+.4f}",
        f"bm_ia  median rho: june={rho('june','bm_ia'):.4f}  green={rho('green','bm_ia'):.4f}  "
        f"delta={rho('green','bm_ia') - rho('june','bm_ia'):+.4f}",
    ]
    summary_path = args.out_dir / "bm_green_timing_summary.txt"
    summary_path.write_text("\n".join(summary_lines) + "\n", encoding="utf-8")

    print(f"\nWrote {cmp_csv}")
    print(f"Wrote {summary_path}")
    print("\n" + "\n".join(summary_lines[4:]), flush=True)


if __name__ == "__main__":
    main()
