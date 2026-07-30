#!/usr/bin/env python3
"""Diagnose SIC mismatches between our panel and GKX datashare.csv.

Compares panel ``sic`` / ``sic2`` against datashare ``sic2``, and (optionally)
checks whether panel mismatches align with CRSP ``msenames.siccd`` vs Compustat
``comp.company.sic`` on a WRDS sample.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

DEFAULT_PANEL = ROOT / "outputs" / "panels" / "all_character_signal_panel.csv"
DEFAULT_DATASHARE = ROOT / "Supplementary_assistive_files" / "datashare.csv"
DEFAULT_OUT = ROOT / "outputs" / "diagnostics" / "sic_source_mismatch_report.txt"


def _norm_sic(value) -> str | None:
    if pd.isna(value):
        return None
    try:
        return f"{int(float(value)):04d}"
    except (TypeError, ValueError):
        text = str(value).strip()
        return text if text else None


def _sic2_from_sic(value) -> str | None:
    sic = _norm_sic(value)
    if sic is None:
        return None
    return sic[:2]


def _load_panel_sic(panel_path: Path, month_col: str) -> pd.DataFrame:
    usecols = ["permno", month_col, "sic"]
    header = pd.read_csv(panel_path, nrows=0).columns.tolist()
    if "sic2" in header:
        usecols.append("sic2")
    panel = pd.read_csv(panel_path, usecols=[c for c in usecols if c in header], low_memory=False)
    panel["permno"] = pd.to_numeric(panel["permno"], errors="coerce").astype("Int64")
    panel = panel.rename(columns={month_col: "yyyymm"})
    panel["yyyymm"] = pd.to_numeric(panel["yyyymm"], errors="coerce").astype("Int64")
    panel["sic_norm"] = panel["sic"].map(_norm_sic)
    panel["sic2_panel"] = panel["sic_norm"].map(lambda x: x[:2] if x else None)
    if "sic2" in panel.columns:
        raw_sic2 = panel["sic2"].astype(str).str.strip().str[:2]
        panel.loc[raw_sic2.str.fullmatch(r"\d{2}", na=False), "sic2_panel"] = raw_sic2
    return panel.drop_duplicates(["permno", "yyyymm"])


def _load_datashare_sic(datashare_path: Path) -> pd.DataFrame:
    ds = pd.read_csv(datashare_path, usecols=["permno", "DATE", "sic2"], low_memory=False)
    ds["permno"] = pd.to_numeric(ds["permno"], errors="coerce").astype("Int64")
    ds["yyyymm"] = pd.to_numeric(ds["DATE"], errors="coerce").floordiv(100).astype("Int64")
    ds["sic2_ds"] = ds["sic2"].astype(str).str.strip().str[:2].replace({"nan": np.nan})
    return ds.drop_duplicates(["permno", "yyyymm"])


def _load_char_sic(char_path: Path) -> pd.DataFrame | None:
    if not char_path.exists():
        return None
    cols = pd.read_csv(char_path, nrows=0).columns.tolist()
    if "sic" not in cols:
        return None
    month_col = "signal_yyyymm" if "signal_yyyymm" in cols else None
    if month_col is None:
        return None
    char = pd.read_csv(char_path, usecols=["permno", month_col, "sic"], low_memory=False)
    char["permno"] = pd.to_numeric(char["permno"], errors="coerce").astype("Int64")
    char = char.rename(columns={month_col: "yyyymm"})
    char["yyyymm"] = pd.to_numeric(char["yyyymm"], errors="coerce").astype("Int64")
    char["sic_norm"] = char["sic"].map(_norm_sic)
    return char.drop_duplicates(["permno", "yyyymm"])


def compare_sic2(panel: pd.DataFrame, ds: pd.DataFrame, label: str) -> dict:
    merged = panel.merge(ds, on=["permno", "yyyymm"], how="inner")
    both = merged["sic2_panel"].notna() & merged["sic2_ds"].notna()
    subset = merged.loc[both].copy()
    match = subset["sic2_panel"] == subset["sic2_ds"]
    mismatch = ~match
    return {
        "label": label,
        "paired_rows": len(merged),
        "both_non_null": len(subset),
        "sic2_match": int(match.sum()),
        "sic2_mismatch": int(mismatch.sum()),
        "panel_sic_missing": int(merged["sic2_panel"].isna().sum()),
        "ds_sic_missing": int(merged["sic2_ds"].isna().sum()),
        "mismatch_sample": subset.loc[mismatch, ["permno", "yyyymm", "sic_norm", "sic2_panel", "sic2_ds"]].head(20),
    }


def wrds_source_check(db, sample: pd.DataFrame) -> pd.DataFrame:
    from output_paths import read_wrds_sql

    if sample.empty:
        return sample

    permnos = ",".join(str(int(p)) for p in sample["permno"].dropna().unique()[:500])
    dates = sample["yyyymm"].dropna().astype(int)
    min_date = f"{dates.min() // 100:04d}-{dates.min() % 100:02d}-01"
    max_y, max_m = divmod(int(dates.max()), 100)
    if max_m == 12:
        max_date = f"{max_y:04d}-12-31"
    else:
        max_date = f"{max_y:04d}-{max_m:02d}-28"

    crsp = read_wrds_sql(
        db,
        f"""
        SELECT m.permno, m.date, n.siccd AS sic_crsp
        FROM crsp.msf AS m
        JOIN crsp.msenames AS n
          ON m.permno = n.permno
         AND n.namedt <= m.date
         AND m.date <= COALESCE(n.nameendt, DATE '9999-12-31')
        WHERE m.permno IN ({permnos})
          AND m.date >= DATE '{min_date}'
          AND m.date <= DATE '{max_date}'
        """,
    )
    crsp["date"] = pd.to_datetime(crsp["date"])
    crsp["yyyymm"] = crsp["date"].dt.year * 100 + crsp["date"].dt.month
    crsp["sic_crsp_norm"] = crsp["sic_crsp"].map(_norm_sic)
    crsp = crsp.drop_duplicates(["permno", "yyyymm"], keep="last")

    links = read_wrds_sql(
        db,
        f"""
        SELECT l.lpermno AS permno, l.gvkey
        FROM crsp.ccmxpf_linktable AS l
        WHERE l.lpermno IN ({permnos})
          AND substr(l.linktype, 1, 1) = 'L'
          AND l.linkprim IN ('P', 'C')
        """,
    )
    gvkeys = ",".join(f"'{g}'" for g in links["gvkey"].dropna().unique()[:500])
    comp = read_wrds_sql(
        db,
        f"""
        SELECT c.gvkey, c.sic AS sic_comp
        FROM comp.company AS c
        WHERE c.gvkey IN ({gvkeys})
        """,
    )
    comp["sic_comp_norm"] = comp["sic"].map(_norm_sic)
    perm_gv = links.drop_duplicates("permno")
    out = sample.merge(crsp[["permno", "yyyymm", "sic_crsp_norm"]], on=["permno", "yyyymm"], how="left")
    out = out.merge(perm_gv, on="permno", how="left")
    out = out.merge(comp, on="gvkey", how="left")
    out["panel_matches_crsp"] = out["sic_norm"] == out["sic_crsp_norm"]
    out["panel_matches_comp"] = out["sic_norm"] == out["sic_comp_norm"]
    out["crsp_differs_from_comp"] = out["sic_crsp_norm"] != out["sic_comp_norm"]
    return out


def format_report(results: list[dict], char_compare: dict, wrds_df: pd.DataFrame | None) -> str:
    lines = ["SIC source mismatch diagnostic", "=" * 60, ""]
    for result in results:
        lines.append(f"## {result['label']}")
        lines.append(f"  Paired permno-months:     {result['paired_rows']:,}")
        lines.append(f"  Both sic2 non-null:       {result['both_non_null']:,}")
        lines.append(f"  sic2 match:               {result['sic2_match']:,}")
        lines.append(f"  sic2 mismatch:            {result['sic2_mismatch']:,}")
        if result["both_non_null"]:
            pct = 100.0 * result["sic2_match"] / result["both_non_null"]
            lines.append(f"  sic2 match rate:          {pct:.2f}%")
        lines.append(f"  Panel sic missing:        {result['panel_sic_missing']:,}")
        lines.append(f"  Datashare sic2 missing:   {result['ds_sic_missing']:,}")
        if not result["mismatch_sample"].empty:
            lines.append("  Sample mismatches (first 20):")
            lines.append(result["mismatch_sample"].to_string(index=False))
        lines.append("")

    if char_compare:
        lines.append("## Per-character CSV sic vs panel (monthly-native leak check)")
        for name, info in char_compare.items():
            lines.append(
                f"  {name}: rows={info['rows']:,}, panel_sic_diff={info['diff_vs_panel']:,}, "
                f"annual_sic_diff={info.get('diff_vs_annual', 'n/a')}"
            )
        lines.append("")

    if wrds_df is not None and not wrds_df.empty:
        n = len(wrds_df)
        lines.append("## WRDS source attribution on mismatch sample")
        lines.append(f"  Sample size: {n:,}")
        lines.append(f"  Panel sic matches CRSP siccd:     {int(wrds_df['panel_matches_crsp'].sum()):,}")
        lines.append(f"  Panel sic matches comp.company.sic: {int(wrds_df['panel_matches_comp'].sum()):,}")
        lines.append(f"  CRSP siccd != comp.company.sic:   {int(wrds_df['crsp_differs_from_comp'].sum()):,}")
        lines.append("")

    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="Diagnose SIC mismatches vs datashare.csv")
    parser.add_argument("--panel", type=Path, default=DEFAULT_PANEL)
    parser.add_argument("--datashare", type=Path, default=DEFAULT_DATASHARE)
    parser.add_argument("--month-col", default="signal_yyyymm")
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument(
        "--wrds-check",
        action="store_true",
        help="Pull a WRDS sample to attribute mismatches to CRSP siccd vs comp.company.sic",
    )
    parser.add_argument("--wrds-user", default=None, help="Optional WRDS username")
    parser.add_argument("--wrds-sample", type=int, default=200, help="Mismatch rows to check against WRDS")
    args = parser.parse_args()

    if not args.panel.exists():
        raise FileNotFoundError(f"Panel not found: {args.panel}")
    if not args.datashare.exists():
        raise FileNotFoundError(f"Datashare not found: {args.datashare}")

    panel = _load_panel_sic(args.panel, args.month_col)
    ds = _load_datashare_sic(args.datashare)
    ds_window = ds[(ds["yyyymm"] >= ds["yyyymm"].min()) & (ds["yyyymm"] <= ds["yyyymm"].max())]

    results = [
        compare_sic2(panel, ds, "Full panel vs datashare (sic2)"),
    ]

    indmom_path = ROOT / "outputs" / "characteristics" / "individual" / "indmom.csv"
    if not indmom_path.exists():
        indmom_path = ROOT / "outputs" / "indmom.csv"
    if indmom_path.exists():
        indmom = _load_char_sic(indmom_path)
        if indmom is not None:
            ind_keys = indmom[["permno", "yyyymm"]].drop_duplicates()
            ind_panel = panel.merge(ind_keys, on=["permno", "yyyymm"], how="inner")
            results.append(
                compare_sic2(ind_panel, ds, "indmom-covered permno-months vs datashare"),
            )

    char_compare = {}
    mom_path = ROOT / "outputs" / "characteristics" / "individual" / "mom12m.csv"
    bm_path = ROOT / "outputs" / "characteristics" / "individual" / "bm.csv"
    if not mom_path.exists():
        mom_path = ROOT / "outputs" / "mom12m.csv"
    if not bm_path.exists():
        bm_path = ROOT / "outputs" / "bm.csv"
    mom = _load_char_sic(mom_path)
    bm = _load_char_sic(bm_path)
    if mom is not None:
        joined = panel.merge(mom, on=["permno", "yyyymm"], suffixes=("_panel", "_char"))
        char_compare["mom12m (CRSP-native)"] = {
            "rows": len(joined),
            "diff_vs_panel": int((joined["sic_norm_panel"] != joined["sic_norm_char"]).sum()),
        }
    if bm is not None and mom is not None:
        joined_bm = bm.merge(mom, on=["permno", "yyyymm"], suffixes=("_annual", "_monthly"))
        char_compare["bm vs mom12m sic"] = {
            "rows": len(joined_bm),
            "diff_vs_panel": int((joined_bm["sic_norm_annual"] != joined_bm["sic_norm_monthly"]).sum()),
            "diff_vs_annual": int((joined_bm["sic_norm_annual"] != joined_bm["sic_norm_monthly"]).sum()),
        }

    wrds_df = None
    mismatch_sample = results[0]["mismatch_sample"]
    if args.wrds_check:
        try:
            import wrds

            db = wrds.Connection(wrds_username=args.wrds_user) if args.wrds_user else wrds.Connection()
            try:
                sample = mismatch_sample.head(args.wrds_sample).copy()
                wrds_df = wrds_source_check(db, sample)
            finally:
                db.close()
        except Exception as exc:
            print(f"WRDS source check skipped: {exc}", file=sys.stderr)

    report = format_report(results, char_compare, wrds_df)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(report, encoding="utf-8")
    print(report)
    print(f"\nWrote report to {args.out}")


if __name__ == "__main__":
    main()
