#!/usr/bin/env python3
"""Lightweight validation for GKX Phase 1 annual characteristics."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from Character_Panels.build_all_character_panel import expand_annual_file  # noqa: E402
from output_paths import (  # noqa: E402
    CHARACTER_INDIVIDUAL_DIR,
    COMPLETE_ALL_PANEL_FILE,
    DIAGNOSTICS_DIR,
    LEGACY_FLAT_OUTPUT_DIR,
    OUTPUT_ROOT,
    PANELS_DIR,
    SIGNAL_PANEL_FILE,
)

BATCH = ("invest", "egr", "chinv", "absacc", "age")
DATASHARE = PROJECT_ROOT / "Supplementary_assistive_files" / "datashare.csv"
REQUIRED_RAW = {"permno", "permco", "gvkey", "datadate", "sic", "fyear"}


def validate_raw_csv(path: Path, character: str) -> dict:
    df = pd.read_csv(path, parse_dates=["datadate"])
    missing_cols = sorted(REQUIRED_RAW - set(df.columns) | {character} - set(df.columns))
    nonnull = int(df[character].notna().sum()) if character in df.columns else 0
    return {
        "character": character,
        "path": str(path),
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
        return {"character": character, "overlap_rows": len(merged), "paired_rows": 0}
    corr = float(x[mask].corr(y[mask]))
    rank_corr = float(x[mask].rank().corr(y[mask].rank()))
    return {
        "character": character,
        "overlap_rows": int(len(merged)),
        "paired_rows": int(mask.sum()),
        "pearson": corr,
        "spearman": rank_corr,
    }


def main():
    parser = argparse.ArgumentParser(description="Validate GKX Phase 1 batch outputs.")
    parser.add_argument("--sample-start", type=int, default=201801)
    parser.add_argument("--sample-end", type=int, default=202312)
    parser.add_argument("--skip-panel", action="store_true")
    parser.add_argument("--skip-datashare", action="store_true")
    args = parser.parse_args()

    lines = ["# GKX Phase 1 validation", ""]
    flat_csvs = list(LEGACY_FLAT_OUTPUT_DIR.glob("*.csv"))
    lines.append(f"- Flat outputs/*.csv count: **{len(flat_csvs)}**")
    if flat_csvs:
        lines.append(f"- Unexpected flat files: {', '.join(p.name for p in flat_csvs)}")

    raw_results = []
    for character in BATCH:
        path = CHARACTER_INDIVIDUAL_DIR / f"{character}.csv"
        if not path.exists():
            raw_results.append({"character": character, "missing_columns": ["FILE_MISSING"]})
            continue
        raw_results.append(validate_raw_csv(path, character))

    lines.extend(["", "## Raw CSV checks", ""])
    for row in raw_results:
        lines.append(
            f"- `{row['character']}`: rows={row.get('rows', 0):,}, "
            f"nonnull={row.get('nonnull', 0):,}, coverage={row.get('coverage', 0):.1%}, "
            f"datadate={row.get('datadate_min', '?')}..{row.get('datadate_max', '?')}, "
            f"missing={row.get('missing_columns', [])}"
        )

    if not args.skip_panel:
        lines.extend(["", "## Panel merge checks", ""])
        if SIGNAL_PANEL_FILE.exists() and COMPLETE_ALL_PANEL_FILE.exists():
            signal = pd.read_csv(SIGNAL_PANEL_FILE, nrows=0)
            complete = pd.read_csv(COMPLETE_ALL_PANEL_FILE, nrows=0)
            for character in BATCH:
                in_signal = character in signal.columns
                in_complete = character in complete.columns
                lines.append(
                    f"- `{character}` in signal panel: {in_signal}; in complete panel: {in_complete}"
                )
        else:
            lines.append("- Panel files missing; run `run_full_pipeline.py --skip-build` after building batch.")

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
            stats = compare_datashare(character, panel, args.sample_start, args.sample_end)
            lines.append(f"- `{character}`: {stats}")

    lines.extend(
        [
            "",
            "## Notes",
            "",
            "- datashare `DATE` is `YYYYMMDD`; comparisons use `signal_yyyymm = DATE // 100`.",
            "- `age` counts Compustat rows per gvkey from the loaded history; truncated sample windows reset counts and weaken datashare agreement.",
            "- High Spearman with low Pearson for `invest`/`egr` often reflects rank-preserving differences (e.g., `ppegt` vs `ppent`, outliers).",
        ]
    )
    docs_out = PROJECT_ROOT / "docs" / "gkx" / "gkx_phase1_validation.md"
    text = "\n".join(lines) + "\n"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(text, encoding="utf-8")
    docs_out.parent.mkdir(parents=True, exist_ok=True)
    docs_out.write_text(text, encoding="utf-8")
    print(text)


if __name__ == "__main__":
    main()
