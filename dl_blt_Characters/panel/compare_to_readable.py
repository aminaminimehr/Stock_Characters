"""Compare dl_blt final panel to Readable_Pipeline signal panel."""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

PIPELINE_ROOT = Path(__file__).resolve().parents[1]
if str(PIPELINE_ROOT) not in sys.path:
    sys.path.insert(0, str(PIPELINE_ROOT))

from config.conventions import DATASHARE_PREDICTORS, PANEL_DIR  # noqa: E402

READABLE_PANEL = (
    PIPELINE_ROOT.parent
    / "Readable_Pipeline"
    / "03_outputs"
    / "panels"
    / "all_character_signal_panel.csv"
)
COMPARE_KEYS = ["permno", "signal_yyyymm"]


#######################################################################################################################
#                                                    Load panels                                                      #
#######################################################################################################################

dl_path = PANEL_DIR / "final_panel.csv"
if not dl_path.exists():
    raise FileNotFoundError(f"Missing dl_blt panel: {dl_path}")
if not READABLE_PANEL.exists():
    raise FileNotFoundError(f"Missing readable panel: {READABLE_PANEL}")

print(f"Loading dl_blt panel: {dl_path}", flush=True)
dl = pd.read_csv(dl_path, low_memory=False)
print(f"Loading readable panel: {READABLE_PANEL}", flush=True)
readable = pd.read_csv(READABLE_PANEL, low_memory=False)

for frame in (dl, readable):
    frame["permno"] = pd.to_numeric(frame["permno"], errors="coerce").astype("Int64")
    frame["signal_yyyymm"] = pd.to_numeric(frame["signal_yyyymm"], errors="coerce").astype("Int64")

shared_cols = sorted(set(DATASHARE_PREDICTORS) & set(dl.columns) & set(readable.columns))
if not shared_cols:
    raise ValueError("No shared DATASHARE_PREDICTORS columns between panels.")

merge_cols = COMPARE_KEYS + shared_cols
merged = dl[merge_cols].merge(
    readable[merge_cols],
    on=COMPARE_KEYS,
    how="inner",
    suffixes=("_dl", "_readable"),
)

print(f"Shared predictors: {len(shared_cols)}", flush=True)
print(f"Inner join on {COMPARE_KEYS}: {len(merged):,} rows", flush=True)

#######################################################################################################################
#                                              Per-column comparison                                                  #
#######################################################################################################################


def compare_column(col: str) -> dict:
    """Compute overlap count, Spearman rho, and max abs diff for one predictor."""
    left = pd.to_numeric(merged[f"{col}_dl"], errors="coerce")
    right = pd.to_numeric(merged[f"{col}_readable"], errors="coerce")
    valid = left.notna() & right.notna()
    count = int(valid.sum())
    if count == 0:
        return {"column": col, "count": 0, "spearman_rho": np.nan, "max_abs_diff": np.nan}
    lv = left[valid]
    rv = right[valid]
    rho = lv.corr(rv, method="spearman")
    max_abs = float((lv - rv).abs().max())
    return {"column": col, "count": count, "spearman_rho": float(rho), "max_abs_diff": max_abs}


rows = [compare_column(col) for col in shared_cols]
summary = pd.DataFrame(rows).sort_values("column").reset_index(drop=True)

pd.set_option("display.max_rows", 200)
pd.set_option("display.width", 120)
pd.set_option("display.float_format", lambda x: f"{x:,.6f}")

print("\nComparison summary (keys: permno, signal_yyyymm):\n", flush=True)
print(summary.to_string(index=False), flush=True)

low_rho = summary[summary["spearman_rho"].notna() & (summary["spearman_rho"] < 0.99)]
if not low_rho.empty:
    print(f"\nColumns with Spearman rho < 0.99: {len(low_rho)}", flush=True)
else:
    print("\nAll shared columns have Spearman rho >= 0.99 (where defined).", flush=True)
