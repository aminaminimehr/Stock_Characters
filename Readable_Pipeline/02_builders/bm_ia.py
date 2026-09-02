"""bm_ia — GKX datashare predictor `bm_ia`.
Each builder runs its own WRDS SQL on the full eligible universe.
"""
from __future__ import annotations

import sys
from pathlib import Path

_DEFS = Path(__file__).resolve().parents[1] / "01_definitions"
if str(_DEFS) not in sys.path:
    sys.path.insert(0, str(_DEFS))

CHARACTER = "bm_ia"

from bm_ia_runner import build_bm_ia_from_parquet, write_bm_ia
from paths import SINGLE_CHARACTERS_DIR


def build_bm_ia(db, use_cache=True):
    _ = db, use_cache
    out = build_bm_ia_from_parquet(SINGLE_CHARACTERS_DIR / "bm.parquet")
    write_bm_ia(out)

if __name__ == "__main__":
    from paths import ensure_output_tree

    ensure_output_tree()
    build_bm_ia(None)
