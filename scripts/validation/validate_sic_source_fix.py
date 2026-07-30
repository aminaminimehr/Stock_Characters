#!/usr/bin/env python3
"""Validate SIC source convention wiring and report pre/post-rebuild checklist."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from pipeline_config import resolve_config  # noqa: E402


def main() -> None:
    for profile in ("green", "datashare", "research"):
        cfg = resolve_config(profile)
        assert cfg.sic_source == "comp_company", profile

    legacy = resolve_config("green", sic_source="crsp_msenames")
    assert legacy.sic_source == "crsp_msenames"

    print("PipelineConfig sic_source defaults: OK")

    diag = ROOT / "scripts" / "diagnose_sic_source_mismatch.py"
    if diag.exists():
        print("\nRunning baseline diagnostic (existing panel)...")
        subprocess.run([sys.executable, str(diag)], check=False, cwd=ROOT)

    print(
        "\nPost-fix validation checklist (requires WRDS rebuild):\n"
        "  1. STOCK_CHARACTERS_SIC_SOURCE=comp_company (default via --profile green|datashare|research)\n"
        "  2. python Character_Builders/build_all_implemented_characters.py --profile green ...\n"
        "  3. python Character_Panels/build_all_character_panel.py\n"
        "  4. python scripts/diagnose_sic_source_mismatch.py  # sic2 match rate should improve\n"
        "  5. python scripts/validation/compare_panel_vs_gkx_datashare.py "
        "--panel outputs/panels/all_character_signal_panel.csv "
        "--datashare Supplementary_assistive_files/datashare.csv\n"
        "  6. Legacy Green baseline: rerun with --sic-source crsp_msenames and confirm no regression\n"
    )


if __name__ == "__main__":
    main()
