#!/usr/bin/env python3
"""Disagreement audit: repo vs datashare for invest, egr, age."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from Character_Panels.build_all_character_panel import expand_annual_file  # noqa: E402
from output_paths import CHARACTER_INDIVIDUAL_DIR, DIAGNOSTICS_DIR  # noqa: E402

BATCH = ("invest", "egr", "age")
DATASHARE = PROJECT_ROOT / "Supplementary_assistive_files" / "datashare.csv"
DOCS_OUT = PROJECT_ROOT / "docs" / "gkx" / "gkx_phase1_disagreement_audit.md"


def load_datashare(character: str, sample_start: int, sample_end: int) -> pd.DataFrame:
    chunks = []
    for chunk in pd.read_csv(DATASHARE, usecols=["permno", "DATE", character], chunksize=500_000):
        chunk["signal_yyyymm"] = pd.to_numeric(chunk["DATE"], errors="coerce") // 100
        chunk = chunk[(chunk["signal_yyyymm"] >= sample_start) & (chunk["signal_yyyymm"] <= sample_end)]
        if len(chunk):
            chunks.append(chunk)
    if not chunks:
        return pd.DataFrame(columns=["permno", "signal_yyyymm", character])
    ds = pd.concat(chunks, ignore_index=True)
    return ds.rename(columns={character: f"{character}_gkx"})


def load_repo_panel(character: str, sample_start: int, sample_end: int) -> pd.DataFrame:
    path = CHARACTER_INDIVIDUAL_DIR / f"{character}.csv"
    raw = pd.read_csv(path, parse_dates=["datadate"])
    panel = expand_annual_file(raw, [character])
    panel = panel[
        (panel["signal_yyyymm"] >= sample_start) & (panel["signal_yyyymm"] <= sample_end)
    ].copy()
    return panel.rename(columns={character: f"{character}_repo"})


def merge_pair(repo: pd.DataFrame, gkx: pd.DataFrame, character: str) -> pd.DataFrame:
    merged = repo.merge(gkx, on=["permno", "signal_yyyymm"], how="inner")
    x = merged[f"{character}_repo"]
    y = merged[f"{character}_gkx"]
    merged["paired"] = x.notna() & y.notna()
    return merged


def winsorize(series: pd.Series, lower: float = 0.01, upper: float = 0.99) -> pd.Series:
    lo = series.quantile(lower)
    hi = series.quantile(upper)
    return series.clip(lo, hi)


def percentile_rank(series: pd.Series) -> pd.Series:
    return series.rank(pct=True, method="average")


def pearson(x: pd.Series, y: pd.Series) -> float:
    mask = x.notna() & y.notna()
    if mask.sum() < 3:
        return float("nan")
    return float(x[mask].corr(y[mask]))


def spearman(x: pd.Series, y: pd.Series) -> float:
    mask = x.notna() & y.notna()
    if mask.sum() < 3:
        return float("nan")
    return float(x[mask].rank().corr(y[mask].rank()))


def monthly_rank_correlations(merged: pd.DataFrame, character: str) -> pd.Series:
    rows = []
    for month, group in merged.groupby("signal_yyyymm"):
        x = group[f"{character}_repo"]
        y = group[f"{character}_gkx"]
        mask = x.notna() & y.notna()
        if mask.sum() < 20:
            continue
        rows.append({"signal_yyyymm": month, "spearman": spearman(x, y), "n": int(mask.sum())})
    return pd.DataFrame(rows)


def add_months_yyyymm(yyyymm: int, months: int) -> int:
    year = yyyymm // 100
    month = yyyymm % 100
    month += months
    while month > 12:
        month -= 12
        year += 1
    while month < 1:
        month += 12
        year -= 1
    return year * 100 + month


def timing_shift_correlations(
    repo: pd.DataFrame, gkx: pd.DataFrame, character: str, shifts: range
) -> list[dict]:
    out = []
    for shift in shifts:
        shifted = repo.copy()
        shifted["signal_yyyymm"] = shifted["signal_yyyymm"].map(
            lambda v: add_months_yyyymm(int(v), shift)
        )
        merged = merge_pair(shifted, gkx, character)
        paired = merged[merged["paired"]]
        out.append(
            {
                "shift_months": shift,
                "paired_rows": int(len(paired)),
                "pearson": pearson(paired[f"{character}_repo"], paired[f"{character}_gkx"]),
                "spearman": spearman(paired[f"{character}_repo"], paired[f"{character}_gkx"]),
            }
        )
    return out


def outlier_diagnostics(merged: pd.DataFrame, character: str) -> dict:
    paired = merged[merged["paired"]].copy()
    x = paired[f"{character}_repo"]
    y = paired[f"{character}_gkx"]
    diff = (x - y).abs()
    q99 = diff.quantile(0.99)
    trimmed = paired[diff <= q99]
    top = paired[diff > q99]
    return {
        "pearson_all": pearson(x, y),
        "pearson_trim_99_diff": pearson(
            trimmed[f"{character}_repo"], trimmed[f"{character}_gkx"]
        ),
        "pearson_top1pct_diff_only": pearson(top[f"{character}_repo"], top[f"{character}_gkx"])
        if len(top) >= 3
        else float("nan"),
        "median_abs_diff": float(diff.median()),
        "p99_abs_diff": float(q99),
        "max_abs_diff": float(diff.max()),
        "share_large_diff_gt_1": float((diff > 1.0).mean()),
    }


def correlation_suite(merged: pd.DataFrame, character: str) -> dict:
    paired = merged[merged["paired"]].copy()
    x = paired[f"{character}_repo"]
    y = paired[f"{character}_gkx"]
    x_w = winsorize(x)
    y_w = winsorize(y)
    x_pct = percentile_rank(x)
    y_pct = percentile_rank(y)
    monthly = monthly_rank_correlations(merged, character)
    return {
        "paired_rows": int(len(paired)),
        "pearson_raw": pearson(x, y),
        "spearman_raw": spearman(x, y),
        "pearson_winsor_1_99": pearson(x_w, y_w),
        "spearman_winsor_1_99": spearman(x_w, y_w),
        "pearson_pct_rank": pearson(x_pct, y_pct),
        "spearman_pct_rank": spearman(x_pct, y_pct),
        "mean_monthly_spearman": float(monthly["spearman"].mean()) if len(monthly) else float("nan"),
        "median_monthly_spearman": float(monthly["spearman"].median()) if len(monthly) else float("nan"),
        "monthly_spearman_min": float(monthly["spearman"].min()) if len(monthly) else float("nan"),
        "monthly_spearman_max": float(monthly["spearman"].max()) if len(monthly) else float("nan"),
        "months_with_20plus_pairs": int(len(monthly)),
        "outliers": outlier_diagnostics(merged, character),
    }


def age_level_diagnostic(merged: pd.DataFrame) -> dict:
    paired = merged[merged["paired"]].copy()
    x = paired["age_repo"]
    y = paired["age_gkx"]
    return {
        "repo_mean": float(x.mean()),
        "gkx_mean": float(y.mean()),
        "repo_median": float(x.median()),
        "gkx_median": float(y.median()),
        "repo_max": float(x.max()),
        "gkx_max": float(y.max()),
        "exact_match_rate": float((x == y).mean()),
        "within_1_rate": float((x.sub(y).abs() <= 1).mean()),
        "within_5_rate": float((x.sub(y).abs() <= 5).mean()),
        "mean_abs_gap": float(x.sub(y).abs().mean()),
    }


def main():
    parser = argparse.ArgumentParser(description="Audit disagreement vs datashare/GKX.")
    parser.add_argument("--sample-start", type=int, default=201801)
    parser.add_argument("--sample-end", type=int, default=202312)
    args = parser.parse_args()

    results = {}
    for character in ("invest", "egr"):
        repo = load_repo_panel(character, args.sample_start, args.sample_end)
        gkx = load_datashare(character, args.sample_start, args.sample_end)
        merged = merge_pair(repo, gkx, character)
        results[character] = {
            "correlations": correlation_suite(merged, character),
            "timing_shifts": timing_shift_correlations(
                repo, gkx, character, range(-6, 7)
            ),
        }

    age_repo = load_repo_panel("age", args.sample_start, args.sample_end)
    age_gkx = load_datashare("age", args.sample_start, args.sample_end)
    age_merged = merge_pair(age_repo, age_gkx, "age")
    results["age"] = {
        "correlations": correlation_suite(age_merged, "age"),
        "levels": age_level_diagnostic(age_merged),
        "timing_shifts": timing_shift_correlations(
            age_repo, age_gkx, "age", range(-6, 7)
        ),
    }

    lines = [
        "# GKX Phase 1 disagreement audit (`invest`, `egr`, `age`)",
        "",
        f"Sample window: `{args.sample_start}`–`{args.sample_end}` (`signal_yyyymm`).",
        "Comparison: repo annual builder + `expand_annual_file` vs local `datashare.csv` (GKX).",
        "No formulas were changed for this audit.",
        "",
    ]

    for character in ("invest", "egr", "age"):
        stats = results[character]["correlations"]
        lines.extend(
            [
                f"## {character}",
                "",
                f"- Paired rows: **{stats['paired_rows']:,}**",
                f"- Pearson (raw): **{stats['pearson_raw']:.4f}**",
                f"- Spearman (raw): **{stats['spearman_raw']:.4f}**",
                f"- Pearson (winsor 1/99): **{stats['pearson_winsor_1_99']:.4f}**",
                f"- Pearson (global percentile ranks): **{stats['pearson_pct_rank']:.4f}**",
                f"- Mean monthly cross-sectional Spearman: **{stats['mean_monthly_spearman']:.4f}**",
                f"- Median monthly cross-sectional Spearman: **{stats['median_monthly_spearman']:.4f}**",
                f"- Monthly Spearman range: {stats['monthly_spearman_min']:.4f} .. {stats['monthly_spearman_max']:.4f}",
                "",
                "### Outlier diagnostics",
                "",
                f"- Pearson after trimming top 1% absolute differences: **{stats['outliers']['pearson_trim_99_diff']:.4f}**",
                f"- Pearson on top 1% absolute differences only: **{stats['outliers']['pearson_top1pct_diff_only']:.4f}**",
                f"- Median |diff|: **{stats['outliers']['median_abs_diff']:.4f}**",
                f"- Share with |diff| > 1: **{stats['outliers']['share_large_diff_gt_1']:.1%}**",
                "",
                "### Timing-shift sensitivity (repo signal month shifted)",
                "",
                "| shift | paired | pearson | spearman |",
                "| ---: | ---: | ---: | ---: |",
            ]
        )
        for row in results[character]["timing_shifts"]:
            lines.append(
                f"| {row['shift_months']:+d} | {row['paired_rows']:,} | "
                f"{row['pearson']:.4f} | {row['spearman']:.4f} |"
            )
        lines.append("")
        if character == "age":
            lv = results["age"]["levels"]
            lines.extend(
                [
                    "### Age level comparison",
                    "",
                    f"- Repo mean/median/max: {lv['repo_mean']:.2f} / {lv['repo_median']:.0f} / {lv['repo_max']:.0f}",
                    f"- GKX mean/median/max: {lv['gkx_mean']:.2f} / {lv['gkx_median']:.0f} / {lv['gkx_max']:.0f}",
                    f"- Exact match rate: **{lv['exact_match_rate']:.1%}**",
                    f"- Within ±1 year: **{lv['within_1_rate']:.1%}**",
                    f"- Within ±5 years: **{lv['within_5_rate']:.1%}**",
                    f"- Mean absolute gap: **{lv['mean_abs_gap']:.2f} years**",
                    "",
                ]
            )

    text = "\n".join(lines) + "\n"
    DOCS_OUT.parent.mkdir(parents=True, exist_ok=True)
    DOCS_OUT.write_text(text, encoding="utf-8")
    diag_out = DIAGNOSTICS_DIR / "gkx_phase1_disagreement_audit.md"
    diag_out.parent.mkdir(parents=True, exist_ok=True)
    diag_out.write_text(text, encoding="utf-8")
    print(text)


if __name__ == "__main__":
    main()
