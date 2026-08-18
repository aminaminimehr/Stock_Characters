#!/usr/bin/env python3
"""Diagnostic: does a MONTHLY market-equity denominator (not annual/December-fixed)
explain datashare's bm_ia better than the current annual-bm builder?

Current builder holds bm = book_equity / December market_equity CONSTANT for the
whole June(y+1)..May(y+2) window (book_equity is annual; market_equity is a single
December snapshot). This script tests a different candidate: book_equity still only
refreshes once a year (per the current June-convention timing), but the market-equity
DENOMINATOR is recomputed every month using that month's own price, so a firm's own
bm can move every month, not just once a year.

NOTE ON INDEPENDENCE: to avoid a fresh WRDS pull, the monthly market-equity
ingredient here is datashare.csv's own published `mvel1` column (log, one-month-lag
market equity) -- used both to recover an approximate December book-equity numerator
and as the monthly denominator. This is the same "use datashare's own non-bm_ia
columns to test a construction MECHANISM" approach as
scripts/audits/audit_bmia_implied_adjustment.py's Test B. It is NOT an independent
(WRDS-only) rebuild -- a good number here says the mechanism is plausible, not that
the gap is closed per the objective in docs/gkx/BM_BMIA_PROBLEM_README.md section 1.

Outputs under outputs/diagnostics/:
  bm_ia_monthly_me_comparison.csv
  bm_ia_monthly_me_summary.txt
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

from Character_Builders._shared.bm_ia_builder import demean_by_industry_month  # noqa: E402
from Character_Panels.timing import expand_annual_file_june  # noqa: E402

DEFAULT_BM_CSV = PROJECT_ROOT / "outputs" / "characteristics" / "individual" / "book_to_market.csv"
DEFAULT_DATASHARE = PROJECT_ROOT / "Supplementary_assistive_files" / "datashare.csv"
OUT_DIR = PROJECT_ROOT / "outputs" / "diagnostics"

MIN_PAIRS = 50
CHUNK_SIZE = 500_000


def load_datashare(datashare_path: Path) -> tuple[pd.DataFrame, int, int]:
    frames = []
    for chunk in pd.read_csv(
        datashare_path,
        usecols=["permno", "DATE", "mvel1", "bm", "bm_ia"],
        chunksize=CHUNK_SIZE,
    ):
        chunk["permno"] = pd.to_numeric(chunk["permno"], errors="coerce").astype("Int64")
        chunk["month"] = (pd.to_numeric(chunk["DATE"], errors="coerce") // 100).astype("Int64")
        for col in ("mvel1", "bm", "bm_ia"):
            chunk[col] = pd.to_numeric(chunk[col], errors="coerce")
        frames.append(chunk.drop(columns=["DATE"]))
    ds = pd.concat(frames, ignore_index=True)
    return ds, int(ds["month"].min()), int(ds["month"].max())


def recover_book_equity_proxy(annual: pd.DataFrame, ds: pd.DataFrame) -> pd.DataFrame:
    """book_eq_proxy = book_to_market * December(calendar_year) market equity.

    datashare's mvel1 is a RAW market-equity level (CRSP price*shrout, $thousands),
    NOT log-transformed -- confirmed empirically (values up to ~3.8e7, and
    np.exp() on it overflows). December(calendar_year) ME is proxied by datashare's
    own mvel1 at DATE = Jan(calendar_year+1) -- the datashare row whose signal
    month is December(calendar_year), matching build_book_to_market.py's own
    December-ME join key (calendar_year = datadate.dt.year).
    """
    annual = annual.copy()
    annual["datadate"] = pd.to_datetime(annual["datadate"])
    annual["calendar_year"] = annual["datadate"].dt.year
    annual["lookup_month"] = (annual["calendar_year"] + 1) * 100 + 1

    dec_me = ds[["permno", "month", "mvel1"]].rename(
        columns={"month": "lookup_month", "mvel1": "me_dec_proxy"}
    )
    annual = annual.merge(dec_me, on=["permno", "lookup_month"], how="left")
    annual["book_eq_proxy"] = annual["book_to_market"] * annual["me_dec_proxy"]
    return annual


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
                "exact_rate_pct": np.nan,
                "median_monthly_spearman": np.nan,
                "mean_monthly_spearman": np.nan,
                "spearman_months": 0,
                "permno_both": 0,
            }
        else:
            pv = m["pv"].astype("float64")
            dv = m["dv"].astype("float64")
            vals = monthly_spearman_values(m.rename(columns={"pv": "a", "dv": "b"}), "a", "b")
            diff = (pv - dv).abs()
            row = {
                "month_align": month_col,
                "paired_obs": int(n_pair),
                "pooled_spearman": float(pv.corr(dv, method="spearman")),
                "exact_rate_pct": 100 * float((diff <= 1e-4).mean()),
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

    print("Loading annual book_to_market...", flush=True)
    annual = pd.read_csv(args.bm_csv)
    print(f"  annual rows={len(annual):,} permnos={annual['permno'].nunique():,}", flush=True)

    print("Loading datashare mvel1 / bm / bm_ia...", flush=True)
    ds, month_min, month_max = load_datashare(args.datashare)
    print(f"  datashare rows={len(ds):,} months={month_min}-{month_max}", flush=True)

    print("\nRecovering book_eq_proxy = book_to_market * December ME (from datashare mvel1)...", flush=True)
    annual_proxy = recover_book_equity_proxy(annual, ds)
    have_proxy = annual_proxy["book_eq_proxy"].notna().sum()
    print(
        f"  annual rows with recovered book_eq_proxy: {have_proxy:,} / {len(annual_proxy):,} "
        f"({100*have_proxy/len(annual_proxy):.1f}%)",
        flush=True,
    )

    print("\nExpanding book_eq_proxy to monthly (June convention, unchanged)...", flush=True)
    monthly = expand_annual_file_june(annual_proxy, ["book_eq_proxy"])
    monthly = monthly[monthly["book_eq_proxy"].notna()].copy()
    print(f"  monthly rows={len(monthly):,} permnos={monthly['permno'].nunique():,}", flush=True)

    print("Joining datashare's own monthly mvel1 as the monthly ME denominator...", flush=True)
    me_monthly = ds[["permno", "month", "mvel1"]].rename(
        columns={"month": "signal_yyyymm", "mvel1": "me_t"}
    )
    monthly = monthly.merge(me_monthly, on=["permno", "signal_yyyymm"], how="left")
    monthly = monthly[monthly["me_t"].notna() & (monthly["me_t"] > 0)].copy()
    monthly["bm"] = monthly["book_eq_proxy"] / monthly["me_t"]
    monthly = monthly[monthly["bm"] > 0].copy()
    print(f"  monthly rows with candidate bm: {len(monthly):,}", flush=True)

    monthly = demean_by_industry_month(
        monthly,
        value_column="bm",
        industry_column="sic",
        industry_digits=2,
        time_column="signal_yyyymm",
        stat="mean",
        output_column="bm_ia",
    )

    results = []
    for char_col, ds_col, note in [
        ("bm", "bm", "sanity check: candidate bm vs published bm"),
        ("bm_ia", "bm_ia", "the real test: candidate bm_ia vs published bm_ia"),
    ]:
        stats = compare_character(
            monthly, ds, panel_col=char_col, ds_col=ds_col,
            month_min=month_min, month_max=month_max,
        )
        print(
            f"\n{note}\n"
            f"  {char_col:6s} vs datashare {ds_col:6s}: "
            f"median rho={stats.get('median_monthly_spearman', float('nan')):.4f}  "
            f"pooled={stats.get('pooled_spearman', float('nan')):.4f}  "
            f"exact%={stats.get('exact_rate_pct', float('nan')):.2f}  "
            f"align={stats.get('month_align')}  paired={stats.get('paired_obs', 0):,}",
            flush=True,
        )
        results.append({
            "candidate": "monthly_me",
            "character": char_col,
            "note": note,
            "month_align": stats.get("month_align"),
            "median_monthly_spearman": stats.get("median_monthly_spearman"),
            "mean_monthly_spearman": stats.get("mean_monthly_spearman"),
            "pooled_spearman": stats.get("pooled_spearman"),
            "exact_rate_pct": stats.get("exact_rate_pct"),
            "paired_obs": stats.get("paired_obs"),
            "permno_both": stats.get("permno_both"),
        })

    res_df = pd.DataFrame(results)
    cmp_csv = args.out_dir / "bm_ia_monthly_me_comparison.csv"
    res_df.to_csv(cmp_csv, index=False)

    bm_rho = res_df.loc[res_df["character"] == "bm", "median_monthly_spearman"].iloc[0]
    bm_ia_rho = res_df.loc[res_df["character"] == "bm_ia", "median_monthly_spearman"].iloc[0]

    summary_lines = [
        "bm_ia rebuild: monthly market-equity (monthly ME) candidate",
        f"Source bm CSV: {args.bm_csv}",
        f"Datashare: {args.datashare}",
        f"Comparison window: {month_min}-{month_max}",
        "",
        "CAVEAT: this candidate uses datashare's own mvel1 column as the monthly-ME",
        "ingredient (both to recover the book-equity numerator and as the monthly",
        "denominator). It is a mechanism test, not an independent WRDS-only rebuild.",
        "",
        res_df[
            ["note", "median_monthly_spearman", "mean_monthly_spearman",
             "pooled_spearman", "exact_rate_pct", "paired_obs"]
        ].to_string(index=False),
        "",
        f"candidate bm    median rho: {bm_rho:.4f}",
        f"candidate bm_ia median rho: {bm_ia_rho:.4f}",
        "",
        "Reference benchmarks (same methodology, from diag_bm_green_timing.py):",
        "  bm_ia june (current builder, annual-hold bm):        0.4182",
        "  bm_ia green/firmspecific (firm-specific FYE timing): 0.4128",
        f"  bm_ia monthly_me (this candidate):                   {bm_ia_rho:.4f}",
    ]
    summary_path = args.out_dir / "bm_ia_monthly_me_summary.txt"
    summary_path.write_text("\n".join(summary_lines) + "\n", encoding="utf-8")

    print(f"\nWrote {cmp_csv}")
    print(f"Wrote {summary_path}")
    print("\n" + "\n".join(summary_lines[4:]), flush=True)


if __name__ == "__main__":
    main()
