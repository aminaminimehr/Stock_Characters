"""Build bm_ia from bm.csv (SIC2 x month demean, datashare convention)."""
import argparse
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))
sys.path.append(str(Path(__file__).resolve().parents[2]))

from _shared.bm_ia_builder import build_bm_ia_character
from output_paths import CHARACTER_INDIVIDUAL_DIR, resolve_output_path


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Build bm_ia from bm.csv.")
    parser.add_argument(
        "--bm-csv",
        default=str(CHARACTER_INDIVIDUAL_DIR / "bm.csv"),
        help="Path to annual bm.csv from HXZ_BM_Generalized/build_book_to_market.py.",
    )
    parser.add_argument("--output", default="bm_ia.csv")
    args = parser.parse_args()

    bm_csv = Path(args.bm_csv)
    if not bm_csv.exists():
        raise FileNotFoundError(
            f"{bm_csv} not found. Build it first with "
            "Character_Builders/HXZ_BM_Generalized/build_book_to_market.py."
        )

    out = build_bm_ia_character(bm_csv)

    output_path = resolve_output_path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(output_path, index=False)
    print(f"Saved bm_ia to: {output_path.resolve()}")
    print(f"Rows: {len(out):,}  permnos: {out['permno'].nunique():,}")
    print(f"non-null bm_ia: {out['bm_ia'].notna().sum():,}")
