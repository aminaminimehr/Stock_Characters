#!/usr/bin/env python3
"""Diagnostic: rebuild panel bm_ia using FF48 industry averaging, compare vs datashare.

Tests the paper's stated convention (Fama-French 48 industries from 4-digit SIC,
equal-weight mean within (ff48, month)) against the current sic2 builder.

Variants:
  - baseline: demean by sic2 x month (current builder behavior)
  - ff48: demean by ff48 x month (paper convention, from 4-digit SIC)

All local (no WRDS). Read-only on production files.

Outputs under outputs/diagnostics/:
  bm_ia_ff48.csv
  bm_ia_rebuild_ff48_comparison.csv
  bm_ia_rebuild_ff48_summary.txt
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "Character_Builders"))
sys.path.insert(0, str(PROJECT_ROOT / "Imputation"))

from Character_Builders._shared.bm_ia_builder import demean_by_industry_month  # noqa: E402
from Character_Panels.timing import expand_annual_file_june  # noqa: E402
from industry_codes import add_fama_french_industry_code  # noqa: E402

DEFAULT_BM_CSV = PROJECT_ROOT / "outputs" / "characteristics" / "individual" / "book_to_market.csv"
DEFAULT_DATASHARE = PROJECT_ROOT / "Supplementary_assistive_files" / "datashare.csv"
OUT_DIR = PROJECT_ROOT / "outputs" / "diagnostics"

BM_COLUMN = "book_to_market"
MIN_PAIRS = 50
CHUNK_SIZE = 500_000
FF_SCHEME = 48


def load_monthly_from_annual(bm_csv: Path) -> pd.DataFrame:
    annual = pd.read_csv(bm_csv)
    monthly = expand_annual_file_june(annual, [BM_COLUMN])
    monthly = monthly[monthly[BM_COLUMN].notna()].copy()
    monthly["sic2"] = (
        pd.to_numeric(monthly["sic"], errors="coerce") // 100
    ).astype("Int64")
    monthly = add_fama_french_industry_code(
        monthly, scheme=FF_SCHEME, sic_col="sic", output_col="ffi48"
    )
    return monthly


def demean_by_group_month(
    df: pd.DataFrame,
    *,
    value_column: str,
    industry_column: str,
    time_column: str = "signal_yyyymm",
    output_column: str = "bm_ia",
) -> pd.DataFrame:
    out = df.copy()
    grouped = out.groupby([industry_column, time_column], dropna=False)[value_column]
    out[output_column] = out[value_column] - grouped.transform("mean")
    return out


def build_variants(monthly: pd.DataFrame) -> dict[str, pd.DataFrame]:
    variants = {}
    work = monthly.copy()
    work["bm"] = work[BM_COLUMN]

    sic2_build = work.copy()
    sic2_build = demean_by_group_month(
        sic2_build,
        value_column="bm",
        industry_column="sic2",
        output_column="bm_ia",
    )
    variants["sic2"] = sic2_build

    ff48_build = work.copy()
    ff48_build = demean_by_group_month(
        ff48_build,
        value_column="bm",
        industry_column="ffi48",
        output_column="bm_ia",
    )
    variants["ff48"] = ff48_build

    return variants


def load_datashare(datashare_path: Path) -> tuple[pd.DataFrame, int, int]:
    frames = []
    for chunk in pd.read_csv(
        datashare_path,
        usecols=["permno", "DATE", "bm_ia"],
        chunksize=CHUNK_SIZE,
    ):
        chunk["permno"] = pd.to_numeric(chunk["permno"], errors="coerce").astype("Int64")
        chunk["month"] = (pd.to_numeric(chunk["DATE"], errors="coerce") // 100).astype("Int64")
        chunk["bm_ia"] = pd.to_numeric(chunk["bm_ia"], errors="coerce")
        frames.append(chunk.drop(columns=["DATE"]))
    ds = pd.concat(frames, ignore_index=True)
    return ds, int(ds["month"].min()), int(ds["month"].max())


def monthly_spearman_values(df: pd.DataFrame, a: str, b: str) -> list[float]:
    vals = []
    for _, grp in df.groupby("month", sort=True):
        sub = grp[[a, b]].dropna()
        if len(sub) < MIN_PAIRS:
            continue
        r = sub[a].corr(sub[b], method="spearman")
        if pd.notna(r):
            vals.append(float(r))
    return vals


def compare_character(
    panel: pd.DataFrame,
    ds: pd.DataFrame,
    *,
    panel_col: str,
    ds_col: str,
    month_min: int,
    month_max: int,
) -> dict:
    ds_sub = ds[["permno", "month", ds_col]].rename(columns={ds_col: "dv"})
    panel_sub = panel[["permno", "signal_yyyymm", "target_yyyymm", panel_col]].rename(
        columns={panel_col: "pv"}
    )

    best = None
    for month_col in ("signal_yyyymm", "target_yyyymm"):
        ps = panel_sub.rename(columns={month_col: "month"})[["permno", "month", "pv"]]
        ps = ps[ps["month"].between(month_min, month_max)]
        m = ds_sub.merge(ps, on=["permno", "month"], how="inner").dropna(subset=["dv", "pv"])
        n_pair = len(m)
        if n_pair < 2:
            row = {
                "month_align": month_col,
                "paired_obs": 0,
                "pooled_spearman": np.nan,
                "median_monthly_spearman": np.nan,
                "mean_monthly_spearman": np.nan,
                "spearman_months": 0,
                "permno_both": 0,
            }
        else:
            pv = m["pv"].astype("float64")
            dv = m["dv"].astype("float64")
            vals = monthly_spearman_values(m.rename(columns={"pv": "a", "dv": "b"}), "a", "b")
            row = {
                "month_align": month_col,
                "paired_obs": int(n_pair),
                "pooled_spearman": float(pv.corr(dv, method="spearman")),
                "median_monthly_spearman": float(np.median(vals)) if vals else np.nan,
                "mean_monthly_spearman": float(np.mean(vals)) if vals else np.nan,
                "spearman_months": len(vals),
                "permno_both": int(m["permno"].nunique()),
            }
        if best is None or (
            pd.notna(row["median_monthly_spearman"])
            and (
                pd.isna(best["median_monthly_spearman"])
                or row["median_monthly_spearman"] > best["median_monthly_spearman"]
            )
        ):
            best = row
    return best or {}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bm-csv", type=Path, default=DEFAULT_BM_CSV)
    parser.add_argument("--datashare", type=Path, default=DEFAULT_DATASHARE)
    parser.add_argument("--out-dir", type=Path, default=OUT_DIR)
    args = parser.parse_args()

    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

    if not args.bm_csv.exists():
        raise FileNotFoundError(f"book_to_market CSV not found: {args.bm_csv}")
    if not args.datashare.exists():
        raise FileNotFoundError(f"datashare not found: {args.datashare}")

    args.out_dir.mkdir(parents=True, exist_ok=True)

    print("Loading annual book_to_market, June-expanding, mapping FF48...", flush=True)
    monthly = load_monthly_from_annual(args.bm_csv)
    ff48_active = monthly["ffi48"].dropna().nunique()
    print(
        f"  monthly rows={len(monthly):,} permnos={monthly['permno'].nunique():,} "
        f"active ffi48 codes={ff48_active}",
        flush=True,
    )

    print("Loading datashare bm_ia...", flush=True)
    ds, month_min, month_max = load_datashare(args.datashare)
    print(f"  datashare rows={len(ds):,} months={month_min}-{month_max}", flush=True)

    print("Building sic2 and ff48 bm_ia variants...", flush=True)
    variants = build_variants(monthly)

    out_ff48 = args.out_dir / "bm_ia_ff48.csv"
    variants["ff48"][["permno", "signal_yyyymm", "target_yyyymm", "bm_ia", "ffi48", "sic2"]].to_csv(
        out_ff48, index=False
    )

    results = []
    for variant_name, monthly_df in (("sic2", variants["sic2"]), ("ff48", variants["ff48"])):
        stats = compare_character(
            monthly_df,
            ds,
            panel_col="bm_ia",
            ds_col="bm_ia",
            month_min=month_min,
            month_max=month_max,
        )
        label = "sic2 x month (current builder)" if variant_name == "sic2" else "ff48 x month (paper convention)"
        print(
            f"  {label}: median rho={stats.get('median_monthly_spearman', float('nan')):.4f} "
            f"(align={stats.get('month_align')}, paired={stats.get('paired_obs', 0):,})",
            flush=True,
        )
        results.append(
            {
                "variant": variant_name,
                "label": label,
                "month_align": stats.get("month_align"),
                "median_monthly_spearman": stats.get("median_monthly_spearman"),
                "mean_monthly_spearman": stats.get("mean_monthly_spearman"),
                "pooled_spearman": stats.get("pooled_spearman"),
                "paired_obs": stats.get("paired_obs"),
                "permno_both": stats.get("permno_both"),
            }
        )

    res_df = pd.DataFrame(results)
    cmp_csv = args.out_dir / "bm_ia_rebuild_ff48_comparison.csv"
    res_df.to_csv(cmp_csv, index=False)

    sic2_rho = results[0]["median_monthly_spearman"]
    ff48_rho = results[1]["median_monthly_spearman"]
    delta = (ff48_rho or 0.0) - (sic2_rho or 0.0)

    summary_lines = [
        "bm_ia rebuild: FF48 vs SIC2 industry averaging",
        f"Source bm CSV: {args.bm_csv}",
        f"Datashare: {args.datashare}",
        f"Comparison window: {month_min}-{month_max}",
        "",
        "Comparison vs datashare bm_ia (best month alignment):",
        "",
        res_df[
            ["label", "median_monthly_spearman", "mean_monthly_spearman", "pooled_spearman", "paired_obs"]
        ].to_string(index=False),
        "",
        f"sic2 median rho : {sic2_rho:.4f}",
        f"ff48 median rho : {ff48_rho:.4f}",
        f"delta (ff48 - sic2): {delta:+.4f}",
        "",
        "Reference benchmarks:",
        "  panel bm_ia (sic2, full pipeline): ~0.436 median monthly Spearman",
        "  reconstruction ceiling (datashare bm + sic2): ~0.443",
        "",
        f"FF48 bm_ia series written to: {out_ff48.name}",
    ]
    summary_path = args.out_dir / "bm_ia_rebuild_ff48_summary.txt"
    summary_path.write_text("\n".join(summary_lines) + "\n", encoding="utf-8")

    print(f"\nWrote {cmp_csv}")
    print(f"Wrote {summary_path}")
    print(f"Wrote {out_ff48}")
    print("\n" + "\n".join(summary_lines[5:]), flush=True)


if __name__ == "__main__":
    main()
