"""rsup — GKX datashare predictor `rsup`.
Each builder runs its own WRDS SQL on the full eligible universe.
"""
from __future__ import annotations

import sys
from pathlib import Path

_DEFS = Path(__file__).resolve().parents[1] / "01_definitions"
if str(_DEFS) not in sys.path:
    sys.path.insert(0, str(_DEFS))

CHARACTER = "rsup"

from catalog import QUARTERLY_FUNDA_ITEMS
from quarterly_runner import build_quarterly_stem, write_quarterly


def build_rsup(db, use_cache=True):
    stem = "rsup"
    items = QUARTERLY_FUNDA_ITEMS[stem]
    out = build_quarterly_stem(db, stem, items, use_cache=use_cache)
    write_quarterly(out, stem)

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
        build_rsup(db)
    finally:
        db.close()
