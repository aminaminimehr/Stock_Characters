#!/usr/bin/env python3
"""Lightweight validation of output layout (no full WRDS production run)."""
from __future__ import annotations

import ast
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from output_paths import (  # noqa: E402
    CACHE_DIR,
    CHARACTER_INDIVIDUAL_DIR,
    DIAGNOSTICS_DIR,
    LEGACY_FLAT_OUTPUT_DIR,
    PANELS_DIR,
    PROJECT_ROOT as OUTPUT_PROJECT_ROOT,
    SIGNAL_PANEL_FILE,
    ensure_output_tree,
    list_character_stems,
    resolve_output_path,
)

WRITER_SCRIPTS = [
    "Character_Builders/HXZ_BM_Generalized/build_book_to_market.py",
    "Character_Builders/HXZ_OPE_Generalized/build_operating_profitability.py",
    "Character_Builders/Datashare_BM_IA_Generalized/build_bm_ia.py",
]

FORBIDDEN_FLAT_WRITE_SNIPPETS = (
    'parents[2] / "outputs" /',
    'PROJECT_ROOT / "outputs" / f"',
    'PROJECT_ROOT / "outputs" / "',
    'OUTPUT_DIR = PROJECT_ROOT / "outputs"',
)


def check_path_helpers():
    assert resolve_output_path("bm.csv") == CHARACTER_INDIVIDUAL_DIR / "bm.csv"
    assert resolve_output_path("operprof.csv") == CHARACTER_INDIVIDUAL_DIR / "operprof.csv"
    assert resolve_output_path("outputs/panels/foo.csv") == (
        OUTPUT_PROJECT_ROOT / "outputs/panels/foo.csv"
    )
    print("  path helpers: OK")


def check_writer_sources():
    for rel in WRITER_SCRIPTS:
        path = PROJECT_ROOT / rel
        if not path.exists():
            raise AssertionError(f"missing writer script: {rel}")
        text = path.read_text(encoding="utf-8")
        for snippet in FORBIDDEN_FLAT_WRITE_SNIPPETS:
            if snippet in text:
                raise AssertionError(f"{rel} still contains forbidden flat-write snippet: {snippet!r}")
    print(f"  writer source scan ({len(WRITER_SCRIPTS)} files): OK")


def check_orchestrator_defaults():
    text = (PROJECT_ROOT / "Character_Panels/run_full_pipeline.py").read_text(encoding="utf-8")
    for token in ("CHARACTER_INDIVIDUAL_DIR", "SIGNAL_PANEL_FILE", "DATASHARE_COLUMNS"):
        if token not in text:
            raise AssertionError(f"run_full_pipeline.py missing {token}")
    ast.parse(text)
    print("  orchestrator references canonical paths: OK")


def main():
    ensure_output_tree()
    assert PANELS_DIR.exists()
    assert CHARACTER_INDIVIDUAL_DIR.exists()
    assert DIAGNOSTICS_DIR.exists()
    assert CACHE_DIR.exists()

    print("Output layout checks")
    check_path_helpers()
    check_writer_sources()
    check_orchestrator_defaults()

    stems = list_character_stems()
    print(f"  discovered character stems: {len(stems)}")

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
        print(f"  {SIGNAL_PANEL_FILE.name}: {'exists' if SIGNAL_PANEL_FILE.exists() else 'missing'}")
    elif stems:
        print(
            f"  skipped heavy panel rebuild ({len(stems)} character CSVs); "
            "use run_full_pipeline.py --skip-build on the server if needed."
        )
    else:
        print("  no character CSVs; skipped panel-only pipeline check.")

    flat_csvs = list(LEGACY_FLAT_OUTPUT_DIR.glob("*.csv")) if LEGACY_FLAT_OUTPUT_DIR.exists() else []
    if flat_csvs:
        print(f"  note: {len(flat_csvs)} flat outputs/*.csv still present (legacy fallback)")

    print("\nAll output layout validations passed.")


if __name__ == "__main__":
    main()
