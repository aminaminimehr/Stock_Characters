#!/usr/bin/env python3
"""Diagnose book-to-market and related duplicate columns in the complete panel."""
import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from output_paths import COMPLETE_ALL_PANEL_FILE, DIAGNOSTICS_DIR, LEGACY_FLAT_OUTPUT_DIR  # noqa: E402


BM_COLUMNS = [
    "bm",
    "bm_ia",
    "bmj",
    "book_to_market",
    "book_to_june_market_equity",
    "cfp",
    "cash_flow_to_price",
    "op",
    "operating_profitability",
]

BUILDER_MAP = {
    "bm": "Green shared annual builder (`green_builders.py`) / `Green_BM_IA` sibling",
    "bm_ia": "Green shared annual builder (`green_builders.py`)",
    "book_to_market": "Character_Builders/HXZ_BM_Generalized/build_book_to_market.py",
    "book_to_june_market_equity": "Character_Builders/HXZ_BMJ_Generalized/build_book_to_june_market_equity.py",
    "bmj": "column name in `book_to_june_market_equity.csv` (HXZ BMJ builder)",
    "cfp": "Green shared annual builder (`green_builders.py`)",
    "cash_flow_to_price": "Character_Builders/HXZ_CFP_Generalized/build_cash_flow_to_price.py",
    "op": "Green shared annual builder (`green_builders.py`)",
    "operating_profitability": "Character_Builders/HXZ_OPE_Generalized/build_operating_profitability.py",
}


def resolve_panel_path(user_path: str | None) -> Path:
    if user_path:
        return Path(user_path)
    if COMPLETE_ALL_PANEL_FILE.exists():
        return COMPLETE_ALL_PANEL_FILE
    legacy = LEGACY_FLAT_OUTPUT_DIR / "complete_all_character_prediction_panel.csv"
    if legacy.exists():
        return legacy
    raise FileNotFoundError("complete_all_character_prediction_panel.csv not found")


def compare_pair(df: pd.DataFrame, left: str, right: str) -> dict:
    keys = ["permno", "signal_yyyymm"]
    if not set(keys).issubset(df.columns):
        return {"pair": (left, right), "error": "missing merge keys"}

    sub = df[keys + [left, right]].dropna()
    if sub.empty:
        return {"pair": (left, right), "error": "no overlapping non-missing rows"}

    equal = np.isclose(sub[left], sub[right], rtol=0, atol=1e-8, equal_nan=True)
    corr = sub[[left, right]].corr().iloc[0, 1]
    return {
        "pair": (left, right),
        "rows": len(sub),
        "equal_share": float(equal.mean()),
        "correlation": float(corr),
        "left_nonnull": int(df[left].notna().sum()),
        "right_nonnull": int(df[right].notna().sum()),
    }


def main():
    parser = argparse.ArgumentParser(description="Book-to-market duplicate audit")
    parser.add_argument("--panel", default=None)
    parser.add_argument(
        "--report",
        default=DIAGNOSTICS_DIR / "book_to_market_audit.md",
    )
    parser.add_argument("--max-rows", type=int, default=500_000, help="Sample rows for pairwise stats")
    args = parser.parse_args()

    panel_path = resolve_panel_path(args.panel)
    df = pd.read_csv(panel_path, nrows=args.max_rows)
    present = [c for c in BM_COLUMNS if c in df.columns]

    lines = [
        "# Book-to-market audit",
        "",
        f"Panel file: `{panel_path}`",
        f"Rows read: **{len(df):,}** (cap={args.max_rows:,})",
        "",
        "## Columns present in panel",
        "",
    ]
    for col in present:
        lines.append(f"- `{col}` — built by {BUILDER_MAP.get(col, 'unknown')}")

    lines.extend(["", "## Pairwise comparison", ""])
    pairs = [
        ("bm", "book_to_market"),
        ("cfp", "cash_flow_to_price"),
        ("op", "operating_profitability"),
        ("bm", "bm_ia"),
        ("book_to_market", "bmj"),
        ("book_to_market", "book_to_june_market_equity"),
    ]
    for left, right in pairs:
        if left not in df.columns or right not in df.columns:
            continue
        stats = compare_pair(df, left, right)
        lines.append(f"### `{left}` vs `{right}`")
        if "error" in stats:
            lines.append(f"- {stats['error']}")
        else:
            lines.append(f"- overlapping rows: {stats['rows']:,}")
            lines.append(f"- equal share (atol=1e-8): {stats['equal_share']:.4f}")
            lines.append(f"- correlation: {stats['correlation']:.4f}")
            lines.append(f"- non-null counts: {stats['left_nonnull']:,} vs {stats['right_nonnull']:,}")
        lines.append("")

    lines.extend(
        [
            "## Interpretation notes",
            "",
            "- `bm` (Green) and `book_to_market` (HXZ) are related but not identical "
            "(different book-equity timing and market-equity denominators).",
            "- `cfp` vs `cash_flow_to_price` and `op` vs `operating_profitability` are "
            "parallel Green vs HXZ implementations with separate column names.",
            "- `bmj` / `book_to_june_market_equity` is a distinct June-price variant.",
            "- Do not delete builders until you choose a single convention for research panels.",
            "",
        ]
    )

    report_path = Path(args.report)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text("\n".join(lines), encoding="utf-8")
    print(report_path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    main()
