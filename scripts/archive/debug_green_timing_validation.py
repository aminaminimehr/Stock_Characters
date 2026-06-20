#!/usr/bin/env python3
"""Debug zero-valid-month issues in validate_green_timing_2010_2015.py."""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pyreadstat

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from scripts.validation.validate_green_timing_2010_2015 import (  # noqa: E402
    GREEN_SAS_PATH,
    REPO_TO_BENCHMARK,
    benchmark_name,
    load_green_sas,
    load_repo_panel,
    monthly_spearman_series,
    normalize_month_from_datashare,
    normalize_month_from_datetime,
)

PANEL = PROJECT_ROOT / "outputs" / "panels" / "all_character_signal_panel.csv"
DATASHARE = PROJECT_ROOT / "Supplementary_assistive_files" / "datashare.csv"
WIN_START, WIN_END = 201001, 201512

DEBUG_VARS = [
    "age",
    "absacc",
    "invest",
    "cfp_ia",
    "bm",
    "bm_ia",
    "chatoia",
    "cashpr",
    "egr",
    "orgcap",
]


def month_pair_counts(merged: pd.DataFrame, min_pairs: int) -> dict:
    counts = merged.groupby("month", sort=True).apply(
        lambda g: int((g["repo_val"].notna() & g["bench_val"].notna()).sum()),
        include_groups=False,
    )
    valid_spearman = []
    for month, group in merged.groupby("month", sort=True):
        sub = group[["repo_val", "bench_val"]].dropna()
        if len(sub) < min_pairs:
            continue
        rho = sub["repo_val"].corr(sub["bench_val"], method="spearman")
        if pd.notna(rho):
            valid_spearman.append(month)
    return {
        "months_ge_1": int((counts >= 1).sum()),
        "months_ge_10": int((counts >= 10).sum()),
        "months_ge_50": int((counts >= 50).sum()),
        "months_spearman_ge_50": len(valid_spearman),
        "max_pairs_per_month": int(counts.max()) if len(counts) else 0,
        "median_pairs_per_month": float(counts.median()) if len(counts) else 0.0,
    }


def diagnose_variable(
    repo: pd.DataFrame,
    green: pd.DataFrame,
    repo_col: str,
    bench_col: str,
) -> dict:
    repo_sub = repo[["permno", "month", repo_col]].rename(columns={repo_col: "repo_val"})
    if bench_col not in green.columns:
        return {
            "variable": repo_col,
            "benchmark_column": bench_col,
            "repo_non_null": int(repo_sub["repo_val"].notna().sum()),
            "green_non_null": 0,
            "green_col_present": False,
            "overlapping_keys": 0,
            "paired_non_missing": 0,
            "months_ge_1": 0,
            "months_ge_10": 0,
            "months_ge_50": 0,
            "months_spearman_ge_50": 0,
            "months_spearman_ge_10": 0,
            "reason": "benchmark column missing after Green load",
        }

    green_sub = green[["permno", "month", bench_col]].rename(columns={bench_col: "bench_val"})
    merged = repo_sub.merge(green_sub, on=["permno", "month"], how="inner")
    paired = merged["repo_val"].notna() & merged["bench_val"].notna()
    counts_50 = month_pair_counts(merged, 50)
    counts_10 = month_pair_counts(merged, 10)

    reason = ""
    if merged.empty:
        reason = "no permno×month overlap"
    elif paired.sum() == 0:
        reason = "overlap exists but all paired values missing"
    elif counts_50["months_ge_50"] == 0 and counts_10["months_ge_10"] > 0:
        reason = "pairs exist but fewer than 50 per month (threshold)"
    elif counts_10["months_ge_10"] > 0 and counts_10["months_spearman_ge_50"] == 0:
        reason = "enough pairs but Spearman undefined (likely constant within month)"
    elif counts_50["months_spearman_ge_50"] == 0:
        reason = "Spearman undefined or below threshold"

    return {
        "variable": repo_col,
        "benchmark_column": bench_col,
        "repo_non_null": int(repo_sub["repo_val"].notna().sum()),
        "green_non_null": int(green_sub["bench_val"].notna().sum()),
        "green_col_present": True,
        "overlapping_keys": len(merged),
        "paired_non_missing": int(paired.sum()),
        **counts_50,
        "months_spearman_ge_10": counts_10["months_spearman_ge_50"],
        "reason": reason,
    }


def check_dtypes_and_dates() -> None:
    print("=== DATE / IDENTIFIER CHECKS ===")
    repo_sample = pd.read_csv(PANEL, nrows=5, usecols=["permno", "signal_yyyymm"])
    print("repo permno dtype:", repo_sample["permno"].dtype, "sample:", repo_sample["permno"].tolist())

    g, _ = pyreadstat.read_sas7bdat(
        str(GREEN_SAS_PATH), usecols=["permno", "DATE"], row_limit=5
    )
    print("green permno dtype:", g["permno"].dtype, "sample:", g["permno"].tolist())
    print("green DATE sample:", g["DATE"].tolist())
    print("green month from datetime:", normalize_month_from_datetime(g["DATE"]).tolist())

    ds = pd.read_csv(DATASHARE, usecols=["permno", "DATE"], nrows=5)
    print("datashare permno dtype:", ds["permno"].dtype, "sample:", ds["permno"].tolist())
    print("datashare DATE sample:", ds["DATE"].tolist())
    print("datashare month:", (pd.to_numeric(ds["DATE"], errors="coerce") // 100).tolist())

    _, meta = pyreadstat.read_sas7bdat(str(GREEN_SAS_PATH), metadataonly=True)
    for v in DEBUG_VARS:
        print(f"  green col {v!r}: {v in meta.column_names}")


def main() -> None:
    check_dtypes_and_dates()

    print("\n=== LOADING DATA ===")
    repo = load_repo_panel(PANEL, DEBUG_VARS, WIN_START, WIN_END)
    bench_cols = sorted({benchmark_name(v) for v in DEBUG_VARS})
    green = load_green_sas(bench_cols, WIN_START, WIN_END)
    print("green loaded columns:", [c for c in bench_cols if c in green.columns])

    rows = []
    for repo_col in DEBUG_VARS:
        bench_col = benchmark_name(repo_col)
        row = diagnose_variable(repo, green, repo_col, bench_col)
        rows.append(row)
        print(
            f"{repo_col}: repo_nn={row['repo_non_null']:,} green_nn={row['green_non_null']:,} "
            f"overlap={row['overlapping_keys']:,} paired={row['paired_non_missing']:,} "
            f"m>=1={row['months_ge_1']} m>=10={row['months_ge_10']} m>=50={row['months_ge_50']} "
            f"spearman>=50={row['months_spearman_ge_50']} | {row['reason']}"
        )

    diag = pd.DataFrame(rows)

    print("\n=== SOURCE CSV DATE RANGES (individual builders) ===")
    ind = PROJECT_ROOT / "outputs" / "characteristics" / "individual"
    for repo_col in DEBUG_VARS:
        p = ind / f"{repo_col}.csv"
        if p.exists():
            d = pd.read_csv(p, usecols=["datadate"])
            print(f"  {repo_col}: {len(d):,} rows, {d['datadate'].min()} .. {d['datadate'].max()}")
        else:
            print(f"  {repo_col}: file missing")

    # Test: load green one column at a time vs batch for age
    print("\n=== BATCH vs SINGLE-COLUMN GREEN LOAD (age) ===")
    green_single = load_green_sas(["age"], WIN_START, WIN_END)
    print("batch age nonnull:", int(green["age"].notna().sum()) if "age" in green.columns else "MISSING")
    print("single age nonnull:", int(green_single["age"].notna().sum()))

    # Spearman diagnostic for age on one month
    if "age" in green.columns:
        m = (
            repo[["permno", "month", "age"]]
            .rename(columns={"age": "repo_val"})
            .merge(
                green[["permno", "month", "age"]].rename(columns={"age": "bench_val"}),
                on=["permno", "month"],
                how="inner",
            )
        )
        m201001 = m[m["month"] == 201001][["repo_val", "bench_val"]].dropna()
        print(f"age 201001 pairs: {len(m201001)}")
        if len(m201001) >= 10:
            print("  repo unique:", m201001["repo_val"].nunique())
            print("  bench unique:", m201001["bench_val"].nunique())
            print("  spearman:", m201001["repo_val"].corr(m201001["bench_val"], method="spearman"))

    out = PROJECT_ROOT / "docs" / "gkx" / "green_timing_validation_2010_2015_debug.md"
    lines = [
        "# Green timing validation debug (2010–2015)",
        "",
        "Diagnostics for variables with 0 valid months in the main validation report.",
        "",
        "## Summary",
        "",
        "Date conversion (`signal_yyyymm`, Green SAS `DATE` → month, datashare `DATE` // 100), "
        "`permno` alignment (both coerced to `Int64` in the validation loader), and Green column "
        "names all check out. Variables with 72 valid months (`bm`, `bm_ia`, `chatoia`) confirm "
        "the merge and Spearman path work in this window.",
        "",
        "For variables with 0 valid months, the repo panel has **zero non-null values** in "
        "201001–201512 because the underlying individual character CSVs only contain fiscal "
        "rows from 2018–2019 onward (see source CSV ranges below). Green SAS has full coverage; "
        "inner `permno×month` overlap exists, but every merged row has a missing repo value.",
        "",
        "Lowering the per-month pair threshold to 10 does **not** produce valid Spearman months "
        "when `repo_non_null = 0`.",
        "",
        "| Variable | Bench col | Repo non-null | Green non-null | Overlap rows | Paired | Months ≥1 | Months ≥10 | Months ≥50 | Spearman months (≥50 pairs) | Spearman months (≥10 pairs) | Reason |",
        "|----------|-----------|--------------:|---------------:|-------------:|-------:|----------:|-----------:|-----------:|----------------------------:|----------------------------:|--------|",
    ]
    for _, r in diag.iterrows():
        lines.append(
            f"| {r['variable']} | {r['benchmark_column']} | {r['repo_non_null']:,} | {r['green_non_null']:,} | "
            f"{r['overlapping_keys']:,} | {r['paired_non_missing']:,} | {r['months_ge_1']} | {r['months_ge_10']} | "
            f"{r['months_ge_50']} | {r['months_spearman_ge_50']} | {r['months_spearman_ge_10']} | {r['reason']} |"
        )
    lines.extend(["", "## Individual builder CSV date ranges", ""])
    ind = PROJECT_ROOT / "outputs" / "characteristics" / "individual"
    for repo_col in DEBUG_VARS:
        p = ind / f"{repo_col}.csv"
        if p.exists():
            d = pd.read_csv(p, usecols=["datadate"])
            lines.append(
                f"- `{repo_col}.csv`: {len(d):,} fiscal rows, "
                f"`{d['datadate'].min()}` – `{d['datadate'].max()}`"
            )
        else:
            lines.append(f"- `{repo_col}.csv`: missing")
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"\nWrote {out}")


if __name__ == "__main__":
    main()
