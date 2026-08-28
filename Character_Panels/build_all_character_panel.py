"""Merge individual character CSVs into the 95-column datashare signal panel."""
import sys
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "Character_Builders"))

from output_paths import (  # noqa: E402
    CHARACTER_INDIVIDUAL_DIR,
    LEGACY_FLAT_OUTPUT_DIR,
    NON_CHARACTER_STEMS,
    SIGNAL_PANEL_FILE,
    iter_character_csv_paths,
)
from pipeline_config import DATASHARE_COLUMNS  # noqa: E402
from Character_Panels.timing import (  # noqa: E402
    MONTHLY_KEYS,
    build_crsp_month_index_from_panels,
    expand_annual_file_green,
    expand_annual_file_june,
    expansion_mode,
)

KNOWN_NON_CHARACTER_COLUMNS = {
    "permno",
    "permco",
    "gvkey",
    "date",
    "DATE",
    "jdate",
    "datadate",
    "source_date",
    "source_yyyymm",
    "signal_yyyymm",
    "target_yyyymm",
    "yyyymm",
    "sic",
    "exchcd",
    "shrcd",
    "fyear",
    "availability_date",
    "calendar_year",
    "lagged_market_equity",
    "june_date",
    "book_equity_per_share",
    "split_adjustment",
    "june_price",
}

NON_CHARACTER_FILES = {f"{stem}.csv" for stem in NON_CHARACTER_STEMS}


def infer_character_columns(df):
    """Return numeric columns that are not panel metadata."""
    return [
        column
        for column in df.columns
        if column not in KNOWN_NON_CHARACTER_COLUMNS
        and pd.api.types.is_numeric_dtype(df[column])
    ]


def normalize_character_file(path, crsp_month_index=None):
    """Read one character CSV and expand it to a monthly frame if needed."""
    df = pd.read_csv(path)
    character_columns = infer_character_columns(df)
    if not character_columns:
        return None

    stem = Path(path).stem
    mode = expansion_mode(stem, df.columns)
    if mode is None:
        return None

    if mode == "monthly_native":
        keep = MONTHLY_KEYS + [
            column for column in ["permco", "gvkey", "sic"] if column in df.columns
        ] + character_columns
        return df[keep]

    if mode == "annual_rolling":
        return expand_annual_file_green(df, character_columns, crsp_month_index=crsp_month_index)

    return expand_annual_file_june(df, character_columns)


def coalesce_metadata(panels):
    """Merge sic metadata across character panels."""
    metadata = None
    for panel in panels:
        meta_cols = [column for column in ["sic"] if column in panel.columns]
        if not meta_cols:
            continue

        one_meta = (
            panel[MONTHLY_KEYS + meta_cols]
            .sort_values(MONTHLY_KEYS)
            .drop_duplicates(MONTHLY_KEYS)
        )
        if metadata is None:
            metadata = one_meta
            continue

        metadata = metadata.merge(
            one_meta,
            on=MONTHLY_KEYS,
            how="outer",
            suffixes=("", "_new"),
        )
        for column in meta_cols:
            new_column = f"{column}_new"
            if new_column in metadata.columns:
                metadata[column] = metadata[column].combine_first(metadata[new_column])
                metadata = metadata.drop(columns=[new_column])

    return metadata


def merge_panels(panels):
    """Outer-merge normalized character panels on MONTHLY_KEYS."""
    final = None
    for panel in panels:
        value_columns = [
            column
            for column in panel.columns
            if column not in set(MONTHLY_KEYS + ["permco", "gvkey", "sic"])
        ]
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


def _load_monthly_native_panels(paths):
    panels = []
    for path in paths:
        if path.name in NON_CHARACTER_FILES:
            continue
        header = pd.read_csv(path, nrows=0)
        if set(MONTHLY_KEYS).issubset(header.columns):
            panels.append(pd.read_csv(path, usecols=["permno", "signal_yyyymm"]))
    return panels


def _load_crsp_month_index(paths):
    """CRSP month universe for annual rolling expansion."""
    for stem in ("mvel1",):
        path = CHARACTER_INDIVIDUAL_DIR / f"{stem}.csv"
        if path.exists():
            return pd.read_csv(path, usecols=["permno", "signal_yyyymm"]).drop_duplicates()
    monthly_native = _load_monthly_native_panels(paths)
    return build_crsp_month_index_from_panels(monthly_native)


def build_all_character_panel(input_dir=None):
    """Build the 95-column datashare signal panel from individual character CSVs."""
    allowlist = DATASHARE_COLUMNS
    if input_dir is None:
        paths = list(iter_character_csv_paths())
    else:
        input_dir = Path(input_dir)
        paths = sorted(input_dir.glob("*.csv"))
        if input_dir == CHARACTER_INDIVIDUAL_DIR and LEGACY_FLAT_OUTPUT_DIR.exists():
            legacy = {p.name for p in paths}
            for path in sorted(LEGACY_FLAT_OUTPUT_DIR.glob("*.csv")):
                if path.name not in legacy and path.name not in NON_CHARACTER_FILES:
                    paths.append(path)

    crsp_month_index = _load_crsp_month_index(paths)

    panels = []
    skipped = []
    for path in paths:
        if path.name in NON_CHARACTER_FILES:
            continue
        if path.stem not in allowlist:
            continue
        panel = normalize_character_file(path, crsp_month_index=crsp_month_index)
        if panel is None:
            skipped.append(path.name)
            continue
        panels.append(panel)

    if not panels:
        raise FileNotFoundError(
            f"No compatible character CSV files found in {Path(input_dir).resolve()}."
        )

    panel = merge_panels(panels)
    from _shared.green_winsor import apply_green_winsorization

    panel = apply_green_winsorization(panel, month_col="signal_yyyymm")
    print("Applied monthly winsorization (p1/p99 or p99 by variable).")
    return panel, skipped


def main():
    panel, skipped = build_all_character_panel()
    output_path = SIGNAL_PANEL_FILE
    output_path.parent.mkdir(parents=True, exist_ok=True)
    panel.to_csv(output_path, index=False)

    print(f"Saved datashare signal panel to: {output_path.resolve()}")
    print(f"Rows: {len(panel):,}")
    metadata_columns = {"sic"}
    character_count = len(
        [
            column
            for column in panel.columns
            if column not in set(MONTHLY_KEYS) | metadata_columns
        ]
    )
    print(f"Character columns: {character_count:,}")
    if skipped:
        print("Skipped incompatible files:")
        for name in skipped:
            print(f"- {name}")


if __name__ == "__main__":
    main()
