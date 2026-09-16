"""Flat procedural script: impute missing predictors and rank cross-sectionally to [-1, 1].

Reads the winsorized dl_blt signal panel (final_panel_dl_blt.csv), recomputes ffi49 from sic
via hardcoded FF49_RANGES, imputes missing values (FF49 x signal_yyyymm median, then month
median fallback), ranks predictors within each signal month, drops rows with no excess_return,
and writes research_panel_dl_blt.csv. No WRDS — excess_return is already in the input CSV.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

PIPELINE_ROOT = Path(__file__).resolve().parents[1]
if str(PIPELINE_ROOT) not in sys.path:
    sys.path.insert(0, str(PIPELINE_ROOT))

from config.conventions import DATASHARE_PREDICTORS, PANEL_DIR  # noqa: E402
from config.ff49_ranges import FF49_RANGES  # noqa: E402

INPUT_PATH = PANEL_DIR / "final_panel_dl_blt.csv"
OUTPUT_PATH = PANEL_DIR / "research_panel_dl_blt.csv"

#######################################################################################################################
#                                                       Load panel                                                    #
#######################################################################################################################

print(f"Loading {INPUT_PATH}...", flush=True)
if not INPUT_PATH.exists():
    raise FileNotFoundError(f"Missing input panel: {INPUT_PATH}")

df = pd.read_csv(INPUT_PATH)
print(f"Loaded {len(df):,} rows x {len(df.columns)} cols", flush=True)

predictors = [c for c in DATASHARE_PREDICTORS if c in df.columns]
missing_predictors = [c for c in DATASHARE_PREDICTORS if c not in df.columns]
if missing_predictors:
    print(f"Warning: {len(missing_predictors)} predictors absent from input:", flush=True)
    print(", ".join(missing_predictors), flush=True)
print(f"Predictors to impute and rank: {len(predictors)}", flush=True)

#######################################################################################################################
#                                              Assign ffi49 from sic (FF49)                                           #
# Uses hardcoded SIC ranges in config/ff49_ranges.py (FF49_RANGES).                                                   #
#######################################################################################################################

print("Assigning ffi49 from sic via FF49_RANGES...", flush=True)
sic = pd.to_numeric(df["sic"], errors="coerce")
ffi49 = pd.Series(pd.NA, index=df.index, dtype="Int64")
for sic_s, sic_e, ffi in FF49_RANGES:
    ffi49.loc[sic.between(sic_s, sic_e)] = int(ffi)
df["ffi49"] = ffi49

#######################################################################################################################
#                    Impute missing predictors: FF49 x signal_yyyymm median, then signal_yyyymm median               #
#######################################################################################################################

print("Imputing missing values (FF49 x signal_yyyymm median, then month median fallback)...", flush=True)
ind_month_median = df.groupby(["signal_yyyymm", "ffi49"], dropna=False)[predictors].transform("median")
month_median = df.groupby("signal_yyyymm", dropna=False)[predictors].transform("median")
df[predictors] = df[predictors].fillna(ind_month_median).fillna(month_median)

#######################################################################################################################
#              Cross-sectional rank predictors to [-1, 1] within each signal_yyyymm (GKX formula)                     #
# ranked_x = 2 * (rank(x) - 1) / (N - 1) - 1; N==1 or still-missing -> 0                                             #
# excess_return is a target column and is NOT ranked.                                                                 #
#######################################################################################################################

print("Ranking predictors into [-1, 1] by signal_yyyymm...", flush=True)
grouped = df.groupby("signal_yyyymm", dropna=False)[predictors]
ranks = grouped.rank(method="average")
n = grouped.transform("count")
with np.errstate(divide="ignore", invalid="ignore"):
    ranked = 2.0 * (ranks - 1.0) / (n - 1.0) - 1.0
ranked = ranked.where(n > 1, 0.0)
df[predictors] = ranked.fillna(0.0)

#######################################################################################################################
#                                    Drop rows with no excess_return; write output                                    #
#######################################################################################################################

before = len(df)
df = df.dropna(subset=["excess_return"]).copy()
print(f"Dropped {before - len(df):,} rows with no excess_return; {len(df):,} rows remain", flush=True)

out_cols = ["permno", "signal_yyyymm", "target_yyyymm", "sic", "ffi49", "excess_return"] + predictors
final = df[out_cols].copy()

PANEL_DIR.mkdir(parents=True, exist_ok=True)
final.to_csv(OUTPUT_PATH, index=False, float_format="%.6f")
print(
    f"Wrote {len(final):,} rows x {len(out_cols)} cols ({len(predictors)} predictors) -> {OUTPUT_PATH}",
    flush=True,
)
