#!/usr/bin/env python3
"""One-time migration: move legacy flat outputs/*.csv into the organized output tree.

Not required after normal pipeline runs. Fresh clones and future
``run_full_pipeline.sh`` / ``run_full_pipeline.py`` runs write directly into
``outputs/characteristics/individual/``, ``outputs/panels/``, etc.

Run this only when upgrading a repository or server that still has old flat
``outputs/*.csv`` files from before the layout refactor.
"""
import shutil
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from output_paths import (  # noqa: E402
    CHARACTER_INDIVIDUAL_DIR,
    DIAGNOSTICS_DIR,
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
    "complete_prediction_panel_imputed.csv",
}
DIAGNOSTIC_FILES = {
    "green_comparable_temp.csv",
    "green_comparable_temp2_winsorized.csv",
    "green_comparable_validation_summary.csv",
    "green_comparable_winsorized_validation_summary.csv",
    "green_comparable_winsorized_validation_summary_fresh.csv",
    "green_missing_character_inventory.csv",
}


def _relocate(path: Path, target: Path, moved: list, removed: list):
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists():
        path.unlink()
        removed.append((path.name, f"duplicate removed ({target} kept)"))
        return
    shutil.move(str(path), str(target))
    moved.append((path.name, str(target)))


def main():
    ensure_output_tree()
    moved = []
    removed = []
    for path in sorted(LEGACY_FLAT_OUTPUT_DIR.glob("*.csv")):
        name = path.name
        if name in PANEL_FILES:
            target = PANELS_DIR / name
        elif name in LEGACY_PANEL_FILES:
            target = LEGACY_PANELS_DIR / name
        elif name in DIAGNOSTIC_FILES:
            target = DIAGNOSTICS_DIR / name
        elif path.stem in NON_CHARACTER_STEMS:
            continue
        else:
            target = CHARACTER_INDIVIDUAL_DIR / name

        _relocate(path, target, moved, removed)

    print(f"Moved {len(moved)} files")
    for name, dest in moved:
        print(f"  {name} -> {dest}")
    if removed:
        print(f"Removed {len(removed)} duplicate flat files")
        for name, note in removed:
            print(f"  {name}: {note}")

    remaining = sorted(LEGACY_FLAT_OUTPUT_DIR.glob("*.csv"))
    if remaining:
        print(f"\nWarning: {len(remaining)} flat CSV(s) remain:")
        for path in remaining:
            print(f"  {path.name}")
    else:
        print("\nFlat outputs/*.csv migration complete (no CSVs left at outputs/ root).")


if __name__ == "__main__":
    main()
