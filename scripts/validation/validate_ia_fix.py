"""Validate that the peer-universe industry-mean fix improves chpmia / pchcapx_ia / ms.

Builds annual characters fresh from WRDS (fiscal years 2007-2012 only via SQL date
filter), then compares against Green SAS output and datashare.csv for 2010-2015.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "Character_Builders"))
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts" / "validation"))

from green_sas_io import read_green_sas  # noqa: E402
from _shared.green_builders import (  # noqa: E402
    attach_permno,
    compute_annual_characters,
    load_annual_age_lookup,
    load_annual_compustat,
    load_annual_orgcap_lookup,
    load_green_ccm_links,
    connect_wrds,
)
from Character_Panels.timing import expand_annual_file_green  # noqa: E402

GREEN_SAS = ROOT / "Supplementary_assistive_files" / "Output_From_Greens_SAS_code.sas7bdat"
DATASHARE = ROOT / "Supplementary_assistive_files" / "datashare.csv"

WIN = (201001, 201512)
CHARS = ["chpmia", "pchcapx_ia", "chatoia", "bm_ia"]


def rho(a: pd.Series, b: pd.Series) -> float:
    m = a.notna() & b.notna()
    return float(a[m].corr(b[m], method="spearman")) if m.sum() > 50 else float("nan")


def load_green(chars: list[str]) -> pd.DataFrame:
    cols = ["permno", "DATE"] + chars
    cols_avail = [c for c in cols if c in _green_cols()]
    g = read_green_sas(GREEN_SAS, cols_avail)
    g = g[g["month"].between(*WIN)].copy()
    g["permno"] = pd.to_numeric(g["permno"], errors="coerce").astype("Int64")
    return g


def _green_cols():
    import pyreadstat
    _, meta = pyreadstat.read_sas7bdat(str(GREEN_SAS), row_limit=1)
    return meta.column_names


def load_datashare(chars: list[str]) -> pd.DataFrame:
    cols = ["permno", "DATE"] + [c for c in chars if c in _ds_cols()]
    d = pd.read_csv(DATASHARE, usecols=lambda c: c in cols)
    d["month"] = d["DATE"] // 100
    d = d[d["month"].between(*WIN)].copy()
    d["permno"] = pd.to_numeric(d["permno"], errors="coerce").astype("Int64")
    return d


def _ds_cols():
    return pd.read_csv(DATASHARE, nrows=0).columns.tolist()


def main() -> None:
    db = connect_wrds(os.environ.get("WRDS_USERNAME"))

    print("Loading CCM links...", flush=True)
    link = load_green_ccm_links(db)
    peer_gvkeys = set(link["gvkey"].dropna().unique())
    print(f"  CCM-linked gvkeys: {len(peer_gvkeys):,}", flush=True)

    print("Loading annual Compustat...", flush=True)
    raw_comp = load_annual_compustat(db)
    all_gvkeys = raw_comp["gvkey"].nunique()
    print(f"  Total Compustat gvkeys: {all_gvkeys:,} -> peer fraction: {len(peer_gvkeys)/all_gvkeys:.1%}", flush=True)

    print("Computing annual characters WITH peer restriction...", flush=True)
    comp_fixed = compute_annual_characters(
        raw_comp,
        age_lookup=load_annual_age_lookup(db),
        orgcap_lookup=load_annual_orgcap_lookup(db),
        peer_gvkeys=peer_gvkeys,
    )
    print("Computing annual characters WITHOUT peer restriction (old behaviour)...", flush=True)
    comp_old = compute_annual_characters(
        raw_comp,
        age_lookup=load_annual_age_lookup(db),
        orgcap_lookup=load_annual_orgcap_lookup(db),
        peer_gvkeys=None,
    )

    for comp_df, label in [(comp_old, "OLD (full Compustat)"), (comp_fixed, "NEW (CCM peer only)")]:
        comp_linked = attach_permno(comp_df, link)
        crsp_idx = comp_linked[["permno", "fyear"]].dropna().drop_duplicates()
        # build a minimal monthly index from the available signal months
        parts = []
        for chunk in pd.read_csv(
            ROOT / "outputs/panels/all_character_signal_panel_for_GKX_comparison.csv",
            usecols=["permno", "signal_yyyymm"],
            chunksize=400_000,
        ):
            chunk = chunk[chunk["signal_yyyymm"].between(*WIN)]
            if len(chunk):
                parts.append(chunk)
        crsp_month_idx = pd.concat(parts).drop_duplicates() if parts else pd.DataFrame()

        annual_for_expand = comp_linked[comp_linked["permno"].notna()][
            ["permno", "permco", "gvkey", "datadate", "sic", "fyear"] + CHARS
        ].copy()
        expanded = expand_annual_file_green(annual_for_expand, CHARS, crsp_month_index=crsp_month_idx)
        expanded["permno"] = pd.to_numeric(expanded["permno"], errors="coerce").astype("Int64")

        print(f"\n{'='*60}")
        print(f"  {label}")
        print(f"  Rows in window: {len(expanded):,}")

        g = load_green([c for c in CHARS if c in _green_cols()])
        d = load_datashare(CHARS)

        for char in CHARS:
            if char not in expanded.columns:
                continue
            # vs Green
            mg = expanded.merge(
                g[["permno", "month", char]].rename(columns={char: "g", "month": "signal_yyyymm"}),
                on=["permno", "signal_yyyymm"], how="inner",
            ).dropna(subset=[char, "g"])
            r_g = rho(mg[char], mg["g"])
            # vs datashare
            if char in d.columns:
                md = expanded.merge(
                    d[["permno", "month", char]].rename(columns={char: "ds", "month": "signal_yyyymm"}),
                    on=["permno", "signal_yyyymm"], how="inner",
                ).dropna(subset=[char, "ds"])
                r_d = rho(md[char], md["ds"])
            else:
                r_d = float("nan")
            print(f"  {char:15s}: vs Green rho={r_g:.3f}  vs datashare rho={r_d:.3f}  n={len(mg):,}")

    db.close()


if __name__ == "__main__":
    main()
