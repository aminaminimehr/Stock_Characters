#!/usr/bin/env python3
"""Professor-specified exercise: visualize the implied industry mean by SIC2 order.

For a given month, using datashare.csv's own published bm and bm_ia:

    industry_mean := bm - bm_ia          (assumes bm_ia = bm - mean_{sic2,month}(bm))

Build a two-column frame (sic2, industry_mean), sort by sic2 ascending (so stocks
in the same sic2 stay together), add a row index after sorting, and plot
row_index vs industry_mean. If bm_ia really is a clean sic2 x month demean, this
should look like a "staircase" of flat plateaus (one per sic2 code, since every
stock in the same sic2 that month should share the same industry_mean) -- and any
point sitting away from its neighbors' plateau is a stock whose implied benchmark
does not match its published sic2 (the "off-mode" firms discussed in
docs/gkx/BM_BMIA_PROBLEM_README.md).

Produces one PNG per requested month under outputs/diagnostics/.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from output_paths import DIAGNOSTICS_DIR  # noqa: E402

DATASHARE = PROJECT_ROOT / "Supplementary_assistive_files" / "datashare.csv"

DEFAULT_MONTHS = [196506, 197506, 198506, 199506, 200506, 201506]


def load_month_frame(datashare_path: Path, months: list[int]) -> pd.DataFrame:
    frames = []
    for chunk in pd.read_csv(
        datashare_path, usecols=["permno", "DATE", "bm", "bm_ia", "sic2"], chunksize=500_000
    ):
        chunk["month"] = (chunk["DATE"] // 100).astype(int)
        chunk = chunk[chunk["month"].isin(months)]
        if not chunk.empty:
            frames.append(chunk.drop(columns=["DATE"]))
    if not frames:
        return pd.DataFrame(columns=["permno", "bm", "bm_ia", "sic2", "month"])
    return pd.concat(frames, ignore_index=True)


def plot_month(df: pd.DataFrame, month: int, out_dir: Path) -> Path:
    sub = df[df["month"] == month].copy()
    sub = sub.dropna(subset=["sic2", "bm", "bm_ia"])
    sub["industry_mean"] = sub["bm"] - sub["bm_ia"]

    frame = sub[["sic2", "industry_mean"]].sort_values("sic2", kind="mergesort").reset_index(drop=True)
    frame["row_index"] = frame.index

    fig, ax = plt.subplots(figsize=(13, 5))
    scatter = ax.scatter(
        frame["row_index"], frame["industry_mean"],
        c=frame["sic2"], cmap="viridis", s=6, linewidths=0,
    )
    # light vertical guides at each sic2 boundary so plateaus/steps are visible
    boundaries = frame.index[frame["sic2"].ne(frame["sic2"].shift())].tolist()
    for b in boundaries:
        ax.axvline(b, color="grey", alpha=0.15, linewidth=0.5)

    ax.set_xlabel("Row index (rows sorted by sic2 ascending)")
    ax.set_ylabel("industry_mean = bm - bm_ia")
    ax.set_title(
        f"Datashare implied industry mean, sorted by SIC2 -- {month}\n"
        f"({frame['sic2'].nunique()} distinct SIC2 codes, {len(frame):,} stocks)"
    )
    cbar = fig.colorbar(scatter, ax=ax, pad=0.01)
    cbar.set_label("sic2")
    fig.tight_layout()

    out_path = out_dir / f"professor_exercise_industry_mean_sic2_{month}.png"
    fig.savefig(out_path, dpi=150)
    plt.close(fig)
    return out_path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--datashare", type=Path, default=DATASHARE)
    parser.add_argument("--months", type=int, nargs="+", default=DEFAULT_MONTHS)
    parser.add_argument("--out-dir", type=Path, default=DIAGNOSTICS_DIR)
    args = parser.parse_args()

    if not args.datashare.exists():
        raise FileNotFoundError(f"datashare not found: {args.datashare}")
    args.out_dir.mkdir(parents=True, exist_ok=True)

    print(f"Loading datashare bm/bm_ia/sic2 for months: {args.months}", flush=True)
    df = load_month_frame(args.datashare, args.months)
    print(f"  rows loaded: {len(df):,}", flush=True)

    written = []
    for month in args.months:
        n = int((df["month"] == month).sum())
        if n == 0:
            print(f"  {month}: no rows found, skipping", flush=True)
            continue
        path = plot_month(df, month, args.out_dir)
        written.append(path)
        print(f"  {month}: {n:,} rows -> {path.name}", flush=True)

    print("\nWrote:")
    for p in written:
        print(f"  {p}")


if __name__ == "__main__":
    main()
