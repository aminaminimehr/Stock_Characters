#!/usr/bin/env python3
"""Build the cross-sectionally ranked research panel (1957+) from the signal panel.

STANDALONE SCRIPT -- not wired into run_full_pipeline.py.
Feed it the winsorized signal panel and it produces the prediction-ready
research panel: missing values imputed, then every characteristic mapped to
cross-sectional ranks in [-1, 1].

Input  (default): outputs/panels/all_character_signal_panel_after_major_change_1.csv
Output (default): outputs/panels/research_panel_1957_ranked.csv

The transformation follows the GKX convention documented in
Character_Panels/RESEARCH_PANEL_1957_DATA_STRUCTURE.txt, steps 1, 4, 5, 6, 7:

  1. Keep target return months from January 1957 onward (target_yyyymm >= 195701).
  4. Impute missing values using signal-month x FF49 industry medians.
  5. If an industry median is unavailable, fall back to the same-month
     cross-sectional median.
  6. Rank each characteristic cross-sectionally within signal_yyyymm and map
     ranks into [-1, 1]:  ranked_x = 2 * (rank(x) - 1) / (N - 1) - 1
  7. If a characteristic is entirely unavailable in a month, set the ranked
     value to 0 (the neutral midpoint).

Step 2 (winsorization) is intentionally NOT repeated here: the input signal
panel is already p1/p99 winsorized by build_all_character_panel.py, so
re-winsorizing would double-clip the tails.

No excess_return column is produced (returns are attached separately downstream).

Usage:
  python Character_Panels/build_research_panel_1957_ranked.py \
      --panel outputs/panels/all_character_signal_panel_after_major_change_1.csv \
      --output outputs/panels/research_panel_1957_ranked.csv
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

# ---------------------------------------------------------------------------
# Path setup: make the repo root importable so we can use the existing
# Imputation/ helpers (FF49 industry-code assignment) without duplicating the
# 236 KB SIC->industry mapping table.
# ---------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from Imputation.industry_codes import add_fama_french_industry_codes  # noqa: E402

# ---------------------------------------------------------------------------
# Defaults
# ---------------------------------------------------------------------------
DEFAULT_PANEL = PROJECT_ROOT / "outputs" / "panels" / "all_character_signal_panel_after_major_change_1.csv"
DEFAULT_OUTPUT = PROJECT_ROOT / "outputs" / "panels" / "research_panel_1957_ranked.csv"

# Earliest target month kept in the research panel (January 1957).
# Equivalently the earliest signal month is December 1956 (195612).
TARGET_MONTH_START = 195701

# Identifier / metadata columns carried through to the output. Everything else
# in the input panel is treated as a predictor characteristic.
ID_COLUMNS = ["permno", "signal_yyyymm", "target_yyyymm", "sic"]

# Columns that exist in the input but are NOT predictors (dropped before ranking).
NON_PREDICTOR_COLUMNS = {"sic2"}


# ---------------------------------------------------------------------------
# Step 1: load + filter to 1957+
# ---------------------------------------------------------------------------
def load_and_filter(panel_path: Path) -> pd.DataFrame:
    """Read the signal panel and keep only rows whose target month is >= 1957-01.

    The signal panel is keyed on (permno, signal_yyyymm, target_yyyymm). A row
    with target_yyyymm = 195701 uses predictors known by end of 195612 to
    predict the January 1957 return, which is the first month GKX keep.
    """
    df = pd.read_csv(panel_path)
    df = df[df["target_yyyymm"] >= TARGET_MONTH_START].copy()
    return df


# ---------------------------------------------------------------------------
# Step 4 + 5: impute missing characteristics
# ---------------------------------------------------------------------------
def impute_characteristics(
    df: pd.DataFrame,
    predictors: list[str],
    time_col: str = "signal_yyyymm",
    industry_col: str = "ffi49",
) -> pd.DataFrame:
    """Fill missing predictor values with industry-month medians, then month medians.

    For each characteristic and each missing cell:

      PRIMARY (step 4): take the median of that characteristic over all stocks
      that share the SAME (signal month, FF49 industry). This is a tight,
      industry-specific level -- e.g. the median book-to-market of all banks
      in March 1990.

      FALLBACK (step 5): if that industry-month median is itself missing, use
      the median of the characteristic over ALL stocks in that signal month
      (every industry pooled together). This is the "same signal-month
      cross-sectional median".

    Why a fallback is needed: an (industry, month) cell can have NO non-missing
    value for a characteristic -- rare industries, very early months, or a
    characteristic that simply is not reported by any firm in that industry that
    month. In that case the industry median is NaN, so filling with it would
    leave the cell still missing. The fallback broadens the pool to the whole
    month so the cell still gets a sensible value (as long as ANY firm in the
    month reports the characteristic).

    Cells that remain missing after BOTH passes (the characteristic is entirely
    absent in that month) are left NaN here and handled in the ranking step,
    where they become the neutral rank 0.
    """
    out = df.copy()
    # Primary: median within (signal month, FF49 industry) for ALL predictors at once.
    # One groupby covers every characteristic instead of one pass per column.
    industry_month_median = out.groupby([time_col, industry_col], dropna=False)[predictors].transform("median")
    # Fallback: median within the whole signal month (all industries pooled) for ALL predictors.
    month_median = out.groupby(time_col, dropna=False)[predictors].transform("median")
    # Chain fillna: try industry-month first, then month, leave the rest NaN.
    out[predictors] = out[predictors].fillna(industry_month_median).fillna(month_median)
    return out


# ---------------------------------------------------------------------------
# Step 6 + 7: cross-sectional ranking into [-1, 1]
# ---------------------------------------------------------------------------
def rank_characteristics(
    df: pd.DataFrame,
    predictors: list[str],
    time_col: str = "signal_yyyymm",
) -> pd.DataFrame:
    """Map each characteristic to cross-sectional ranks in [-1, 1] per signal month.

    Formula (GKX):  ranked_x = 2 * (rank(x) - 1) / (N - 1) - 1
      - rank: average rank of the value within its signal month (ties share the
        average rank).
      - N: number of non-missing observations for that characteristic in the
        signal month (after imputation).

    Edge cases:
      - N == 1: denominator is 0; the single observation is mapped to 0
        (neutral) rather than producing a division-by-zero.
      - Value still NaN after imputation (characteristic entirely missing in
        the month): rank is NaN, mapped to 0 (neutral midpoint, step 7).
    """
    out = df.copy()
    # One groupby for all predictors: average ranks within each signal month.
    grouped = out.groupby(time_col, dropna=False)[predictors]
    ranks = grouped.rank(method="average")          # NaN where value missing
    # Non-NaN count per month, per characteristic.
    n = grouped.transform("count")
    with np.errstate(divide="ignore", invalid="ignore"):
        ranked = 2.0 * (ranks - 1.0) / (n - 1.0) - 1.0
    # Months with a single observation (N == 1) -> neutral 0.
    ranked = ranked.where(n > 1, 0.0)
    # Any remaining NaN (value missing, characteristic absent in month) -> 0.
    out[predictors] = ranked.fillna(0.0)
    return out


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------
def build_research_panel(panel_path: Path, output_path: Path) -> None:
    """Run the full load -> impute -> rank -> write sequence."""
    # Step 1: load and restrict to 1957+.
    df = load_and_filter(panel_path)
    print(f"Loaded {len(df):,} rows (target_yyyymm >= {TARGET_MONTH_START}) from")
    print(f"  {panel_path}")

    # Drop non-predictor helper columns (e.g. sic2) before identifying predictors.
    df = df.drop(columns=[c for c in NON_PREDICTOR_COLUMNS if c in df.columns])

    # Predictors = every column that is not an identifier.
    predictors = [c for c in df.columns if c not in ID_COLUMNS]
    print(f"Predictor characteristics: {len(predictors)}")

    # Step 3 (FF49 assignment, needed for industry imputation): add ffi49 from sic.
    df = add_fama_french_industry_codes(df, sic_col="sic", schemes=(49,))
    print("Assigned FF49 industry codes from SIC.")

    # Steps 4 + 5: impute missing values.
    df = impute_characteristics(df, predictors)
    print("Imputed missing values (FF49 industry-month median, then month median fallback).")

    # Steps 6 + 7: cross-sectional ranking into [-1, 1].
    df = rank_characteristics(df, predictors)
    print("Ranked characteristics into [-1, 1] within each signal month.")

    # Final column order: identifiers + ffi49 + ranked predictors.
    ordered = ID_COLUMNS + ["ffi49"] + predictors
    df = df[ordered]

    # Write output. Ranked values are floats in [-1, 1]; writing them at full
    # float64 precision balloons the file to multiple GB, so format to 4
    # decimals (20,001 distinct levels -- plenty for cross-sectional ranking).
    output_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output_path, index=False, float_format="%.4f")
    print(f"\nSaved research panel to: {output_path.resolve()}")
    print(f"Rows: {len(df):,}  Predictors: {len(predictors)}")
    print(f"Target months: {int(df['target_yyyymm'].min())}-{int(df['target_yyyymm'].max())}")
    print(f"Unique permnos: {df['permno'].nunique():,}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Build the cross-sectionally ranked research panel (1957+) from the signal panel."
    )
    parser.add_argument("--panel", type=Path, default=DEFAULT_PANEL, help="Input winsorized signal panel CSV.")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT, help="Output ranked research panel CSV.")
    args = parser.parse_args()

    if not args.panel.exists():
        raise FileNotFoundError(f"Input panel not found: {args.panel}")

    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

    build_research_panel(args.panel, args.output)


if __name__ == "__main__":
    main()
