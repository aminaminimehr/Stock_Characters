"""Merge individual character Parquet files into the 95-column datashare signal panel."""
from __future__ import annotations

from pathlib import Path

import pandas as pd
import pyarrow.parquet as pq

from config import DATASHARE_COLUMNS
from paths import NON_CHARACTER_STEMS, SIGNAL_PANEL_FILE, SINGLE_CHARACTERS_DIR
from timing import (
    MONTHLY_KEYS,
    build_crsp_month_index_from_panels,
    expand_annual_file_green,
    expand_annual_file_june,
    expansion_mode,
)
from winsor import apply_green_winsorization

KNOWN_NON_CHARACTER_COLUMNS = {
    "permno", "permco", "gvkey", "date", "DATE", "jdate", "datadate", "source_date",
    "source_yyyymm", "signal_yyyymm", "target_yyyymm", "yyyymm", "sic", "exchcd", "shrcd",
    "fyear", "availability_date", "calendar_year", "lagged_market_equity", "june_date",
    "book_equity_per_share", "split_adjustment", "june_price",
}
NON_CHARACTER_FILES = {f"{stem}.parquet" for stem in NON_CHARACTER_STEMS}


def _parquet_columns(path: Path) -> list[str]:
    return list(pq.read_schema(path).names)


def infer_character_columns(df: pd.DataFrame) -> list[str]:
    return [
        c for c in df.columns
        if c not in KNOWN_NON_CHARACTER_COLUMNS and pd.api.types.is_numeric_dtype(df[c])
    ]


def normalize_character_file(path: Path, crsp_month_index=None):
    df = pd.read_parquet(path)
    character_columns = infer_character_columns(df)
    if not character_columns:
        return None
    stem = Path(path).stem
    mode = expansion_mode(stem, df.columns)
    if mode is None:
        return None
    if mode == "monthly_native":
        keep = MONTHLY_KEYS + [c for c in ["permco", "gvkey", "sic"] if c in df.columns] + character_columns
        return df[keep]
    if mode == "annual_rolling":
        return expand_annual_file_green(df, character_columns, crsp_month_index=crsp_month_index)
    return expand_annual_file_june(df, character_columns)


def coalesce_metadata(panels: list[pd.DataFrame]):
    metadata = None
    for panel in panels:
        meta_cols = [c for c in ["sic"] if c in panel.columns]
        if not meta_cols:
            continue
        one_meta = panel[MONTHLY_KEYS + meta_cols].sort_values(MONTHLY_KEYS).drop_duplicates(MONTHLY_KEYS)
        if metadata is None:
            metadata = one_meta
            continue
        metadata = metadata.merge(one_meta, on=MONTHLY_KEYS, how="outer", suffixes=("", "_new"))
        for column in meta_cols:
            new_column = f"{column}_new"
            if new_column in metadata.columns:
                metadata[column] = metadata[column].combine_first(metadata[new_column])
                metadata = metadata.drop(columns=[new_column])
    return metadata


def merge_panels(panels: list[pd.DataFrame]) -> pd.DataFrame:
    final = None
    for panel in panels:
        value_columns = [c for c in panel.columns if c not in set(MONTHLY_KEYS + ["permco", "gvkey", "sic"])]
        panel = panel[MONTHLY_KEYS + value_columns].drop_duplicates(MONTHLY_KEYS)
        if final is None:
            final = panel
        else:
            dup_cols = [c for c in panel.columns if c in final.columns and c not in MONTHLY_KEYS]
            if dup_cols:
                panel = panel.drop(columns=dup_cols)
            final = final.merge(panel, on=MONTHLY_KEYS, how="outer")
    metadata = coalesce_metadata(panels)
    if metadata is not None:
        final = metadata.merge(final, on=MONTHLY_KEYS, how="right")
    return final


def _load_crsp_month_index(paths: list[Path]) -> pd.DataFrame:
    for stem in ("mvel1",):
        path = SINGLE_CHARACTERS_DIR / f"{stem}.parquet"
        if path.exists():
            return pd.read_parquet(path, columns=["permno", "signal_yyyymm"]).drop_duplicates()
    parts = []
    for path in paths:
        if path.name in NON_CHARACTER_FILES:
            continue
        columns = _parquet_columns(path)
        if set(MONTHLY_KEYS).issubset(columns):
            parts.append(pd.read_parquet(path, columns=["permno", "signal_yyyymm"]))
    return build_crsp_month_index_from_panels(parts)


def build_all_character_panel(input_dir: Path | None = None):
    input_dir = input_dir or SINGLE_CHARACTERS_DIR
    paths = sorted(input_dir.glob("*.parquet"))
    crsp_month_index = _load_crsp_month_index(paths)
    panels, skipped = [], []
    for path in paths:
        if path.name in NON_CHARACTER_FILES or path.stem not in DATASHARE_COLUMNS:
            continue
        panel = normalize_character_file(path, crsp_month_index=crsp_month_index)
        if panel is None:
            skipped.append(path.name)
            continue
        panels.append(panel)
    if not panels:
        raise FileNotFoundError(f"No compatible character Parquet files in {input_dir.resolve()}.")
    panel = merge_panels(panels)
    panel = apply_green_winsorization(panel, month_col="signal_yyyymm")
    return panel, skipped


def write_signal_panel(input_dir: Path | None = None) -> Path:
    panel, skipped = build_all_character_panel(input_dir)
    SIGNAL_PANEL_FILE.parent.mkdir(parents=True, exist_ok=True)
    panel.to_csv(SIGNAL_PANEL_FILE, index=False)
    print(f"Saved panel: {SIGNAL_PANEL_FILE} ({len(panel):,} rows)", flush=True)
    if skipped:
        print("Skipped:", skipped, flush=True)
    return SIGNAL_PANEL_FILE
