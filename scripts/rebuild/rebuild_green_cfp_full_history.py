#!/usr/bin/env python3
"""Rebuild Green cfp from an earlier Compustat start date into scratch outputs."""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "Character_Builders"))

from Character_Panels.timing import expand_annual_file_green  # noqa: E402
from output_paths import CHARACTER_INDIVIDUAL_DIR, ensure_output_tree  # noqa: E402
from _shared.green_builders import (  # noqa: E402
    attach_permno,
    connect_wrds,
    load_green_ccm_links,
    raw_sql_with_retry,
    safe_divide,
)


DATASHARE = PROJECT_ROOT / "Supplementary_assistive_files" / "datashare.csv"
SCRATCH_DIR = PROJECT_ROOT / "outputs" / "characteristics" / "datashare_style"
DIAG_DIR = PROJECT_ROOT / "outputs" / "diagnostics"
ANNUAL_ID_COLUMNS = ["permno", "permco", "gvkey", "datadate", "sic", "fyear"]


def load_full_history_compustat(db, annual_start: str) -> pd.DataFrame:
    comp = raw_sql_with_retry(
        db,
        f"""
        SELECT c.gvkey, f.datadate, f.fyear, c.sic,
               f.act, f.che, f.lct, f.dlc, f.txp, f.dp,
               f.ib, f.oancf, f.csho, ABS(f.prcc_f) AS prcc_f,
               f.at, f.ni
        FROM comp.company AS c
        JOIN comp.funda AS f
          ON c.gvkey = f.gvkey
        WHERE f.indfmt = 'INDL'
          AND f.datafmt = 'STD'
          AND f.popsrc = 'D'
          AND f.consol = 'C'
          AND f.at IS NOT NULL
          AND f.prcc_f IS NOT NULL
          AND f.ni IS NOT NULL
          AND f.datadate >= DATE '{annual_start}'
        """,
    )
    comp["datadate"] = pd.to_datetime(comp["datadate"])
    return (
        comp.sort_values(["gvkey", "datadate"])
        .drop_duplicates(["gvkey", "datadate"], keep="last")
        .sort_values(["gvkey", "datadate"])
    )


def compute_green_cfp(comp: pd.DataFrame) -> pd.DataFrame:
    comp = comp.copy()
    comp["mve_f"] = comp["prcc_f"] * comp["csho"]
    for col in ["act", "che", "lct", "dlc", "txp"]:
        comp[f"lag_{col}"] = comp.groupby("gvkey", sort=False)[col].shift(1)

    working_capital_accrual = (
        (comp["act"] - comp["lag_act"] - (comp["che"] - comp["lag_che"]))
        - (
            (comp["lct"] - comp["lag_lct"])
            - (comp["dlc"] - comp["lag_dlc"])
            - (comp["txp"] - comp["lag_txp"])
            - comp["dp"]
        )
    )
    comp["cfp"] = safe_divide(comp["ib"] - working_capital_accrual, comp["mve_f"])
    comp.loc[comp["oancf"].notna(), "cfp"] = safe_divide(comp["oancf"], comp["mve_f"])
    comp["cfp"] = comp["cfp"].replace([np.inf, -np.inf], np.nan)
    return comp


def load_datashare_cfp() -> pd.DataFrame:
    frames = []
    for chunk in pd.read_csv(DATASHARE, usecols=["permno", "DATE", "cfp"], chunksize=500_000):
        chunk["permno"] = pd.to_numeric(chunk["permno"], errors="coerce").astype("Int64")
        chunk["month"] = (pd.to_numeric(chunk["DATE"], errors="coerce") // 100).astype("Int64")
        chunk = chunk.drop(columns=["DATE"]).dropna(subset=["permno", "month", "cfp"])
        if len(chunk):
            frames.append(chunk)
    if not frames:
        return pd.DataFrame(columns=["permno", "month", "cfp"])
    return pd.concat(frames, ignore_index=True)


def month_add(month: pd.Series, shift: int) -> pd.Series:
    yy = month // 100
    mm = month % 100 + shift
    while True:
        over = mm > 12
        under = mm < 1
        if not (over.any() or under.any()):
            break
        yy = yy + over.astype(int) - under.astype(int)
        mm = np.where(over, mm - 12, mm)
        mm = np.where(under, mm + 12, mm)
    return (yy * 100 + mm).astype("Int64")


def monthly_spearman(df: pd.DataFrame) -> tuple[float, int]:
    rhos = []
    for _, group in df.groupby("month", sort=True):
        if len(group) < 50:
            continue
        rho = group["built"].corr(group["datashare"], method="spearman")
        if pd.notna(rho):
            rhos.append(rho)
    return (float(np.median(rhos)), len(rhos)) if rhos else (np.nan, 0)


def metrics_for_pair(built: pd.DataFrame, ds: pd.DataFrame, month_col: str, shift: int) -> dict:
    left = built[["permno", month_col, "cfp"]].dropna().rename(
        columns={month_col: "month", "cfp": "built"}
    )
    if shift:
        left["month"] = month_add(left["month"].astype("Int64"), shift)
    right = ds.rename(columns={"cfp": "datashare"})
    merged = left.merge(right, on=["permno", "month"], how="inner").dropna()

    out = {
        "month_source": month_col,
        "shift": shift,
        "paired_obs": len(merged),
        "pre1975_paired_obs": int((merged["month"] < 197501).sum()) if len(merged) else 0,
        "median_monthly_rho": np.nan,
        "months": 0,
        "pooled_rho": np.nan,
        "exact_pct": np.nan,
        "median_abs_diff": np.nan,
        "p95_abs_diff": np.nan,
    }
    if len(merged) < 2:
        return out

    diff = (merged["built"].astype("float64") - merged["datashare"].astype("float64")).abs()
    med, months = monthly_spearman(merged)
    out.update(
        {
            "median_monthly_rho": med,
            "months": months,
            "pooled_rho": float(merged["built"].corr(merged["datashare"], method="spearman")),
            "exact_pct": float((diff <= 1e-4).mean()) * 100,
            "median_abs_diff": float(diff.median()),
            "p95_abs_diff": float(diff.quantile(0.95)),
        }
    )
    return out


def validate(monthly: pd.DataFrame) -> pd.DataFrame:
    ds = load_datashare_cfp()
    rows = []
    for month_col in ["signal_yyyymm", "target_yyyymm"]:
        for shift in [0, 1, -1]:
            rows.append(metrics_for_pair(monthly, ds, month_col, shift))
    return pd.DataFrame(rows).sort_values(["median_monthly_rho", "pooled_rho"], ascending=False)


def format_report(metrics: pd.DataFrame, annual: pd.DataFrame, monthly: pd.DataFrame, annual_start: str) -> str:
    best = metrics.iloc[0].to_dict() if len(metrics) else {}
    pre1975_gain = int(best.get("pre1975_paired_obs", 0))
    lines = [
        "# Green cfp Full-History Scratch Rebuild",
        "",
        f"Annual start: {annual_start}",
        f"Annual rows with nonmissing cfp: {annual['cfp'].notna().sum():,}",
        f"Annual datadate range: {annual['datadate'].min()} .. {annual['datadate'].max()}",
        f"Monthly rows: {len(monthly):,}",
        "",
        "## Best alignment",
        "",
        f"month_source={best.get('month_source')} shift={best.get('shift'):+.0f}",
        f"median monthly rho={best.get('median_monthly_rho', np.nan):.6f}",
        f"pooled rho={best.get('pooled_rho', np.nan):.6f}",
        f"exact <= 1e-4={best.get('exact_pct', np.nan):.2f}%",
        f"paired obs={best.get('paired_obs', 0):,}",
        f"pre-1975 paired obs gained={pre1975_gain:,}",
        "",
        "## All alignments",
        "",
        metrics.to_string(index=False),
        "",
    ]
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--wrds-user", default=os.environ.get("WRDS_USERNAME") or os.environ.get("WRDS_USER"))
    parser.add_argument("--annual-start", default="1959-01-01")
    parser.add_argument("--annual-output", default=str(SCRATCH_DIR / "green_cfp_full_history_annual.csv"))
    parser.add_argument("--monthly-output", default=str(SCRATCH_DIR / "green_cfp_full_history.csv"))
    parser.add_argument("--metrics-output", default=str(DIAG_DIR / "cfp_full_history_metrics.csv"))
    parser.add_argument("--report", default=str(DIAG_DIR / "cfp_full_history_validation.txt"))
    args = parser.parse_args()

    ensure_output_tree()
    SCRATCH_DIR.mkdir(parents=True, exist_ok=True)
    DIAG_DIR.mkdir(parents=True, exist_ok=True)

    db = connect_wrds(args.wrds_user)
    try:
        print(f"Loading Compustat annual rows from {args.annual_start}...", flush=True)
        comp = compute_green_cfp(load_full_history_compustat(db, args.annual_start))
        print("Attaching Green CCM links...", flush=True)
        linked = attach_permno(comp, load_green_ccm_links(db))
    finally:
        db.close()

    annual = linked[ANNUAL_ID_COLUMNS + ["cfp"]].dropna(subset=["cfp"]).copy()
    annual_path = Path(args.annual_output)
    monthly_path = Path(args.monthly_output)
    metrics_path = Path(args.metrics_output)
    report_path = Path(args.report)
    for path in [annual_path, monthly_path, metrics_path, report_path]:
        path.parent.mkdir(parents=True, exist_ok=True)

    annual.to_csv(annual_path, index=False)
    print(f"Wrote annual scratch cfp: {annual_path} ({len(annual):,} rows)", flush=True)

    monthly = expand_annual_file_green(annual, ["cfp"])
    monthly.to_csv(monthly_path, index=False)
    print(f"Wrote monthly scratch cfp: {monthly_path} ({len(monthly):,} rows)", flush=True)

    metrics = validate(monthly)
    metrics.to_csv(metrics_path, index=False)
    report = format_report(metrics, annual, monthly, args.annual_start)
    report_path.write_text(report, encoding="utf-8")
    print(report)

    current_path = CHARACTER_INDIVIDUAL_DIR / "cfp.csv"
    print(f"Current individual cfp left untouched: {current_path}", flush=True)


if __name__ == "__main__":
    main()
