#!/usr/bin/env python3
"""Rebuild Green annual character CSVs from full Compustat history."""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "Character_Builders"))

from output_paths import CHARACTER_INDIVIDUAL_DIR, ensure_output_tree  # noqa: E402
from _shared.green_builders import (  # noqa: E402
    ANNUAL_CHARACTER_INFO,
    attach_permno,
    compute_annual_characters,
    connect_wrds,
    load_annual_age_lookup,
    load_annual_orgcap_lookup,
    load_annual_compustat,
    load_ccm_links,
    write_character,
)

ANNUAL_ID_COLUMNS = ["permno", "permco", "gvkey", "datadate", "sic", "fyear"]
DEFAULT_TARGETS = [
    "age",
    "absacc",
    "invest",
    "cfp_ia",
    "cashpr",
    "egr",
    "orgcap",
]


def late_start_annual_stems(individual_dir: Path, cutoff: str = "2018-01-01") -> list[str]:
    """Annual characters whose on-disk CSV fiscal dates begin at or after cutoff."""
    late: list[str] = []
    for character in sorted(ANNUAL_CHARACTER_INFO):
        path = individual_dir / f"{character}.csv"
        if not path.exists():
            late.append(character)
            continue
        dates = pd.read_csv(path, usecols=["datadate"])
        if str(dates["datadate"].min()) >= cutoff:
            late.append(character)
    return late


def main(targets: list[str] | None = None) -> None:
    for key in ("STOCK_CHARACTERS_SAMPLE_START", "STOCK_CHARACTERS_SAMPLE_END"):
        os.environ.pop(key, None)

    targets = targets or DEFAULT_TARGETS
    wrds_user = os.environ.get("WRDS_USERNAME")
    print("WRDS user:", wrds_user)
    print("Sample bounds:", os.environ.get("STOCK_CHARACTERS_SAMPLE_START"), os.environ.get("STOCK_CHARACTERS_SAMPLE_END"))

    ensure_output_tree()
    db = connect_wrds(wrds_user)
    try:
        print("Loading full annual Compustat...", flush=True)
        comp = load_annual_compustat(db)
        print(f"Annual panel rows: {len(comp):,}", flush=True)
        print(f"Annual datadate range: {comp['datadate'].min()} .. {comp['datadate'].max()}", flush=True)
        print("Computing annual characters...", flush=True)
        comp = compute_annual_characters(
            comp,
            age_lookup=load_annual_age_lookup(db),
            orgcap_lookup=load_annual_orgcap_lookup(db),
        )
        print("Attaching permno...", flush=True)
        comp = attach_permno(comp, load_ccm_links(db))
        for character in targets:
            write_character(comp[ANNUAL_ID_COLUMNS + [character]], character, CHARACTER_INDIVIDUAL_DIR)
    finally:
        db.close()
    print("Done rebuilding targets.", flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--all-late",
        action="store_true",
        help="Rebuild every annual character CSV with fiscal start >= 2018-01-01.",
    )
    parser.add_argument(
        "--all-annual",
        action="store_true",
        help="Rebuild all Green annual characters (72).",
    )
    parser.add_argument("--characters", nargs="+", default=None, help="Explicit character list.")
    args = parser.parse_args()

    if args.all_annual:
        targets = sorted(ANNUAL_CHARACTER_INFO)
    elif args.all_late:
        targets = late_start_annual_stems(CHARACTER_INDIVIDUAL_DIR)
    elif args.characters:
        targets = args.characters
    else:
        targets = None
    main(targets)
