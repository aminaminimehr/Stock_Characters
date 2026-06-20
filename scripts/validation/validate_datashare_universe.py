"""Validate datashare universe coverage and correlation for bm, operprof, cfp."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

DEFAULT_DATASHARE = PROJECT_ROOT / "Supplementary_assistive_files" / "datashare.csv"
DEFAULT_PANEL = PROJECT_ROOT / "outputs" / "panels" / "all_character_signal_panel.csv"
REPORT_MD = PROJECT_ROOT / "docs" / "gkx" / "datashare_universe_validation_report.md"
REPORT_CSV = PROJECT_ROOT / "outputs" / "diagnostics" / "datashare_universe_validation.csv"

MAPPING = {
    "bm": "book_to_market",
    "operprof": "operating_profitability",
    "cfp": "cfp",
}


def load_datashare(path: Path, cols: list[str]) -> pd.DataFrame:
    usecols = ["permno", "DATE"] + cols
    chunks = []
    for chunk in pd.read_csv(path, usecols=usecols, chunksize=500_000):
        chunk["permno"] = pd.to_numeric(chunk["permno"], errors="coerce").astype("Int64")
        chunk["target_yyyymm"] = (pd.to_numeric(chunk["DATE"], errors="coerce") // 100).astype("Int64")
        chunk["signal_yyyymm"] = chunk["target_yyyymm"].map(_month_add_minus_one)
        chunks.append(chunk)
    return pd.concat(chunks, ignore_index=True)


def _month_add_minus_one(yyyymm: int) -> int:
    if pd.isna(yyyymm):
        return pd.NA
    y, m = int(yyyymm) // 100, int(yyyymm) % 100
    m -= 1
    if m == 0:
        return (y - 1) * 100 + 12
    return y * 100 + m


def load_panel(path: Path, repo_col: str) -> pd.DataFrame:
    df = pd.read_csv(path, usecols=["permno", "signal_yyyymm", "target_yyyymm", repo_col])
    df["permno"] = pd.to_numeric(df["permno"], errors="coerce").astype("Int64")
    df = df.rename(columns={repo_col: "repo_val"})
    return df.dropna(subset=["permno", repo_col])


def coverage_and_metrics(
    ds: pd.DataFrame,
    repo: pd.DataFrame,
    ds_col: str,
    join_on: str,
) -> dict:
    ds_keys = ds.loc[ds[ds_col].notna(), ["permno", join_on, ds_col]].copy()
    ds_keys = ds_keys.rename(columns={join_on: "month", ds_col: "ds_val"})
    repo_keys = repo.loc[repo["repo_val"].notna(), ["permno", join_on, "repo_val"]].copy()
    repo_keys = repo_keys.rename(columns={join_on: "month"})

    ds_set = set(map(tuple, ds_keys[["permno", "month"]].itertuples(index=False, name=None)))
    repo_set = set(map(tuple, repo_keys[["permno", "month"]].itertuples(index=False, name=None)))
    both_set = ds_set & repo_set
    ds_only = ds_set - repo_set
    repo_only = repo_set - ds_set

    merged = ds_keys.merge(repo_keys, on=["permno", "month"], how="inner")
    merged = merged.dropna(subset=["ds_val", "repo_val"])

    out = {
        "datashare_col": ds_col,
        "repo_col": MAPPING[ds_col],
        "join_key": join_on,
        "keys_datashare": len(ds_set),
        "keys_repo": len(repo_set),
        "keys_both": len(both_set),
        "datashare_only": len(ds_only),
        "repo_only": len(repo_only),
        "permno_datashare": ds_keys["permno"].nunique(),
        "permno_repo": repo_keys["permno"].nunique(),
        "permno_both": merged["permno"].nunique() if len(merged) else 0,
        "paired_obs": len(merged),
        "median_monthly_rho": np.nan,
        "pooled_rho": np.nan,
        "exact_pct": np.nan,
    }

    if len(merged) < 2:
        return out

    rhos = []
    for _, g in merged.groupby("month"):
        if len(g) < 30:
            continue
        r = g["repo_val"].corr(g["ds_val"], method="spearman")
        if pd.notna(r):
            rhos.append(r)
    diff = (merged["repo_val"] - merged["ds_val"]).abs()
    out["median_monthly_rho"] = float(np.median(rhos)) if rhos else np.nan
    out["pooled_rho"] = float(merged["repo_val"].corr(merged["ds_val"], method="spearman"))
    out["exact_pct"] = float((diff <= 1e-4).mean()) * 100
    return out


def format_report(rows: list[dict], panel: Path, datashare: Path) -> str:
    lines = [
        "# Datashare universe validation",
        "",
        f"Panel: `{panel.relative_to(PROJECT_ROOT).as_posix()}`",
        f"Datashare: `{datashare.relative_to(PROJECT_ROOT).as_posix()}`",
        "",
        "Compares **coverage first**, then Spearman on the intersection (`keys_both`).",
        "`bm_ia` is out of scope.",
        "",
        "| datashare | repo | join | keys_ds | keys_repo | both | ds_only | repo_only | permno_both | median rho | pooled rho | exact % |",
        "|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for r in rows:
        lines.append(
            f"| {r['datashare_col']} | {r['repo_col']} | {r['join_key']} | "
            f"{r['keys_datashare']:,} | {r['keys_repo']:,} | {r['keys_both']:,} | "
            f"{r['datashare_only']:,} | {r['repo_only']:,} | {r['permno_both']:,} | "
            f"{r['median_monthly_rho']:.4f} | {r['pooled_rho']:.4f} | {r['exact_pct']:.1f} |"
        )
    lines.append("")
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--datashare", default=str(DEFAULT_DATASHARE))
    parser.add_argument("--panel", default=str(DEFAULT_PANEL))
    parser.add_argument(
        "--join",
        choices=("signal_yyyymm", "target_yyyymm"),
        default="target_yyyymm",
        help="Month key for panel side (default target = datashare DATE month).",
    )
    args = parser.parse_args()

    datashare = Path(args.datashare)
    panel = Path(args.panel)
    if not datashare.exists():
        raise SystemExit(f"Missing datashare: {datashare}")
    if not panel.exists():
        raise SystemExit(f"Missing panel: {panel} — build with --profile datashare first.")

    ds = load_datashare(datashare, list(MAPPING.keys()))
    repo_panel = pd.read_csv(panel, low_memory=False)

    rows = []
    for ds_col, repo_col in MAPPING.items():
        if repo_col not in repo_panel.columns:
            rows.append(
                {
                    "datashare_col": ds_col,
                    "repo_col": repo_col,
                    "join_key": args.join,
                    "keys_datashare": 0,
                    "keys_repo": 0,
                    "keys_both": 0,
                    "datashare_only": 0,
                    "repo_only": 0,
                    "permno_datashare": 0,
                    "permno_repo": 0,
                    "permno_both": 0,
                    "paired_obs": 0,
                    "median_monthly_rho": np.nan,
                    "pooled_rho": np.nan,
                    "exact_pct": np.nan,
                }
            )
            continue
        repo = repo_panel[["permno", "signal_yyyymm", "target_yyyymm", repo_col]].copy()
        repo["permno"] = pd.to_numeric(repo["permno"], errors="coerce").astype("Int64")
        repo = repo.rename(columns={repo_col: "repo_val"})
        rows.append(coverage_and_metrics(ds, repo, ds_col, args.join))

    REPORT_CSV.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_csv(REPORT_CSV, index=False)
    REPORT_MD.write_text(format_report(rows, panel, datashare), encoding="utf-8")
    print(REPORT_MD.read_text(encoding="utf-8"))


if __name__ == "__main__":
    main()
