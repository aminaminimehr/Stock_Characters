#!/usr/bin/env python3
"""Lightweight validation for GKX Phase 5 annual characteristics."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from Character_Panels.build_all_character_panel import expand_annual_file  # noqa: E402
from output_paths import (  # noqa: E402
    CHARACTER_INDIVIDUAL_DIR,
    COMPLETE_ALL_PANEL_FILE,
    DIAGNOSTICS_DIR,
    LEGACY_FLAT_OUTPUT_DIR,
    SIGNAL_PANEL_FILE,
)

BATCH = ("realestate", "obklg", "chobklg")
DATASHARE = PROJECT_ROOT / "Supplementary_assistive_files" / "datashare.csv"
REQUIRED_RAW = {"permno", "permco", "gvkey", "datadate", "sic", "fyear"}


def validate_raw_csv(path: Path, character: str) -> dict:
    df = pd.read_csv(path, parse_dates=["datadate"])
    missing_cols = sorted(REQUIRED_RAW - set(df.columns) | {character} - set(df.columns))
    nonnull = int(df[character].notna().sum()) if character in df.columns else 0
    return {
        "character": character,
        "rows": len(df),
        "nonnull": nonnull,
        "coverage": nonnull / len(df) if len(df) else 0.0,
        "datadate_min": str(df["datadate"].min()) if len(df) else "",
        "datadate_max": str(df["datadate"].max()) if len(df) else "",
        "missing_columns": missing_cols,
    }


def compare_datashare(character: str, panel: pd.DataFrame, sample_start: int, sample_end: int) -> dict:
    if not DATASHARE.exists():
        return {"character": character, "status": "datashare missing"}
    header = pd.read_csv(DATASHARE, nrows=0)
    if character not in header.columns:
        return {"character": character, "status": "not in datashare.csv"}
    ds = pd.read_csv(DATASHARE, usecols=["permno", "DATE", character])
    ds["signal_yyyymm"] = pd.to_numeric(ds["DATE"], errors="coerce") // 100
    ds = ds[(ds["signal_yyyymm"] >= sample_start) & (ds["signal_yyyymm"] <= sample_end)]
    merged = panel.merge(ds, on=["permno", "signal_yyyymm"], how="inner", suffixes=("_repo", "_gkx"))
    if merged.empty:
        return {"character": character, "overlap_rows": 0}
    x = merged[f"{character}_repo"]
    y = merged[f"{character}_gkx"]
    mask = x.notna() & y.notna()
    if not mask.any():
        return {"character": character, "overlap_rows": int(len(merged)), "paired_rows": 0}
    return {
        "character": character,
        "overlap_rows": int(len(merged)),
        "paired_rows": int(mask.sum()),
        "pearson": float(x[mask].corr(y[mask])),
        "spearman": float(x[mask].rank().corr(y[mask].rank())),
    }


def main():
    parser = argparse.ArgumentParser(description="Validate GKX Phase 5 batch outputs.")
    parser.add_argument("--sample-start", type=int, default=201801)
    parser.add_argument("--sample-end", type=int, default=202312)
    parser.add_argument("--skip-panel", action="store_true")
    parser.add_argument("--skip-datashare", action="store_true")
    args = parser.parse_args()

    lines = ["# GKX Phase 5 validation", ""]
    flat_csvs = list(LEGACY_FLAT_OUTPUT_DIR.glob("*.csv"))
    lines.append(f"- Flat outputs/*.csv count: **{len(flat_csvs)}**")

    if SIGNAL_PANEL_FILE.exists():
        signal_cols = len(
            [c for c in pd.read_csv(SIGNAL_PANEL_FILE, nrows=0).columns if c not in {
                "permno", "permco", "gvkey", "signal_yyyymm", "target_yyyymm", "sic",
            }]
        )
        lines.append(f"- Signal panel characteristic columns: **{signal_cols}**")
    if COMPLETE_ALL_PANEL_FILE.exists():
        complete_cols = len(
            [c for c in pd.read_csv(COMPLETE_ALL_PANEL_FILE, nrows=0).columns if c not in {
                "permno", "permco", "gvkey", "signal_yyyymm", "target_yyyymm", "sic",
                "excess_return",
            }]
        )
        lines.append(f"- Complete panel characteristic columns: **{complete_cols}**")

    lines.extend(["", "## Raw CSV checks", ""])
    for character in BATCH:
        path = CHARACTER_INDIVIDUAL_DIR / f"{character}.csv"
        if not path.exists():
            lines.append(f"- `{character}`: **FILE_MISSING**")
            continue
        row = validate_raw_csv(path, character)
        lines.append(
            f"- `{character}`: rows={row['rows']:,}, nonnull={row['nonnull']:,}, "
            f"coverage={row['coverage']:.1%}, datadate={row['datadate_min']}..{row['datadate_max']}, "
            f"missing={row['missing_columns']}"
        )

    if not args.skip_panel:
        lines.extend(["", "## Panel merge checks", ""])
        if SIGNAL_PANEL_FILE.exists() and COMPLETE_ALL_PANEL_FILE.exists():
            signal = pd.read_csv(SIGNAL_PANEL_FILE, nrows=0)
            complete = pd.read_csv(COMPLETE_ALL_PANEL_FILE, nrows=0)
            for character in BATCH:
                lines.append(
                    f"- `{character}` in signal panel: {character in signal.columns}; "
                    f"in complete panel: {character in complete.columns}"
                )
        else:
            lines.append("- Panel files missing; rebuild panels after writing batch CSVs.")

    if not args.skip_datashare:
        lines.extend(["", "## datashare.csv comparison (sample window)", ""])
        for character in BATCH:
            path = CHARACTER_INDIVIDUAL_DIR / f"{character}.csv"
            if not path.exists():
                continue
            raw = pd.read_csv(path, parse_dates=["datadate"])
            panel = expand_annual_file(raw, [character])
            panel = panel[
                (panel["signal_yyyymm"] >= args.sample_start)
                & (panel["signal_yyyymm"] <= args.sample_end)
            ]
            lines.append(f"- `{character}`: {compare_datashare(character, panel, args.sample_start, args.sample_end)}")

    lines.extend(
        [
            "",
            "## Notes",
            "",
            "- `obklg` and `chobklg` are not in GKX datashare; expect no datashare comparison.",
            "- `ob` is sparse in Compustat; low row counts for backlog variables are expected.",
            "- Phase 1–4 variables were not modified in this batch.",
        ]
    )

    text = "\n".join(lines) + "\n"
    docs_out = PROJECT_ROOT / "docs" / "gkx" / "gkx_phase5_validation.md"
    docs_out.parent.mkdir(parents=True, exist_ok=True)
    docs_out.write_text(text, encoding="utf-8")
    diag_out = DIAGNOSTICS_DIR / "gkx_phase5_validation.md"
    diag_out.parent.mkdir(parents=True, exist_ok=True)
    diag_out.write_text(text, encoding="utf-8")
    print(text)


if __name__ == "__main__":
    main()
