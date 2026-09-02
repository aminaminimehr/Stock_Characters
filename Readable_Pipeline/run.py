#!/usr/bin/env python3
"""Run independent per-character builders and merge the 95-column panel."""
from __future__ import annotations

import argparse
import importlib
import sys
from pathlib import Path

READABLE_ROOT = Path(__file__).resolve().parent
STOCK_ROOT = READABLE_ROOT.parent
BUILDERS_DIR = READABLE_ROOT / "02_builders"
DEFS_DIR = READABLE_ROOT / "01_definitions"

for path in (STOCK_ROOT, READABLE_ROOT, DEFS_DIR, BUILDERS_DIR):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from catalog import BUILD_ORDER  # noqa: E402
from config import DATASHARE_PREDICTORS  # noqa: E402
from paths import ensure_output_tree  # noqa: E402
from panel import write_signal_panel  # noqa: E402
from wrds_io import connect_wrds  # noqa: E402

from all_builds import BUILDERS  # noqa: E402


def load_builder(stem: str):
    mod = importlib.import_module(stem)
    fn = getattr(mod, f"build_{stem}", None)
    if fn is None:
        fn = BUILDERS.get(stem)
    if fn is None:
        raise KeyError(f"No builder for {stem!r}")
    return fn


def run_character(db, stem: str, use_cache: bool = True) -> None:
    print(f"\n=== Building {stem} ===", flush=True)
    build = load_builder(stem)
    build(db, use_cache=use_cache)


def run_all(db, use_cache: bool = True, stems: list[str] | None = None) -> None:
    order = stems or BUILD_ORDER
    for stem in order:
        if stem not in BUILDERS:
            print(f"Skipping unknown stem: {stem}", flush=True)
            continue
        run_character(db, stem, use_cache=use_cache)


def main():
    parser = argparse.ArgumentParser(description="Readable independent character pipeline.")
    parser.add_argument("--wrds-user", default=None)
    parser.add_argument("--character", default=None, help="Build one stem (e.g. ep)")
    parser.add_argument("--all", action="store_true", help="Build all 95 characters in dependency order")
    parser.add_argument("--panel", action="store_true", help="Merge single_characters/ Parquet files into panel CSV")
    parser.add_argument("--skip-cache", action="store_true", help="Ignore per-stem parquet caches")
    parser.add_argument("--list", action="store_true", help="List available stems")
    args = parser.parse_args()

    if args.list:
        for stem in DATASHARE_PREDICTORS:
            print(stem)
        return

    ensure_output_tree()
    use_cache = not args.skip_cache

    if args.panel and not args.character and not args.all:
        write_signal_panel()
        return

    db = None
    if args.character or args.all:
        db = connect_wrds(args.wrds_user)
        try:
            if args.character:
                if args.character == "bm_ia" and not (READABLE_ROOT / "03_outputs/single_characters/bm.parquet").exists():
                    run_character(db, "bm", use_cache=use_cache)
                run_character(db, args.character, use_cache=use_cache)
            elif args.all:
                run_all(db, use_cache=use_cache)
        finally:
            db.close()

    if args.panel:
        write_signal_panel()


if __name__ == "__main__":
    main()
