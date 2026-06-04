#!/usr/bin/env python3
"""Lightweight validation of output layout (no full WRDS production run)."""
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from output_paths import (  # noqa: E402
    CHARACTER_INDIVIDUAL_DIR,
    COMPLETE_ALL_PANEL_FILE,
    PANELS_DIR,
    SIGNAL_PANEL_FILE,
    ensure_output_tree,
    list_character_stems,
)


def main():
    ensure_output_tree()
    assert PANELS_DIR.exists()
    assert CHARACTER_INDIVIDUAL_DIR.exists()

    stems = list_character_stems()
    print("Output layout OK")
    print(f"  characteristics/individual exists: {CHARACTER_INDIVIDUAL_DIR}")
    print(f"  panels exists: {PANELS_DIR}")
    print(f"  discovered character stems: {len(stems)}")

    # Optional panel-only rebuild when a small test set exists (skip on full production tree).
    if stems and len(stems) <= 12:
        cmd = [
            sys.executable,
            "Character_Panels/run_full_pipeline.py",
            "--wrds-user",
            "layout_check",
            "--skip-build",
        ]
        print("\nRunning panel-only pipeline check:", " ".join(cmd))
        subprocess.run(cmd, cwd=PROJECT_ROOT, check=True)
        for path in (SIGNAL_PANEL_FILE, COMPLETE_ALL_PANEL_FILE):
            print(f"  {path.name}: {'exists' if path.exists() else 'missing'}")
    elif stems:
        print(
            f"Found {len(stems)} character CSVs; skipped heavy panel rebuild in validation "
            "(use run_full_pipeline.py --skip-build on the server)."
        )
    else:
        print("No character CSVs found; skipped panel-only pipeline check.")


if __name__ == "__main__":
    main()
