"""mvel1 — GKX datashare predictor `mvel1`.
Each builder runs its own WRDS SQL on the full eligible universe.
"""
from __future__ import annotations

import sys
from pathlib import Path

_DEFS = Path(__file__).resolve().parents[1] / "01_definitions"
if str(_DEFS) not in sys.path:
    sys.path.insert(0, str(_DEFS))

CHARACTER = "mvel1"

from monthly_runner import attach_monthly_sic, compute_monthly_feature, fetch_crsp_msf, write_monthly


def build_mvel1(db, use_cache=True):
    stem = "mvel1"
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
        build_mvel1(db)
    finally:
        db.close()
