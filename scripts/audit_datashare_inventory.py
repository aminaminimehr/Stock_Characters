#!/usr/bin/env python3
"""Inventory datashare.csv columns and lightweight metadata (no full dataset load)."""
from __future__ import annotations

import re
import sys
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from output_paths import DIAGNOSTICS_DIR  # noqa: E402

DATASHARE = PROJECT_ROOT / "Supplementary_assistive_files" / "datashare.csv"
GKX_TXT = PROJECT_ROOT / "Supplementary_assistive_files" / "GKX_characters.txt"
DOCS_GKX = PROJECT_ROOT / "docs" / "gkx"
META = {"permno", "date", "sic2"}


def norm(name: str) -> str:
    return re.sub(r"[^a-z0-9_]", "", str(name).strip().lower())


def load_gkx_descriptions() -> dict[str, str]:
    descriptions = {}
    for line in GKX_TXT.read_text(encoding="utf-8").splitlines():
        match = re.match(r"\s*\d+\s+(\S+)\s+(.+?)\s+[A-Z]", line)
        if not match:
            continue
        key = norm(match.group(1).replace(" ", "_"))
        descriptions[key] = match.group(2).strip()
    return descriptions


def main():
    header = pd.read_csv(DATASHARE, nrows=0)
    columns = list(header.columns)
    predictors = [c for c in columns if norm(c) not in META]
    descriptions = load_gkx_descriptions()

    # Date range from DATE column only (chunked).
    date_min = None
    date_max = None
    row_count = 0
    for chunk in pd.read_csv(DATASHARE, usecols=["DATE"], chunksize=500_000):
        row_count += len(chunk)
        values = pd.to_numeric(chunk["DATE"], errors="coerce").dropna()
        if values.empty:
            continue
        cmin = int(values.min())
        cmax = int(values.max())
        date_min = cmin if date_min is None else min(date_min, cmin)
        date_max = cmax if date_max is None else max(date_max, cmax)

    lines = [
        "# datashare.csv inventory",
        "",
        f"- Path: `{DATASHARE.relative_to(PROJECT_ROOT).as_posix()}`",
        f"- Total columns: **{len(columns)}**",
        f"- Predictor columns: **{len(predictors)}**",
        f"- Row count (chunk scan): **{row_count:,}**",
        f"- DATE range (YYYYMM): **{date_min}** to **{date_max}**",
        "",
        "## Columns",
        "",
        "| Column | GKX description (if known) |",
        "| --- | --- |",
    ]
    for col in columns:
        desc = descriptions.get(norm(col), "")
        lines.append(f"| `{col}` | {desc} |")

    out = DOCS_GKX / "datashare_inventory.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    mirror = DIAGNOSTICS_DIR / "datashare_inventory.md"
    mirror.parent.mkdir(parents=True, exist_ok=True)
    mirror.write_text(out.read_text(encoding="utf-8"), encoding="utf-8")
    print(out.read_text(encoding="utf-8"))


if __name__ == "__main__":
    main()
