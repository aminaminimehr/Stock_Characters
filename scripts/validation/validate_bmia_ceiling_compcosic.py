#!/usr/bin/env python3
"""WRDS-free bm_ia formula ceiling: datashare sic2 vs panel comp.company.sic.

Holds datashare's own ``bm`` constant and swaps only the industry grouping SIC:
  - baseline: datashare published ``sic2`` (expect median rho ~0.83)
  - test: panel ``sic`` (= comp.company.sic 4-digit, June-expanded; expect ~0.93 if SIC drives jump)

Writes ``outputs/diagnostics/bmia_ceiling_compcosic.csv``.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "Character_Builders"))

from _shared.bm_ia_builder import demean_by_industry_month  # noqa: E402
from output_paths import DIAGNOSTICS_DIR  # noqa: E402

DATASHARE = ROOT / "Supplementary_assistive_files" / "datashare.csv"
DEFAULT_PANEL = ROOT / "outputs" / "panels" / "all_character_signal_panel.csv"
MIN_PAIRS = 50


def monthly_median_spearman(
    df: pd.DataFrame,
    actual: str,
    hat: str,
    month_col: str = "month",
) -> tuple[float, float, int]:
    vals = []
    for _, grp in df.groupby(month_col, sort=True):
        sub = grp[[actual, hat]].dropna()
        if len(sub) < MIN_PAIRS:
            continue
        r = sub[actual].corr(sub[hat], method="spearman")
        if pd.notna(r):
            vals.append(r)
    if not vals:
        return np.nan, np.nan, 0
    return float(np.median(vals)), float(np.mean(vals)), len(vals)


def report_candidate(
    df: pd.DataFrame,
    hat_col: str,
    label: str,
    month_col: str = "month",
) -> dict:
    sub = df.dropna(subset=["bm_ia", hat_col])
    diff = (sub["bm_ia"] - sub[hat_col]).abs()
    med, mean, n_months = monthly_median_spearman(sub, "bm_ia", hat_col, month_col)
    pct_bad = np.nan
    if n_months:
        monthly_rhos = []
        for _, grp in sub.groupby(month_col, sort=True):
            g = grp[["bm_ia", hat_col]].dropna()
            if len(g) < MIN_PAIRS:
                continue
            r = g["bm_ia"].corr(g[hat_col], method="spearman")
            if pd.notna(r):
                monthly_rhos.append(r)
        if monthly_rhos:
            pct_bad = 100 * float(np.mean(np.array(monthly_rhos) < 0.5))
    return {
        "candidate": label,
        "median_monthly_spearman": med,
        "mean_monthly_spearman": mean,
        "pooled_spearman": float(sub["bm_ia"].corr(sub[hat_col], method="spearman"))
        if len(sub) > 1
        else np.nan,
        "exact_rate_pct": 100 * float((diff <= 1e-4).mean()) if len(sub) else np.nan,
        "round4_rate_pct": 100 * float((diff.round(4) == 0).mean()) if len(sub) else np.nan,
        "paired_N": len(sub),
        "unique_permnos": int(sub["permno"].nunique()),
        "spearman_months": n_months,
        "pct_months_rho_below_0_5": pct_bad,
    }


def load_datashare(path: Path) -> pd.DataFrame:
    frames = []
    for chunk in pd.read_csv(
        path,
        usecols=["permno", "DATE", "bm", "bm_ia", "sic2"],
        chunksize=500_000,
    ):
        chunk["permno"] = pd.to_numeric(chunk["permno"], errors="coerce").astype("Int64")
        chunk["month"] = (pd.to_numeric(chunk["DATE"], errors="coerce") // 100).astype("Int64")
        chunk["bm"] = pd.to_numeric(chunk["bm"], errors="coerce")
        chunk["bm_ia"] = pd.to_numeric(chunk["bm_ia"], errors="coerce")
        chunk["sic2"] = pd.to_numeric(chunk["sic2"], errors="coerce")
        frames.append(chunk.drop(columns=["DATE"]))
    return pd.concat(frames, ignore_index=True).dropna(subset=["bm", "bm_ia"])


def load_panel_sic(path: Path) -> pd.DataFrame:
    header = pd.read_csv(path, nrows=0).columns.tolist()
    usecols = ["permno", "signal_yyyymm", "target_yyyymm"]
    if "sic" in header:
        usecols.append("sic")
    elif "sic2" in header:
        usecols.append("sic2")
    else:
        raise ValueError(f"Panel {path} has no sic/sic2 column")

    frames = []
    for chunk in pd.read_csv(path, usecols=usecols, chunksize=500_000, low_memory=False):
        chunk["permno"] = pd.to_numeric(chunk["permno"], errors="coerce").astype("Int64")
        chunk["signal_yyyymm"] = pd.to_numeric(chunk["signal_yyyymm"], errors="coerce").astype("Int64")
        chunk["target_yyyymm"] = pd.to_numeric(chunk["target_yyyymm"], errors="coerce").astype("Int64")
        if "sic" in chunk.columns:
            chunk["panel_sic"] = pd.to_numeric(chunk["sic"], errors="coerce")
        else:
            sic2 = pd.to_numeric(chunk["sic2"], errors="coerce")
            chunk["panel_sic"] = sic2 * 100
        frames.append(chunk[["permno", "signal_yyyymm", "target_yyyymm", "panel_sic"]])
    panel = pd.concat(frames, ignore_index=True)
    panel = panel.dropna(subset=["panel_sic"]).drop_duplicates(
        ["permno", "signal_yyyymm"],
        keep="last",
    )
    return panel


def demean_with_sic(df: pd.DataFrame, sic_col: str, hat_col: str) -> pd.DataFrame:
    work = df.copy()
    work["sic"] = pd.to_numeric(work[sic_col], errors="coerce")
    work = work.dropna(subset=["sic", "bm"])
    return demean_by_industry_month(
        work,
        value_column="bm",
        industry_column="sic",
        industry_digits=2,
        time_column="month",
        stat="mean",
        output_column=hat_col,
    )


def attach_panel_sic(ds: pd.DataFrame, panel: pd.DataFrame, month_col: str) -> pd.DataFrame:
    key = "signal_yyyymm" if month_col == "signal_yyyymm" else "target_yyyymm"
    p = panel.rename(columns={key: "month"})[["permno", "month", "panel_sic"]]
    p = p.drop_duplicates(["permno", "month"])
    p["permno"] = pd.to_numeric(p["permno"], errors="coerce").astype("Int64")
    p["month"] = pd.to_numeric(p["month"], errors="coerce").astype("Int64")
    return ds.merge(p, on=["permno", "month"], how="inner")


def best_alignment_report(
    ds: pd.DataFrame,
    panel: pd.DataFrame,
    sic_col: str,
    label: str,
) -> dict:
    best_row = None
    best_align = None
    for align in ("signal_yyyymm", "target_yyyymm"):
        merged = attach_panel_sic(ds, panel, align)
        demeaned = demean_with_sic(merged, sic_col, "bm_ia_hat")
        row = report_candidate(demeaned, "bm_ia_hat", label)
        row["month_align"] = align
        if best_row is None or (
            pd.notna(row["median_monthly_spearman"])
            and (
                pd.isna(best_row["median_monthly_spearman"])
                or row["median_monthly_spearman"] > best_row["median_monthly_spearman"]
            )
        ):
            best_row = row
            best_align = align
    assert best_row is not None
    best_row["month_align"] = best_align
    return best_row


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--datashare", type=Path, default=DATASHARE)
    parser.add_argument("--panel", type=Path, default=DEFAULT_PANEL)
    args = parser.parse_args()

    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

    if not args.panel.exists():
        raise FileNotFoundError(f"Panel not found: {args.panel}")

    print("Loading datashare bm / bm_ia / sic2...", flush=True)
    ds = load_datashare(args.datashare)

    print(f"Loading panel sic (comp.company.sic, 4-digit): {args.panel}", flush=True)
    panel = load_panel_sic(args.panel)

    rows = []

    print("\nBaseline: demean datashare bm by datashare published sic2...", flush=True)
    ds_pub = ds.dropna(subset=["sic2"]).copy()
    ds_pub["sic_published"] = ds_pub["sic2"].astype(int) * 100
    pub = demean_with_sic(ds_pub, "sic_published", "bm_ia_hat")
    row_pub = report_candidate(pub, "bm_ia_hat", "datashare published sic2 (formula ceiling baseline)")
    row_pub["month_align"] = "DATE//100"
    rows.append(row_pub)
    print(
        f"  median rho={row_pub['median_monthly_spearman']:.4f}  "
        f"pooled={row_pub['pooled_spearman']:.4f}  "
        f"exact={row_pub['exact_rate_pct']:.2f}%  "
        f"paired N={row_pub['paired_N']:,}",
        flush=True,
    )

    print("\nTest: demean datashare bm by panel sic (= comp.company.sic)...", flush=True)
    row_test = best_alignment_report(
        ds,
        panel,
        "panel_sic",
        "panel sic2 / comp.company.sic (June-expanded)",
    )
    rows.append(row_test)
    print(
        f"  align={row_test['month_align']}  median rho={row_test['median_monthly_spearman']:.4f}  "
        f"pooled={row_test['pooled_spearman']:.4f}  "
        f"exact={row_test['exact_rate_pct']:.2f}%  "
        f"paired N={row_test['paired_N']:,}  permnos={row_test['unique_permnos']:,}",
        flush=True,
    )

    res = pd.DataFrame(rows)
    DIAGNOSTICS_DIR.mkdir(parents=True, exist_ok=True)
    out_path = DIAGNOSTICS_DIR / "bmia_ceiling_compcosic.csv"
    res.to_csv(out_path, index=False)

    print("\n=== bm_ia formula ceiling: datashare sic2 vs comp.company.sic ===")
    print(res.to_string(index=False, float_format=lambda v: f"{v:.4f}"))
    print(f"\nWrote {out_path}")


if __name__ == "__main__":
    main()
