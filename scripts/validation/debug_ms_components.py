#!/usr/bin/env python3
"""Print m1-m8 components for sample permno-months vs Green ms."""
from __future__ import annotations

import os
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "Character_Builders"))
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts" / "validation"))

from Character_Panels.timing import expand_annual_file_green  # noqa: E402
from green_sas_io import read_green_sas  # noqa: E402
from _shared.green_builders import (  # noqa: E402
    attach_permno,
    compute_annual_characters,
    connect_wrds,
    load_annual_age_lookup,
    load_annual_compustat,
    load_annual_orgcap_lookup,
    load_crsp_monthly,
    load_green_ccm_links,
)
from _shared.quarterly_builders import (  # noqa: E402
    expand_quarterly_columns_to_monthly,
    prepare_quarterly_compustat_panel,
)

M_COLUMNS = [f"m{i}" for i in range(1, 9)]
PERMNOS = [10001, 10006, 10104]
MONTHS = [201001, 201002, 201003]


def main() -> None:
    db = connect_wrds(os.environ.get("WRDS_USERNAME"))
    comp = compute_annual_characters(
        load_annual_compustat(db),
        age_lookup=load_annual_age_lookup(db),
        orgcap_lookup=load_annual_orgcap_lookup(db),
    )
    comp = attach_permno(comp, load_green_ccm_links(db))
    monthly = load_crsp_monthly(db)[["permno", "signal_yyyymm", "date"]].drop_duplicates()
    annual = comp[comp["permno"].notna()][
        ["permno", "permco", "gvkey", "datadate", "sic", "fyear"] + M_COLUMNS[:6]
    ]
    annual = expand_annual_file_green(annual, M_COLUMNS[:6], crsp_month_index=monthly)
    quarterly = prepare_quarterly_compustat_panel(db, use_ibes=False)
    qm = expand_quarterly_columns_to_monthly(
        db, quarterly, ["m7", "m8"], require_rdq=False, require_values=False
    )
    crsp_dates = load_crsp_monthly(db)[["permno", "signal_yyyymm", "date"]].drop_duplicates()
    db.close()

    g = read_green_sas(
        ROOT / "Supplementary_assistive_files" / "Output_From_Greens_SAS_code.sas7bdat",
        ["permno", "DATE", "ms"],
    )

    for permno in PERMNOS:
        for month in MONTHS:
            a = annual[(annual["permno"] == permno) & (annual["signal_yyyymm"] == month)]
            q = qm[(qm["permno"] == permno) & (qm["signal_yyyymm"] == month)]
            gv = g[(g["permno"] == permno) & (g["month"] == month)]
            print(f"\npermno={permno} month={month} green_ms={gv['ms'].tolist()}")
            if not a.empty:
                print(" annual m1-m6:", a[M_COLUMNS[:6]].iloc[0].tolist())
            else:
                print(" annual: MISSING")
            if not q.empty:
                print(" quarterly m7-m8:", q[["m7", "m8"]].iloc[0].tolist())
            else:
                print(" quarterly: MISSING")


if __name__ == "__main__":
    main()
