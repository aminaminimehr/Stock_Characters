"""std_dolvol — GKX datashare predictor `std_dolvol`.
Each builder runs its own WRDS SQL on the full eligible universe.
"""
from __future__ import annotations

import sys
from pathlib import Path

_DEFS = Path(__file__).resolve().parents[1] / "01_definitions"
if str(_DEFS) not in sys.path:
    sys.path.insert(0, str(_DEFS))

CHARACTER = "std_dolvol"

from daily_monthly_runner import merge_daily_to_monthly, write_daily_monthly


def build_std_dolvol(db, use_cache=True):
    stem = "std_dolvol"
    out = merge_daily_to_monthly(db, stem, use_cache=use_cache)
    write_daily_monthly(out, stem)

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
        build_std_dolvol(db)
    finally:
        db.close()
