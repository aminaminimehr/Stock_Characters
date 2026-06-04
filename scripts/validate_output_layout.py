#!/usr/bin/env python3
"""Lightweight validation of output layout (no full WRDS production run)."""
from __future__ import annotations

import ast
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from output_paths import (  # noqa: E402
    CACHE_DIR,
    CHARACTER_INDIVIDUAL_DIR,
    COMPLETE_ALL_PANEL_FILE,
    DIAGNOSTICS_DIR,
    LEGACY_FLAT_OUTPUT_DIR,
    LEGACY_PANELS_DIR,
    PANELS_DIR,
    PROJECT_ROOT as OUTPUT_PROJECT_ROOT,
    SIGNAL_PANEL_FILE,
    ensure_output_tree,
    list_character_stems,
    resolve_legacy_panel_path,
    resolve_output_path,
)

# Writers that must not default-save to flat outputs/ via parents[2] / "outputs" / ...
WRITER_SCRIPTS = [
    "Character_Builders/HXZ_BM_Generalized/build_book_to_market.py",
    "Character_Builders/HXZ_BMJ_Generalized/build_book_to_june_market_equity.py",
    "Character_Builders/HXZ_OPE_Generalized/build_operating_profitability.py",
    "Character_Builders/HXZ_CFP_Generalized/build_cash_flow_to_price.py",
    "Character_Builders/Green_MVEL1_Generalized/build_mvel1.py",
    "Character_Builders/Green_ZEROTRADE_Generalized/build_zerotrade.py",
    "Character_Panels/build_monthly_character_panel.py",
    "Character_Panels/build_annual_character_panel.py",
]

FORBIDDEN_FLAT_WRITE_SNIPPETS = (
    'parents[2] / "outputs" /',
    'PROJECT_ROOT / "outputs" / f"',
    'PROJECT_ROOT / "outputs" / "',
    'OUTPUT_DIR = PROJECT_ROOT / "outputs"',
)


def check_path_helpers():
    assert resolve_output_path("book_to_market.csv") == (
        CHARACTER_INDIVIDUAL_DIR / "book_to_market.csv"
    )
    assert resolve_output_path("zerotrade.csv") == CHARACTER_INDIVIDUAL_DIR / "zerotrade.csv"
    assert resolve_output_path("outputs/panels/foo.csv") == (
        OUTPUT_PROJECT_ROOT / "outputs/panels/foo.csv"
    )
    assert resolve_legacy_panel_path("monthly_character_panel.csv") == (
        LEGACY_PANELS_DIR / "monthly_character_panel.csv"
    )
    print("  path helpers: OK")


def check_writer_sources():
    for rel in WRITER_SCRIPTS:
        text = (PROJECT_ROOT / rel).read_text(encoding="utf-8")
        for snippet in FORBIDDEN_FLAT_WRITE_SNIPPETS:
            if snippet in text:
                raise AssertionError(f"{rel} still contains forbidden flat-write snippet: {snippet!r}")
    print(f"  writer source scan ({len(WRITER_SCRIPTS)} files): OK")


def check_legacy_gating():
    for script in (
        "Character_Panels/build_monthly_character_panel.py",
        "Character_Panels/build_annual_character_panel.py",
    ):
        proc = subprocess.run(
            [sys.executable, script],
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
        )
        if proc.returncode == 0:
            raise AssertionError(f"{script} should exit non-zero without --allow-legacy")
        if "deprecated" not in (proc.stdout + proc.stderr).lower():
            raise AssertionError(f"{script} did not report deprecation message")
    print("  legacy panel gating: OK")


def check_orchestrator_defaults():
    text = (PROJECT_ROOT / "Character_Panels/run_full_pipeline.py").read_text(encoding="utf-8")
    for token in ("CHARACTER_INDIVIDUAL_DIR", "SIGNAL_PANEL_FILE", "COMPLETE_ALL_PANEL_FILE"):
        if token not in text:
            raise AssertionError(f"run_full_pipeline.py missing {token}")
    tree = ast.parse(text)
    print("  orchestrator references canonical paths: OK")


def main():
    ensure_output_tree()
    assert PANELS_DIR.exists()
    assert CHARACTER_INDIVIDUAL_DIR.exists()
    assert DIAGNOSTICS_DIR.exists()
    assert CACHE_DIR.exists()
    assert LEGACY_PANELS_DIR.exists()

    print("Output layout checks")
    check_path_helpers()
    check_writer_sources()
    check_legacy_gating()
    check_orchestrator_defaults()

    stems = list_character_stems()
    print(f"  discovered character stems: {len(stems)}")
    flat_csvs = list(LEGACY_FLAT_OUTPUT_DIR.glob("*.csv")) if LEGACY_FLAT_OUTPUT_DIR.exists() else []
    if flat_csvs:
        print(
            f"  note: {len(flat_csvs)} flat outputs/*.csv still present "
            "(read fallback OK; run migrate_outputs_layout.py once if upgrading)"
        )

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
            f"  skipped heavy panel rebuild ({len(stems)} character CSVs); "
            "use run_full_pipeline.py --skip-build on the server if needed."
        )
    else:
        print("  no character CSVs; skipped panel-only pipeline check.")

    print("\nAll output layout validations passed.")


if __name__ == "__main__":
    main()
