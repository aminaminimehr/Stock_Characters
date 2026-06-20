#!/usr/bin/env python3
"""Rebuild characters affected by Green formula/timing alignment fixes."""
from __future__ import annotations

import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "Character_Builders"))

from output_paths import CHARACTER_INDIVIDUAL_DIR, ensure_output_tree  # noqa: E402
from _shared.beta_builder import build_beta_character, build_betasq_character  # noqa: E402
from _shared.event_builders import build_abr_character  # noqa: E402
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
from _shared.quarterly_builders import (  # noqa: E402
    QUARTERLY_CHARACTER_INFO,
    build_quarterly_character,
    prepare_quarterly_compustat_panel,
)

ANNUAL_ID_COLUMNS = ["permno", "permco", "gvkey", "datadate", "sic", "fyear"]


def main() -> None:
    for key in ("STOCK_CHARACTERS_SAMPLE_START", "STOCK_CHARACTERS_SAMPLE_END"):
        os.environ.pop(key, None)

    ensure_output_tree()
    wrds_user = os.environ.get("WRDS_USERNAME")
    db = connect_wrds(wrds_user)
    try:
        print("Rebuilding annual characters...", flush=True)
        comp = compute_annual_characters(
            load_annual_compustat(db),
            age_lookup=load_annual_age_lookup(db),
            orgcap_lookup=load_annual_orgcap_lookup(db),
        )
        comp = attach_permno(comp, load_ccm_links(db))
        annual_targets = [c for c in ANNUAL_CHARACTER_INFO if c not in {"cash"}]
        for character in annual_targets:
            write_character(comp[ANNUAL_ID_COLUMNS + [character]], character, CHARACTER_INDIVIDUAL_DIR)

        print("Rebuilding quarterly characters...", flush=True)
        quarterly_comp = prepare_quarterly_compustat_panel(db, use_ibes=False)
        for character in QUARTERLY_CHARACTER_INFO:
            out = build_quarterly_character(db, character, comp=quarterly_comp, use_ibes=False)
            path = CHARACTER_INDIVIDUAL_DIR / f"{character}.csv"
            out.to_csv(path, index=False)
            print(f"{character}: {len(out):,} rows -> {path}")

        print("Rebuilding abr (EAR)...", flush=True)
        build_abr_character(db).to_csv(CHARACTER_INDIVIDUAL_DIR / "abr.csv", index=False)

        print("Rebuilding beta / betasq...", flush=True)
        build_beta_character(db).to_csv(CHARACTER_INDIVIDUAL_DIR / "beta.csv", index=False)
        build_betasq_character(db).to_csv(CHARACTER_INDIVIDUAL_DIR / "betasq.csv", index=False)
    finally:
        db.close()
    print("Done.", flush=True)


if __name__ == "__main__":
    main()
