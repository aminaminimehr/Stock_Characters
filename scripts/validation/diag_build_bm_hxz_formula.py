#!/usr/bin/env python3
"""H2 diagnostic: rebuild book_to_market with HXZ seq-only book equity (no fallback).

HXZ accounting_60_hxz.py book equity:

    ps = first nonmissing of pstkrv, pstkl, pstk, else 0
    be = seq + txditc.fillna(0) - ps   # NO ceq+ps / at-lt fallback
    bm = be / December CRSP market equity

Writes ``outputs/diagnostics/book_to_market_hxz_formula.csv``, builds bm_ia from
it, and compares to datashare bm_ia (five metrics). Also writes
``outputs/diagnostics/bmia_hxz_formula_metrics.txt``.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "Character_Builders"))

import pandas as pd
import wrds

from _shared.bm_ia_builder import build_bm_ia_character  # noqa: E402
from _shared.ccm import add_ccm_arguments, attach_ccm_links, load_ccm_links  # noqa: E402
from output_paths import DIAGNOSTICS_DIR, read_wrds_sql, crsp_universe_filter  # noqa: E402

DATASHARE = ROOT / "Supplementary_assistive_files" / "datashare.csv"
BM_OUT = DIAGNOSTICS_DIR / "book_to_market_hxz_formula.csv"
BM_IA_OUT = DIAGNOSTICS_DIR / "bm_ia_hxz_formula.csv"
METRICS_OUT = DIAGNOSTICS_DIR / "bmia_hxz_formula_metrics.txt"
MIN_PAIRS = 50


def load_compustat_hxz(db) -> pd.DataFrame:
    comp = read_wrds_sql(
        db,
        """
        SELECT gvkey, datadate, fyear,
               seq, pstk, pstkl, pstkrv, txditc
        FROM comp.funda
        WHERE indfmt = 'INDL'
          AND datafmt = 'STD'
          AND popsrc = 'D'
          AND consol = 'C'
        """,
    )
    comp["datadate"] = pd.to_datetime(comp["datadate"])

    company = read_wrds_sql(db, "SELECT gvkey, sic FROM comp.company")
    comp = comp.merge(company, on="gvkey", how="left")

    comp["preferred_stock"] = (
        comp["pstkrv"].fillna(comp["pstkl"]).fillna(comp["pstk"]).fillna(0)
    )
    comp["txditc"] = comp["txditc"].fillna(0)
    comp["book_equity"] = comp["seq"] + comp["txditc"] - comp["preferred_stock"]
    comp = comp[comp["book_equity"] > 0].copy()
    comp["book_equity"] = comp["book_equity"] * 1000
    comp["calendar_year"] = comp["datadate"].dt.year

    return (
        comp.sort_values(["gvkey", "calendar_year", "datadate"])
        .drop_duplicates(["gvkey", "calendar_year"], keep="last")
    )


def load_crsp_monthly(db, use_imputed_market_equity: bool) -> pd.DataFrame:
    crsp = read_wrds_sql(
        db,
        f"""
        SELECT m.permno, m.permco, m.date, m.prc, m.shrout,
               n.exchcd, n.shrcd
        FROM crsp.msf AS m
        JOIN crsp.msenames AS n
          ON m.permno = n.permno
         AND n.namedt <= m.date
         AND m.date <= COALESCE(n.nameendt, DATE '9999-12-31')
        WHERE {crsp_universe_filter("n")}
        """,
    )
    crsp["date"] = pd.to_datetime(crsp["date"])
    crsp["year"] = crsp["date"].dt.year
    crsp["month"] = crsp["date"].dt.month
    crsp = crsp.sort_values(["permno", "date"])

    if use_imputed_market_equity:
        crsp[["price_for_me", "shrout_for_me"]] = crsp.groupby("permno")[["prc", "shrout"]].ffill()
    else:
        crsp["price_for_me"] = crsp["prc"]
        crsp["shrout_for_me"] = crsp["shrout"]

    crsp["market_equity"] = crsp["price_for_me"].abs() * crsp["shrout_for_me"]
    return crsp[crsp["market_equity"].notna() & (crsp["market_equity"] > 0)].copy()


def december_firm_market_equity(crsp: pd.DataFrame) -> pd.DataFrame:
    december = crsp[crsp["month"] == 12].copy()
    return (
        december.groupby(["permco", "year"], as_index=False)["market_equity"]
        .sum()
        .rename(columns={"year": "calendar_year"})
    )


def build_book_to_market(comp: pd.DataFrame, crsp_december_me: pd.DataFrame, link: pd.DataFrame) -> pd.DataFrame:
    comp_linked = attach_ccm_links(comp, link)
    bm = comp_linked.merge(crsp_december_me, on=["permco", "calendar_year"], how="inner")
    bm["book_to_market"] = bm["book_equity"] / bm["market_equity"]
    bm = bm[bm["book_to_market"] > 0].copy()
    bm = (
        bm.sort_values(["permno", "datadate", "market_equity"], ascending=[True, True, False])
        .drop_duplicates(["permno", "datadate"], keep="first")
    )
    return bm[["permno", "permco", "gvkey", "datadate", "sic", "fyear", "book_to_market"]]


def monthly_spearman_values(df: pd.DataFrame, a: str, b: str) -> list[float]:
    vals = []
    for _, grp in df.groupby("month", sort=True):
        sub = grp[[a, b]].dropna()
        if len(sub) < MIN_PAIRS:
            continue
        r = sub[a].corr(sub[b], method="spearman")
        if pd.notna(r):
            vals.append(r)
    return vals


def compare_bm_ia(panel_path: Path, datashare_path: Path) -> dict:
    import numpy as np

    panel = pd.read_csv(panel_path)
    panel["permno"] = pd.to_numeric(panel["permno"], errors="coerce").astype("Int64")
    panel["signal_yyyymm"] = pd.to_numeric(panel["signal_yyyymm"], errors="coerce").astype("Int64")
    panel["target_yyyymm"] = pd.to_numeric(panel["target_yyyymm"], errors="coerce").astype("Int64")
    panel["bm_ia"] = pd.to_numeric(panel["bm_ia"], errors="coerce")

    frames = []
    for chunk in pd.read_csv(datashare_path, usecols=["permno", "DATE", "bm_ia"], chunksize=500_000):
        chunk["permno"] = pd.to_numeric(chunk["permno"], errors="coerce").astype("Int64")
        chunk["month"] = (pd.to_numeric(chunk["DATE"], errors="coerce") // 100).astype("Int64")
        chunk["bm_ia"] = pd.to_numeric(chunk["bm_ia"], errors="coerce")
        frames.append(chunk[["permno", "month", "bm_ia"]])
    ds = pd.concat(frames, ignore_index=True)

    best = None
    for month_col in ("signal_yyyymm", "target_yyyymm"):
        ps = panel.rename(columns={month_col: "month"})[["permno", "month", "bm_ia"]]
        m = ds.merge(ps, on=["permno", "month"], how="inner", suffixes=("_ds", "_panel"))
        m = m.dropna(subset=["bm_ia_ds", "bm_ia_panel"])
        if len(m) < 2:
            continue
        vals = monthly_spearman_values(
            m.rename(columns={"bm_ia_panel": "a", "bm_ia_ds": "b"}),
            "a",
            "b",
        )
        row = {
            "month_align": month_col,
            "paired_obs": len(m),
            "pooled_spearman": float(m["bm_ia_panel"].corr(m["bm_ia_ds"], method="spearman")),
            "median_monthly_spearman": float(np.median(vals)) if vals else np.nan,
            "mean_monthly_spearman": float(np.mean(vals)) if vals else np.nan,
            "spearman_months": len(vals),
            "exact_rate": float((m["bm_ia_panel"] - m["bm_ia_ds"]).abs().le(1e-4).mean()),
            "permno_both": int(m["permno"].nunique()),
        }
        if best is None or (
            pd.notna(row["median_monthly_spearman"])
            and (
                pd.isna(best.get("median_monthly_spearman"))
                or row["median_monthly_spearman"] > best["median_monthly_spearman"]
            )
        ):
            best = row
    return best or {}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--wrds-user", default=None)
    parser.add_argument("--datashare", type=Path, default=DATASHARE)
    parser.add_argument("--use-imputed-market-equity", action="store_true")
    add_ccm_arguments(parser)
    parser.add_argument("--skip-wrds", action="store_true", help="Use existing diagnostic CSVs only")
    args = parser.parse_args()

    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

    DIAGNOSTICS_DIR.mkdir(parents=True, exist_ok=True)

    if not args.skip_wrds:
        db = wrds.Connection(wrds_username=args.wrds_user) if args.wrds_user else wrds.Connection()
        try:
            print("Building HXZ seq-only book_to_market from WRDS...", flush=True)
            comp = load_compustat_hxz(db)
            crsp = load_crsp_monthly(db, args.use_imputed_market_equity)
            link = load_ccm_links(db, args.ccm_linktypes, args.ccm_linkprim)
        finally:
            db.close()

        bm = build_book_to_market(comp, december_firm_market_equity(crsp), link)
        bm.to_csv(BM_OUT, index=False)
        print(f"Saved {BM_OUT}  rows={len(bm):,}  permnos={bm['permno'].nunique():,}", flush=True)

        print("Building bm_ia from HXZ-formula book_to_market...", flush=True)
        bm_ia = build_bm_ia_character(BM_OUT)
        bm_ia.to_csv(BM_IA_OUT, index=False)
        print(f"Saved {BM_IA_OUT}  non-null bm_ia={bm_ia['bm_ia'].notna().sum():,}", flush=True)
    else:
        if not BM_IA_OUT.exists():
            raise FileNotFoundError(f"{BM_IA_OUT} missing; run without --skip-wrds")

    print("Comparing bm_ia_hxz_formula vs datashare...", flush=True)
    metrics = compare_bm_ia(BM_IA_OUT, args.datashare)

    lines = [
        "=== H2: full rebuild bm_ia (HXZ seq-only book equity) vs datashare ===",
        f"  month align              : {metrics.get('month_align', 'n/a')}",
        f"  median monthly Spearman  : {metrics.get('median_monthly_spearman', float('nan')):.4f}",
        f"  mean monthly Spearman    : {metrics.get('mean_monthly_spearman', float('nan')):.4f}",
        f"  pooled Spearman          : {metrics.get('pooled_spearman', float('nan')):.4f}",
        f"  exact (|Δ|≤1e-4)         : {100 * metrics.get('exact_rate', 0):.2f}%",
        f"  paired N                 : {metrics.get('paired_obs', 0):,}",
        f"  unique permnos (both)    : {metrics.get('permno_both', 0):,}",
        "",
        "Reference baselines:",
        "  Formula ceiling (datashare bm, published sic2): median rho ~ 0.8357",
        "  Full rebuild (FF fallback bm):                  median rho ~ 0.4182",
    ]
    text = "\n".join(lines)
    METRICS_OUT.write_text(text, encoding="utf-8")
    print(text)
    print(f"\nWrote {METRICS_OUT}")


if __name__ == "__main__":
    main()
