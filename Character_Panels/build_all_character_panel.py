import argparse
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
import sys

sys.path.insert(0, str(PROJECT_ROOT))
from output_paths import (  # noqa: E402
    CHARACTER_INDIVIDUAL_DIR,
    LEGACY_FLAT_OUTPUT_DIR,
    NON_CHARACTER_STEMS,
    SIGNAL_PANEL_FILE,
    iter_character_csv_paths,
)
from Character_Panels.timing import (  # noqa: E402
    MONTHLY_KEYS,
    TimingConvention,
    build_crsp_month_index_from_panels,
    classify_stem,
    expand_annual_file,
    expand_annual_file_june,
    expand_annual_file_green,
)

# Re-export for legacy script imports.
ANNUAL_ID_COLUMNS = [
    "permno",
    "permco",
    "gvkey",
    "datadate",
    "sic",
    "fyear",
]

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

# Green SAS final sample screen (Greens_code.sas L1147-1152):
#   where not missing(mve) and not missing(mom1m) and not missing(bm)
# Because bm = ceq/mve_f, this requires a linked Compustat annual record, so it
# reduces the pure-CRSP spine to Green's CRSP-Compustat-merged universe.
GREEN_UNIVERSE_REQUIRED = ("bm", "mom1m", "mve")
# Repo column aliases for the Green screen variables (mve is exported as mvel1/me).
GREEN_UNIVERSE_ALIASES = {"mve": ("mve", "mvel1", "me")}


def apply_green_universe_screen(panel):
    """Drop rows missing any of bm/mom1m/mve, reproducing Green's final screen.

    Returns (filtered_panel, resolved_columns). Missing screen columns are
    reported so callers can warn instead of silently dropping the screen.
    """
    resolved = []
    missing_required = []
    for name in GREEN_UNIVERSE_REQUIRED:
        candidates = GREEN_UNIVERSE_ALIASES.get(name, (name,))
        found = next((c for c in candidates if c in panel.columns), None)
        if found is None:
            missing_required.append(name)
        else:
            resolved.append(found)
    if missing_required:
        raise KeyError(
            "Cannot apply Green universe screen; panel is missing required "
            f"column(s): {missing_required}. Present resolved: {resolved}."
        )
    return panel.dropna(subset=resolved).reset_index(drop=True), resolved


def infer_character_columns(df):
    return [
        column
        for column in df.columns
        if column not in KNOWN_NON_CHARACTER_COLUMNS
        and pd.api.types.is_numeric_dtype(df[column])
    ]


def normalize_character_file(path, crsp_month_index=None, force_june_annual=False):
    df = pd.read_csv(path)
    character_columns = infer_character_columns(df)
    if not character_columns:
        return None

    stem = Path(path).stem
    convention = classify_stem(stem, df.columns)
    if convention is None:
        return None

    if convention == TimingConvention.MONTHLY_NATIVE:
        keep = MONTHLY_KEYS + [
            column for column in ["permco", "gvkey", "sic"] if column in df.columns
        ] + character_columns
        return df[keep]

    if force_june_annual:
        return expand_annual_file_june(df, character_columns)

    if convention == TimingConvention.GREEN_ANNUAL_ROLLING:
        return expand_annual_file_green(df, character_columns, crsp_month_index=crsp_month_index)

    return expand_annual_file_june(df, character_columns)


def coalesce_metadata(panels):
    metadata = None
    for panel in panels:
        meta_cols = [
            column
            for column in ["sic"]
            if column in panel.columns
        ]
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
            # Drop columns already in final (except join keys) to prevent pandas 3.0
            # MergeError from duplicate non-key columns across files.
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
    """CRSP month universe for Green annual expansion (prefer me.csv)."""
    me_path = CHARACTER_INDIVIDUAL_DIR / "me.csv"
    if me_path.exists():
        return pd.read_csv(me_path, usecols=["permno", "signal_yyyymm"]).drop_duplicates()
    monthly_native = _load_monthly_native_panels(paths)
    return build_crsp_month_index_from_panels(monthly_native)


def build_all_character_panel(input_dir=None, force_june_annual=False, green_universe=False, green_winsor=False):
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
        panel = normalize_character_file(
            path,
            crsp_month_index=crsp_month_index,
            force_june_annual=force_june_annual,
        )
        if panel is None:
            skipped.append(path.name)
            continue
        panels.append(panel)

    if not panels:
        raise FileNotFoundError(
            f"No compatible character CSV files found in {Path(input_dir).resolve()}."
        )

    panel = merge_panels(panels)
    if green_universe:
        before = len(panel)
        panel, resolved = apply_green_universe_screen(panel)
        print(
            f"Green universe screen on {resolved}: {before:,} -> {len(panel):,} rows "
            f"({len(panel) / before:.1%} retained)."
        )
    if green_winsor:
        import sys

        builders_root = PROJECT_ROOT / "Character_Builders"
        if str(builders_root) not in sys.path:
            sys.path.insert(0, str(builders_root))
        from _shared.green_winsor import apply_green_winsorization  # noqa: WPS433

        panel = apply_green_winsorization(panel, month_col="signal_yyyymm")
        print("Applied Green SAS monthly winsorization (p1/p99 or p99 by variable).")
    return panel, skipped


def main():
    parser = argparse.ArgumentParser(
        description="Combine local character CSVs into one signal-month panel."
    )
    parser.add_argument("--input-dir", default=None)
    parser.add_argument("--output", default=str(SIGNAL_PANEL_FILE))
    parser.add_argument(
        "--legacy-june-annual",
        action="store_true",
        help="Force June flat expansion for all annual CSVs (legacy behavior).",
    )
    parser.add_argument(
        "--green-universe",
        action="store_true",
        help=(
            "Apply Green SAS final sample screen (keep rows with non-missing "
            "bm, mom1m, and mve) to match Green's CRSP-Compustat-merged universe."
        ),
    )
    parser.add_argument(
        "--green-winsor",
        action="store_true",
        help=(
            "Apply Green SAS final monthly winsorization (Greens_code.sas L1160-1240) "
            "so continuous predictors match Green/datashare export levels."
        ),
    )
    args = parser.parse_args()

    panel, skipped = build_all_character_panel(
        args.input_dir,
        force_june_annual=args.legacy_june_annual,
        green_universe=args.green_universe,
        green_winsor=args.green_winsor,
    )

    output_path = Path(args.output)
    if not output_path.is_absolute():
        output_path = PROJECT_ROOT / output_path
    output_path.parent.mkdir(parents=True, exist_ok=True)
    panel.to_csv(output_path, index=False)

    print(f"Saved all-character signal panel to: {output_path.resolve()}")
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
