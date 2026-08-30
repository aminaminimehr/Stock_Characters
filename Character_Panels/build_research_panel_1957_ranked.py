#!/usr/bin/env python3
"""Build the cross-sectionally ranked research panel (1957+) with excess returns.

STANDALONE SCRIPT -- not wired into run_full_pipeline.py.
Feed it the winsorized signal panel; it downloads CRSP monthly returns and
the risk-free rate from WRDS, merges next-month excess returns onto the panel,
imputes missing characteristics, ranks every characteristic to [-1, 1], and
writes a prediction-ready panel (features + excess_return target).

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

Excess returns are downloaded fresh from WRDS (CRSP msf + msedelist + FF
monthly factors) and merged onto the ranked panel on (permno, target_yyyymm).
excess_return is a target, never a predictor, so it is added AFTER ranking.
Rows with no matching return (delisted before the target month) are dropped.

Usage (server, WRDS required):
  python -u Character_Panels/build_research_panel_1957_ranked.py \
      --wrds-user <user> \
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
# 236 KB SIC->industry mapping table, and reuse the output_paths WRDS helpers
# plus the _shared connection/retry utilities (fail-fast credentials,
# escalating backoff, single connection, no parallelism).
# ---------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
_BUILDERS_DIR = PROJECT_ROOT / "Character_Builders"
if str(_BUILDERS_DIR) not in sys.path:
    sys.path.insert(0, str(_BUILDERS_DIR))

from output_paths import (  # noqa: E402
    crsp_universe_filter,
    sql_date_filter,
)
from Imputation.industry_codes import add_fama_french_industry_codes  # noqa: E402
from _shared.green_builders import connect_wrds, raw_sql_with_retry  # noqa: E402

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


# ===========================================================================
# Excess returns: download from WRDS and compute (target column)
# ===========================================================================
def load_crsp_monthly_returns(db) -> pd.DataFrame:
    """Pull CRSP monthly returns (msf) joined to msenames for the universe filter.

    Uses the hardcoded CRSP universe (shrcd ALL, exchcd 1/2/3) and sample-date
    bounds from pipeline_config via the output_paths helpers -- no env vars.
    Single SQL query, no chunking, no parallelism.
    """
    crsp = raw_sql_with_retry(
        db,
        f"""
        SELECT m.permno, m.permco, m.date, m.ret, m.retx,
               n.exchcd, n.shrcd
        FROM crsp.msf AS m
        JOIN crsp.msenames AS n
          ON m.permno = n.permno
         AND n.namedt <= m.date
         AND m.date <= COALESCE(n.nameendt, DATE '9999-12-31')
        WHERE {crsp_universe_filter("n")}
          AND {sql_date_filter("date", "m")}
        """,
    )
    crsp["date"] = pd.to_datetime(crsp["date"]) + pd.offsets.MonthEnd(0)
    crsp["ret"] = pd.to_numeric(crsp["ret"], errors="coerce")
    crsp["retx"] = pd.to_numeric(crsp["retx"], errors="coerce")
    return crsp


def load_delisting_returns(db) -> pd.DataFrame:
    """Pull CRSP delisting returns (msedelist). Small table; fetched in full."""
    dlret = raw_sql_with_retry(
        db,
        """
        SELECT permno, dlstdt, dlret, dlstcd
        FROM crsp.msedelist
        WHERE dlstdt IS NOT NULL
        """,
    )
    dlret["date"] = pd.to_datetime(dlret["dlstdt"]) + pd.offsets.MonthEnd(0)
    dlret["dlret"] = pd.to_numeric(dlret["dlret"], errors="coerce")
    return dlret[["permno", "date", "dlret", "dlstcd"]]


def load_risk_free_rate(db) -> pd.DataFrame:
    """Pull the monthly risk-free rate from the Fama-French factors table.

    WRDS factor tables are commonly stored in percent units; auto-convert to
    decimal when the median magnitude indicates percentages (> 0.02).
    """
    factors = raw_sql_with_retry(
        db,
        """
        SELECT date, rf
        FROM ff.factors_monthly
        """,
    )
    factors["date"] = pd.to_datetime(factors["date"]) + pd.offsets.MonthEnd(0)
    factors["rf"] = pd.to_numeric(factors["rf"], errors="coerce")
    median_abs_rf = factors["rf"].abs().median()
    if pd.notna(median_abs_rf) and median_abs_rf > 0.02:
        factors["rf"] = factors["rf"] / 100
    return factors


def apply_green_delisting_fill(returns: pd.DataFrame) -> pd.DataFrame:
    """Always apply the Green-style distress-delisting return fill.

    This runs unconditionally whenever excess returns are computed -- it is not
    a user option. The full logic, commented step by step:

    1. Identify "distress" delistings. CRSP delisting codes (dlstcd) in the
       range 500-584 mark performance-related / involuntary delistings (e.g.
       liquidations, bankruptcies, dropped listings). Codes 501-504 are
       *non*-distress exits (mergers, exchanges, sold/acquired) that typically
       carry a known, fair-value delisting return, so they are EXCLUDED from
       the fill. We keep only the distress subset:
           distress = dlstcd in [500,584] and dlstcd not in {501,502,503,504}

    2. Among those distress rows, find the ones whose delisting return (dlret)
       is MISSING. CRSP frequently leaves dlret blank for distress delistings
       even though the stock typically realized a large negative return, so a
       raw NaN here would silently drop a big loss and bias the panel upward.
           missing_distress = dlret is NaN AND distress

    3. Fill the missing distress delisting returns by exchange, because the
       expected distress return differs by listing venue (per the Green SAS
       code, which uses historical delisting-return assumptions):
           - NYSE / AMEX  (exchcd in {1, 2}) -> fill -0.35  (-35%)
           - NASDAQ        (exchcd == 3)    -> fill -0.55  (-55%)
       These are conservative large-magnitude fills so a delisting is never
       silently treated as a 0% month. Rows that already have a dlret, and all
       non-distress rows, are left untouched.

    The result feeds into retadj = (1 + ret) * (1 + dlret) - 1 downstream, so a
    filled -35% / -55% becomes part of the compounded monthly return used for
    the excess-return target.
    """
    # Step 1: distress delistings = codes 500-584 excluding the non-distress 501-504.
    distress_codes = (
        returns["dlstcd"].between(500, 584)
        & ~returns["dlstcd"].isin([501, 502, 503, 504])
    )
    # Step 2: distress rows whose delisting return is missing.
    missing_distress_dlret = returns["dlret"].isna() & distress_codes
    # Step 3: fill by exchange venue -- NYSE/AMEX -35%, NASDAQ -55%.
    nyse_amex = missing_distress_dlret & returns["exchcd"].isin([1, 2])
    nasdaq = missing_distress_dlret & returns["exchcd"].eq(3)
    returns.loc[nyse_amex, "dlret"] = -0.35
    returns.loc[nasdaq, "dlret"] = -0.55
    return returns


def build_excess_returns(
    crsp: pd.DataFrame,
    dlret: pd.DataFrame,
    rf: pd.DataFrame,
) -> pd.DataFrame:
    """Merge returns + delisting returns + rf, then compute monthly excess return.

    The Green-style distress-delisting fill is ALWAYS applied here (not an
    option): missing delisting returns for distress delistings are filled
    before compounding, so a delisting loss is never silently dropped.

    retadj compounds the regular monthly return with the delisting return:
        retadj = (1 + ret) * (1 + dlret) - 1
    where missing ret/dlret are treated as 0 for the compound (a month with no
    regular return but a delisting return still gets the delisting performance).
    excess_return = retadj - rf, keyed by target_yyyymm (the return month).
    """
    returns = crsp.merge(dlret, on=["permno", "date"], how="left")
    # Always run the distress-delisting fill before compounding.
    returns = apply_green_delisting_fill(returns)

    returns["ret_for_adjustment"] = returns["ret"].fillna(0)
    returns["dlret_for_adjustment"] = returns["dlret"].fillna(0)
    returns["retadj"] = (
        (1 + returns["ret_for_adjustment"]) * (1 + returns["dlret_for_adjustment"]) - 1
    )
    returns.loc[returns["ret"].isna() & returns["dlret"].isna(), "retadj"] = np.nan

    returns = returns.merge(rf, on="date", how="left")
    returns["excess_return"] = returns["retadj"] - returns["rf"]
    returns["target_yyyymm"] = returns["date"].dt.year * 100 + returns["date"].dt.month

    returns = returns[
        returns["excess_return"].replace([np.inf, -np.inf], np.nan).notna()
    ].copy()

    return returns[["permno", "date", "target_yyyymm", "excess_return"]].sort_values(
        ["permno", "target_yyyymm"]
    )


def download_excess_returns(wrds_user: str) -> pd.DataFrame:
    """Open a single WRDS connection, pull the three return tables, compute excess return.

    The distress-delisting fill always runs inside build_excess_returns.
    """
    db = connect_wrds(wrds_user)
    try:
        print("Downloading CRSP monthly returns (msf)...", flush=True)
        crsp = load_crsp_monthly_returns(db)
        print(f"  msf rows: {len(crsp):,}", flush=True)
        print("Downloading CRSP delisting returns (msedelist)...", flush=True)
        dlret = load_delisting_returns(db)
        print(f"  msedelist rows: {len(dlret):,}", flush=True)
        print("Downloading Fama-French monthly risk-free rate...", flush=True)
        rf = load_risk_free_rate(db)
        print(f"  factors rows: {len(rf):,}", flush=True)
    finally:
        db.close()
    return build_excess_returns(crsp, dlret, rf)


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------
def build_research_panel(panel_path: Path, output_path: Path, wrds_user: str) -> None:
    """Run the full load -> impute -> rank -> merge returns -> write sequence."""
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

    # Excess returns: download from WRDS and merge onto the ranked panel.
    # excess_return is a target (never ranked), so it is attached AFTER ranking
    # on (permno, target_yyyymm). The merge also brings the month-end `date`.
    # The distress-delisting fill always runs as part of the return computation.
    returns = download_excess_returns(wrds_user)
    print(f"Excess returns: {len(returns):,} rows; merging on (permno, target_yyyymm).")
    before = len(df)
    df = df.merge(returns, on=["permno", "target_yyyymm"], how="left")
    # Drop rows with no matching return (delisted before the target month).
    df = df.dropna(subset=["excess_return"]).copy()
    print(f"Rows after return merge: {len(df):,} (dropped {before - len(df):,} with no return).")

    # Final column order: identifiers + date + ffi49 + target + ranked predictors.
    ordered = ["permno", "signal_yyyymm", "target_yyyymm", "date", "sic", "ffi49", "excess_return"] + predictors
    df = df[ordered]

    # Write output. Ranked values are floats in [-1, 1]; writing them at full
    # float64 precision balloons the file to multiple GB, so format to 6
    # decimals (preserves rank distinctions for cross-sections up to ~200k stocks
    # -- far beyond any real monthly count, so no computation is sacrificed).
    output_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output_path, index=False, float_format="%.6f")
    print(f"\nSaved research panel to: {output_path.resolve()}")
    print(f"Rows: {len(df):,}  Predictors: {len(predictors)}")
    print(f"Target months: {int(df['target_yyyymm'].min())}-{int(df['target_yyyymm'].max())}")
    print(f"Unique permnos: {df['permno'].nunique():,}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Build the cross-sectionally ranked research panel (1957+) with excess returns."
    )
    parser.add_argument("--wrds-user", required=True, help="WRDS PostgreSQL username (needed to download returns).")
    parser.add_argument("--panel", type=Path, default=DEFAULT_PANEL, help="Input winsorized signal panel CSV.")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT, help="Output ranked research panel CSV.")
    args = parser.parse_args()

    if not args.panel.exists():
        raise FileNotFoundError(f"Input panel not found: {args.panel}")

    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

    build_research_panel(args.panel, args.output, args.wrds_user)


if __name__ == "__main__":
    main()
