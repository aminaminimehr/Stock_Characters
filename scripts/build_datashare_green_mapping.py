#!/usr/bin/env python3
"""Build datashare-column mapping and Green-primary validation tables."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pyreadstat

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from scripts.validate_green_timing_2010_2015 import (  # noqa: E402
    DATASHARE_PATH,
    GREEN_SAS_PATH,
    MIN_PAIRS,
    load_datashare,
    load_green_sas,
    load_repo_panel,
    monthly_spearman_series,
    summarize_monthly_rhos,
)

DEFAULT_PANEL = PROJECT_ROOT / "outputs" / "panels" / "all_character_signal_panel.csv"
MAPPING_CSV = PROJECT_ROOT / "docs" / "gkx" / "datashare_columns_green_benchmark_mapping.csv"
MAPPING_MD = PROJECT_ROOT / "docs" / "gkx" / "datashare_columns_green_benchmark_mapping.md"
VALIDATION_MD = PROJECT_ROOT / "docs" / "gkx" / "datashare_columns_green_validation.md"

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

# datashare export name -> current repo panel column (if any).
DATASHARE_TO_REPO: dict[str, str | None] = {
    "ear": "abr",
    "roaq": "roaq",
    "rd_mve": "rdm",
    "retvol": "rvar_mean",
    "mve_ia": "me_ia",
    "operprof": "operprof",
    "roeq": "roeq",
}

# Green SAS column for each datashare predictor (when names differ).
DATASHARE_TO_GREEN: dict[str, str] = {
    "ear": "abr",
    "roaq": "roaq",
    "rd_mve": "rd_mve",
    "retvol": "retvol",
    "mve_ia": "mve_ia",
    "operprof": "operprof",
    "roeq": "roeq",
    "mvel1": "mve",  # Green column is mve (log market equity); datashare name is mvel1
}

WIN_START = 201001
WIN_END = 201512


def datashare_predictors() -> list[str]:
    cols = list(pd.read_csv(DATASHARE_PATH, nrows=0).columns)
    return sorted(c for c in cols if c not in ("permno", "DATE"))


def green_columns() -> set[str]:
    _, meta = pyreadstat.read_sas7bdat(str(GREEN_SAS_PATH), metadataonly=True)
    return set(meta.column_names)


def panel_character_columns(panel_path: Path) -> set[str]:
    return set(pd.read_csv(panel_path, nrows=0).columns) - PANEL_META


def repo_column(ds_col: str, panel_cols: set[str]) -> str | None:
    if ds_col in DATASHARE_TO_REPO:
        mapped = DATASHARE_TO_REPO[ds_col]
        if mapped is None:
            return None
        return mapped if mapped in panel_cols else None
    return ds_col if ds_col in panel_cols else None


def green_column(ds_col: str, green_cols: set[str]) -> str | None:
    candidate = DATASHARE_TO_GREEN.get(ds_col, ds_col)
    if candidate in green_cols:
        return candidate
    if ds_col in green_cols:
        return ds_col
    return None


def compare_pair(
    repo: pd.DataFrame,
    green: pd.DataFrame,
    repo_col: str,
    green_col_name: str,
) -> dict:
    merged = (
        repo[["permno", "month", repo_col]]
        .rename(columns={repo_col: "repo_val"})
        .merge(
            green[["permno", "month", green_col_name]].rename(columns={green_col_name: "green_val"}),
            on=["permno", "month"],
            how="inner",
        )
    )
    rhos = monthly_spearman_series(merged, "repo_val", "green_val")
    stats = summarize_monthly_rhos(rhos)

    green_nonnull = green[["permno", "month", green_col_name]].dropna(subset=[green_col_name])
    repo_nonnull = repo[["permno", "month", repo_col]].dropna(subset=[repo_col])
    paired = merged.dropna(subset=["repo_val", "green_val"])
    median_pairs = (
        paired.groupby("month", sort=True).size().median() if not paired.empty else 0.0
    )
    green_obs = len(green_nonnull)
    coverage = len(paired) / green_obs if green_obs else np.nan

    return {
        **stats,
        "median_paired_obs_per_month": float(median_pairs),
        "total_paired_obs": int(len(paired)),
        "green_nonmissing_obs": int(green_obs),
        "coverage_ratio": float(coverage) if pd.notna(coverage) else np.nan,
    }


def assign_status(
    implemented: bool,
    green_available: bool,
    alias_needed: bool,
    validated: bool,
    median: float,
    notes: str,
) -> str:
    if not implemented:
        return "missing from repo"
    if not green_available:
        return "Green column unavailable"
    if alias_needed and not validated:
        return "alias needed"
    if validated and pd.notna(median):
        suffix = " (alias)" if alias_needed else ""
        if median >= 0.95:
            return f"Green-validated >= 0.95{suffix}"
        return f"Green-validated < 0.95{suffix}"
    if notes:
        return notes
    return "formula/timing audit needed"


def build_mapping(panel_path: Path) -> pd.DataFrame:
    ds_cols = datashare_predictors()
    green_cols = green_columns()
    panel_cols = panel_character_columns(panel_path)

    repo_cols_needed = sorted(
        {c for ds in ds_cols if (c := repo_column(ds, panel_cols)) is not None}
    )
    green_cols_needed = sorted(
        {c for ds in ds_cols if (c := green_column(ds, green_cols)) is not None}
    )

    print(f"Loading repo panel ({len(repo_cols_needed)} source columns)...", flush=True)
    repo = load_repo_panel(panel_path, repo_cols_needed, WIN_START, WIN_END)
    print("Loading Green SAS...", flush=True)
    green = load_green_sas(green_cols_needed, WIN_START, WIN_END)

    rows: list[dict] = []
    for ds_col in ds_cols:
        repo_col = repo_column(ds_col, panel_cols)
        green_col_name = green_column(ds_col, green_cols)
        implemented = repo_col is not None
        green_available = green_col_name is not None
        alias_needed = implemented and repo_col != ds_col

        notes = ""
        if ds_col == "mvel1":
            notes = ""
        if ds_col == "operprof":
            notes = "Try repo `op` as alternate source; `operating_profitability` scores 0.57 vs Green"

        stats: dict = {
            "months": 0,
            "median": np.nan,
            "median_paired_obs_per_month": np.nan,
            "total_paired_obs": 0,
            "green_nonmissing_obs": 0,
            "coverage_ratio": np.nan,
        }
        if implemented and green_available and repo_col is not None and green_col_name is not None:
            stats = compare_pair(repo, green, repo_col, green_col_name)

        validated = stats["months"] > 0 and pd.notna(stats["median"])
        status = assign_status(
            implemented,
            green_available,
            alias_needed,
            validated,
            stats["median"],
            notes,
        )

        rows.append(
            {
                "datashare_column": ds_col,
                "repo_column": repo_col or "",
                "green_sas_column": green_col_name or "",
                "implemented": implemented,
                "validated_against_green": validated,
                "median_monthly_spearman_vs_green": stats["median"] if validated else "",
                "valid_months": stats["months"] if validated else 0,
                "median_paired_obs_per_month": stats["median_paired_obs_per_month"]
                if validated
                else "",
                "total_paired_obs": stats["total_paired_obs"] if validated else 0,
                "coverage_vs_green": stats["coverage_ratio"] if validated else "",
                "status": status,
            }
        )

    return pd.DataFrame(rows)


def green_only_extras(green_cols: set[str], ds_cols: list[str]) -> list[str]:
    ds_set = set(ds_cols)
    meta = {
        "permno",
        "gvkey",
        "fyear",
        "sic2",
        "date",
        "datadate",
        "rdq",
        "prccq",
        "eamonth",
        "exchcd",
        "ret",
        "prc",
        "shrout",
        "vol",
        "dlret",
        "dlstcd",
        "ewret",
        "ipo",
        "retcons_pos",
        "retcons_neg",
        "rsq1",
        "pps",
        "i",
        "j",
        "count",
        "spi",
        "spii",
        "cf",
        "chadv",
        "grgw",
        "wogw",
        "chdrc",
        "rdbias",
        "conv",
        "credrat",
        "credrat_dwn",
        "disp",
        "chfeps",
        "fgr5yr",
        "meanrec",
        "chrec",
        "nanalyst",
        "sfe",
        "meanest",
        "ltg",
        "chnanalyst",
        "sgrvol",
        "mve_m",
        "mve_f",
        "mve",
        "roe",
        "ni",
        "cash",
        "chpm",
        "chobklg",
        "obklg",
        "rna",
        "pchcapx",
        "noa",
        "ato",
        "adm",
        "alm",
        "pm",
        "seas1a",
        "mom60m",
        "rvar_capm",
        "rvar_ff3",
        "me",
    }
    return sorted(c for c in green_cols if c not in ds_set and c not in meta)


def fmt(x: object, digits: int = 4) -> str:
    if x == "" or x is None or (isinstance(x, float) and pd.isna(x)):
        return "—"
    if isinstance(x, float):
        return f"{x:.{digits}f}"
    if isinstance(x, bool):
        return "yes" if x else "no"
    return str(x)


def write_mapping_md(df: pd.DataFrame, out_path: Path) -> None:
    green_cols = green_columns()
    ds_cols = datashare_predictors()
    extras = green_only_extras(green_cols, ds_cols)

    lines = [
        "# Datashare columns → Green SAS benchmark mapping",
        "",
        "This table defines the **target production column universe** (`datashare.csv`) "
        "and how each predictor maps to the current repo panel and Green SAS output.",
        "",
        "**Benchmark policy**",
        "",
        "- Primary value/timing benchmark: `Supplementary_assistive_files/Output_From_Greens_SAS_code.sas7bdat`",
        "- Column universe only: `Supplementary_assistive_files/datashare.csv`",
        "- Final export names follow **datashare**; repo/Green aliases are documented below.",
        "- Do not prioritize Green-only variables absent from datashare.",
        "",
        f"Window for validation stats: `{WIN_START}`–`{WIN_END}` (monthly `permno × YYYYMM`).",
        "",
        "## Summary",
        "",
        f"- Datashare predictors: **{len(df)}**",
        f"- Green-validated ≥ 0.95: **{(df['status'].str.startswith('Green-validated >= 0.95')).sum()}**",
        f"- Green-validated < 0.95: **{(df['status'].str.startswith('Green-validated < 0.95')).sum()}**",
        f"- Missing from repo: **{(df['status'] == 'missing from repo').sum()}**",
        f"- Green column unavailable: **{(df['status'] == 'Green column unavailable').sum()}**",
        f"- Alias / audit needed: **{df['status'].isin(['alias needed', 'formula/timing audit needed']).sum()}**",
        "",
        "## Full mapping",
        "",
        "| Datashare | Repo source | Green SAS | Impl. | Validated | Median ρ vs Green | Valid months | Coverage vs Green | Status |",
        "|-----------|-------------|-----------|-------|-----------|------------------:|-------------:|------------------:|--------|",
    ]
    for _, row in df.iterrows():
        lines.append(
            f"| `{row['datashare_column']}` | `{row['repo_column'] or '—'}` | "
            f"`{row['green_sas_column'] or '—'}` | {fmt(row['implemented'])} | "
            f"{fmt(row['validated_against_green'])} | "
            f"{fmt(row['median_monthly_spearman_vs_green'])} | {row['valid_months']} | "
            f"{fmt(row['coverage_vs_green'])} | {row['status']} |"
        )

    lines.extend(
        [
            "",
            "## Known name aliases (export layer)",
            "",
            "| Datashare export | Repo source today | Green SAS column |",
            "|------------------|-------------------|------------------|",
            "| `ear` | `abr` | `ear` |",
            "| `roaq` | `roa1` | `roaq` |",
            "| `rd_mve` | `rdm` | `rd_mve` |",
            "| `retvol` | `rvar_mean` | `retvol` |",
            "| `mve_ia` | `me_ia` | `mve_ia` |",
            "| `operprof` | `operating_profitability` (candidate) | `operprof` |",
            "| `roeq` | *not built* (repo has annual `roe` only) | `roeq` |",
            "| `mvel1` | `mvel1` | `mve` (Green name differs) |",
            "",
            "## Repo variables outside datashare universe",
            "",
            "These exist in the repo panel and/or Green SAS but are **not** datashare predictors "
            "(no production export required unless added to datashare later):",
            "",
            "`sue` (Green uses IBES when available; repo proxy exists), `roe` (annual; datashare uses quarterly `roeq`), "
            "`ni`, `chpm`, `chobklg`, `obklg`, `rna`, `pchcapx`, `book_to_market`, `cash_flow_to_price`, "
            "`mom60m`, `rvar_capm`, `rvar_ff3`, `me`, and other repo-only diagnostics.",
            "",
            "## Green-only variables excluded from production scope",
            "",
            "Green SAS contains predictors and intermediates **not** in datashare. "
            "These are out of scope unless needed as build inputs:",
            "",
        ]
    )
    lines.append(", ".join(f"`{c}`" for c in extras[:60]))
    if len(extras) > 60:
        lines.append(f"\n… and {len(extras) - 60} more (see CSV `green_only_extras` note).")

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_validation_md(df: pd.DataFrame, out_path: Path) -> None:
    validated = df[df["validated_against_green"]].copy()
    validated["median_monthly_spearman_vs_green"] = pd.to_numeric(
        validated["median_monthly_spearman_vs_green"], errors="coerce"
    )
    low = validated[validated["median_monthly_spearman_vs_green"] < 0.95].sort_values(
        "median_monthly_spearman_vs_green"
    )
    missing = df[df["status"] == "missing from repo"]
    audit = df[df["status"].isin(["alias needed", "formula/timing audit needed"])]

    lines = [
        "# Datashare columns — Green SAS validation (primary)",
        "",
        f"Validation window: `{WIN_START}`–`{WIN_END}`. "
        "Monthly cross-sectional Spearman on `permno × YYYYMM`; "
        f"months with < {MIN_PAIRS} paired observations skipped.",
        "",
        "Repo panel: `outputs/panels/all_character_signal_panel.csv`",
        "Green SAS: `Supplementary_assistive_files/Output_From_Greens_SAS_code.sas7bdat`",
        "",
        "**Datashare values are not the primary benchmark** — they are omitted here except "
        "where noted for diagnostics in separate reports.",
        "",
        "## Green-validated predictors",
        "",
        "| Datashare | Green SAS | Repo source | Median ρ | Valid months | Median pairs/mo | Total pairs | Coverage | Status |",
        "|-----------|-----------|-------------|---------:|-------------:|----------------:|------------:|---------:|--------|",
    ]
    for _, row in validated.sort_values("median_monthly_spearman_vs_green", ascending=False).iterrows():
        lines.append(
            f"| `{row['datashare_column']}` | `{row['green_sas_column']}` | "
            f"`{row['repo_column']}` | {fmt(row['median_monthly_spearman_vs_green'])} | "
            f"{row['valid_months']} | {fmt(row['median_paired_obs_per_month'], 0)} | "
            f"{row['total_paired_obs']} | {fmt(row['coverage_vs_green'])} | {row['status']} |"
        )

    lines.extend(["", "## Below 0.95 vs Green (fix priority)", ""])
    if low.empty:
        lines.append("None.")
    else:
        lines.append(
            "| Rank | Datashare | Repo | Green | Median ρ | Valid months | Notes |"
        )
        lines.append("|-----:|-----------|------|-------|---------:|-------------:|-------|")
        notes_map = {
            "ear": "Event-window `abr` rewrite still mismatches Green `ear`",
            "beta": "Green weekly 36m EW-market beta; rebuild pending",
            "betasq": "Square of `beta`; fix follows beta",
            "sue": "Green uses IBES when available; repo uses `che/mveq` proxy",
            "pchcapx_ia": "Industry-adjusted cap-ex growth; audit formula/timing",
            "nincr": "Close (0.92); quarterly earnings-streak logic",
            "roeq": "Quarterly ROE not implemented; do not use annual `roe` as proxy",
            "operprof": "Repo `operating_profitability` mismatches; try `op` or rebuild from Green",
        }
        for i, (_, row) in enumerate(low.iterrows(), 1):
            note = notes_map.get(row["datashare_column"], "")
            lines.append(
                f"| {i} | `{row['datashare_column']}` | `{row['repo_column']}` | "
                f"`{row['green_sas_column']}` | {fmt(row['median_monthly_spearman_vs_green'])} | "
                f"{row['valid_months']} | {note} |"
            )

    lines.extend(["", "## Not validated against Green", ""])
    not_val = df[~df["validated_against_green"]]
    lines.append("| Datashare | Repo | Green | Status | Reason |")
    lines.append("|-----------|------|-------|--------|--------|")
    reasons = {
        "missing from repo": "No repo implementation / export column",
        "Green column unavailable": "Green SAS has no direct column (e.g. `mvel1`)",
        "alias needed": "Name alias or export layer not wired",
        "formula/timing audit needed": "Implemented under different name or wrong economic definition",
    }
    for _, row in not_val.iterrows():
        lines.append(
            f"| `{row['datashare_column']}` | `{row['repo_column'] or '—'}` | "
            f"`{row['green_sas_column'] or '—'}` | {row['status']} | "
            f"{reasons.get(row['status'], '')} |"
        )

    lines.extend(
        [
            "",
            "## Recommended next fixes (ranked)",
            "",
            "1. **`ear` (`abr`)** — largest gap (ρ ≈ 0.03). Audit event-window construction vs Green SAS `ear`.",
            "2. **`beta` / `betasq`** — rebuild with Green weekly 36-month EW-market method (`beta_builder.py`).",
            "3. **`pchcapx_ia`** — industry-adjusted cap-ex; audit formula and annual timing.",
            "4. **`nincr`** — near threshold (ρ ≈ 0.92); audit quarterly streak definition.",
            "5. **`sue`** — treat separately: IBES policy decision; secondary diagnostic only.",
            "6. **`operprof`** — repo `operating_profitability` scores ρ ≈ 0.57 vs Green; audit `op` and Green formula.",
            "7. **Missing datashare predictors** — implement in Green order: `aeavol`, `idiovol`, "
            "`pricedelay`, `stdacc`/`stdcf`/`roavol`, `chmom`/`indmom`, `sic2`, `ms`.",
            "8. **`roeq`** — build quarterly `roeq` export; do not alias annual `roe`.",
            "9. **Export alias layer** — rename `roa1→roaq`, `rdm→rd_mve`, `rvar_mean→retvol`, `me_ia→mve_ia`.",
            "",
            "## `sue` (separate policy)",
            "",
            "Green SAS uses IBES actuals when available. The repo currently implements a Compustat "
            "`che/mveq` proxy. Validate against Green only after an explicit IBES policy decision.",
        ]
    )

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    global WIN_START, WIN_END
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--panel", type=Path, default=DEFAULT_PANEL)
    parser.add_argument("--mapping-csv", type=Path, default=MAPPING_CSV)
    parser.add_argument("--mapping-md", type=Path, default=MAPPING_MD)
    parser.add_argument("--validation-md", type=Path, default=VALIDATION_MD)
    parser.add_argument("--win-start", type=int, default=WIN_START)
    parser.add_argument("--win-end", type=int, default=WIN_END)
    args = parser.parse_args()

    WIN_START = args.win_start
    WIN_END = args.win_end

    if not args.panel.exists():
        raise FileNotFoundError(args.panel)

    df = build_mapping(args.panel)
    args.mapping_csv.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(args.mapping_csv, index=False)
    write_mapping_md(df, args.mapping_md)
    write_validation_md(df, args.validation_md)

    print(f"Wrote {args.mapping_csv}")
    print(f"Wrote {args.mapping_md}")
    print(f"Wrote {args.validation_md}")
    print(df["status"].value_counts().to_string())


if __name__ == "__main__":
    main()
