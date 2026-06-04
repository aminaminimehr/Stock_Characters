import argparse
import sys
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from output_paths import (  # noqa: E402
    COMPLETE_ALL_PANEL_FILE,
    EXCESS_RETURNS_FILE,
    LEGACY_COMPLETE_PANEL_FILE,
    LEGACY_MONTHLY_PANEL_FILE,
    SIGNAL_PANEL_FILE,
)

MERGE_KEYS = ["permno", "target_yyyymm"]


def require_files(character_panel_file, excess_return_file):
    missing = [
        path
        for path in [Path(character_panel_file), Path(excess_return_file)]
        if not path.exists()
    ]
    if not missing:
        return

    missing_text = "\n".join(f"- {path}" for path in missing)
    raise FileNotFoundError(
        "Missing local input files for the complete prediction panel.\n\n"
        "Run the full pipeline first:\n\n"
        "python Character_Panels/run_full_pipeline.py --wrds-user YOUR_WRDS_USERNAME --skip-ibes\n\n"
        f"Missing files:\n{missing_text}"
    )


def build_complete_prediction_panel(character_panel, excess_returns):
    required_character_columns = {"permno", "signal_yyyymm", "target_yyyymm"}
    required_return_columns = {"permno", "target_yyyymm", "excess_return"}
    if not required_character_columns.issubset(character_panel.columns):
        raise ValueError(
            "The character panel must contain permno, signal_yyyymm, and target_yyyymm."
        )
    if not required_return_columns.issubset(excess_returns.columns):
        raise ValueError(
            "The return file must contain permno, target_yyyymm, and excess_return."
        )

    return_cols = [
        "permno",
        "target_yyyymm",
        "date",
        "ret",
        "dlret",
        "dlstcd",
        "retadj",
        "rf",
        "excess_return",
    ]
    return_cols = [col for col in return_cols if col in excess_returns.columns]
    excess_returns = excess_returns[return_cols].drop_duplicates(MERGE_KEYS)

    return character_panel.merge(excess_returns, on=MERGE_KEYS, how="inner")


def main():
    parser = argparse.ArgumentParser(
        description="Merge signal-month character rows to next-month CRSP excess returns."
    )
    parser.add_argument("--characters", default=str(SIGNAL_PANEL_FILE))
    parser.add_argument("--returns", default=str(EXCESS_RETURNS_FILE))
    parser.add_argument("--output", default=str(COMPLETE_ALL_PANEL_FILE))
    parser.add_argument(
        "--legacy-narrow-panel",
        action="store_true",
        help=(
            "Deprecated: merge the old HXZ-only monthly_character_panel into "
            "panels/legacy/complete_prediction_panel.csv."
        ),
    )
    args = parser.parse_args()

    if args.legacy_narrow_panel:
        character_path = Path(args.characters) if args.characters != str(SIGNAL_PANEL_FILE) else LEGACY_MONTHLY_PANEL_FILE
        return_path = Path(args.returns) if args.returns != str(EXCESS_RETURNS_FILE) else EXCESS_RETURNS_FILE
        output_path = LEGACY_COMPLETE_PANEL_FILE
        print(
            "WARNING: --legacy-narrow-panel builds the deprecated narrow panel. "
            "Use run_full_pipeline.py for the full all-character panel.",
            flush=True,
        )
    else:
        character_path = Path(args.characters)
        return_path = Path(args.returns)
        output_path = Path(args.output)

    if not character_path.is_absolute():
        character_path = PROJECT_ROOT / character_path
    if not return_path.is_absolute():
        return_path = PROJECT_ROOT / return_path
    if not output_path.is_absolute():
        output_path = PROJECT_ROOT / output_path

    require_files(character_path, return_path)

    character_panel = pd.read_csv(character_path)
    excess_returns = pd.read_csv(return_path)
    complete_panel = build_complete_prediction_panel(character_panel, excess_returns)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    complete_panel.to_csv(output_path, index=False)

    print(f"Saved complete prediction panel to: {output_path.resolve()}")
    print(f"Character rows: {len(character_panel):,}")
    print(f"Return rows: {len(excess_returns):,}")
    print(f"Complete rows: {len(complete_panel):,}")
    print("Merged on ['permno', 'target_yyyymm'].")


if __name__ == "__main__":
    main()
