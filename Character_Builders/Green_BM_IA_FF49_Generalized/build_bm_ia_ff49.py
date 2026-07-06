import argparse
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

from _shared.bm_ia_ff49_builder import build_bm_ia_ff49_character
from _shared.ccm import add_ccm_arguments
from _shared.green_builders import OUTPUT_DIR, connect_wrds


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Build bm_ia_ff49: FF49 × datadate industry-adjusted book-to-market (GKX)."
    )
    parser.add_argument("--wrds-user", default=None)
    parser.add_argument("--output", default="bm_ia_ff49.csv")
    add_ccm_arguments(parser)
    args = parser.parse_args()

    db = connect_wrds(args.wrds_user)
    try:
        out = build_bm_ia_ff49_character(db, args.ccm_linktypes, args.ccm_linkprim)
    finally:
        db.close()

    output_path = Path(args.output)
    if not output_path.is_absolute():
        output_path = OUTPUT_DIR / output_path
    output_path.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(output_path, index=False)
    print(f"Saved bm_ia_ff49 to: {output_path.resolve()}")
    print(f"Rows: {len(out):,}")
