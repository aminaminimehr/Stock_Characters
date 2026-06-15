#!/usr/bin/env python3
"""Orchestrate isolated Green SAS replication pipeline."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

MODULE_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(MODULE_ROOT))

from config import (  # noqa: E402
    CHECKPOINT_DIR,
    DEFAULT_SAMPLE_END,
    DEFAULT_SAMPLE_START,
    DIAGNOSTICS_DIR,
    FINAL_OUTPUT_PARQUET,
    IBES_COLUMNS,
    OUTPUT_DIR,
    PIPELINE_STAGES,
)
from modules.annual_compustat import run_annual_compustat  # noqa: E402
from modules.annual_to_monthly_timing import align_annual_to_monthly  # noqa: E402
from modules.ccm_linking import run_ccm_annual  # noqa: E402
from modules.crsp_daily import add_crsp_daily_variables  # noqa: E402
from modules.crsp_monthly import add_crsp_monthly_variables  # noqa: E402
from modules.ibes_stubs import apply_ibes_stubs  # noqa: E402
from modules.quarterly_compustat import merge_quarterly_to_monthly, run_quarterly_compustat  # noqa: E402
from modules.validation import run_validation, write_validation_reports  # noqa: E402
from modules.winsorization import winsorize_green  # noqa: E402
from wrds_utils import connect_wrds, load_checkpoint, run_wrds_smoke_test, safe_close_wrds, save_checkpoint, set_wrds_debug  # noqa: E402


def apply_final_filters(df):
    import numpy as np
    import pandas as pd

    out = df.copy()
    out = out[out["mve"].notna() & out["mom1m"].notna() & out["bm"].notna()].copy()
    out["eamonth"] = out.get("eamonth", 0).fillna(0)
    out["ipo"] = out.get("ipo", out.get("IPO", 0)).fillna(0)
    if "IPO" in out.columns:
        out = out.rename(columns={"IPO": "ipo"})
    return out


def run_stage(stage: str, db, args):
    sample_start = args.sample_start
    sample_end = args.sample_end

    if stage == "annual_compustat":
        df = run_annual_compustat(db, sample_start, sample_end)
        save_checkpoint(df, stage)
        return df

    if stage == "ccm_annual":
        annual = load_checkpoint("annual_compustat") if args.from_checkpoint else run_stage("annual_compustat", db, args)
        df = run_ccm_annual(db, annual)
        save_checkpoint(df, stage)
        return df

    if stage == "annual_monthly":
        annual = load_checkpoint("ccm_annual")
        df = align_annual_to_monthly(db, annual, sample_start, sample_end)
        save_checkpoint(df, stage)
        return df

    if stage == "quarterly_compustat":
        df = run_quarterly_compustat(db, sample_start, sample_end)
        save_checkpoint(df, stage)
        return df

    if stage == "merge_quarterly":
        monthly = load_checkpoint("annual_monthly")
        quarterly = load_checkpoint("quarterly_compustat") if args.from_checkpoint else run_stage(
            "quarterly_compustat", db, args
        )
        df = merge_quarterly_to_monthly(monthly, quarterly)
        save_checkpoint(df, stage)
        return df

    if stage == "ibes_stubs":
        df = apply_ibes_stubs(load_checkpoint("merge_quarterly"))
        save_checkpoint(df, stage)
        return df

    if stage == "crsp_monthly":
        df = add_crsp_monthly_variables(load_checkpoint("ibes_stubs"))
        save_checkpoint(df, stage)
        return df

    if stage == "crsp_daily":
        df = add_crsp_daily_variables(db, load_checkpoint("crsp_monthly"), sample_start, sample_end)
        save_checkpoint(df, stage)
        return df

    if stage == "final_filters":
        src = "crsp_daily" if _checkpoint_exists("crsp_daily") else "crsp_monthly"
        df = apply_final_filters(load_checkpoint(src))
        save_checkpoint(df, stage)
        return df

    if stage == "winsorize":
        src = "final_filters" if _checkpoint_exists("final_filters") else "crsp_daily"
        df = winsorize_green(load_checkpoint(src))
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        df.to_parquet(FINAL_OUTPUT_PARQUET, index=False)
        save_checkpoint(df, stage)
        return df

    raise ValueError(f"Unknown stage: {stage}")


def _checkpoint_exists(name: str) -> bool:
    return (CHECKPOINT_DIR / f"{name}.parquet").exists()


def run_pipeline(args) -> None:
    stages = PIPELINE_STAGES
    if args.stage:
        if args.stage not in stages:
            raise ValueError(f"Stage must be one of {stages}")
        stages = [args.stage]

    db = None if args.no_wrds else connect_wrds(args.wrds_user)
    try:
        for stage in stages:
            print(f"Running stage: {stage}", flush=True)
            if args.no_wrds and stage not in {"winsorize", "final_filters"}:
                if not _checkpoint_exists(stage):
                    raise RuntimeError(f"--no-wrds set but checkpoint missing for stage {stage}")
                continue
            run_stage(stage, db, args)
    finally:
        safe_close_wrds()

    if args.validate_only or not args.skip_validation:
        validate_output(args)


def validate_output(args) -> None:
    import pandas as pd

    if FINAL_OUTPUT_PARQUET.exists():
        py = pd.read_parquet(FINAL_OUTPUT_PARQUET)
    elif _checkpoint_exists("winsorize"):
        py = load_checkpoint("winsorize")
    else:
        raise FileNotFoundError("No replication output found for validation.")

    report, summary = run_validation(
        py,
        sample_start=args.sample_start,
        sample_end=args.sample_end,
        exclude_vars=set(),
    )
    write_validation_reports(report, summary, args.sample_start, args.sample_end)
    _write_ibes_report()
    _write_imperfect_notes(report)
    print(f"Validation written to {DIAGNOSTICS_DIR}", flush=True)


def _write_ibes_report() -> None:
    lines = [
        "# IBES Exclusion Report",
        "",
        "Direct IBES WRDS access is unavailable for this replication. IBES-dependent",
        "variables are retained in the output schema as missing (or Compustat fallback for `sue`).",
        "",
        "| Variable | SAS lines | IBES table | Status | Fallback | Output treatment |",
        "|----------|-----------|------------|--------|----------|------------------|",
        "| sue | 684-686 | ibes.statsum_epsus (fpi=6) | Partial | che/mveq when IBES missing | Compustat-only `che/mveq` always |",
        "| disp | 830-831 | ibes.statsum_epsus (fpi=1) | Excluded | None | Column present, NaN |",
        "| chfeps | 832-833 | ibes.statsum_epsus (fpi=1) | Excluded | None | Column present, NaN |",
        "| fgr5yr | 836-856 | ibes.statsum_epsus (fpi=0) | Excluded | None | Column present, NaN |",
        "| meanrec | 858-867 | ibes.recdsum | Excluded | None | Column present, NaN |",
        "| chrec | 872-879 | ibes.recdsum | Excluded | None | Column present, NaN |",
        "| nanalyst | 897-923 | ibes.statsum_epsus | Excluded | Set to 0 post-1989 in SAS cleanup | NaN then 0 post-1989 per SAS cleanup |",
        "| sfe | 899 | ibes.statsum_epsus | Excluded | None | Column present, NaN |",
        "| meanest | 899 | ibes.statsum_epsus | Excluded | None | Column present, NaN |",
        "| ltg | 914-915 | Derived from fgr5yr | Excluded | 0/1 indicator from fgr5yr | 0 post-1989 when fgr5yr missing |",
        "| chnanalyst | 960 | nanalyst lag | Excluded | Depends on nanalyst | NaN / rule-based on stub nanalyst |",
        "",
        "## SUE divergence note",
        "",
        "Green SAS sets `sue = (actual - medest) / abs(prccq)` when IBES forecast and actual",
        "are available; otherwise `sue = che/mveq`. This replication always uses `che/mveq`,",
        "so agreement with Green SAS will be imperfect wherever IBES was used in the benchmark.",
    ]
    path = DIAGNOSTICS_DIR / "ibes_exclusion_report.md"
    DIAGNOSTICS_DIR.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def _write_imperfect_notes(report) -> None:
    import pandas as pd

    if report.empty:
        return
    bad = report[
        (report["pearson"] < 0.99) | report["pearson"].isna()
    ].sort_values("pearson", na_position="first")
    lines = [
        "# Imperfect Match Notes",
        "",
        "Variables with Pearson correlation below 0.99 vs Green SAS benchmark.",
        "",
        bad[["variable", "pearson", "paired_rows", "coverage_diff", "median_abs_diff"]].to_markdown(index=False),
        "",
        "## Common causes",
        "",
        "- WRDS data revisions vs frozen Green SAS output",
        "- IBES-only paths (see ibes_exclusion_report.md)",
        "- SAS vs Python numerical differences (std across lags, proc reg, intnx)",
        "- Exchange history construction from crsp.mseall",
    ]
    (DIAGNOSTICS_DIR / "imperfect_match_notes.md").write_text("\n".join(lines), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description="Green SAS replication pipeline")
    parser.add_argument("--wrds-user", default=None)
    parser.add_argument("--sample-start", default=DEFAULT_SAMPLE_START)
    parser.add_argument("--sample-end", default=DEFAULT_SAMPLE_END)
    parser.add_argument("--stage", default=None, choices=PIPELINE_STAGES)
    parser.add_argument("--from-checkpoint", action="store_true")
    parser.add_argument("--validate-only", action="store_true")
    parser.add_argument("--skip-validation", action="store_true")
    parser.add_argument("--no-wrds", action="store_true")
    parser.add_argument(
        "--smoke-test",
        action="store_true",
        help="Verify WRDS connectivity with a single SELECT 1 query, then exit.",
    )
    parser.add_argument(
        "--debug-wrds",
        action="store_true",
        help="Print WRDS connection lifecycle and raw_sql calls.",
    )
    args = parser.parse_args()

    set_wrds_debug(args.debug_wrds)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    CHECKPOINT_DIR.mkdir(parents=True, exist_ok=True)

    if args.smoke_test:
        raise SystemExit(run_wrds_smoke_test(args.wrds_user))

    if args.validate_only:
        validate_output(args)
        return

    run_pipeline(args)


if __name__ == "__main__":
    main()
