"""Merge category character Parquet files into the final datashare signal panel."""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

PIPELINE_ROOT = Path(__file__).resolve().parents[1]
if str(PIPELINE_ROOT) not in sys.path:
    sys.path.insert(0, str(PIPELINE_ROOT))

from config.conventions import (  # noqa: E402
    CHARACTERS_DIR,
    DATASHARE_PREDICTORS,
    MONTHLY_MERGE_KEYS,
    PANEL_DIR,
)
from config.reference_tables import apply_winsorization, assign_ff49  # noqa: E402

CHARACTER_PANELS = (
    "annual",
    "quarterly",
    "monthly",
    "daily_monthly",
    "beta_family",
    "event",
    "ms",
)

NON_VALUE_COLUMNS = frozenset(
    MONTHLY_MERGE_KEYS
    + ["permco", "gvkey", "date", "exchcd", "shrcd", "sic", "sic2"]
)


#######################################################################################################################
#                                                    Helper functions                                                 #
#######################################################################################################################


def load_character_panel(stem: str) -> pd.DataFrame:
    """Load one category parquet from outputs/characters/."""
    path = CHARACTERS_DIR / f"{stem}.parquet"
    if not path.exists():
        raise FileNotFoundError(f"Missing character panel: {path}")
    print(f"Loading {path.name} ({path.stat().st_size / 1_048_576:.1f} MB)...", flush=True)
    return pd.read_parquet(path)


def character_value_columns(df: pd.DataFrame) -> list[str]:
    """Return predictor columns excluding merge keys and metadata."""
    return [c for c in df.columns if c not in NON_VALUE_COLUMNS]


def coalesce_sic(panels: list[pd.DataFrame]) -> pd.DataFrame | None:
    """Outer-merge sic metadata from all panels onto MONTHLY_MERGE_KEYS."""
    metadata = None
    for panel in panels:
        if "sic" not in panel.columns:
            continue
        one = (
            panel[MONTHLY_MERGE_KEYS + ["sic"]]
            .sort_values(MONTHLY_MERGE_KEYS)
            .drop_duplicates(MONTHLY_MERGE_KEYS, keep="last")
        )
        if metadata is None:
            metadata = one
            continue
        metadata = metadata.merge(one, on=MONTHLY_MERGE_KEYS, how="outer", suffixes=("", "_new"))
        metadata["sic"] = metadata["sic"].combine_first(metadata["sic_new"])
        metadata = metadata.drop(columns=["sic_new"])
    return metadata


def outer_merge_panels(panels: list[pd.DataFrame]) -> pd.DataFrame:
    """Outer-merge all category panels on (permno, signal_yyyymm, target_yyyymm)."""
    final = None
    for panel in panels:
        value_columns = character_value_columns(panel)
        keep = MONTHLY_MERGE_KEYS + value_columns
        one = panel[keep].drop_duplicates(MONTHLY_MERGE_KEYS, keep="last")
        if final is None:
            final = one
            continue
        dup_cols = [c for c in one.columns if c in final.columns and c not in MONTHLY_MERGE_KEYS]
        if dup_cols:
            one = one.drop(columns=dup_cols)
        final = final.merge(one, on=MONTHLY_MERGE_KEYS, how="outer")
    if final is None:
        raise ValueError("No character panels loaded.")
    sic_meta = coalesce_sic(panels)
    if sic_meta is not None:
        final = sic_meta.merge(final, on=MONTHLY_MERGE_KEYS, how="right")
    return final


#######################################################################################################################
#                                              Load and merge character panels                                        #
#######################################################################################################################

print("Merging category character panels...", flush=True)
panels = [load_character_panel(stem) for stem in CHARACTER_PANELS]
panel = outer_merge_panels(panels)
print(f"Merged panel: {len(panel):,} rows x {len(panel.columns)} cols", flush=True)

#######################################################################################################################
#                                                 Winsorize predictors                                                #
#######################################################################################################################

print("Applying Green winsorization by signal_yyyymm...", flush=True)
panel = apply_winsorization(panel, month_col="signal_yyyymm")

#######################################################################################################################
#                                              Attach excess returns + FF49                                           #
#######################################################################################################################

returns_path = PANEL_DIR / "excess_returns.parquet"
if not returns_path.exists():
    raise FileNotFoundError(f"Missing excess returns file: {returns_path}")
print(f"Loading {returns_path.name}...", flush=True)
returns = pd.read_parquet(returns_path, columns=["permno", "target_yyyymm", "excess_return"])
returns = returns.drop_duplicates(["permno", "target_yyyymm"], keep="last")

panel = panel.merge(returns, on=["permno", "target_yyyymm"], how="left")
panel["ffi49"] = assign_ff49(panel["sic"])

#######################################################################################################################
#                                                       Output                                                        #
#######################################################################################################################

predictor_cols = [c for c in DATASHARE_PREDICTORS if c in panel.columns]
missing_predictors = [c for c in DATASHARE_PREDICTORS if c not in panel.columns]
if missing_predictors:
    print(f"Warning: {len(missing_predictors)} predictors absent from merged panel:", flush=True)
    print(", ".join(missing_predictors), flush=True)

out_cols = (
    ["permno", "signal_yyyymm", "target_yyyymm", "sic", "ffi49", "excess_return"]
    + predictor_cols
)
final = panel[out_cols].copy()

PANEL_DIR.mkdir(parents=True, exist_ok=True)
out_path = PANEL_DIR / "final_panel.csv"
final.to_csv(out_path, index=False)
print(
    f"Wrote {len(final):,} rows x {len(out_cols)} cols ({len(predictor_cols)} predictors) -> {out_path}",
    flush=True,
)
