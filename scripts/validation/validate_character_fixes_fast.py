#!/usr/bin/env python3
"""Fast Green validation for the 22 target predictors (1-2 year window).

Builds only the affected characters with a narrow WRDS sample, then compares
monthly cross-sectional Spearman vs Green SAS on 2010-2011 (default).
"""
from __future__ import annotations

import argparse
import os
import sys
import tempfile
from pathlib import Path

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "Character_Builders"))

from scripts.validation.validate_green_timing_2010_2015 import (  # noqa: E402
    GREEN_SAS_PATH,
    MIN_PAIRS,
    load_green_sas,
    monthly_spearman_series,
    summarize_monthly_rhos,
)

from _shared.beta_builder import (  # noqa: E402
    _build_factor_panel,
    _finalize_factor_character,
)
from _shared.event_builders import build_abr_character, build_aeavol_character  # noqa: E402
from _shared.green_builders import (  # noqa: E402
    ANNUAL_CHARACTER_INFO,
    attach_permno,
    build_monthly_character,
    compute_annual_characters,
    connect_wrds,
    load_annual_age_lookup,
    load_annual_compustat,
    load_annual_orgcap_lookup,
    load_ccm_links,
    load_crsp_monthly,
    write_character,
)
from _shared.ms_builder import build_ms_character  # noqa: E402
from _shared.quarterly_builders import (  # noqa: E402
    QUARTERLY_CHARACTER_INFO,
    build_quarterly_character,
    prepare_quarterly_compustat_panel,
)
from Character_Panels.timing import expand_annual_file_green  # noqa: E402

TARGETS: dict[str, tuple[str, str]] = {
    "cinvest": ("cinvest", "cinvest"),
    "nincr": ("nincr", "nincr"),
    "ear": ("abr", "ear"),
    "chtx": ("chtx", "chtx"),
    "rsup": ("rsup", "rsup"),
    "beta": ("beta", "beta"),
    "betasq": ("betasq", "betasq"),
    "operprof": ("operprof", "operprof"),
    "pchcapx_ia": ("pchcapx_ia", "pchcapx_ia"),
    "roaq": ("roaq", "roaq"),
    "cash": ("cash", "cash"),
    "aeavol": ("aeavol", "aeavol"),
    "chmom": ("chmom", "chmom"),
    "idiovol": ("idiovol", "idiovol"),
    "indmom": ("indmom", "indmom"),
    "ms": ("ms", "ms"),
    "pricedelay": ("pricedelay", "pricedelay"),
    "roavol": ("roavol", "roavol"),
    "roeq": ("roeq", "roeq"),
    "sic2": ("sic2", "sic2"),
    "stdacc": ("stdacc", "stdacc"),
    "stdcf": ("stdcf", "stdcf"),
}

QUARTERLY_TARGETS = {
    "cinvest", "nincr", "chtx", "rsup", "roaq", "cash", "roeq", "stdacc", "stdcf", "roavol",
}
ANNUAL_TARGETS = {"operprof", "pchcapx_ia", "sic2"}
MONTHLY_TARGETS = {"chmom", "indmom"}
DAILY_FACTOR_TARGETS = ("beta", "betasq", "idiovol", "pricedelay")
EVENT_TARGETS = {"ear": build_abr_character, "aeavol": build_aeavol_character}


def compare_series(repo: pd.DataFrame, green: pd.DataFrame, repo_col: str, green_col: str, win_start: int, win_end: int) -> dict:
    merged = (
        repo[["permno", "signal_yyyymm", repo_col]]
        .rename(columns={repo_col: "repo_val", "signal_yyyymm": "month"})
        .merge(
            green[["permno", "month", green_col]].rename(columns={green_col: "green_val"}),
            on=["permno", "month"],
            how="inner",
        )
    )
    merged = merged[(merged["month"] >= win_start) & (merged["month"] <= win_end)]
    rhos = monthly_spearman_series(merged, "repo_val", "green_val")
    return summarize_monthly_rhos(rhos)


def build_targets(db, output_dir: Path, workers: int | None, win_start: int, win_end: int) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)

    quarterly_chars = [c for c in QUARTERLY_TARGETS if c in QUARTERLY_CHARACTER_INFO]
    if quarterly_chars:
        print("Building quarterly batch...", flush=True)
        qcomp = prepare_quarterly_compustat_panel(db, use_ibes=False)
        for character in quarterly_chars:
            out = build_quarterly_character(db, character, comp=qcomp, use_ibes=False)
            write_character(out, character, output_dir)

    annual_chars = [c for c in ANNUAL_TARGETS if c in ANNUAL_CHARACTER_INFO]
    if annual_chars:
        print("Building annual targets...", flush=True)
        crsp_idx = load_crsp_monthly(db)[["permno", "signal_yyyymm"]].drop_duplicates()
        comp = compute_annual_characters(
            load_annual_compustat(db),
            age_lookup=load_annual_age_lookup(db),
            orgcap_lookup=load_annual_orgcap_lookup(db),
        )
        comp = attach_permno(comp, load_ccm_links(db))
        for character in annual_chars:
            annual = comp[comp["permno"].notna()][
                ["permno", "permco", "gvkey", "datadate", "sic", "fyear", character]
            ].copy()
            monthly = expand_annual_file_green(annual, [character], crsp_month_index=crsp_idx)
            write_character(monthly, character, output_dir)

    for character in MONTHLY_TARGETS:
        print(f"Building {character}...", flush=True)
        write_character(build_monthly_character(db, character), character, output_dir)

    for name, builder in EVENT_TARGETS.items():
        print(f"Building {name}...", flush=True)
        write_character(builder(db, workers=workers), TARGETS[name][0], output_dir)

    factor_monthly = load_crsp_monthly(db)[
        ["permno", "permco", "date", "signal_yyyymm", "target_yyyymm", "siccd", "exchcd", "shrcd"]
    ].rename(columns={"siccd": "sic"})
    factor_monthly = factor_monthly[
        (factor_monthly["signal_yyyymm"] >= win_start) & (factor_monthly["signal_yyyymm"] <= win_end)
    ].copy()
    print(f"Building daily factors for {len(factor_monthly):,} monthly rows...", flush=True)
    factor_panel = _build_factor_panel(db, output_dir, workers=workers, monthly_panel=factor_monthly)
    for name in DAILY_FACTOR_TARGETS:
        write_character(_finalize_factor_character(factor_panel, name), TARGETS[name][0], output_dir)

    print("Building ms...", flush=True)
    write_character(build_ms_character(db, use_ibes=False, workers=workers), TARGETS["ms"][0], output_dir)


def load_built(repo_col: str, path: Path, win_start: int, win_end: int) -> pd.DataFrame:
    df = pd.read_csv(path, usecols=["permno", "signal_yyyymm", repo_col])
    df = df[(df["signal_yyyymm"] >= win_start) & (df["signal_yyyymm"] <= win_end)]
    return df


def main() -> None:
    parser = argparse.ArgumentParser(description="Fast Green validation for 22 target predictors.")
    parser.add_argument("--win-start", type=int, default=201001)
    parser.add_argument("--win-end", type=int, default=201112, help="Green comparison window (default: 2 years).")
    parser.add_argument(
        "--sample-start",
        default=None,
        help="WRDS pull lower bound. Default: 36 months before --win-start (for beta lookback).",
    )
    parser.add_argument(
        "--sample-end",
        default=None,
        help="WRDS pull upper bound. Default: end of --win-end calendar year.",
    )
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--build-dir", default=None, help="Reuse existing build directory.")
    parser.add_argument("--skip-build", action="store_true")
    args = parser.parse_args()

    win_start_year = args.win_start // 100
    if args.sample_start is None:
        args.sample_start = f"{win_start_year - 3}-01-01"
    if args.sample_end is None:
        args.sample_end = f"{args.win_end // 100}-12-31"

    os.environ["STOCK_CHARACTERS_SAMPLE_START"] = args.sample_start
    os.environ["STOCK_CHARACTERS_SAMPLE_END"] = args.sample_end
    print(
        f"WRDS sample: {args.sample_start} .. {args.sample_end} | "
        f"Green compare: {args.win_start} .. {args.win_end}",
        flush=True,
    )

    green = load_green_sas(list({g for _, g in TARGETS.values()}), args.win_start, args.win_end)

    if args.build_dir:
        build_dir = Path(args.build_dir)
    else:
        build_dir = Path(tempfile.mkdtemp(prefix="char_fix_val_"))

    if not args.skip_build:
        db = connect_wrds(os.environ.get("WRDS_USERNAME"))
        try:
            build_targets(db, build_dir, workers=args.workers, win_start=args.win_start, win_end=args.win_end)
        finally:
            db.close()

    rows = []
    for ds_name, (repo_col, green_col) in TARGETS.items():
        path = build_dir / f"{repo_col}.csv"
        if not path.exists():
            rows.append({"datashare": ds_name, "repo": repo_col, "median_rho": np.nan, "months": 0, "status": "missing build"})
            continue
        repo = load_built(repo_col, path, args.win_start, args.win_end)
        stats = compare_series(repo, green, repo_col, green_col, args.win_start, args.win_end)
        rho = stats["median"]
        status = "PASS" if np.isfinite(rho) and rho >= 0.95 else "FAIL"
        rows.append(
            {
                "datashare": ds_name,
                "repo": repo_col,
                "median_rho": rho,
                "months": stats["months"],
                "status": status,
            }
        )

    report = pd.DataFrame(rows).sort_values(["status", "median_rho"], ascending=[True, False])
    out_path = PROJECT_ROOT / "docs" / "gkx" / "character_fixes_fast_validation.csv"
    report.to_csv(out_path, index=False)

    passed = (report["status"] == "PASS").sum()
    print(f"\nValidation {args.win_start}-{args.win_end}: {passed}/{len(report)} passed (rho >= 0.95)")
    print(report.to_string(index=False))
    print(f"\nWrote {out_path}")
    if not args.build_dir and not args.skip_build:
        print(f"Build artifacts: {build_dir}")


if __name__ == "__main__":
    main()
