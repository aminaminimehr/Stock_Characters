#!/usr/bin/env python3
"""Rebuild quarterly/special characters after formula fixes (annual already built)."""
from __future__ import annotations

import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "Character_Builders"))

from output_paths import CHARACTER_INDIVIDUAL_DIR, ensure_output_tree  # noqa: E402
from _shared.beta_builder import build_beta_character, build_betasq_character  # noqa: E402
from _shared.event_builders import build_abr_character  # noqa: E402
from _shared.green_builders import connect_wrds  # noqa: E402
from _shared.quarterly_builders import (  # noqa: E402
    QUARTERLY_CHARACTER_INFO,
    build_quarterly_character,
    prepare_quarterly_compustat_panel,
)


def main() -> None:
    for key in ("STOCK_CHARACTERS_SAMPLE_START", "STOCK_CHARACTERS_SAMPLE_END"):
        os.environ.pop(key, None)
    ensure_output_tree()
    db = connect_wrds(os.environ.get("WRDS_USERNAME"))
    try:
        print("Quarterly panel...", flush=True)
        quarterly_comp = prepare_quarterly_compustat_panel(db, use_ibes=False)
        for character in QUARTERLY_CHARACTER_INFO:
            out = build_quarterly_character(db, character, comp=quarterly_comp, use_ibes=False)
            path = CHARACTER_INDIVIDUAL_DIR / f"{character}.csv"
            out.to_csv(path, index=False)
            print(f"{character}: {len(out):,} rows", flush=True)
        print("abr...", flush=True)
        build_abr_character(db).to_csv(CHARACTER_INDIVIDUAL_DIR / "abr.csv", index=False)
    finally:
        db.close()
    print("Done (beta skipped — run beta_builder separately if needed).", flush=True)


if __name__ == "__main__":
    main()
