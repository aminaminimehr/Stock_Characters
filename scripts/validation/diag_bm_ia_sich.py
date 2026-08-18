#!/usr/bin/env python3
"""H1 diagnostic: historical Compustat ``sich`` vs ``comp.company.sic`` for bm_ia.

Recomputes bm_ia at the formula ceiling using datashare's own published ``bm``
(isolates SIC grouping from our bm rebuild quality):

    bm_ia_hat = bm - mean(bm) over (two-digit SIC, calendar month)

Three SIC sources are compared against published datashare ``bm_ia``:
  1. published sic2 (datashare column; baseline ~0.84 median rho)
  2. wrds_company_sic  (comp.company.sic, June-expanded to signal months)
  3. wrds_historical_sich (comp.funda.sich, June-expanded to signal months)

Reports the five required metrics per candidate. Writes
``outputs/diagnostics/bmia_sich_comparison.csv``.
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

from Character_Panels.timing import expand_annual_file_june  # noqa: E402
from _shared.bm_ia_builder import demean_by_industry_month  # noqa: E402
from output_paths import (  # noqa: E402
    DIAGNOSTICS_DIR,
    read_wrds_sql,
    sql_date_filter,
)

DATASHARE = ROOT / "Supplementary_assistive_files" / "datashare.csv"
DEFAULT_BM = ROOT / "outputs" / "characteristics" / "individual" / "book_to_market.csv"
SICH_CACHE = DIAGNOSTICS_DIR / "cache" / "funda_sich_gvkey_datadate.csv"
MIN_PAIRS = 50


def monthly_median_spearman(df: pd.DataFrame, actual: str, hat: str) -> tuple[float, float, int]:
    vals = []
    for _, grp in df.groupby("month", sort=True):
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
) -> dict:
    sub = df.dropna(subset=["bm_ia", hat_col])
    diff = (sub["bm_ia"] - sub[hat_col]).abs()
    med, mean, n_months = monthly_median_spearman(sub, "bm_ia", hat_col)
    return {
        "candidate": label,
        "median_monthly_spearman": med,
        "mean_monthly_spearman": mean,
        "pooled_spearman": float(sub["bm_ia"].corr(sub[hat_col], method="spearman")) if len(sub) > 1 else np.nan,
        "exact_rate_pct": 100 * float((diff <= 1e-4).mean()) if len(sub) else np.nan,
        "paired_N": len(sub),
        "unique_permnos": int(sub["permno"].nunique()),
        "spearman_months": n_months,
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
    out = pd.concat(frames, ignore_index=True)
    return out.dropna(subset=["bm", "bm_ia"])


def load_or_fetch_sich(db, bm_annual: pd.DataFrame, *, refresh: bool) -> pd.DataFrame:
    if SICH_CACHE.exists() and not refresh:
        print(f"Loading cached sich: {SICH_CACHE}", flush=True)
        sich = pd.read_csv(SICH_CACHE)
        sich["datadate"] = pd.to_datetime(sich["datadate"])
        return sich

    gvkeys = bm_annual["gvkey"].dropna().astype(str).unique().tolist()
    if not gvkeys:
        raise ValueError("book_to_market.csv has no gvkeys for sich pull")

    print(f"Pulling comp.funda.sich for {len(gvkeys):,} gvkeys from WRDS...", flush=True)
    gvkey_list = ", ".join(f"'{g}'" for g in gvkeys)
    date_clause = sql_date_filter("datadate", "f")
    sich = read_wrds_sql(
        db,
        f"""
        SELECT f.gvkey, f.datadate, f.fyear, f.sich
        FROM comp.funda AS f
        WHERE f.gvkey IN ({gvkey_list})
          AND f.indfmt = 'INDL'
          AND f.datafmt = 'STD'
          AND f.popsrc = 'D'
          AND f.consol = 'C'
          AND {date_clause}
        """,
    )
    sich["datadate"] = pd.to_datetime(sich["datadate"])
    SICH_CACHE.parent.mkdir(parents=True, exist_ok=True)
    sich.to_csv(SICH_CACHE, index=False)
    print(f"Cached sich to {SICH_CACHE}", flush=True)
    return sich


def build_monthly_sic_panel(bm_annual: pd.DataFrame, sich: pd.DataFrame) -> pd.DataFrame:
    annual = bm_annual.copy()
    annual["datadate"] = pd.to_datetime(annual["datadate"])
    annual["gvkey"] = annual["gvkey"].astype(str)

    sich = sich.copy()
    sich["gvkey"] = sich["gvkey"].astype(str)
    sich["datadate"] = pd.to_datetime(sich["datadate"])
    annual = annual.merge(
        sich[["gvkey", "datadate", "sich"]],
        on=["gvkey", "datadate"],
        how="left",
    )
    annual["sic_company"] = pd.to_numeric(annual["sic"], errors="coerce")
    annual["sic_historical"] = pd.to_numeric(annual["sich"], errors="coerce")
    annual.loc[annual["sic_historical"].isna(), "sic_historical"] = annual["sic_company"]

    monthly = expand_annual_file_june(
        annual,
        ["sic_company", "sic_historical"],
    )
    return monthly[
        ["permno", "signal_yyyymm", "target_yyyymm", "sic_company", "sic_historical"]
    ].drop_duplicates(["permno", "signal_yyyymm"])


def attach_wrds_sic(ds: pd.DataFrame, sic_monthly: pd.DataFrame, month_col: str) -> pd.DataFrame:
    """Merge WRDS SIC onto datashare rows using signal or target month key."""
    key = "signal_yyyymm" if month_col == "signal_yyyymm" else "target_yyyymm"
    panel = sic_monthly.rename(columns={key: "month"})
    panel["permno"] = pd.to_numeric(panel["permno"], errors="coerce").astype("Int64")
    panel["month"] = pd.to_numeric(panel["month"], errors="coerce").astype("Int64")
    return ds.merge(
        panel[["permno", "month", "sic_company", "sic_historical"]],
        on=["permno", "month"],
        how="inner",
    )


def best_alignment_report(
    ds: pd.DataFrame,
    sic_monthly: pd.DataFrame,
    sic_col: str,
    label: str,
) -> dict:
    """Try signal and target month alignment; return metrics for the better one."""
    best_row = None
    best_align = None
    for align in ("signal_yyyymm", "target_yyyymm"):
        merged = attach_wrds_sic(ds, sic_monthly, align)
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


def demean_with_sic(df: pd.DataFrame, sic_col: str, hat_col: str) -> pd.DataFrame:
    work = df.copy()
    work["sic"] = pd.to_numeric(work[sic_col], errors="coerce")
    work = work.dropna(subset=["sic", "bm"])
    out = demean_by_industry_month(
        work,
        value_column="bm",
        industry_column="sic",
        industry_digits=2,
        time_column="month",
        stat="mean",
        output_column=hat_col,
    )
    return out


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--datashare", type=Path, default=DATASHARE)
    parser.add_argument("--bm-csv", type=Path, default=DEFAULT_BM)
    parser.add_argument("--wrds-user", default=None)
    parser.add_argument("--refresh-sich-cache", action="store_true")
    args = parser.parse_args()

    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

    if not args.bm_csv.exists():
        raise FileNotFoundError(f"{args.bm_csv} not found")

    print("Loading datashare bm / bm_ia / sic2...", flush=True)
    ds = load_datashare(args.datashare)

    print(f"Loading annual book_to_market: {args.bm_csv}", flush=True)
    bm_annual = pd.read_csv(args.bm_csv)

    import wrds

    db = wrds.Connection(wrds_username=args.wrds_user) if args.wrds_user else wrds.Connection()
    try:
        sich = load_or_fetch_sich(db, bm_annual, refresh=args.refresh_sich_cache)
    finally:
        db.close()

    print("Building June-expanded monthly SIC panel (company vs historical)...", flush=True)
    sic_monthly = build_monthly_sic_panel(bm_annual, sich)

    ds["sic_published"] = ds["sic2"] * 100

    rows = []

    print("\nDemeaning with datashare published sic2 (full datashare, no WRDS join)...", flush=True)
    pub = demean_with_sic(ds.dropna(subset=["sic2"]), "sic_published", "bm_ia_hat")
    row_pub = report_candidate(pub, "bm_ia_hat", "datashare published sic2 (formula ceiling baseline)")
    row_pub["month_align"] = "DATE//100"
    rows.append(row_pub)
    print(
        f"  median rho={row_pub['median_monthly_spearman']:.4f}  "
        f"pooled={row_pub['pooled_spearman']:.4f}  "
        f"paired N={row_pub['paired_N']:,}",
        flush=True,
    )

    wrds_candidates = [
        ("wrds_company_sic", "sic_company", "WRDS comp.company.sic (June-expanded)"),
        ("wrds_historical_sich", "sic_historical", "WRDS comp.funda.sich (June-expanded)"),
    ]
    for _hat, sic_col, label in wrds_candidates:
        print(f"\nDemeaning with {label}...", flush=True)
        row = best_alignment_report(ds, sic_monthly, sic_col, label)
        rows.append(row)
        print(
            f"  align={row['month_align']}  median rho={row['median_monthly_spearman']:.4f}  "
            f"pooled={row['pooled_spearman']:.4f}  "
            f"paired N={row['paired_N']:,}  permnos={row['unique_permnos']:,}",
            flush=True,
        )

    res = pd.DataFrame(rows)
    DIAGNOSTICS_DIR.mkdir(parents=True, exist_ok=True)
    out_path = DIAGNOSTICS_DIR / "bmia_sich_comparison.csv"
    res.to_csv(out_path, index=False)

    print("\n=== H1: SIC-source bm_ia formula ceiling (datashare bm inputs) ===")
    print(res.to_string(index=False, float_format=lambda v: f"{v:.4f}"))
    print(f"\nWrote {out_path}")


if __name__ == "__main__":
    main()
