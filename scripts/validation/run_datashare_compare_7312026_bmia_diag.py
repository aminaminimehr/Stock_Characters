#!/usr/bin/env python3
"""One-off diagnostic: compare research_panel_1957_ranked_7312026.csv vs datashare.csv.

Overrides the canonical bm_ia alias to use panel ``bm_ia`` (Green FF49) instead of
``bm_ia_sic2m`` (datashare SIC2 x month convention, absent in this panel).
Writes to dated diagnostic paths so the benchmark docs are not overwritten.

Usage:
  python scripts/validation/run_datashare_compare_7312026_bmia_diag.py
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CANONICAL = ROOT / "scripts" / "validation" / "compare_panel_vs_gkx_datashare.py"
DEFAULT_PANEL = ROOT / "outputs" / "panels" / "research_panel_1957_ranked_7312026.csv"
DEFAULT_DATASHARE = ROOT / "Supplementary_assistive_files" / "datashare.csv"
OUT_CSV = ROOT / "docs" / "gkx" / "panel_gkx_datashare_comparison_7312026_bmia_diag.csv"
OUT_MD = ROOT / "docs" / "gkx" / "panel_gkx_datashare_comparison_7312026_bmia_diag.md"


def load_canonical():
    spec = importlib.util.spec_from_file_location("compare_panel_vs_gkx_datashare", CANONICAL)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["compare_panel_vs_gkx_datashare"] = mod
    spec.loader.exec_module(mod)
    return mod


def main() -> None:
    cmp = load_canonical()

    # Override: compare datashare bm_ia against Green FF49 bm_ia (not bm_ia_sic2m).
    cmp.PANEL_ALIAS["bm_ia"] = "bm_ia"
    cmp.OUT_CSV = OUT_CSV
    cmp.OUT_MD = OUT_MD

    sys.argv = [
        str(CANONICAL),
        "--panel",
        str(DEFAULT_PANEL),
        "--datashare",
        str(DEFAULT_DATASHARE),
    ]
    cmp.main()


if __name__ == "__main__":
    main()
