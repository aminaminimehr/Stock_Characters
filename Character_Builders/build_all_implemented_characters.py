"""Build all 95 datashare character CSVs from WRDS (except bm, operprof, bm_ia)."""
import argparse
import sys
from pathlib import Path

from _shared.beta_builder import build_factor_characters, clear_factor_caches
from _shared.event_builders import build_aeavol_character, build_ear_character
from _shared.ms_builder import build_ms_character
from _shared.green_builders import (
    ANNUAL_CHARACTER_INFO,
    DAILY_MONTHLY_CHARACTER_INFO,
    MONTHLY_CHARACTER_INFO,
    attach_permno,
    build_all_monthly_characters,
    clear_monthly_crsp_cache,
    compute_annual_characters,
    compute_industry_adjusted_annual,
    connect_wrds,
    load_annual_age_lookup,
    load_annual_orgcap_lookup,
    load_annual_compustat,
    load_green_ccm_links,
    load_daily_monthly,
    load_monthly_alignment_frame,
    write_character,
)
from _shared.quarterly_builders import (
    QUARTERLY_CHARACTER_INFO,
    build_quarterly_character,
    prepare_quarterly_compustat_panel,
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))
from output_paths import CHARACTER_INDIVIDUAL_DIR, ensure_output_tree  # noqa: E402
from pipeline_config import DATASHARE_COLUMNS, SKIP_IBES  # noqa: E402

OUTPUT_DIR = CHARACTER_INDIVIDUAL_DIR
ANNUAL_ID_COLUMNS = ["permno", "permco", "gvkey", "datadate", "sic", "fyear"]

# Built by HXZ subprocess jobs in run_full_pipeline.py, not this script.
HXZ_EXTERNAL = frozenset({"bm", "operprof", "bm_ia"})


def _should_write(name: str) -> bool:
    return name in DATASHARE_COLUMNS and name not in HXZ_EXTERNAL


def build_annual_characters(db, output_dir):
    comp = compute_annual_characters(
        load_annual_compustat(db),
        age_lookup=load_annual_age_lookup(db),
        orgcap_lookup=load_annual_orgcap_lookup(db),
    )
    comp = attach_permno(comp, load_green_ccm_links(db))
    comp = compute_industry_adjusted_annual(comp)

    for character in ANNUAL_CHARACTER_INFO:
        if not _should_write(character):
            continue
        if character not in comp.columns:
            print(f"{character}: skipped (not in annual comp frame)")
            continue
        write_character(comp[ANNUAL_ID_COLUMNS + [character]], character, output_dir)


def build_monthly_characters(db, output_dir):
    pending = [c for c in MONTHLY_CHARACTER_INFO if _should_write(c)]
    if not pending:
        return
    monthly_outputs = build_all_monthly_characters(db, pending)
    for character, out in monthly_outputs.items():
        write_character(out, character, output_dir)


def build_quarterly_characters(db, output_dir):
    quarterly_chars = [c for c in QUARTERLY_CHARACTER_INFO if _should_write(c)]
    if not quarterly_chars:
        return
    print("Loading quarterly Compustat panel once for all quarterly characters...")
    quarterly_comp = prepare_quarterly_compustat_panel(db, use_ibes=not SKIP_IBES)
    for character in quarterly_chars:
        out = build_quarterly_character(
            db,
            character,
            use_ibes=not SKIP_IBES,
            comp=quarterly_comp,
        )
        write_character(out, character, output_dir)


def build_special_characters(db, output_dir, workers=None):
    factor_names = [n for n in ("beta", "betasq", "idiovol", "pricedelay") if _should_write(n)]
    if factor_names:
        clear_factor_caches()
        try:
            factor_outputs = build_factor_characters(
                db, output_dir, workers=workers, names=tuple(factor_names)
            )
            for name, out in factor_outputs.items():
                write_character(out, name, output_dir)
        finally:
            clear_factor_caches()

    if _should_write("ear"):
        write_character(build_ear_character(db, workers=workers), "ear", output_dir)
    if _should_write("aeavol"):
        write_character(build_aeavol_character(db, workers=workers), "aeavol", output_dir)
    if _should_write("ms"):
        write_character(
            build_ms_character(db, use_ibes=not SKIP_IBES, workers=workers),
            "ms",
            output_dir,
        )


def build_daily_monthly_characters(db, output_dir):
    daily = load_daily_monthly(db)
    monthly = load_monthly_alignment_frame(output_dir, db=db)

    for character in DAILY_MONTHLY_CHARACTER_INFO:
        if not _should_write(character):
            continue
        out = monthly.merge(
            daily[["permno", "source_yyyymm", character]],
            on=["permno", "source_yyyymm"],
            how="left",
        )
        out = out[
            ["permno", "permco", "date", "signal_yyyymm", "target_yyyymm", "sic", "exchcd", "shrcd", character]
        ]
        write_character(out, character, output_dir)


def main():
    parser = argparse.ArgumentParser(description="Build datashare character CSVs from WRDS.")
    parser.add_argument("--wrds-user", default=None)
    parser.add_argument("--output-dir", default=OUTPUT_DIR)
    parser.add_argument(
        "--workers",
        type=int,
        default=None,
        help="Parallel workers for beta/ear/aeavol/ms builders.",
    )
    args = parser.parse_args()

    ensure_output_tree()
    output_dir = Path(args.output_dir)
    if not output_dir.is_absolute():
        output_dir = PROJECT_ROOT / output_dir
    output_dir.mkdir(parents=True, exist_ok=True)

    db = connect_wrds(args.wrds_user)
    try:
        clear_monthly_crsp_cache()
        build_annual_characters(db, output_dir)
        build_monthly_characters(db, output_dir)
        build_quarterly_characters(db, output_dir)
        build_special_characters(db, output_dir, workers=args.workers)
        build_daily_monthly_characters(db, output_dir)
    finally:
        clear_monthly_crsp_cache()
        db.close()


if __name__ == "__main__":
    main()
