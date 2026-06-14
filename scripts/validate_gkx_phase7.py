#!/usr/bin/env python3
"""Lightweight validation for GKX Phase 7 (Batch C industry-adjusted)."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from output_paths import (  # noqa: E402
    CHARACTER_INDIVIDUAL_DIR,
    COMPLETE_ALL_PANEL_FILE,
    DIAGNOSTICS_DIR,
    LEGACY_FLAT_OUTPUT_DIR,
    SIGNAL_PANEL_FILE,
)

BATCH = ("cfp_ia", "chatoia", "chempia", "chpmia", "pchcapx_ia")
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


def main():
    parser = argparse.ArgumentParser(description="Validate GKX Phase 7 batch outputs.")
    args = parser.parse_args()

    lines = [
        "# GKX Phase 7 validation (Batch C — industry-adjusted)",
        "",
        "Industry grouping: **Compustat SIC2 × fiscal year**, subtract industry **mean** (Green SAS).",
        "",
    ]
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
            f"coverage={row['coverage']:.1%}, datadate={row['datadate_min']}..{row['datadate_max']}, "
            f"missing={row['missing_columns']}"
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
        lines.append("- Panel files missing.")

    lines.extend(
        [
            "",
            "## Notes",
            "",
            "- Industry adjustment follows Green SAS (`sic2` × `fyear`, mean demean), not Dacheng FF49.",
            "- Phase 1–6 variables not modified except additive `chpmia` column.",
        ]
    )

    text = "\n".join(lines) + "\n"
    docs_out = PROJECT_ROOT / "docs" / "gkx" / "gkx_phase7_validation.md"
    docs_out.write_text(text, encoding="utf-8")
    diag_out = DIAGNOSTICS_DIR / "gkx_phase7_validation.md"
    diag_out.write_text(text, encoding="utf-8")
    print(text)


if __name__ == "__main__":
    main()
