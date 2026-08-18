#!/usr/bin/env python3
"""Diagnostic: per-month winsorized bm -> bm_ia vs datashare.

Tests whether cross-sectional monthly winsorization of book_to_market
(before SIC2 x month demeaning) improves replication of datashare bm and bm_ia.

Variants:
  - baseline: no winsorization
  - p1: clip to [1%, 99%] each signal month
  - p25: clip to [2.5%, 97.5%] each signal month

All processing is local (no WRDS). Does not modify production builders.

Outputs under outputs/diagnostics/:
  bm_winsor_{baseline,p1,p25}.csv
  bm_ia_winsor_{baseline,p1,p25}.csv
  winsorized_bm_bmia_comparison.csv
  winsorized_bm_bmia_summary.txt
  bm_ia_scatter_200401_winsor_{best}.png  (optional)
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "Character_Builders"))

from Character_Builders._shared.bm_ia_builder import demean_by_industry_month  # noqa: E402
from Character_Panels.timing import expand_annual_file_june  # noqa: E402

DEFAULT_BM_CSV = PROJECT_ROOT / "outputs" / "characteristics" / "individual" / "book_to_market.csv"
DEFAULT_DATASHARE = PROJECT_ROOT / "Supplementary_assistive_files" / "datashare.csv"
OUT_DIR = PROJECT_ROOT / "outputs" / "diagnostics"

BM_COLUMN = "book_to_market"
MIN_PAIRS = 50
CHUNK_SIZE = 500_000
SCATTER_MONTH = 200401

VARIANTS: tuple[tuple[str, float | None], ...] = (
    ("baseline", None),
    ("p1", 0.01),
    ("p25", 0.025),
)


def winsorize_cross_section(
    monthly: pd.DataFrame,
    *,
    value_column: str,
    time_column: str = "signal_yyyymm",
    tail: float,
) -> pd.DataFrame:
    """Clip ``value_column`` to [q(tail), q(1-tail)] within each month."""
    out = monthly.copy()
    grouped = out.groupby(time_column, sort=False)[value_column]
    lo = grouped.transform(lambda s: s.quantile(tail))
    hi = grouped.transform(lambda s: s.quantile(1.0 - tail))
    clipped = out[value_column].clip(lower=lo, upper=hi)
    out[value_column] = clipped.where(lo.notna() & hi.notna(), pd.NA)
    return out


def load_monthly_from_annual(bm_csv: Path) -> pd.DataFrame:
    annual = pd.read_csv(bm_csv)
    monthly = expand_annual_file_june(annual, [BM_COLUMN])
    monthly = monthly[monthly[BM_COLUMN].notna()].copy()
    sic = pd.to_numeric(monthly["sic"], errors="coerce")
    monthly["sic2"] = (sic // 100).astype("Int64")
    return monthly


def build_variant(monthly: pd.DataFrame, tail: float | None) -> pd.DataFrame:
    work = monthly.copy()
    if tail is not None:
        work = winsorize_cross_section(work, value_column=BM_COLUMN, tail=tail)
    work["bm"] = work[BM_COLUMN]
    work = demean_by_industry_month(
        work,
        value_column="bm",
        industry_column="sic",
        industry_digits=2,
        time_column="signal_yyyymm",
        stat="mean",
        output_column="bm_ia",
    )
    return work


def load_datashare(datashare_path: Path) -> pd.DataFrame:
    frames = []
    for chunk in pd.read_csv(
        datashare_path,
        usecols=["permno", "DATE", "bm", "bm_ia"],
        chunksize=CHUNK_SIZE,
    ):
        chunk["permno"] = pd.to_numeric(chunk["permno"], errors="coerce").astype("Int64")
        chunk["month"] = (pd.to_numeric(chunk["DATE"], errors="coerce") // 100).astype("Int64")
        for col in ("bm", "bm_ia"):
            chunk[col] = pd.to_numeric(chunk[col], errors="coerce")
        frames.append(chunk.drop(columns=["DATE"]))
    ds = pd.concat(frames, ignore_index=True)
    month_min = int(ds["month"].min())
    month_max = int(ds["month"].max())
    return ds, month_min, month_max


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
                "median_monthly_spearman": np.nan,
                "mean_monthly_spearman": np.nan,
                "spearman_months": 0,
                "exact_rate": np.nan,
                "round4_rate": np.nan,
                "permno_both": 0,
            }
        else:
            pv = m["pv"].astype("float64")
            dv = m["dv"].astype("float64")
            diff = (pv - dv).abs()
            vals = monthly_spearman_values(m.rename(columns={"pv": "a", "dv": "b"}), "a", "b")
            row = {
                "month_align": month_col,
                "paired_obs": int(n_pair),
                "pooled_spearman": float(pv.corr(dv, method="spearman")),
                "median_monthly_spearman": float(np.median(vals)) if vals else np.nan,
                "mean_monthly_spearman": float(np.mean(vals)) if vals else np.nan,
                "spearman_months": len(vals),
                "exact_rate": float((diff <= 1e-4).mean()),
                "round4_rate": float((np.round(pv, 4) == np.round(dv, 4)).mean()),
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


def write_variant_csvs(variant: str, monthly: pd.DataFrame, out_dir: Path) -> None:
    bm_out = monthly[["permno", "signal_yyyymm", "target_yyyymm", "bm", "sic2"]].copy()
    bm_ia_out = monthly[["permno", "signal_yyyymm", "target_yyyymm", "bm_ia", "sic2"]].copy()
    bm_out.to_csv(out_dir / f"bm_winsor_{variant}.csv", index=False)
    bm_ia_out.to_csv(out_dir / f"bm_ia_winsor_{variant}.csv", index=False)


def plot_scatter(
    panel: pd.DataFrame,
    ds: pd.DataFrame,
    *,
    variant: str,
    month: int,
    month_align: str,
    out_png: Path,
) -> None:
    ds_sub = ds.loc[ds["month"] == month, ["permno", "bm_ia"]].rename(columns={"bm_ia": "ds_bm_ia"})
    ps = panel.rename(columns={month_align: "month"})[["permno", "month", "bm_ia"]]
    ps = ps.loc[ps["month"] == month].rename(columns={"bm_ia": "panel_bm_ia"})
    m = ds_sub.merge(ps, on="permno", how="inner").dropna()
    if len(m) < 2:
        return

    rho = m["panel_bm_ia"].corr(m["ds_bm_ia"], method="spearman")
    pearson = m["panel_bm_ia"].corr(m["ds_bm_ia"], method="pearson")

    x_lo, x_hi = np.nanpercentile(m["ds_bm_ia"], [1, 99])
    y_lo, y_hi = np.nanpercentile(m["panel_bm_ia"], [1, 99])
    pad = 0.08
    x_rng, y_rng = x_hi - x_lo, y_hi - y_lo
    x_lim = (x_lo - pad * x_rng, x_hi + pad * x_rng)
    y_lim = (y_lo - pad * y_rng, y_hi + pad * y_rng)

    fig, ax = plt.subplots(figsize=(7, 7))
    ax.scatter(m["ds_bm_ia"], m["panel_bm_ia"], s=10, alpha=0.4, edgecolors="none")
    ax.set_xlim(x_lim)
    ax.set_ylim(y_lim)
    ax.set_xlabel("datashare bm_ia")
    ax.set_ylabel("panel bm_ia")
    ax.set_title(
        f"bm_ia winsor {variant} — {month // 100}-{month % 100:02d} ({month_align})\n"
        f"n={len(m):,} | Spearman ρ={rho:.3f} | Pearson r={pearson:.3f}"
    )
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    out_png.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_png, dpi=150)
    plt.close(fig)


def format_variant_label(variant: str, tail: float | None) -> str:
    if tail is None:
        return "baseline (no winsor)"
    return f"p={tail:.3f} ({100 * tail:.1f}% top+bottom)"


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

    print("Loading annual book_to_market and June-expanding...", flush=True)
    monthly_base = load_monthly_from_annual(args.bm_csv)
    print(
        f"  monthly rows={len(monthly_base):,} permnos={monthly_base['permno'].nunique():,} "
        f"months={monthly_base['signal_yyyymm'].min()}–{monthly_base['signal_yyyymm'].max()}",
        flush=True,
    )

    print("Loading datashare bm / bm_ia...", flush=True)
    ds, month_min, month_max = load_datashare(args.datashare)
    print(
        f"  datashare rows={len(ds):,} months={month_min}–{month_max}",
        flush=True,
    )

    results = []
    built: dict[str, pd.DataFrame] = {}

    for variant, tail in VARIANTS:
        label = format_variant_label(variant, tail)
        print(f"\n=== Variant: {label} ===", flush=True)
        monthly = build_variant(monthly_base, tail)
        built[variant] = monthly
        write_variant_csvs(variant, monthly, args.out_dir)
        print(f"  wrote bm_winsor_{variant}.csv and bm_ia_winsor_{variant}.csv", flush=True)

        bm_stats = compare_character(
            monthly,
            ds,
            panel_col="bm",
            ds_col="bm",
            month_min=month_min,
            month_max=month_max,
        )
        bm_ia_stats = compare_character(
            monthly,
            ds,
            panel_col="bm_ia",
            ds_col="bm_ia",
            month_min=month_min,
            month_max=month_max,
        )

        print(
            f"  bm:    median ρ={bm_stats.get('median_monthly_spearman', float('nan')):.4f} "
            f"(align={bm_stats.get('month_align')}, paired={bm_stats.get('paired_obs', 0):,})",
            flush=True,
        )
        print(
            f"  bm_ia: median ρ={bm_ia_stats.get('median_monthly_spearman', float('nan')):.4f} "
            f"(align={bm_ia_stats.get('month_align')}, paired={bm_ia_stats.get('paired_obs', 0):,})",
            flush=True,
        )

        results.append(
            {
                "variant": variant,
                "winsor_tail": tail if tail is not None else 0.0,
                "label": label,
                "bm_month_align": bm_stats.get("month_align"),
                "bm_median_rho": bm_stats.get("median_monthly_spearman"),
                "bm_mean_rho": bm_stats.get("mean_monthly_spearman"),
                "bm_pooled_rho": bm_stats.get("pooled_spearman"),
                "bm_paired_obs": bm_stats.get("paired_obs"),
                "bm_permno_both": bm_stats.get("permno_both"),
                "bm_ia_month_align": bm_ia_stats.get("month_align"),
                "bm_ia_median_rho": bm_ia_stats.get("median_monthly_spearman"),
                "bm_ia_mean_rho": bm_ia_stats.get("mean_monthly_spearman"),
                "bm_ia_pooled_rho": bm_ia_stats.get("pooled_spearman"),
                "bm_ia_paired_obs": bm_ia_stats.get("paired_obs"),
                "bm_ia_permno_both": bm_ia_stats.get("permno_both"),
            }
        )

    res_df = pd.DataFrame(results)
    cmp_csv = args.out_dir / "winsorized_bm_bmia_comparison.csv"
    res_df.to_csv(cmp_csv, index=False)

    best_row = res_df.sort_values("bm_ia_median_rho", ascending=False, na_position="last").iloc[0]
    best_variant = str(best_row["variant"])
    best_align = str(best_row["bm_ia_month_align"])

    scatter_png = args.out_dir / f"bm_ia_scatter_{SCATTER_MONTH}_winsor_{best_variant}.png"
    plot_scatter(
        built[best_variant],
        ds,
        variant=best_variant,
        month=SCATTER_MONTH,
        month_align=best_align,
        out_png=scatter_png,
    )

    summary_lines = [
        "Per-month winsorized bm / bm_ia diagnostic",
        f"Source bm CSV: {args.bm_csv}",
        f"Datashare: {args.datashare}",
        f"Comparison window: {month_min}–{month_max}",
        "",
        "Comparison matrix (best month alignment per character):",
        "",
        res_df[
            [
                "label",
                "bm_median_rho",
                "bm_paired_obs",
                "bm_ia_median_rho",
                "bm_ia_paired_obs",
                "bm_month_align",
                "bm_ia_month_align",
            ]
        ].to_string(index=False),
        "",
        f"Best bm_ia variant by median monthly Spearman: {best_row['label']} "
        f"(median ρ={best_row['bm_ia_median_rho']:.4f})",
        f"Same variant bm median ρ: {best_row['bm_median_rho']:.4f}",
        "",
        "Reference benchmarks:",
        "  bm baseline (panel, un-winsorized): ~0.929 median monthly Spearman",
        "  bm_ia baseline (panel, un-winsorized): ~0.436 median monthly Spearman",
        "  bm_ia formula ceiling (datashare bm + sic2): ~0.836",
        "",
        f"Scatter for best variant: {scatter_png.name}",
    ]
    summary_path = args.out_dir / "winsorized_bm_bmia_summary.txt"
    summary_path.write_text("\n".join(summary_lines) + "\n", encoding="utf-8")

    print(f"\nWrote {cmp_csv}")
    print(f"Wrote {summary_path}")
    print(f"Wrote {scatter_png}")
    print("\n" + "\n".join(summary_lines[6:]), flush=True)


if __name__ == "__main__":
    main()
