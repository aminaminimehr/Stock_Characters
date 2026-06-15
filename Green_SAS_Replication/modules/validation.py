"""Validation against Green SAS benchmark output."""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import pyreadstat

from config import DIAGNOSTICS_DIR, GREEN_BENCHMARK_PATH


def _normalize_green_columns(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    rename = {c: c.lower() for c in out.columns}
    out = out.rename(columns=rename)
    if "date" in out.columns:
        out["date"] = pd.to_datetime(out["date"])
    return out


def load_green_benchmark(columns: list[str] | None = None, sample_start: str | None = None, sample_end: str | None = None) -> pd.DataFrame:
    _, meta = pyreadstat.read_sas7bdat(str(GREEN_BENCHMARK_PATH), metadataonly=True)
    usecols = ["permno", "DATE"] + [c for c in (columns or meta.column_names) if c in meta.column_names and c not in {"permno", "DATE"}]
    frames = []
    for off in range(0, meta.number_rows, 400_000):
        chunk, _ = pyreadstat.read_sas7bdat(
            str(GREEN_BENCHMARK_PATH), usecols=usecols, row_offset=off, row_limit=400_000
        )
        frames.append(chunk)
    g = _normalize_green_columns(pd.concat(frames, ignore_index=True))
    if sample_start:
        g = g[g["date"] >= pd.Timestamp(sample_start)]
    if sample_end:
        g = g[g["date"] <= pd.Timestamp(sample_end)]
    g["permno"] = pd.to_numeric(g["permno"], errors="coerce").astype("Int64")
    return g


def _winsorize_series(s: pd.Series, lower: float = 0.01, upper: float = 0.99) -> pd.Series:
    if s.notna().sum() == 0:
        return s
    return s.clip(s.quantile(lower), s.quantile(upper))


def compare_variable(repo: pd.Series, green: pd.Series) -> dict:
    if not pd.api.types.is_numeric_dtype(repo) and not pd.api.types.is_numeric_dtype(green):
        return {
            "paired_rows": 0,
            "python_non_null": int(repo.notna().sum()),
            "green_non_null": int(green.notna().sum()),
            "coverage_diff": int(repo.notna().sum()) - int(green.notna().sum()),
            "pearson": np.nan,
            "spearman": np.nan,
            "winsor_pearson": np.nan,
            "exact_match_rate": np.nan,
            "near_exact_match_rate": np.nan,
            "median_abs_diff": np.nan,
            "mean_abs_diff": np.nan,
            "non_numeric": True,
        }
    repo = pd.to_numeric(repo, errors="coerce")
    green = pd.to_numeric(green, errors="coerce")
    paired = repo.notna() & green.notna()
    n = int(paired.sum())
    out = {
        "paired_rows": n,
        "python_non_null": int(repo.notna().sum()),
        "green_non_null": int(green.notna().sum()),
        "coverage_diff": int(repo.notna().sum()) - int(green.notna().sum()),
    }
    if n == 0:
        out.update(
            {
                "pearson": np.nan,
                "spearman": np.nan,
                "winsor_pearson": np.nan,
                "exact_match_rate": np.nan,
                "near_exact_match_rate": np.nan,
                "median_abs_diff": np.nan,
                "mean_abs_diff": np.nan,
            }
        )
        return out
    r, g = repo[paired].astype(float), green[paired].astype(float)
    out["pearson"] = float(r.corr(g, method="pearson"))
    out["spearman"] = float(r.corr(g, method="spearman"))
    out["winsor_pearson"] = float(_winsorize_series(r).corr(_winsorize_series(g), method="pearson"))
    out["exact_match_rate"] = float(np.isclose(r, g, rtol=0, atol=1e-6).mean())
    out["near_exact_match_rate"] = float(np.isclose(r, g, rtol=0, atol=1e-2).mean())
    out["median_abs_diff"] = float((r - g).abs().median())
    out["mean_abs_diff"] = float((r - g).abs().mean())
    return out


def run_validation(
    python_df: pd.DataFrame,
    sample_start: str | None = None,
    sample_end: str | None = None,
    exclude_vars: set[str] | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    py = _normalize_green_columns(python_df)
    exclude_vars = {v.lower() for v in (exclude_vars or set())}
    compare_cols = sorted(
        c
        for c in py.columns
        if c not in {"permno", "date", "gvkey", "datadate", "rdq", "sic2", "fyear"}
        and c not in exclude_vars
        and (pd.api.types.is_numeric_dtype(py[c]) or c in green.columns)
    )
    green = load_green_benchmark(columns=[c.upper() for c in compare_cols], sample_start=sample_start, sample_end=sample_end)
    merged = py.merge(green, on=["permno", "date"], how="inner", suffixes=("_py", "_green"))

    rows = []
    for col in compare_cols:
        py_col = f"{col}_py" if f"{col}_py" in merged.columns else col
        g_col = f"{col}_green" if f"{col}_green" in merged.columns else col
        if py_col not in merged.columns or g_col not in merged.columns:
            continue
        stats = compare_variable(merged[py_col], merged[g_col])
        stats["variable"] = col
        rows.append(stats)

    report = pd.DataFrame(rows)
    summary = pd.DataFrame(
        {
            "metric": ["paired_panel_rows", "python_rows", "green_rows", "merged_keys"],
            "value": [len(merged), len(py), len(green), len(merged)],
        }
    )
    return report, summary


def write_validation_reports(
    report: pd.DataFrame,
    summary: pd.DataFrame,
    sample_start: str | None,
    sample_end: str | None,
) -> None:
    DIAGNOSTICS_DIR.mkdir(parents=True, exist_ok=True)
    csv_path = DIAGNOSTICS_DIR / "green_replication_validation.csv"
    md_path = DIAGNOSTICS_DIR / "green_replication_validation.md"
    report.to_csv(csv_path, index=False)

    lines = [
        "# Green SAS Replication Validation",
        "",
        f"Benchmark: `{GREEN_BENCHMARK_PATH}`",
        f"Sample: {sample_start or 'all'} to {sample_end or 'all'}",
        "",
        "## Panel summary",
        "",
        summary.to_markdown(index=False),
        "",
        "## Variable-level comparison",
        "",
        report.sort_values("pearson", ascending=False, na_position="last").to_markdown(index=False),
    ]
    md_path.write_text("\n".join(lines), encoding="utf-8")
