#!/usr/bin/env python3
"""Split all_builds.py into per-stem modules under 02_builders/."""
from __future__ import annotations

import inspect
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
BUILDERS_DIR = ROOT
DEFS = ROOT.parent / "01_definitions"

sys.path.insert(0, str(DEFS))
sys.path.insert(0, str(BUILDERS_DIR))

import all_builds  # noqa: E402
from catalog import (  # noqa: E402
    DAILY_MONTHLY_STEMS,
    GREEN_ANNUAL_STEMS,
    HXZ_STEMS,
    MONTHLY_CRSP_STEMS,
    NO_WRDS_STEMS,
    QUARTERLY_STEMS,
)
from config import DATASHARE_PREDICTORS  # noqa: E402

HEADER = '''\
"""{stem} — GKX datashare predictor `{stem}`.
Each builder runs its own WRDS SQL on the full eligible universe.
"""
from __future__ import annotations

import sys
from pathlib import Path

_DEFS = Path(__file__).resolve().parents[1] / "01_definitions"
if str(_DEFS) not in sys.path:
    sys.path.insert(0, str(_DEFS))

CHARACTER = "{stem}"
'''

IMPORTS_ANNUAL = """
from annual_formulas import apply_annual_formula, needs_industry_adjustment
from annual_runner import fetch_green_funda, finalize_green_annual, write_annual
from catalog import ANNUAL_FUNDA_ITEMS
"""

IMPORTS_MONTHLY = """
from monthly_runner import attach_monthly_sic, compute_monthly_feature, fetch_crsp_msf, write_monthly
"""

IMPORTS_DAILY = """
from daily_monthly_runner import merge_daily_to_monthly, write_daily_monthly
"""

IMPORTS_QUARTERLY = """
from catalog import QUARTERLY_FUNDA_ITEMS
from quarterly_runner import build_quarterly_stem, write_quarterly
"""

IMPORTS_HXZ_BM = """
from hxz_runner import build_bm_panel, write_hxz_annual
"""

IMPORTS_HXZ_OPE = """
from hxz_runner import build_operprof_panel, write_hxz_annual
"""

IMPORTS_BM_IA = """
from bm_ia_runner import build_bm_ia_from_parquet, write_bm_ia
from paths import SINGLE_CHARACTERS_DIR
"""

IMPORTS_FACTOR = """
from beta_runner import build_factor_stem, write_factor
"""

IMPORTS_EVENT = """
from event_runner import build_event_stem, write_event
"""

IMPORTS_MS = """
from ms_runner import build_ms_panel, write_ms
"""

MAIN_BLOCK = '''
if __name__ == "__main__":
    import argparse
    from paths import ensure_output_tree
    from wrds_io import connect_wrds

    p = argparse.ArgumentParser()
    p.add_argument("--wrds-user", default=None)
    args = p.parse_args()
    ensure_output_tree()
    db = connect_wrds(args.wrds_user)
    try:
        build_{stem}(db)
    finally:
        db.close()
'''

MAIN_BLOCK_NO_WRDS = '''
if __name__ == "__main__":
    from paths import ensure_output_tree

    ensure_output_tree()
    build_{stem}(None)
'''


def imports_for(stem: str) -> str:
    if stem in GREEN_ANNUAL_STEMS:
        return IMPORTS_ANNUAL
    if stem in MONTHLY_CRSP_STEMS:
        return IMPORTS_MONTHLY
    if stem in DAILY_MONTHLY_STEMS:
        return IMPORTS_DAILY
    if stem in QUARTERLY_STEMS:
        return IMPORTS_QUARTERLY
    if stem == "bm":
        return IMPORTS_HXZ_BM
    if stem == "operprof":
        return IMPORTS_HXZ_OPE
    if stem in NO_WRDS_STEMS:
        return IMPORTS_BM_IA
    if stem in ("beta", "betasq", "idiovol", "pricedelay"):
        return IMPORTS_FACTOR
    if stem in ("ear", "aeavol"):
        return IMPORTS_EVENT
    if stem == "ms":
        return IMPORTS_MS
    return ""


def main() -> None:
    BUILDERS_DIR.mkdir(parents=True, exist_ok=True)
    written = []
    for stem in DATASHARE_PREDICTORS:
        fn = getattr(all_builds, f"build_{stem}")
        src = inspect.getsource(fn).rstrip()
        content = HEADER.format(stem=stem)
        content += imports_for(stem) + "\n\n" + src + "\n"
        if stem in NO_WRDS_STEMS:
            content += MAIN_BLOCK_NO_WRDS.format(stem=stem)
        else:
            content += MAIN_BLOCK.format(stem=stem)
        path = BUILDERS_DIR / f"{stem}.py"
        path.write_text(content, encoding="utf-8")
        written.append(path.name)
    print(f"Wrote {len(written)} stem modules under {BUILDERS_DIR}")


if __name__ == "__main__":
    main()
