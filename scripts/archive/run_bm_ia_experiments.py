#!/usr/bin/env python3
"""Logged experiment grid for reverse-engineering datashare bm_ia."""
from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from Character_Panels.timing import expand_annual_file_green, expand_annual_file_june  # noqa: E402
from Imputation.industry_codes import add_fama_french_industry_codes  # noqa: E402


DATASHARE = PROJECT_ROOT / "Supplementary_assistive_files" / "datashare.csv"
INDIVIDUAL_DIR = PROJECT_ROOT / "outputs" / "characteristics" / "individual"
DIAG_DIR = PROJECT_ROOT / "outputs" / "diagnostics" / "bm_ia_experiments"
SCRATCH_DIR = PROJECT_ROOT / "outputs" / "characteristics" / "datashare_style"

DEFAULT_INDUSTRIES_QUICK = ["sic2", "ffi48", "ffi49"]
DEFAULT_INDUSTRIES_FULL = ["sic2", "sic3", "ffi12", "ffi17", "ffi30", "ffi48", "ffi49"]
FF_SCHEMES = (12, 17, 30, 48, 49)


@dataclass(frozen=True)
class Candidate:
    input: str
    group_time: str
    industry: str
    stat: str
    weight: str
    universe: str
    bench_month_shift: int = 0


def month_add_scalar(month: pd.Series, shift: int) -> pd.Series:
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


def june_cohort(month: pd.Series) -> pd.Series:
    year = month // 100
    mon = month % 100
    return (year - (mon < 6).astype(int)).astype("Int64")


def june_datadate_year(month: pd.Series) -> pd.Series:
    return (june_cohort(month) - 1).astype("Int64")


def add_industries(df: pd.DataFrame, sic_col: str = "sic") -> pd.DataFrame:
    out = df.copy()
    if sic_col in out.columns:
        sic_num = pd.to_numeric(out[sic_col], errors="coerce")
        out["sic2"] = (sic_num // 100).astype("Int64")
        out["sic3"] = (sic_num // 10).astype("Int64")
        out = add_fama_french_industry_codes(out, sic_col=sic_col, schemes=FF_SCHEMES)
    elif "sic2" in out.columns:
        out["sic2"] = pd.to_numeric(out["sic2"], errors="coerce").astype("Int64")
    return out


def load_datashare() -> pd.DataFrame:
    frames = []
    usecols = ["permno", "DATE", "bm", "bm_ia", "sic2", "mvel1"]
    for chunk in pd.read_csv(DATASHARE, usecols=usecols, chunksize=500_000):
        chunk["permno"] = pd.to_numeric(chunk["permno"], errors="coerce").astype("Int64")
        chunk["month"] = (pd.to_numeric(chunk["DATE"], errors="coerce") // 100).astype("Int64")
        chunk = chunk.drop(columns=["DATE"])
        frames.append(chunk)
    ds = pd.concat(frames, ignore_index=True)
    ds = ds.dropna(subset=["permno", "month"])
    ds["sic2_ds"] = pd.to_numeric(ds["sic2"], errors="coerce").astype("Int64")
    ds["mvel1"] = pd.to_numeric(ds["mvel1"], errors="coerce")
    ds.loc[ds["mvel1"] <= 0, "mvel1"] = np.nan
    return ds


def load_repo_btm_annual() -> pd.DataFrame:
    path = INDIVIDUAL_DIR / "book_to_market.csv"
    usecols = ["permno", "permco", "gvkey", "datadate", "sic", "fyear", "book_to_market"]
    annual = pd.read_csv(path, usecols=usecols, parse_dates=["datadate"])
    annual["permno"] = pd.to_numeric(annual["permno"], errors="coerce").astype("Int64")
    annual["permco"] = pd.to_numeric(annual["permco"], errors="coerce")
    annual["book_to_market"] = pd.to_numeric(annual["book_to_market"], errors="coerce")
    annual = annual.dropna(subset=["permno", "datadate", "book_to_market"])
    annual["datadate_year"] = annual["datadate"].dt.year.astype("Int64")
    return add_industries(annual, sic_col="sic")


def load_me_weights() -> pd.DataFrame:
    path = INDIVIDUAL_DIR / "me.csv"
    usecols = ["permno", "signal_yyyymm", "me"]
    me = pd.read_csv(path, usecols=usecols)
    me["permno"] = pd.to_numeric(me["permno"], errors="coerce").astype("Int64")
    me["month"] = pd.to_numeric(me["signal_yyyymm"], errors="coerce").astype("Int64")
    me["me"] = pd.to_numeric(me["me"], errors="coerce")
    me.loc[me["me"] <= 0, "me"] = np.nan
    return me[["permno", "month", "me"]].dropna()


def expand_repo_btm(annual: pd.DataFrame, timing: str, me: pd.DataFrame | None) -> pd.DataFrame:
    id_cols = ["permno", "permco", "gvkey", "datadate", "sic", "fyear", "book_to_market"]
    if timing == "june":
        monthly = expand_annual_file_june(annual[id_cols], ["book_to_market"])
    elif timing == "green":
        monthly = expand_annual_file_green(annual[id_cols], ["book_to_market"])
    else:
        raise ValueError(timing)
    monthly = monthly.rename(columns={"signal_yyyymm": "month", "book_to_market": "value"})
    monthly["month"] = pd.to_numeric(monthly["month"], errors="coerce").astype("Int64")
    monthly = add_industries(monthly, sic_col="sic")
    if me is not None:
        monthly = monthly.merge(me, on=["permno", "month"], how="left")
    else:
        monthly["me"] = np.nan
    monthly["june_cohort"] = june_cohort(monthly["month"])
    monthly["datadate_year_from_month"] = june_datadate_year(monthly["month"])
    return monthly


def attach_target_sic(ds: pd.DataFrame, repo_monthly_june: pd.DataFrame, repo_monthly_green: pd.DataFrame) -> pd.DataFrame:
    sic_map = pd.concat(
        [
            repo_monthly_june[["permno", "month", "sic"]].dropna(),
            repo_monthly_green[["permno", "month", "sic"]].dropna(),
        ],
        ignore_index=True,
    )
    sic_map = sic_map.drop_duplicates(["permno", "month"], keep="first")
    target = ds.merge(sic_map, on=["permno", "month"], how="left")
    target = add_industries(target, sic_col="sic")
    target["sic2"] = target["sic2"].fillna(target["sic2_ds"]).astype("Int64")
    target["june_cohort"] = june_cohort(target["month"])
    target["datadate_year_from_month"] = june_datadate_year(target["month"])
    target["public_bench"] = target["bm"] - target["bm_ia"]
    target["target_value_weight"] = target["mvel1"]
    return target


def weighted_mean(df: pd.DataFrame, keys: list[str], value_col: str, weight_col: str) -> pd.DataFrame:
    work = df[keys + [value_col, weight_col]].dropna()
    work = work[work[weight_col] > 0].copy()
    work["_wx"] = work[value_col] * work[weight_col]
    grouped = work.groupby(keys, dropna=False, sort=False)
    out = grouped[["_wx", weight_col]].sum().reset_index()
    out["bench"] = out["_wx"] / out[weight_col].replace(0, np.nan)
    return out[keys + ["bench"]]


def weighted_median(df: pd.DataFrame, keys: list[str], value_col: str, weight_col: str) -> pd.DataFrame:
    work = df[keys + [value_col, weight_col]].dropna()
    work = work[work[weight_col] > 0].copy()
    if work.empty:
        return pd.DataFrame(columns=keys + ["bench"])
    work = work.sort_values(keys + [value_col])
    work["_cum_w"] = work.groupby(keys, dropna=False, sort=False)[weight_col].cumsum()
    work["_tot_w"] = work.groupby(keys, dropna=False, sort=False)[weight_col].transform("sum")
    out = work[work["_cum_w"] >= work["_tot_w"] / 2].drop_duplicates(keys, keep="first")
    return out[keys + [value_col]].rename(columns={value_col: "bench"})


def equal_stat(df: pd.DataFrame, keys: list[str], value_col: str, stat: str) -> pd.DataFrame:
    work = df[keys + [value_col]].dropna()
    grouped = work.groupby(keys, dropna=False, sort=False)[value_col]
    if stat == "mean":
        out = grouped.mean().reset_index()
    elif stat == "median":
        out = grouped.median().reset_index()
    else:
        raise ValueError(stat)
    return out.rename(columns={value_col: "bench"})


def build_benchmark(source: pd.DataFrame, candidate: Candidate) -> tuple[pd.DataFrame, list[str]]:
    if candidate.industry not in source.columns:
        return pd.DataFrame(), []

    if candidate.group_time == "monthly":
        source = source.copy()
        source["bench_time"] = source["month"]
    elif candidate.group_time == "june_cohort":
        source = source.copy()
        source["bench_time"] = source["june_cohort"]
    elif candidate.group_time == "annual_datadate_year":
        source = source.copy()
        if "datadate_year" in source.columns:
            source["bench_time"] = source["datadate_year"]
        else:
            source["bench_time"] = source["datadate_year_from_month"]
    else:
        raise ValueError(candidate.group_time)

    keys = ["bench_time", candidate.industry]
    value_col = "value"
    if candidate.weight == "equal":
        bench = equal_stat(source, keys, value_col, candidate.stat)
    elif candidate.weight == "value" and candidate.stat == "mean":
        bench = weighted_mean(source, keys, value_col, "weight")
    elif candidate.weight == "value" and candidate.stat == "median":
        bench = weighted_median(source, keys, value_col, "weight")
    else:
        raise ValueError(candidate.weight)
    return bench, keys


def prepare_target_for_candidate(target: pd.DataFrame, candidate: Candidate) -> pd.DataFrame:
    if candidate.industry not in target.columns:
        return pd.DataFrame()
    out = target[["permno", "month", "bm", "bm_ia", "public_bench", candidate.industry]].copy()
    if candidate.group_time == "monthly":
        out["bench_time"] = month_add_scalar(out["month"].astype("Int64"), candidate.bench_month_shift)
    elif candidate.group_time == "june_cohort":
        out["bench_time"] = june_cohort(out["month"].astype("Int64"))
    elif candidate.group_time == "annual_datadate_year":
        out["bench_time"] = june_datadate_year(out["month"].astype("Int64"))
    else:
        raise ValueError(candidate.group_time)
    return out.dropna(subset=["bm", "bm_ia", candidate.industry, "bench_time"])


def screen_25160(target_for_candidate: pd.DataFrame, bench: pd.DataFrame, candidate: Candidate) -> dict:
    keys = ["bench_time", candidate.industry]
    sample = target_for_candidate[target_for_candidate["permno"] == 25160].copy()
    sample = sample[(sample["month"] >= 196207) & (sample["month"] <= 196312)]
    if sample.empty or bench.empty:
        return {"screen_obs": 0, "bench_distinct_25160": np.nan, "bench_mae_25160": np.nan, "screen_status": "no_screen_data"}
    merged = sample.merge(bench, on=keys, how="left").dropna(subset=["bench", "public_bench"])
    if merged.empty:
        return {"screen_obs": 0, "bench_distinct_25160": np.nan, "bench_mae_25160": np.nan, "screen_status": "no_screen_data"}
    distinct = int(merged["bench"].round(8).nunique())
    mae = float((merged["bench"] - merged["public_bench"]).abs().mean())
    status = "passes_screen" if distinct > 1 else "flat_discard"
    return {"screen_obs": len(merged), "bench_distinct_25160": distinct, "bench_mae_25160": mae, "screen_status": status}


def monthly_spearman(df: pd.DataFrame) -> tuple[float, int]:
    rhos = []
    for _, group in df.groupby("month", sort=True):
        if len(group) < 50:
            continue
        rho = group["hat"].corr(group["bm_ia"], method="spearman")
        if pd.notna(rho):
            rhos.append(rho)
    return (float(np.median(rhos)), len(rhos)) if rhos else (np.nan, 0)


def compare_candidate(target_for_candidate: pd.DataFrame, bench: pd.DataFrame, candidate: Candidate) -> tuple[dict, pd.DataFrame]:
    keys = ["bench_time", candidate.industry]
    merged = target_for_candidate.merge(bench, on=keys, how="inner")
    merged = merged.dropna(subset=["bm", "bm_ia", "bench"]).copy()
    merged["hat"] = merged["bm"] - merged["bench"]
    if len(merged) < 2:
        return {
            "median_rho": np.nan,
            "pooled_rho": np.nan,
            "exact": np.nan,
            "paired_obs": len(merged),
            "months": 0,
            "median_abs_diff": np.nan,
            "p95_abs_diff": np.nan,
        }, merged
    diff = (merged["hat"].astype("float64") - merged["bm_ia"].astype("float64")).abs()
    med, months = monthly_spearman(merged)
    return {
        "median_rho": med,
        "pooled_rho": float(merged["hat"].corr(merged["bm_ia"], method="spearman")),
        "exact": float((diff <= 1e-4).mean()) * 100,
        "paired_obs": len(merged),
        "months": months,
        "median_abs_diff": float(diff.median()),
        "p95_abs_diff": float(diff.quantile(0.95)),
    }, merged


def per_decade_metrics(merged: pd.DataFrame) -> pd.DataFrame:
    rows = []
    if merged.empty:
        return pd.DataFrame()
    work = merged.copy()
    work["decade"] = ((work["month"] // 100) // 10) * 10
    for decade, group in work.groupby("decade", sort=True):
        if len(group) < 2:
            continue
        diff = (group["hat"].astype("float64") - group["bm_ia"].astype("float64")).abs()
        med, months = monthly_spearman(group)
        rows.append(
            {
                "decade": int(decade),
                "median_rho": med,
                "pooled_rho": float(group["hat"].corr(group["bm_ia"], method="spearman")),
                "exact": float((diff <= 1e-4).mean()) * 100,
                "paired_obs": len(group),
                "months": months,
            }
        )
    return pd.DataFrame(rows)


def make_candidates(full_grid: bool) -> list[Candidate]:
    industries = DEFAULT_INDUSTRIES_FULL if full_grid else DEFAULT_INDUSTRIES_QUICK
    shifts = [-1, 0, 1]
    candidates: list[Candidate] = []

    monthly_inputs = [
        ("public_bm", "published_panel_rows"),
        ("repo_btm_june", "all_repo_btm_linked"),
        ("repo_btm_green", "all_repo_btm_linked"),
    ]
    group_times = ["monthly", "june_cohort"] if full_grid else ["monthly"]
    for input_name, universe in monthly_inputs:
        for group_time in group_times:
            for industry in industries:
                for stat in ["mean", "median"]:
                    for weight in ["equal", "value"]:
                        month_shifts = shifts if group_time == "monthly" else [0]
                        for shift in month_shifts:
                            candidates.append(
                                Candidate(input_name, group_time, industry, stat, weight, universe, shift)
                            )

    for industry in industries:
        for stat in ["mean", "median"]:
            for weight in ["equal", "value"]:
                candidates.append(
                    Candidate(
                        "raw_annual_btm",
                        "annual_datadate_year",
                        industry,
                        stat,
                        weight,
                        "annual_repo_btm_linked",
                        0,
                    )
                )
    return candidates


def source_frames(target: pd.DataFrame, annual: pd.DataFrame, repo_june: pd.DataFrame, repo_green: pd.DataFrame) -> dict[str, pd.DataFrame]:
    public = target.rename(columns={"bm": "value", "target_value_weight": "weight"}).copy()
    repo_june_src = repo_june.rename(columns={"me": "weight"}).copy()
    repo_green_src = repo_green.rename(columns={"me": "weight"}).copy()
    annual_src = annual.rename(columns={"book_to_market": "value"}).copy()
    annual_src["weight"] = np.nan
    return {
        "public_bm": public,
        "repo_btm_june": repo_june_src,
        "repo_btm_green": repo_green_src,
        "raw_annual_btm": annual_src,
    }


def result_row(candidate: Candidate, metrics: dict, screen: dict) -> dict:
    row = {
        "input": candidate.input,
        "group_time": candidate.group_time,
        "industry": candidate.industry,
        "stat": candidate.stat,
        "weight": candidate.weight,
        "universe": candidate.universe,
        "median_rho": metrics.get("median_rho", np.nan),
        "pooled_rho": metrics.get("pooled_rho", np.nan),
        "exact": metrics.get("exact", np.nan),
        "paired_obs": metrics.get("paired_obs", 0),
        "bench_month_shift": candidate.bench_month_shift,
        "months": metrics.get("months", 0),
        "median_abs_diff": metrics.get("median_abs_diff", np.nan),
        "p95_abs_diff": metrics.get("p95_abs_diff", np.nan),
    }
    row.update(screen)
    return row


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--full-grid", action="store_true", help="Run the larger grid.")
    parser.add_argument(
        "--no-discard-flat-screen",
        action="store_true",
        help="Still compute full metrics for candidates flat in the permno=25160 screen.",
    )
    parser.add_argument("--results", default=str(DIAG_DIR / "results.csv"))
    parser.add_argument("--best-output", default=str(SCRATCH_DIR / "bm_ia_best_candidate.csv"))
    parser.add_argument("--best-decade-output", default=str(DIAG_DIR / "best_per_decade.csv"))
    args = parser.parse_args()

    DIAG_DIR.mkdir(parents=True, exist_ok=True)
    SCRATCH_DIR.mkdir(parents=True, exist_ok=True)

    print("Loading datashare target...", flush=True)
    ds = load_datashare()
    print(f"datashare rows: {len(ds):,}", flush=True)

    print("Loading repo book_to_market annual and monthly ME weights...", flush=True)
    annual = load_repo_btm_annual()
    me = load_me_weights()
    print(f"annual btm rows: {len(annual):,}; monthly ME rows: {len(me):,}", flush=True)

    print("Expanding repo book_to_market with June and Green timing...", flush=True)
    repo_june = expand_repo_btm(annual, "june", me)
    repo_green = expand_repo_btm(annual, "green", me)
    print(f"repo June monthly rows: {len(repo_june):,}; repo Green monthly rows: {len(repo_green):,}", flush=True)

    target = attach_target_sic(ds, repo_june, repo_green)
    sources = source_frames(target, annual, repo_june, repo_green)
    candidates = make_candidates(args.full_grid)
    print(f"Running {len(candidates):,} candidates...", flush=True)

    results = []
    best_key = None
    best_metrics = None
    best_merged = pd.DataFrame()
    for idx, candidate in enumerate(candidates, start=1):
        source = sources[candidate.input]
        bench, _ = build_benchmark(source, candidate)
        target_for_candidate = prepare_target_for_candidate(target, candidate)
        screen = screen_25160(target_for_candidate, bench, candidate)
        should_discard = (
            screen.get("screen_status") == "flat_discard"
            and not args.no_discard_flat_screen
        )
        if bench.empty or target_for_candidate.empty:
            metrics = {"paired_obs": 0}
            screen["screen_status"] = "missing_key"
            merged = pd.DataFrame()
        elif should_discard:
            metrics = {"paired_obs": 0}
            merged = pd.DataFrame()
        else:
            metrics, merged = compare_candidate(target_for_candidate, bench, candidate)

        row = result_row(candidate, metrics, screen)
        results.append(row)
        if pd.notna(row["median_rho"]):
            if best_metrics is None or (row["median_rho"], row["pooled_rho"]) > (
                best_metrics["median_rho"],
                best_metrics["pooled_rho"],
            ):
                best_key = candidate
                best_metrics = row
                best_merged = merged

        if idx % 10 == 0 or idx == len(candidates):
            print(f"  {idx:,}/{len(candidates):,} candidates complete", flush=True)

    results_df = pd.DataFrame(results)
    results_df = results_df.sort_values(["median_rho", "pooled_rho"], ascending=False, na_position="last")
    results_path = Path(args.results)
    results_path.parent.mkdir(parents=True, exist_ok=True)
    results_df.to_csv(results_path, index=False)
    print(f"Wrote results: {results_path}", flush=True)

    if best_key is not None and not best_merged.empty:
        out = best_merged[["permno", "month", "hat", "bm_ia", "bench"]].rename(
            columns={"month": "signal_yyyymm", "hat": "bm_ia_hat", "bm_ia": "bm_ia_datashare"}
        )
        best_output = Path(args.best_output)
        best_output.parent.mkdir(parents=True, exist_ok=True)
        out.to_csv(best_output, index=False)
        decade = per_decade_metrics(best_merged)
        decade_output = Path(args.best_decade_output)
        decade_output.parent.mkdir(parents=True, exist_ok=True)
        decade.to_csv(decade_output, index=False)
        print(f"Best candidate: {best_key}", flush=True)
        print(
            "Best metrics: "
            f"median_rho={best_metrics['median_rho']:.6f}, "
            f"pooled_rho={best_metrics['pooled_rho']:.6f}, "
            f"exact={best_metrics['exact']:.2f}%, "
            f"paired_obs={best_metrics['paired_obs']:,}",
            flush=True,
        )
        print(f"Wrote best candidate panel: {best_output}", flush=True)
        print(f"Wrote best per-decade metrics: {decade_output}", flush=True)
    else:
        print("No candidate produced full metrics.", flush=True)


if __name__ == "__main__":
    main()
