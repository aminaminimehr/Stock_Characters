#!/usr/bin/env python3
"""Monthly Spearman validation: repo panel vs Green SAS and datashare (2010-2015)."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pyreadstat

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

DEFAULT_PANEL = PROJECT_ROOT / "outputs" / "panels" / "all_character_signal_panel.csv"
DATASHARE_PATH = PROJECT_ROOT / "Supplementary_assistive_files" / "datashare.csv"
GREEN_SAS_PATH = PROJECT_ROOT / "Supplementary_assistive_files" / "Output_From_Greens_SAS_code.sas7bdat"
DEFAULT_REPORT = PROJECT_ROOT / "docs" / "gkx" / "green_timing_validation_2010_2015.md"

MIN_PAIRS = 50

REPO_TO_BENCHMARK = {
    "abr": "ear",
    "rdm": "rd_mve",
    "rvar_mean": "retvol",
    "roa1": "roaq",
    "me_ia": "mve_ia",
}

PANEL_META = {
    "permno",
    "permco",
    "gvkey",
    "signal_yyyymm",
    "target_yyyymm",
    "sic",
    "exchcd",
    "shrcd",
}

GREEN_TIMING_AUDIT_VARS = [
    "age",
    "absacc",
    "invest",
    "egr",
    "chinv",
    "grcapx",
    "pchdepr",
    "cashpr",
    "orgcap",
    "pchcurrat",
    "pchcapx",
    "pchsaleinv",
    "pchquick",
    "currat",
    "saleinv",
    "salerec",
    "quick",
    "tang",
    "sin",
    "realestate",
    "chatoia",
    "cfp_ia",
    "chempia",
    "chpmia",
    "pchcapx_ia",
]


def benchmark_name(repo_col: str) -> str:
    return REPO_TO_BENCHMARK.get(repo_col, repo_col)


def discover_repo_variables(panel_columns: list[str]) -> list[str]:
    return sorted(c for c in panel_columns if c not in PANEL_META)


def build_comparison_pairs(repo_vars: list[str], benchmark_columns: set[str]) -> list[tuple[str, str]]:
    pairs: list[tuple[str, str]] = []
    seen: set[tuple[str, str]] = set()
    for repo_col in repo_vars:
        bench = benchmark_name(repo_col)
        if bench in benchmark_columns:
            key = (repo_col, bench)
            if key not in seen:
                pairs.append(key)
                seen.add(key)
    return pairs


def normalize_month_from_datashare(date_series: pd.Series) -> pd.Series:
    return pd.to_numeric(date_series, errors="coerce") // 100


def normalize_month_from_datetime(date_series: pd.Series) -> pd.Series:
    dt = pd.to_datetime(date_series)
    return (dt.dt.year * 100 + dt.dt.month).astype("Int64")


def monthly_spearman_series(merged: pd.DataFrame, repo_col: str, bench_col: str) -> pd.Series:
    values: list[float] = []
    for _, group in merged.groupby("month", sort=True):
        sub = group[[repo_col, bench_col]].dropna()
        if len(sub) < MIN_PAIRS:
            continue
        rho = sub[repo_col].corr(sub[bench_col], method="spearman")
        if pd.notna(rho):
            values.append(float(rho))
    return pd.Series(values, dtype=float)


def summarize_monthly_rhos(rhos: pd.Series) -> dict:
    if rhos.empty:
        return {"months": 0, "median": np.nan, "mean": np.nan, "p25": np.nan, "p75": np.nan}
    return {
        "months": int(len(rhos)),
        "median": float(rhos.median()),
        "mean": float(rhos.mean()),
        "p25": float(rhos.quantile(0.25)),
        "p75": float(rhos.quantile(0.75)),
    }


def load_repo_panel(
    panel_path: Path, repo_cols: list[str], win_start: int, win_end: int
) -> pd.DataFrame:
    usecols = ["permno", "signal_yyyymm"] + sorted(set(repo_cols))
    frames: list[pd.DataFrame] = []
    for chunk in pd.read_csv(panel_path, usecols=usecols, chunksize=1_000_000):
        chunk = chunk[(chunk["signal_yyyymm"] >= win_start) & (chunk["signal_yyyymm"] <= win_end)].copy()
        if chunk.empty:
            continue
        chunk["permno"] = pd.to_numeric(chunk["permno"], errors="coerce").astype("Int64")
        chunk["month"] = chunk["signal_yyyymm"].astype(int)
        frames.append(chunk)
    if not frames:
        return pd.DataFrame(columns=["permno", "month"] + repo_cols)
    return pd.concat(frames, ignore_index=True)


def load_datashare(bench_cols: list[str], win_start: int, win_end: int) -> pd.DataFrame:
    usecols = ["permno", "DATE"] + sorted(set(bench_cols))
    frames: list[pd.DataFrame] = []
    for chunk in pd.read_csv(DATASHARE_PATH, usecols=usecols, chunksize=500_000):
        chunk = chunk.copy()
        chunk["month"] = normalize_month_from_datashare(chunk["DATE"]).astype("Int64")
        chunk = chunk[(chunk["month"] >= win_start) & (chunk["month"] <= win_end)]
        chunk["permno"] = pd.to_numeric(chunk["permno"], errors="coerce").astype("Int64")
        if chunk.empty:
            continue
        frames.append(chunk.drop(columns=["DATE"]))
    if not frames:
        return pd.DataFrame(columns=["permno", "month"] + bench_cols)
    return pd.concat(frames, ignore_index=True)


def load_green_sas(bench_cols: list[str], win_start: int, win_end: int) -> pd.DataFrame:
    _, meta = pyreadstat.read_sas7bdat(str(GREEN_SAS_PATH), metadataonly=True)
    available = [c for c in bench_cols if c in meta.column_names]
    if not available:
        return pd.DataFrame(columns=["permno", "month"] + bench_cols)

    usecols = ["permno", "DATE"] + available
    frames: list[pd.DataFrame] = []
    for offset in range(0, meta.number_rows, 400_000):
        chunk, _ = pyreadstat.read_sas7bdat(
            str(GREEN_SAS_PATH),
            usecols=usecols,
            row_offset=offset,
            row_limit=400_000,
        )
        chunk = chunk.copy()
        chunk["month"] = normalize_month_from_datetime(chunk["DATE"]).astype("Int64")
        chunk = chunk[(chunk["month"] >= win_start) & (chunk["month"] <= win_end)]
        chunk["permno"] = pd.to_numeric(chunk["permno"], errors="coerce").astype("Int64")
        if chunk.empty:
            continue
        frames.append(chunk.drop(columns=["DATE"]))
    if not frames:
        return pd.DataFrame(columns=["permno", "month"] + bench_cols)
    return pd.concat(frames, ignore_index=True)


def compare_against_benchmark(
    repo: pd.DataFrame,
    benchmark: pd.DataFrame,
    pairs: list[tuple[str, str]],
) -> pd.DataFrame:
    rows: list[dict] = []
    for repo_col, bench_col in pairs:
        if repo_col not in repo.columns or bench_col not in benchmark.columns:
            continue
        merged = (
            repo[["permno", "month", repo_col]]
            .rename(columns={repo_col: "repo_val"})
            .merge(
                benchmark[["permno", "month", bench_col]].rename(columns={bench_col: "bench_val"}),
                on=["permno", "month"],
                how="inner",
            )
        )
        stats = summarize_monthly_rhos(monthly_spearman_series(merged, "repo_val", "bench_val"))
        rows.append({"variable": repo_col, "benchmark_column": bench_col, **stats})
    return pd.DataFrame(rows)


def format_float(x: float) -> str:
    if pd.isna(x):
        return "—"
    return f"{x:.4f}"


def write_report(
    green_stats: pd.DataFrame,
    datashare_stats: pd.DataFrame,
    out_path: Path,
    win_start: int,
    win_end: int,
    panel_path: Path,
) -> None:
    main = green_stats.rename(
        columns={"months": "months_green", "median": "median_green"}
    ).merge(
        datashare_stats.rename(columns={"months": "months_datashare", "median": "median_datashare"})[
            ["variable", "median_datashare", "months_datashare"]
        ],
        on="variable",
        how="outer",
    )
    main = main.sort_values("median_green", ascending=False, na_position="last")

    lines = [
        "# Green timing validation (2010–2015)",
        "",
        f"Window: `{win_start}`–`{win_end}` (monthly `permno × YYYYMM`).",
        "",
        f"Repo panel: `{panel_path.relative_to(PROJECT_ROOT)}`",
        f"Green SAS: `{GREEN_SAS_PATH.relative_to(PROJECT_ROOT)}`",
        f"Datashare: `{DATASHARE_PATH.relative_to(PROJECT_ROOT)}`",
        "",
        "Method: monthly cross-sectional Spearman only; months with fewer than "
        f"{MIN_PAIRS} paired non-missing observations skipped.",
        "",
        "## All overlapping variables",
        "",
        "| Variable | Median Spearman vs Green | Median Spearman vs Datashare | Months Used (Green) | Months Used (Datashare) |",
        "|----------|-------------------------:|-----------------------------:|--------------------:|------------------------:|",
    ]

    for _, row in main.iterrows():
        lines.append(
            f"| {row['variable']} | {format_float(row.get('median_green'))} | "
            f"{format_float(row.get('median_datashare'))} | "
            f"{int(row['months_green']) if pd.notna(row.get('months_green')) else '—'} | "
            f"{int(row['months_datashare']) if pd.notna(row.get('months_datashare')) else '—'} |"
        )

    low = main[main["median_green"] < 0.90].sort_values("median_green")
    lines.extend(["", "## Candidates for further investigation (median Spearman vs Green < 0.90)", ""])
    if low.empty:
        lines.append("None in this window.")
    else:
        lines.append("| Variable | Median Spearman vs Green | Months Used |")
        lines.append("|----------|-------------------------:|------------:|")
        for _, row in low.iterrows():
            lines.append(
                f"| {row['variable']} | {format_float(row['median_green'])} | {int(row['months_green'])} |"
            )

    lines.extend(
        [
            "",
            "## Green-timing migration audit variables",
            "",
            "Median monthly Spearman vs Green SAS for characteristics expected to track "
            "Green rolling timing after panel migration.",
            "",
            "| Variable | Median Spearman vs Green | Mean | P25 | P75 | Months Used |",
            "|----------|-------------------------:|-----:|----:|----:|------------:|",
        ]
    )
    audit = green_stats[green_stats["variable"].isin(GREEN_TIMING_AUDIT_VARS)].copy()
    audit = audit.sort_values("median", ascending=False, na_position="last")
    for _, row in audit.iterrows():
        lines.append(
            f"| {row['variable']} | {format_float(row['median'])} | {format_float(row['mean'])} | "
            f"{format_float(row['p25'])} | {format_float(row['p75'])} | {int(row['months'])} |"
        )

    missing_audit = sorted(set(GREEN_TIMING_AUDIT_VARS) - set(audit["variable"]))
    if missing_audit:
        lines.extend(["", "Audit variables not compared (no overlap or no valid months):", ""])
        lines.append(", ".join(f"`{v}`" for v in missing_audit))

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--panel", type=Path, default=DEFAULT_PANEL)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--win-start", type=int, default=201001)
    parser.add_argument("--win-end", type=int, default=201512)
    args = parser.parse_args()

    for path, label in (
        (args.panel, "panel"),
        (DATASHARE_PATH, "datashare"),
        (GREEN_SAS_PATH, "Green SAS"),
    ):
        if not path.exists():
            raise FileNotFoundError(f"Missing {label}: {path}")

    repo_vars = discover_repo_variables(list(pd.read_csv(args.panel, nrows=0).columns))
    ds_header = set(pd.read_csv(DATASHARE_PATH, nrows=0).columns)
    _, green_meta = pyreadstat.read_sas7bdat(str(GREEN_SAS_PATH), metadataonly=True)
    green_cols = set(green_meta.column_names)

    pairs_green = build_comparison_pairs(repo_vars, green_cols)
    pairs_datashare = build_comparison_pairs(repo_vars, ds_header)
    repo_cols_needed = sorted({p[0] for p in pairs_green} | {p[0] for p in pairs_datashare})

    print(f"Loading repo panel ({len(repo_cols_needed)} variables)...", flush=True)
    repo = load_repo_panel(args.panel, repo_cols_needed, args.win_start, args.win_end)

    print(f"Loading Green SAS...", flush=True)
    green = load_green_sas(sorted({p[1] for p in pairs_green}), args.win_start, args.win_end)

    print(f"Loading datashare...", flush=True)
    datashare = load_datashare(sorted({p[1] for p in pairs_datashare}), args.win_start, args.win_end)

    print("Computing monthly Spearman vs Green SAS...", flush=True)
    green_stats = compare_against_benchmark(repo, green, pairs_green)

    print("Computing monthly Spearman vs datashare...", flush=True)
    datashare_stats = compare_against_benchmark(repo, datashare, pairs_datashare)

    write_report(green_stats, datashare_stats, args.report, args.win_start, args.win_end, args.panel)
    print(f"Wrote {args.report}")
    print(f"Compared {len(green_stats)} variables vs Green, {len(datashare_stats)} vs datashare.")


if __name__ == "__main__":
    main()
