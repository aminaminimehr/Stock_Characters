#!/usr/bin/env python3
"""Move legacy flat outputs/*.csv into the organized output tree."""
import shutil
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from output_paths import (  # noqa: E402
    CHARACTER_INDIVIDUAL_DIR,
    LEGACY_FLAT_OUTPUT_DIR,
    LEGACY_PANELS_DIR,
    NON_CHARACTER_STEMS,
    PANELS_DIR,
    ensure_output_tree,
)

PANEL_FILES = {
    "all_character_signal_panel.csv",
    "complete_all_character_prediction_panel.csv",
    "research_panel_1957_ranked.csv",
    "excess_returns.csv",
}
LEGACY_PANEL_FILES = {
    "annual_character_panel.csv",
    "monthly_character_panel.csv",
    "complete_prediction_panel.csv",
}


def main():
    ensure_output_tree()
    moved = []
    for path in sorted(LEGACY_FLAT_OUTPUT_DIR.glob("*.csv")):
        if path.name in PANEL_FILES:
            target = PANELS_DIR / path.name
        elif path.name in LEGACY_PANEL_FILES:
            target = LEGACY_PANELS_DIR / path.name
        elif path.stem in NON_CHARACTER_STEMS:
            continue
        else:
            target = CHARACTER_INDIVIDUAL_DIR / path.name

        target.parent.mkdir(parents=True, exist_ok=True)
        if target.exists():
            continue
        shutil.move(str(path), str(target))
        moved.append((path.name, str(target)))

    print(f"Moved {len(moved)} files")
    for name, dest in moved:
        print(f"  {name} -> {dest}")


if __name__ == "__main__":
    main()
