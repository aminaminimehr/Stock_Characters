#!/usr/bin/env python3
"""Cross-sectional match of bm_ia: bm_bmia_panel.csv vs GKX datashare.csv.

Computes monthly cross-sectional Spearman correlation between panel bm_ia and
datashare bm_ia on matched permno x YYYYMM keys. Evaluates both signal_yyyymm
and target_yyyymm alignments and writes summary + per-month diagnostics.

Usage:
  python scripts/validation/claude-opus-5/compare_bmia_panel_vs_datashare.py
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
DEFAULT_PANEL = ROOT / "outputs" / "panels" / "bm_bmia_panel.csv"
DEFAULT_DATASHARE = ROOT / "Supplementary_assistive_files" / "datashare.csv"
DEFAULT_OUTDIR = Path(__file__).resolve().parent

MIN_PAIRS = 50
LOW_RHO_THRESHOLD = 0.5
CHAR_NAME = "bm_ia"


def resolve_column(columns: list[str], candidates: tuple[str, ...], label: str) -> str:
    """Return the first matching column name (case-insensitive)."""
    lower_map = {c.lower(): c for c in columns}
    for cand in candidates:
        if cand.lower() in lower_map:
            return lower_map[cand.lower()]
    raise KeyError(
        f"Could not find {label} among candidates {candidates}. "
        f"Available columns: {columns}"
    )


def monthly_spearman_values(df: pd.DataFrame, a: str, b: str) -> list[float]:
    vals: list[float] = []
    for _, grp in df.groupby("month", sort=True):
        sub = grp[[a, b]].dropna()
        if len(sub) < MIN_PAIRS:
            continue
        r = sub[a].corr(sub[b], method="spearman")
        if pd.notna(r):
            vals.append(float(r))
    return vals


def monthly_spearman_table(df: pd.DataFrame, a: str, b: str) -> pd.DataFrame:
    rows: list[dict] = []
    for month, grp in df.groupby("month", sort=True):
        sub = grp[[a, b, "permno"]].dropna(subset=[a, b])
        n = len(sub)
        if n < MIN_PAIRS:
            continue
        rho = sub[a].corr(sub[b], method="spearman")
        if pd.notna(rho):
            rows.append(
                {
                    "month": int(month),
                    "spearman": float(rho),
                    "paired_obs": int(n),
                    "unique_permnos": int(sub["permno"].nunique()),
                }
            )
    return pd.DataFrame(rows)


def count_duplicate_keys(df: pd.DataFrame, key_cols: list[str]) -> int:
    """Return number of rows beyond unique (permno, month) keys."""
    if df.empty:
        return 0
    return int(len(df) - df.drop_duplicates(subset=key_cols).shape[0])


def load_datashare(datashare_path: Path) -> pd.DataFrame:
    header = list(pd.read_csv(datashare_path, nrows=0).columns)
    permno_col = resolve_column(header, ("permno",), "permno")
    date_col = resolve_column(header, ("date",), "DATE")
    bm_col = resolve_column(header, ("bm_ia",), "bm_ia")

    frames: list[pd.DataFrame] = []
    for chunk in pd.read_csv(
        datashare_path,
        usecols=[permno_col, date_col, bm_col],
        chunksize=500_000,
    ):
        chunk = chunk.rename(
            columns={permno_col: "permno", date_col: "DATE", bm_col: "bm_ia"}
        )
        chunk["permno"] = pd.to_numeric(chunk["permno"], errors="coerce").astype("Int64")
        chunk["month"] = (pd.to_numeric(chunk["DATE"], errors="coerce") // 100).astype("Int64")
        chunk["bm_ia"] = pd.to_numeric(chunk["bm_ia"], errors="coerce")
        frames.append(chunk[["permno", "month", "bm_ia"]])
    return pd.concat(frames, ignore_index=True)


def load_panel(panel_path: Path) -> pd.DataFrame:
    header = list(pd.read_csv(panel_path, nrows=0).columns)
    permno_col = resolve_column(header, ("permno",), "permno")
    signal_col = resolve_column(header, ("signal_yyyymm",), "signal_yyyymm")
    target_col = resolve_column(header, ("target_yyyymm",), "target_yyyymm")
    bm_col = resolve_column(header, ("bm_ia",), "bm_ia")

    frames: list[pd.DataFrame] = []
    for chunk in pd.read_csv(
        panel_path,
        usecols=[permno_col, signal_col, target_col, bm_col],
        chunksize=500_000,
    ):
        chunk = chunk.rename(
            columns={
                permno_col: "permno",
                signal_col: "signal_yyyymm",
                target_col: "target_yyyymm",
                bm_col: "bm_ia",
            }
        )
        chunk["permno"] = (
            pd.to_numeric(chunk["permno"], errors="coerce").round().astype("Int64")
        )
        chunk["signal_yyyymm"] = pd.to_numeric(
            chunk["signal_yyyymm"], errors="coerce"
        ).astype("Int64")
        chunk["target_yyyymm"] = pd.to_numeric(
            chunk["target_yyyymm"], errors="coerce"
        ).astype("Int64")
        chunk["bm_ia"] = pd.to_numeric(chunk["bm_ia"], errors="coerce")
        frames.append(chunk)
    return pd.concat(frames, ignore_index=True)


def restrict_panel_to_datashare_window(
    panel: pd.DataFrame,
    month_min: int,
    month_max: int,
) -> pd.DataFrame:
    in_window = panel["signal_yyyymm"].between(month_min, month_max) | panel[
        "target_yyyymm"
    ].between(month_min, month_max)
    return panel.loc[in_window].copy()


def compare_alignment(
    panel: pd.DataFrame,
    ds: pd.DataFrame,
    month_col: str,
    month_min: int,
    month_max: int,
) -> tuple[dict, pd.DataFrame]:
    ds_sub = ds[["permno", "month", "bm_ia"]].rename(columns={"bm_ia": "bm_ia_ds"})
    panel_sub = panel[["permno", month_col, "bm_ia"]].rename(
        columns={month_col: "month", "bm_ia": "bm_ia_panel"}
    )
    panel_sub = panel_sub[panel_sub["month"].between(month_min, month_max)]

    ds_keys = set(
        map(
            tuple,
            ds_sub.loc[ds_sub["bm_ia_ds"].notna(), ["permno", "month"]].itertuples(
                index=False, name=None
            ),
        )
    )
    panel_keys = set(
        map(
            tuple,
            panel_sub.loc[panel_sub["bm_ia_panel"].notna(), ["permno", "month"]].itertuples(
                index=False, name=None
            ),
        )
    )

    m = ds_sub.merge(panel_sub, on=["permno", "month"], how="inner")
    m = m.dropna(subset=["bm_ia_ds", "bm_ia_panel"])
    n_pair = len(m)

    if n_pair < 2:
        summary = {
            "characteristic": CHAR_NAME,
            "month_align": month_col,
            "median_monthly_spearman": np.nan,
            "mean_monthly_spearman": np.nan,
            "p10_monthly_spearman": np.nan,
            "p90_monthly_spearman": np.nan,
            "pct_months_rho_lt_05": np.nan,
            "pooled_spearman": np.nan,
            "match_rate_abs1e-4": np.nan,
            "match_rate_round4": np.nan,
            "paired_obs": 0,
            "panel_nonnull": len(panel_keys),
            "datashare_nonnull": len(ds_keys),
            "keys_both": len(ds_keys & panel_keys),
            "datashare_only": len(ds_keys - panel_keys),
            "panel_only": len(panel_keys - ds_keys),
            "permno_panel": int(panel_sub.loc[panel_sub["bm_ia_panel"].notna(), "permno"].nunique()),
            "permno_datashare": int(ds_sub.loc[ds_sub["bm_ia_ds"].notna(), "permno"].nunique()),
            "permno_both": 0,
            "spearman_months": 0,
            "panel_duplicate_keys": count_duplicate_keys(panel_sub, ["permno", "month"]),
            "datashare_duplicate_keys": count_duplicate_keys(ds_sub, ["permno", "month"]),
            "merged_duplicate_keys": count_duplicate_keys(m, ["permno", "month"]),
        }
        return summary, pd.DataFrame()

    pv = m["bm_ia_panel"].astype("float64")
    dv = m["bm_ia_ds"].astype("float64")
    diff = (pv - dv).abs()
    monthly = monthly_spearman_table(m, "bm_ia_panel", "bm_ia_ds")
    vals = monthly["spearman"].tolist() if not monthly.empty else []

    summary = {
        "characteristic": CHAR_NAME,
        "month_align": month_col,
        "median_monthly_spearman": float(np.median(vals)) if vals else np.nan,
        "mean_monthly_spearman": float(np.mean(vals)) if vals else np.nan,
        "p10_monthly_spearman": float(np.percentile(vals, 10)) if vals else np.nan,
        "p90_monthly_spearman": float(np.percentile(vals, 90)) if vals else np.nan,
        "pct_months_rho_lt_05": float(np.mean([v < LOW_RHO_THRESHOLD for v in vals])) if vals else np.nan,
        "pooled_spearman": float(pv.corr(dv, method="spearman")),
        "match_rate_abs1e-4": float((diff <= 1e-4).mean()),
        "match_rate_round4": float((np.round(pv, 4) == np.round(dv, 4)).mean()),
        "paired_obs": int(n_pair),
        "panel_nonnull": len(panel_keys),
        "datashare_nonnull": len(ds_keys),
        "keys_both": len(ds_keys & panel_keys),
        "datashare_only": len(ds_keys - panel_keys),
        "panel_only": len(panel_keys - ds_keys),
        "permno_panel": int(panel_sub.loc[panel_sub["bm_ia_panel"].notna(), "permno"].nunique()),
        "permno_datashare": int(ds_sub.loc[ds_sub["bm_ia_ds"].notna(), "permno"].nunique()),
        "permno_both": int(m["permno"].nunique()),
        "spearman_months": len(vals),
        "panel_duplicate_keys": count_duplicate_keys(panel_sub, ["permno", "month"]),
        "datashare_duplicate_keys": count_duplicate_keys(ds_sub, ["permno", "month"]),
        "merged_duplicate_keys": count_duplicate_keys(m, ["permno", "month"]),
    }
    monthly = monthly.assign(month_align=month_col)
    return summary, monthly


def decade_breakdown(monthly: pd.DataFrame) -> pd.DataFrame:
    if monthly.empty:
        return pd.DataFrame()
    out = monthly.copy()
    out["decade"] = (out["month"] // 100 // 10) * 10
    return (
        out.groupby("decade", as_index=False)
        .agg(
            months=("spearman", "count"),
            median_spearman=("spearman", "median"),
            mean_spearman=("spearman", "mean"),
            mean_paired_obs=("paired_obs", "mean"),
        )
        .sort_values("decade")
    )


def fmt(x: float | int | None, digits: int = 4) -> str:
    if x is None or (isinstance(x, float) and pd.isna(x)):
        return "—"
    if isinstance(x, int):
        return f"{x:,}"
    return f"{x:.{digits}f}"


def write_summary_md(
    outdir: Path,
    panel_path: Path,
    datashare_path: Path,
    month_min: int,
    month_max: int,
    summaries: pd.DataFrame,
    best_monthly: pd.DataFrame,
    best_align: str,
) -> None:
    best = summaries.loc[summaries["month_align"] == best_align].iloc[0]
    decades = decade_breakdown(best_monthly)

    lines = [
        "# bm_ia cross-sectional match: panel vs GKX datashare",
        "",
        f"- Panel: `{panel_path}`",
        f"- Datashare: `{datashare_path}`",
        f"- Comparison window: datashare months **{month_min}–{month_max}**",
        "- Month key: datashare `DATE // 100`; panel `signal_yyyymm` vs `target_yyyymm`",
        f"- Minimum paired obs per month for Spearman: **{MIN_PAIRS}**",
        "",
        "## Required metrics (best alignment)",
        "",
        f"- Characteristic: **{CHAR_NAME}**",
        f"- Best month align: **{best_align}**",
        f"- Median monthly Spearman (cross-sectional): **{fmt(best['median_monthly_spearman'])}**",
        f"- Mean monthly Spearman: **{fmt(best['mean_monthly_spearman'])}**",
        f"- Pooled Spearman: **{fmt(best['pooled_spearman'])}**",
        f"- Sample N (panel / ours): **{fmt(best['panel_nonnull'])}**",
        f"- Sample N (datashare / GKX): **{fmt(best['datashare_nonnull'])}**",
        f"- Paired N (inner join, non-null both): **{fmt(best['paired_obs'])}**",
        f"- Unique permnos (panel): **{fmt(best['permno_panel'])}**",
        f"- Unique permnos (datashare): **{fmt(best['permno_datashare'])}**",
        f"- Unique permnos (both): **{fmt(best['permno_both'])}**",
        f"- Exact match |Δ|≤1e-4: **{100 * best['match_rate_abs1e-4']:.2f}%**",
        f"- Round-4 match: **{100 * best['match_rate_round4']:.2f}%**",
        "",
        "## Both alignments",
        "",
        "| align | median ρ | mean ρ | pooled ρ | paired N | panel N | ds N | permno panel | permno ds | permno both |",
        "|-------|---------:|-------:|---------:|---------:|--------:|-----:|-------------:|----------:|------------:|",
    ]
    for _, r in summaries.iterrows():
        lines.append(
            f"| `{r['month_align']}` | {fmt(r['median_monthly_spearman'])} | "
            f"{fmt(r['mean_monthly_spearman'])} | {fmt(r['pooled_spearman'])} | "
            f"{fmt(r['paired_obs'])} | {fmt(r['panel_nonnull'])} | {fmt(r['datashare_nonnull'])} | "
            f"{fmt(r['permno_panel'])} | {fmt(r['permno_datashare'])} | {fmt(r['permno_both'])} |"
        )

    lines += [
        "",
        "## Key overlap (best alignment)",
        "",
        f"- Keys in both: **{fmt(best['keys_both'])}**",
        f"- Datashare-only keys: **{fmt(best['datashare_only'])}**",
        f"- Panel-only keys: **{fmt(best['panel_only'])}**",
        f"- Duplicate keys — panel: **{fmt(best['panel_duplicate_keys'])}**, "
        f"datashare: **{fmt(best['datashare_duplicate_keys'])}**, "
        f"merged: **{fmt(best['merged_duplicate_keys'])}**",
        "",
        "## Decade breakdown (best alignment)",
        "",
        "| decade | months | median ρ | mean ρ | mean paired obs |",
        "|-------:|-------:|---------:|-------:|----------------:|",
    ]
    for _, r in decades.iterrows():
        lines.append(
            f"| {int(r['decade'])}s | {int(r['months'])} | "
            f"{fmt(r['median_spearman'])} | {fmt(r['mean_spearman'])} | "
            f"{fmt(r['mean_paired_obs'], 1)} |"
        )

    lines += [
        "",
        "## Note",
        "",
        "Prior repo work documents a realistic bm_ia ceiling around 0.83–0.85 median monthly "
        "Spearman due to construction-SIC vintage residuals.",
        "",
    ]
    (outdir / "bmia_match_summary.md").write_text("\n".join(lines), encoding="utf-8")


def print_required_metrics(row: dict) -> None:
    print(f"\n=== {CHAR_NAME} vs datashare ({row['month_align']}) ===")
    print(f"  Median monthly Spearman  : {fmt(row['median_monthly_spearman'])}  ({row['spearman_months']} months)")
    print(f"  Mean monthly Spearman    : {fmt(row['mean_monthly_spearman'])}")
    print(f"  Pooled Spearman          : {fmt(row['pooled_spearman'])}")
    print(f"  Sample N (panel / ours)  : {fmt(row['panel_nonnull'])}")
    print(f"  Sample N (datashare/GKX) : {fmt(row['datashare_nonnull'])}")
    print(f"  Paired N                 : {fmt(row['paired_obs'])}")
    print(f"  Unique permnos (panel)   : {fmt(row['permno_panel'])}")
    print(f"  Unique permnos (datashare): {fmt(row['permno_datashare'])}")
    print(f"  Unique permnos (both)    : {fmt(row['permno_both'])}")
    print(f"  Exact (|Δ|≤1e-4)         : {100 * row['match_rate_abs1e-4']:.2f}%")
    print(f"  Round-4 match            : {100 * row['match_rate_round4']:.2f}%")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--panel", type=Path, default=DEFAULT_PANEL)
    parser.add_argument("--datashare", type=Path, default=DEFAULT_DATASHARE)
    parser.add_argument("--outdir", type=Path, default=DEFAULT_OUTDIR)
    args = parser.parse_args()

    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

    outdir = args.outdir
    outdir.mkdir(parents=True, exist_ok=True)

    print(f"Loading datashare: {args.datashare}", flush=True)
    ds = load_datashare(args.datashare)
    month_min = int(ds["month"].min())
    month_max = int(ds["month"].max())
    print(
        f"  datashare rows={len(ds):,} permnos={ds['permno'].nunique():,} "
        f"months={month_min}–{month_max}",
        flush=True,
    )

    print(f"Loading panel: {args.panel}", flush=True)
    panel = load_panel(args.panel)
    panel_full_rows = len(panel)
    panel = restrict_panel_to_datashare_window(panel, month_min, month_max)
    print(
        f"  panel rows={len(panel):,} (restricted from {panel_full_rows:,}) "
        f"permnos={panel['permno'].nunique():,}",
        flush=True,
    )

    summaries: list[dict] = []
    monthly_frames: list[pd.DataFrame] = []
    for month_col in ("signal_yyyymm", "target_yyyymm"):
        print(f"Comparing alignment: {month_col}", flush=True)
        summary, monthly = compare_alignment(panel, ds, month_col, month_min, month_max)
        summaries.append(summary)
        if not monthly.empty:
            monthly_frames.append(monthly)
        print_required_metrics(summary)

    summary_df = pd.DataFrame(summaries)
    summary_df.to_csv(outdir / "bmia_summary.csv", index=False)

    best_idx = summary_df["median_monthly_spearman"].astype("float64").idxmax()
    best_align = summary_df.loc[best_idx, "month_align"]
    best_monthly = pd.concat(
        [m for m in monthly_frames if m["month_align"].iloc[0] == best_align],
        ignore_index=True,
    )
    monthly_out = pd.concat(monthly_frames, ignore_index=True) if monthly_frames else pd.DataFrame()
    monthly_out.to_csv(outdir / "bmia_monthly_spearman.csv", index=False)

    write_summary_md(
        outdir,
        args.panel,
        args.datashare,
        month_min,
        month_max,
        summary_df,
        best_monthly,
        best_align,
    )

    print(f"\nWrote {outdir / 'bmia_summary.csv'}")
    print(f"Wrote {outdir / 'bmia_monthly_spearman.csv'}")
    print(f"Wrote {outdir / 'bmia_match_summary.md'}")
    print(f"\nBest alignment: {best_align} (median monthly Spearman = {fmt(summary_df.loc[best_idx, 'median_monthly_spearman'])})")


if __name__ == "__main__":
    main()
