#!/usr/bin/env python3
"""Compare built character CSVs against Supplementary chars60_summary.csv."""
import argparse
import sys
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from output_paths import (  # noqa: E402
    DIAGNOSTICS_DIR,
    ensure_output_tree,
    list_character_stems,
)


def normalize_acronym(value: str) -> str:
    return value.strip().lower().replace(" ", "")


def load_chars60(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    df["acronym_norm"] = df["Acronym"].map(normalize_acronym)
    return df


def main():
    parser = argparse.ArgumentParser(description="Audit built characters vs chars60_summary.csv")
    parser.add_argument(
        "--chars60",
        default=PROJECT_ROOT
        / "Supplementary_assistive_files"
        / "chars60_summary.csv",
    )
    parser.add_argument(
        "--report",
        default=DIAGNOSTICS_DIR / "character_inventory_report.md",
    )
    args = parser.parse_args()

    ensure_output_tree()
    chars60 = load_chars60(Path(args.chars60))
    target = set(chars60["acronym_norm"])
    built = {normalize_acronym(s) for s in list_character_stems()}

    # Project-specific aliases not listed as separate rows in chars60.
    project_extras = {
        "book_to_market",
        "book_to_june_market_equity",
        "operating_profitability",
        "cash_flow_to_price",
        "mvel1",
        "bmj",
    }
    built_extras = sorted(built - target)
    missing = sorted(target - built)
    matched = sorted(target & built)

    lines = [
        "# Character inventory audit",
        "",
        f"- chars60 target count: **{len(target)}**",
        f"- built character CSV count: **{len(built)}**",
        f"- matched chars60 acronyms: **{len(matched)}**",
        f"- missing from chars60: **{len(missing)}**",
        f"- built but not in chars60: **{len(built_extras)}**",
        "",
        "## Built and listed in chars60",
        "",
        ", ".join(matched) if matched else "(none)",
        "",
        "## Missing relative to chars60",
        "",
    ]
    if missing:
        for item in missing:
            row = chars60.loc[chars60["acronym_norm"] == item].iloc[0]
            lines.append(f"- `{item}` — {row['Description']}")
    else:
        lines.append("(none)")

    lines.extend(["", "## Built extras (not separate chars60 rows)", ""])
    if built_extras:
        lines.append(", ".join(built_extras))
    else:
        lines.append("(none)")

    lines.extend(["", "## All built stems", "", ", ".join(sorted(built))])

    report_path = Path(args.report)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(report_path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    main()
