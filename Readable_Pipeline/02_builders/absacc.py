"""absacc — GKX datashare predictor `absacc`.
Each builder runs its own WRDS SQL on the full eligible universe.
"""
from __future__ import annotations

import sys
from pathlib import Path

_DEFS = Path(__file__).resolve().parents[1] / "01_definitions"
if str(_DEFS) not in sys.path:
    sys.path.insert(0, str(_DEFS))

CHARACTER = "absacc"

from annual_formulas import apply_annual_formula, needs_industry_adjustment
from annual_runner import fetch_green_funda, finalize_green_annual, write_annual
from catalog import ANNUAL_FUNDA_ITEMS


def build_absacc(db, use_cache=True):
    stem = "absacc"
    items = ANNUAL_FUNDA_ITEMS[stem]
    comp = fetch_green_funda(db, stem, items, use_cache=use_cache)
    comp = apply_annual_formula(comp, stem, db=db)
    comp = finalize_green_annual(comp, stem, needs_ia=needs_industry_adjustment(stem), db=db)
    write_annual(comp, stem)

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
        build_absacc(db)
    finally:
        db.close()
