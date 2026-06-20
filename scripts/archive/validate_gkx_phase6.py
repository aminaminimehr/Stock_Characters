#!/usr/bin/env python3
"""Lightweight validation for GKX Phase 6 (Batch A + B)."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from output_paths import (  # noqa: E402
    CHARACTER_INDIVIDUAL_DIR,
    COMPLETE_ALL_PANEL_FILE,
    DIAGNOSTICS_DIR,
    LEGACY_FLAT_OUTPUT_DIR,
    SIGNAL_PANEL_FILE,
)

BATCH_A = ("betasq",)
BATCH_B = (
    "rd", "divi", "divo", "roic", "tb", "convind", "secured", "securedind",
    "pchgm_pchsale", "pchsale_pchinvt", "pchsale_pchrect", "pchsale_pchxsga",
)
BATCH = BATCH_A + BATCH_B
REQUIRED_RAW = {"permno", "permco", "gvkey", "datadate", "sic", "fyear"}
REQUIRED_MONTHLY = {"permno", "signal_yyyymm", "target_yyyymm"}


def validate_raw_csv(path: Path, character: str) -> dict:
    df = pd.read_csv(path, parse_dates=[c for c in ("datadate", "date") if c in pd.read_csv(path, nrows=0).columns])
    cols = set(df.columns)
    if character in BATCH_A:
        missing_cols = sorted(REQUIRED_MONTHLY - cols | {character} - cols)
    else:
        missing_cols = sorted(REQUIRED_RAW - cols | {character} - cols)
    nonnull = int(df[character].notna().sum()) if character in df.columns else 0
    date_col = "datadate" if "datadate" in df.columns else "date"
    return {
        "character": character,
        "rows": len(df),
        "nonnull": nonnull,
        "coverage": nonnull / len(df) if len(df) else 0.0,
        "date_min": str(df[date_col].min()) if len(df) and date_col in df.columns else "",
        "date_max": str(df[date_col].max()) if len(df) and date_col in df.columns else "",
        "missing_columns": missing_cols,
        "unique_sample": sorted(df[character].dropna().unique())[:10] if character in df.columns else [],
    }


def main():
    parser = argparse.ArgumentParser(description="Validate GKX Phase 6 batch outputs.")
    args = parser.parse_args()

    lines = ["# GKX Phase 6 validation (Batch A + B)", ""]
    flat_csvs = list(LEGACY_FLAT_OUTPUT_DIR.glob("*.csv"))
    lines.append(f"- Flat outputs/*.csv count: **{len(flat_csvs)}**")

    meta_signal = {"permno", "permco", "gvkey", "signal_yyyymm", "target_yyyymm", "sic"}
    meta_complete = meta_signal | {"excess_return"}
    if SIGNAL_PANEL_FILE.exists():
        signal_cols = len([c for c in pd.read_csv(SIGNAL_PANEL_FILE, nrows=0).columns if c not in meta_signal])
        lines.append(f"- Signal panel characteristic columns: **{signal_cols}**")
    if COMPLETE_ALL_PANEL_FILE.exists():
        complete_cols = len([c for c in pd.read_csv(COMPLETE_ALL_PANEL_FILE, nrows=0).columns if c not in meta_complete])
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
            f"coverage={row['coverage']:.1%}, range={row['date_min']}..{row['date_max']}, "
            f"unique={row['unique_sample']}, missing={row['missing_columns']}"
        )

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

    lines.extend(
        [
            "",
            "## Notes",
            "",
            "- `ms` audit completed; not implemented (deferred quarterly Mohanram score).",
            "- Phase 1–5 variables were not modified in this batch.",
            "- datashare comparisons omitted from public methodology per project convention.",
        ]
    )

    text = "\n".join(lines) + "\n"
    docs_out = PROJECT_ROOT / "docs" / "gkx" / "gkx_phase6_validation.md"
    docs_out.parent.mkdir(parents=True, exist_ok=True)
    docs_out.write_text(text, encoding="utf-8")
    diag_out = DIAGNOSTICS_DIR / "gkx_phase6_validation.md"
    diag_out.parent.mkdir(parents=True, exist_ok=True)
    diag_out.write_text(text, encoding="utf-8")
    print(text)


if __name__ == "__main__":
    main()
