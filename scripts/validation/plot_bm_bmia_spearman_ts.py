#!/usr/bin/env python3
"""Plot monthly cross-sectional Spearman time series for bm and bm_ia vs datashare.

Compares panel vs GKX datashare.csv for:
  - datashare bm  vs panel book_to_market
  - datashare bm_ia vs panel bm_ia

Alignment: panel signal_yyyymm = datashare month (DATE // 100).
Window: datashare min/max month only.

Outputs:
  - outputs/diagnostics/bm_bmia_spearman_monthly_ts.csv
  - outputs/diagnostics/bm_bmia_spearman_monthly_ts.png

Standalone: no repo imports.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_PANEL = PROJECT_ROOT / "outputs" / "panels" / "research_panel_1957_ranked_7312026.csv"
DEFAULT_DATASHARE = PROJECT_ROOT / "Supplementary_assistive_files" / "datashare.csv"
OUT_CSV = PROJECT_ROOT / "outputs" / "diagnostics" / "bm_bmia_spearman_monthly_ts.csv"
OUT_PNG = PROJECT_ROOT / "outputs" / "diagnostics" / "bm_bmia_spearman_monthly_ts.png"

MIN_PAIRS = 50
ROLLING_WINDOW = 12
CHUNK_SIZE = 500_000

CHAR_SPECS = (
    ("bm", "book_to_market", "rho_bm", "n_pairs_bm"),
    ("bm_ia", "bm_ia", "rho_bm_ia", "n_pairs_bm_ia"),
)


def month_to_datetime(month: int) -> pd.Timestamp:
    year = month // 100
    mon = month % 100
    return pd.Timestamp(year=year, month=mon, day=1)


def load_datashare(datashare_path: Path) -> pd.DataFrame:
    frames = []
    usecols = ["permno", "DATE", "bm", "bm_ia"]
    for chunk in pd.read_csv(datashare_path, usecols=usecols, chunksize=CHUNK_SIZE):
        chunk["permno"] = pd.to_numeric(chunk["permno"], errors="coerce").astype("Int64")
        chunk["month"] = (pd.to_numeric(chunk["DATE"], errors="coerce") // 100).astype("Int64")
        for col in ("bm", "bm_ia"):
            chunk[col] = pd.to_numeric(chunk[col], errors="coerce").astype("float32")
        frames.append(chunk.drop(columns=["DATE"]))
    return pd.concat(frames, ignore_index=True)


def datashare_month_bounds(ds: pd.DataFrame) -> tuple[int, int]:
    months = ds["month"].dropna()
    return int(months.min()), int(months.max())


def load_panel(panel_path: Path, month_min: int, month_max: int) -> pd.DataFrame:
    usecols = ["permno", "signal_yyyymm", "book_to_market", "bm_ia"]
    frames = []
    for chunk in pd.read_csv(panel_path, usecols=usecols, chunksize=CHUNK_SIZE):
        chunk["permno"] = pd.to_numeric(chunk["permno"], errors="coerce").astype("Int64")
        chunk["signal_yyyymm"] = pd.to_numeric(
            chunk["signal_yyyymm"], errors="coerce"
        ).astype("Int64")
        for col in ("book_to_market", "bm_ia"):
            chunk[col] = pd.to_numeric(chunk[col], errors="coerce").astype("float32")
        in_window = chunk["signal_yyyymm"].between(month_min, month_max)
        frames.append(chunk.loc[in_window])
    return pd.concat(frames, ignore_index=True)


def merge_character(
    ds: pd.DataFrame,
    panel: pd.DataFrame,
    ds_col: str,
    panel_col: str,
    month_min: int,
    month_max: int,
) -> pd.DataFrame:
    ds_sub = ds[["permno", "month", ds_col]].rename(columns={ds_col: "dv"})
    ds_sub = ds_sub[ds_sub["month"].between(month_min, month_max)]
    panel_sub = panel[["permno", "signal_yyyymm", panel_col]].rename(
        columns={"signal_yyyymm": "month", panel_col: "pv"}
    )
    return ds_sub.merge(panel_sub, on=["permno", "month"], how="inner")


def monthly_spearman_series(
    merged: pd.DataFrame,
) -> tuple[pd.DataFrame, float, float]:
    rows = []
    for month, grp in merged.groupby("month", sort=True):
        sub = grp[["pv", "dv"]].dropna()
        n_pairs = len(sub)
        if n_pairs < MIN_PAIRS:
            continue
        rho = sub["pv"].corr(sub["dv"], method="spearman")
        if pd.notna(rho):
            rows.append({"month": int(month), "n_pairs": n_pairs, "rho": float(rho)})

    ts = pd.DataFrame(rows)
    if ts.empty:
        return ts, np.nan, np.nan

    pooled = merged[["pv", "dv"]].dropna()
    pooled_rho = float(pooled["pv"].corr(pooled["dv"], method="spearman"))
    median_rho = float(ts["rho"].median())
    return ts, pooled_rho, median_rho


def build_combined_table(
    bm_ts: pd.DataFrame,
    bm_ia_ts: pd.DataFrame,
) -> pd.DataFrame:
    bm_part = bm_ts.rename(columns={"n_pairs": "n_pairs_bm", "rho": "rho_bm"})
    bm_ia_part = bm_ia_ts.rename(
        columns={"n_pairs": "n_pairs_bm_ia", "rho": "rho_bm_ia"}
    )
    if bm_part.empty and bm_ia_part.empty:
        return pd.DataFrame(
            columns=["month", "n_pairs_bm", "rho_bm", "n_pairs_bm_ia", "rho_bm_ia"]
        )
    combined = bm_part.merge(bm_ia_part, on="month", how="outer")
    return combined.sort_values("month").reset_index(drop=True)


def plot_time_series(combined: pd.DataFrame, out_png: Path) -> None:
    fig, ax = plt.subplots(figsize=(14, 6))

    def plot_series(
        month_col: pd.Series,
        rho_col: pd.Series,
        label: str,
        color: str,
        ref_rho: float,
    ) -> None:
        valid = rho_col.notna()
        if not valid.any():
            return
        months = month_col[valid].astype(int).map(month_to_datetime)
        rhos = rho_col[valid].astype(float)
        ax.plot(months, rhos, color=color, alpha=0.35, linewidth=0.8, label=f"{label} (monthly)")
        rolling = rhos.rolling(window=ROLLING_WINDOW, min_periods=6).mean()
        ax.plot(
            months,
            rolling,
            color=color,
            linewidth=2.0,
            linestyle="--",
            label=f"{label} ({ROLLING_WINDOW}m rolling mean)",
        )
        ax.axhline(ref_rho, color=color, linewidth=0.8, linestyle=":", alpha=0.6)

    plot_series(combined["month"], combined["rho_bm"], "bm", "#1f77b4", 0.929)
    plot_series(combined["month"], combined["rho_bm_ia"], "bm_ia", "#d62728", 0.436)

    ax.set_title("Monthly cross-sectional Spearman: panel vs datashare")
    ax.set_xlabel("Month")
    ax.set_ylabel("Spearman ρ")
    ax.set_ylim(0.0, 1.0)
    ax.grid(True, alpha=0.3)
    ax.legend(loc="lower left", fontsize=9)
    fig.tight_layout()
    out_png.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_png, dpi=150)
    plt.close(fig)


def print_summary(
    bm_ts: pd.DataFrame,
    bm_ia_ts: pd.DataFrame,
    bm_pooled: float,
    bm_median: float,
    bm_ia_pooled: float,
    bm_ia_median: float,
) -> None:
    print("\n=== Summary (cross-check vs report) ===")
    for name, ts, pooled, median in (
        ("bm (book_to_market)", bm_ts, bm_pooled, bm_median),
        ("bm_ia", bm_ia_ts, bm_ia_pooled, bm_ia_median),
    ):
        print(f"\n{name}:")
        print(f"  pooled Spearman:  {pooled:.4f}")
        print(f"  median monthly ρ: {median:.4f}")
        if not ts.empty:
            print(f"  months with ρ:    {len(ts)}")
            print(f"  month range:      {int(ts['month'].min())} – {int(ts['month'].max())}")
            print(f"  % months ρ < 0.5: {100 * (ts['rho'] < 0.5).mean():.1f}%")
        else:
            print("  (no monthly series)")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--panel", type=Path, default=DEFAULT_PANEL)
    parser.add_argument("--datashare", type=Path, default=DEFAULT_DATASHARE)
    parser.add_argument("--out-csv", type=Path, default=OUT_CSV)
    parser.add_argument("--out-png", type=Path, default=OUT_PNG)
    args = parser.parse_args()

    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

    panel_path = args.panel if args.panel.is_absolute() else PROJECT_ROOT / args.panel
    datashare_path = (
        args.datashare if args.datashare.is_absolute() else PROJECT_ROOT / args.datashare
    )

    if not panel_path.exists():
        raise FileNotFoundError(f"Panel not found: {panel_path}")
    if not datashare_path.exists():
        raise FileNotFoundError(f"Datashare not found: {datashare_path}")

    print("Loading datashare...", flush=True)
    ds = load_datashare(datashare_path)
    month_min, month_max = datashare_month_bounds(ds)
    print(
        f"  rows={len(ds):,} permnos={ds['permno'].nunique():,} months={month_min}–{month_max}",
        flush=True,
    )

    print("Loading panel...", flush=True)
    panel = load_panel(panel_path, month_min, month_max)
    print(
        f"  rows={len(panel):,} permnos={panel['permno'].nunique():,}",
        flush=True,
    )

    print("Merging bm...", flush=True)
    bm_merged = merge_character(ds, panel, "bm", "book_to_market", month_min, month_max)
    bm_ts, bm_pooled, bm_median = monthly_spearman_series(bm_merged)
    print(f"  paired obs={len(bm_merged):,} monthly months={len(bm_ts)}", flush=True)

    print("Merging bm_ia...", flush=True)
    bm_ia_merged = merge_character(ds, panel, "bm_ia", "bm_ia", month_min, month_max)
    bm_ia_ts, bm_ia_pooled, bm_ia_median = monthly_spearman_series(bm_ia_merged)
    print(f"  paired obs={len(bm_ia_merged):,} monthly months={len(bm_ia_ts)}", flush=True)

    combined = build_combined_table(bm_ts, bm_ia_ts)
    args.out_csv.parent.mkdir(parents=True, exist_ok=True)
    combined.to_csv(args.out_csv, index=False)
    print(f"\nWrote {args.out_csv}", flush=True)

    plot_time_series(combined, args.out_png)
    print(f"Wrote {args.out_png}", flush=True)

    print_summary(bm_ts, bm_ia_ts, bm_pooled, bm_median, bm_ia_pooled, bm_ia_median)


if __name__ == "__main__":
    main()
