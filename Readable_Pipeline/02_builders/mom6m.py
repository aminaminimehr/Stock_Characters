"""mom6m — GKX datashare predictor `mom6m`.
Each builder runs its own WRDS SQL on the full eligible universe.
"""
from __future__ import annotations

import sys
from pathlib import Path

_DEFS = Path(__file__).resolve().parents[1] / "01_definitions"
if str(_DEFS) not in sys.path:
    sys.path.insert(0, str(_DEFS))

CHARACTER = "mom6m"

from monthly_runner import attach_monthly_sic, compute_monthly_feature, fetch_crsp_msf, write_monthly


def build_mom6m(db, use_cache=True):
    stem = "mom6m"
    crsp = fetch_crsp_msf(db, stem, use_cache=use_cache)
    crsp = attach_monthly_sic(crsp, db, stem, use_cache=use_cache)
    crsp = compute_monthly_feature(crsp, stem)
    write_monthly(crsp, stem)

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
        build_mom6m(db)
    finally:
        db.close()
