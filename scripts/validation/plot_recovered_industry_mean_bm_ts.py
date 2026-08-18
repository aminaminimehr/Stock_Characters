#!/usr/bin/env python3
"""Plot recovered industry mean(bm) time series from datashare bm and bm_ia.

Recovers mean(bm) = bm - bm_ia per row, collapses to modal value per (sic2, month),
and plots:
  1) all industry mean(bm) series over time with cross-sectional median overlay
  2) active SIC2 count vs distinct recovered means per month (off-mode gap)

Standalone: no repo imports. Read-only on datashare.csv.

Outputs under outputs/diagnostics/:
  recovered_industry_mean_bm_ts.png
  recovered_industry_mean_bm.csv
  recovered_mean_count_gap.csv
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DATASHARE = PROJECT_ROOT / "Supplementary_assistive_files" / "datashare.csv"
OUT_DIR = PROJECT_ROOT / "outputs" / "diagnostics"
OUT_PNG = OUT_DIR / "recovered_industry_mean_bm_ts.png"
OUT_LONG_CSV = OUT_DIR / "recovered_industry_mean_bm.csv"
OUT_GAP_CSV = OUT_DIR / "recovered_mean_count_gap.csv"

CHUNK_SIZE = 500_000
MIN_CELL_SIZE = 10
ROUND_DECIMALS = 6


def month_to_datetime(month: int) -> pd.Timestamp:
    year = month // 100
    mon = month % 100
    return pd.Timestamp(year=year, month=mon, day=1)


def load_datashare(datashare_path: Path) -> pd.DataFrame:
    frames = []
    usecols = ["permno", "DATE", "bm", "bm_ia", "sic2"]
    for chunk in pd.read_csv(datashare_path, usecols=usecols, chunksize=CHUNK_SIZE):
        chunk["permno"] = pd.to_numeric(chunk["permno"], errors="coerce").astype("Int64")
        chunk["month"] = (pd.to_numeric(chunk["DATE"], errors="coerce") // 100).astype("Int64")
        for col in ("bm", "bm_ia", "sic2"):
            chunk[col] = pd.to_numeric(chunk[col], errors="coerce")
        frames.append(chunk.drop(columns=["DATE"]))
    return pd.concat(frames, ignore_index=True)


def modal_value(values: pd.Series) -> float:
    rounded = values.round(ROUND_DECIMALS)
    counts = rounded.value_counts()
    if counts.empty:
        return np.nan
    return float(counts.index[0])


def build_industry_means(
    df: pd.DataFrame,
    *,
    min_cell_size: int = MIN_CELL_SIZE,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    sub = df.dropna(subset=["bm", "bm_ia", "sic2"]).copy()
    sub["recovered_mean"] = (sub["bm"] - sub["bm_ia"]).round(ROUND_DECIMALS)

    gap = (
        sub.groupby("month", sort=True)
        .agg(
            n_active_sic2=("sic2", "nunique"),
            n_distinct_recovered_means=("recovered_mean", "nunique"),
            n_rows=("recovered_mean", "size"),
        )
        .reset_index()
    )
    gap["off_mode_gap"] = gap["n_distinct_recovered_means"] - gap["n_active_sic2"]

    cell_stats = (
        sub.groupby(["sic2", "month"], sort=True)["recovered_mean"]
        .agg(
            mean_bm=modal_value,
            n_cell="size",
            n_distinct="nunique",
        )
        .reset_index()
    )
    cell_stats = cell_stats[cell_stats["n_cell"] >= min_cell_size].copy()
    return cell_stats, gap


def plot_figure(
    industry: pd.DataFrame,
    gap: pd.DataFrame,
    out_png: Path,
    *,
    min_cell_size: int = MIN_CELL_SIZE,
) -> None:
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 10), sharex=True, gridspec_kw={"height_ratios": [2, 1]})

    y_vals = industry["mean_bm"].astype(float)
    y_lo, y_hi = np.nanpercentile(y_vals, [0.5, 99.5])
    pad = 0.05 * (y_hi - y_lo)
    y_lim = (y_lo - pad, y_hi + pad)

    sic2_values = sorted(industry["sic2"].dropna().unique())
    cmap = plt.get_cmap("tab20")
    color_map = {sic2: cmap(i % 20) for i, sic2 in enumerate(sic2_values)}

    for sic2, grp in industry.groupby("sic2", sort=True):
        months = grp["month"].astype(int).map(month_to_datetime)
        ax1.plot(
            months,
            grp["mean_bm"],
            color=color_map.get(sic2, "gray"),
            alpha=0.35,
            linewidth=0.8,
        )

    monthly_median = (
        industry.groupby("month", sort=True)["mean_bm"]
        .median()
        .reset_index()
    )
    ax1.plot(
        monthly_median["month"].astype(int).map(month_to_datetime),
        monthly_median["mean_bm"],
        color="black",
        linewidth=2.2,
        label="Cross-sectional median",
    )
    ax1.axhline(0.0, color="gray", linewidth=0.8, linestyle=":", alpha=0.7)
    ax1.set_ylabel("Recovered mean(bm)")
    ax1.set_title(
        "Recovered industry mean(bm) = bm - bm_ia, by SIC2 (modal per cell)\n"
        f"axes clipped to 0.5-99.5 percentiles; cells with n < {min_cell_size} dropped"
    )
    ax1.set_ylim(y_lim)
    ax1.grid(True, alpha=0.3)
    ax1.legend(loc="upper right")

    months_gap = gap["month"].astype(int).map(month_to_datetime)
    ax2.plot(months_gap, gap["n_active_sic2"], color="#1f77b4", linewidth=1.8, label="Active SIC2")
    ax2.plot(
        months_gap,
        gap["n_distinct_recovered_means"],
        color="#d62728",
        linewidth=1.8,
        label="Distinct recovered means",
    )
    ax2.fill_between(
        months_gap,
        gap["n_active_sic2"],
        gap["n_distinct_recovered_means"],
        color="#d62728",
        alpha=0.15,
        label="Off-mode gap",
    )
    ax2.set_ylabel("Count")
    ax2.set_xlabel("Month")
    ax2.set_title(
        "Active SIC2 vs distinct recovered means per month (gap = off-mode SIC-vintage noise)\n"
        f"distinct counts rounded to {ROUND_DECIMALS} decimals to remove float noise"
    )
    ax2.grid(True, alpha=0.3)
    ax2.legend(loc="upper left", fontsize=9)

    fig.tight_layout()
    out_png.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_png, dpi=150)
    plt.close(fig)


def print_summary(
    industry: pd.DataFrame,
    gap: pd.DataFrame,
    *,
    min_cell_size: int = MIN_CELL_SIZE,
) -> None:
    print("\n=== Summary ===")
    print(f"Unique SIC2 in modal table: {industry['sic2'].nunique()}")
    print(f"Industry-month cells (n >= {min_cell_size}): {len(industry):,}")
    print(f"Months covered: {int(gap['month'].min())} - {int(gap['month'].max())}")
    print(
        f"Mean active SIC2 / month: {gap['n_active_sic2'].mean():.1f} "
        f"(min={int(gap['n_active_sic2'].min())}, max={int(gap['n_active_sic2'].max())})"
    )
    print(
        f"Mean distinct recovered means / month: {gap['n_distinct_recovered_means'].mean():.1f} "
        f"(min={int(gap['n_distinct_recovered_means'].min())}, max={int(gap['n_distinct_recovered_means'].max())})"
    )
    print(
        f"Mean off-mode gap / month: {gap['off_mode_gap'].mean():.1f} "
        f"(median={gap['off_mode_gap'].median():.1f})"
    )
    print("\nSample months:")
    sample_months = [196301, 198001, 200001, 200401, 202012]
    sample = gap[gap["month"].isin(sample_months)].sort_values("month")
    print(sample.to_string(index=False))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--datashare", type=Path, default=DEFAULT_DATASHARE)
    parser.add_argument("--out-dir", type=Path, default=OUT_DIR)
    parser.add_argument("--min-cell-size", type=int, default=MIN_CELL_SIZE)
    args = parser.parse_args()

    min_cell_size = args.min_cell_size

    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

    if not args.datashare.exists():
        raise FileNotFoundError(f"Datashare not found: {args.datashare}")

    args.out_dir.mkdir(parents=True, exist_ok=True)

    print("Loading datashare...", flush=True)
    ds = load_datashare(args.datashare)
    print(
        f"  rows={len(ds):,} permnos={ds['permno'].nunique():,} "
        f"months={int(ds['month'].min())}-{int(ds['month'].max())}",
        flush=True,
    )

    print("Recovering modal industry means...", flush=True)
    industry, gap = build_industry_means(ds, min_cell_size=min_cell_size)
    print(
        f"  industry-month cells={len(industry):,} unique sic2={industry['sic2'].nunique()}",
        flush=True,
    )

    out_png = args.out_dir / OUT_PNG.name
    out_long = args.out_dir / OUT_LONG_CSV.name
    out_gap = args.out_dir / OUT_GAP_CSV.name

    industry.to_csv(out_long, index=False)
    gap.to_csv(out_gap, index=False)
    plot_figure(industry, gap, out_png, min_cell_size=min_cell_size)

    print(f"\nWrote {out_long}")
    print(f"Wrote {out_gap}")
    print(f"Wrote {out_png}")
    print_summary(industry, gap, min_cell_size=min_cell_size)


if __name__ == "__main__":
    main()
