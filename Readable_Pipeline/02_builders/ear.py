"""ear — GKX datashare predictor `ear`.
Each builder runs its own WRDS SQL on the full eligible universe.
"""
from __future__ import annotations

import sys
from pathlib import Path

_DEFS = Path(__file__).resolve().parents[1] / "01_definitions"
if str(_DEFS) not in sys.path:
    sys.path.insert(0, str(_DEFS))

CHARACTER = "ear"

from event_runner import build_event_stem, write_event


def build_ear(db, use_cache=True):
    stem = "ear"
    out = build_event_stem(db, stem, use_cache=use_cache)
    write_event(out, stem)

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
        build_ear(db)
    finally:
        db.close()
