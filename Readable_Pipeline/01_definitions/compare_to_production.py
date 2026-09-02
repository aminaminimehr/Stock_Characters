"""Compare readable pipeline outputs to production (thin validation helper)."""
from __future__ import annotations

from pathlib import Path

import pandas as pd

STOCK_ROOT = Path(__file__).resolve().parents[2]
PROD_INDIVIDUAL = STOCK_ROOT / "outputs" / "characteristics" / "individual"
READABLE_INDIVIDUAL = Path(__file__).resolve().parents[1] / "03_outputs" / "single_characters"


def compare_character_csv(stem: str) -> dict | None:
    new_path = READABLE_INDIVIDUAL / f"{stem}.parquet"
    prod_path = PROD_INDIVIDUAL / f"{stem}.csv"
    if not new_path.exists() or not prod_path.exists():
        return None
    new = pd.read_parquet(new_path)
    prod = pd.read_csv(prod_path)
    if "datadate" in new.columns and "datadate" in prod.columns:
        keys = ["permno", "datadate"]
    elif "signal_yyyymm" in new.columns:
        keys = ["permno", "signal_yyyymm"]
    else:
        return None
    merged = new.merge(prod, on=keys, suffixes=("_new", "_prod"))
    col_new = f"{stem}_new" if f"{stem}_new" in merged.columns else stem
    col_prod = f"{stem}_prod" if f"{stem}_prod" in merged.columns else stem
    diff = (merged[col_new] - merged[col_prod]).abs()
    return {"stem": stem, "n": len(merged), "max_abs_diff": float(diff.max()) if len(diff) else None}


if __name__ == "__main__":
    from config import DATASHARE_PREDICTORS

    rows = []
    for stem in DATASHARE_PREDICTORS:
        result = compare_character_csv(stem)
        if result:
            rows.append(result)
            print(result)
    if not rows:
        print("No overlapping production/readable character file pairs found.")
