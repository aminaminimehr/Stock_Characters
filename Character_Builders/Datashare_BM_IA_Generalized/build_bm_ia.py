"""Build bm_ia: datashare-convention industry-adjusted book-to-market.

bm_ia = book_to_market - mean(book_to_market) over (SIC2, signal month),
with the equal-weight mean recomputed every month (see docs/gkx/
datashare_reverse_engineering.md, 2026-07-09/10 updates).

WRDS-free: reads the already-built book_to_market.csv from
outputs/characteristics/individual/ and writes a monthly-native CSV that
build_all_character_panel.py auto-merges. Run AFTER build_book_to_market.py.
"""
import argparse
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))
sys.path.append(str(Path(__file__).resolve().parents[2]))

from _shared.bm_ia_builder import build_bm_ia_character
from output_paths import CHARACTER_INDIVIDUAL_DIR, resolve_output_path


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Build bm_ia (SIC2 x month demeaned book-to-market, datashare convention)."
    )
    parser.add_argument(
        "--bm-csv",
        default=str(CHARACTER_INDIVIDUAL_DIR / "book_to_market.csv"),
        help="Path to the annual book_to_market.csv produced by build_book_to_market.py.",
    )
    parser.add_argument("--output", default="bm_ia.csv")
    parser.add_argument("--industry-digits", type=int, default=2)
    parser.add_argument("--stat", default="mean", choices=("mean", "median"))
    args = parser.parse_args()

    bm_csv = Path(args.bm_csv)
    if not bm_csv.exists():
        raise FileNotFoundError(
            f"{bm_csv} not found. Build it first with "
            "Character_Builders/HXZ_BM_Generalized/build_book_to_market.py."
        )

    out = build_bm_ia_character(
        bm_csv,
        industry_digits=args.industry_digits,
        stat=args.stat,
    )

    output_path = resolve_output_path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(output_path, index=False)
    print(f"Saved bm_ia to: {output_path.resolve()}")
    print(f"Rows: {len(out):,}  permnos: {out['permno'].nunique():,}")
    print(f"non-null bm_ia: {out['bm_ia'].notna().sum():,}")
