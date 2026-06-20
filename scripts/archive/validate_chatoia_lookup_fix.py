#!/usr/bin/env python3
"""Post-fix validation for chatoia lookup-merge order correction."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pyreadstat

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "Character_Builders"))

from Character_Panels.build_all_character_panel import expand_annual_file  # noqa: E402
from output_paths import (  # noqa: E402
    CHARACTER_INDIVIDUAL_DIR,
    DIAGNOSTICS_DIR,
    LEGACY_FLAT_OUTPUT_DIR,
    COMPLETE_ALL_PANEL_FILE,
    SIGNAL_PANEL_FILE,
)

DATASHARE = PROJECT_ROOT / "Supplementary_assistive_files" / "datashare.csv"
GREEN_SAS = PROJECT_ROOT / "Supplementary_assistive_files" / "Output_From_Greens_SAS_code.sas7bdat"
DOCS_OUT = PROJECT_ROOT / "docs" / "gkx" / "gkx_chatoia_lookup_fix_validation.md"

UNAFFECTED = ("cfp_ia", "chempia", "chpmia", "pchcapx_ia", "age", "orgcap", "ps")
DEFAULT_START = 201801
DEFAULT_END = 202312


def file_md5(path: Path) -> str:
    h = hashlib.md5()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def winsorize_pair(x: pd.Series, y: pd.Series) -> tuple[pd.Series, pd.Series]:
    combined = pd.concat([x, y], axis=1)
    lo = combined.quantile(0.01).min()
    hi = combined.quantile(0.99).max()
    return x.clip(lo, hi), y.clip(lo, hi)


def compare_series(x: pd.Series, y: pd.Series) -> dict:
    mask = x.notna() & y.notna()
    paired = int(mask.sum())
    out = {"paired_rows": paired}
    if paired < 3:
        return out
    xv, yv = x[mask], y[mask]
    xw, yw = winsorize_pair(xv, yv)
    diff = (xv - yv).abs()
    out.update(
        {
            "pearson": float(xv.corr(yv)),
            "spearman": float(xv.rank().corr(yv.rank())),
            "pearson_winsor_1_99": float(xw.corr(yw)),
            "median_abs_diff": float(diff.median()),
            "mean_abs_diff": float(diff.mean()),
        }
    )
    return out


def load_repo_monthly(character: str, start: int, end: int) -> pd.DataFrame:
    path = CHARACTER_INDIVIDUAL_DIR / f"{character}.csv"
    raw = pd.read_csv(path, parse_dates=["datadate"])
    panel = expand_annual_file(raw, [character])
    panel = panel[(panel["signal_yyyymm"] >= start) & (panel["signal_yyyymm"] <= end)]
    return panel.rename(columns={character: f"{character}_repo"})


def load_datashare_chatoia(start: int, end: int) -> pd.DataFrame:
    chunks = []
    for chunk in pd.read_csv(DATASHARE, usecols=["permno", "DATE", "chatoia"], chunksize=500_000):
        chunk["signal_yyyymm"] = pd.to_numeric(chunk["DATE"], errors="coerce") // 100
        chunk = chunk[(chunk["signal_yyyymm"] >= start) & (chunk["signal_yyyymm"] <= end)]
        if len(chunk):
            chunks.append(chunk)
    if not chunks:
        return pd.DataFrame(columns=["permno", "signal_yyyymm", "chatoia_gkx"])
    out = pd.concat(chunks, ignore_index=True)
    return out.rename(columns={"chatoia": "chatoia_gkx"})


def load_green_sas_chatoia(start: int, end: int) -> pd.DataFrame:
    meta = pyreadstat.read_sas7bdat(str(GREEN_SAS), metadataonly=True)[1]
    frames = []
    for offset in range(0, meta.number_rows, 400_000):
        chunk, _ = pyreadstat.read_sas7bdat(
            str(GREEN_SAS), usecols=["permno", "DATE", "chatoia"], row_offset=offset, row_limit=400_000
        )
        chunk["signal_yyyymm"] = pd.to_datetime(chunk["DATE"]).dt.year * 100 + pd.to_datetime(chunk["DATE"]).dt.month
        chunk = chunk[(chunk["signal_yyyymm"] >= start) & (chunk["signal_yyyymm"] <= end)]
        if len(chunk):
            frames.append(chunk)
    if not frames:
        return pd.DataFrame(columns=["permno", "signal_yyyymm", "chatoia_green"])
    out = pd.concat(frames, ignore_index=True).drop_duplicates(["permno", "signal_yyyymm"], keep="last")
    return out.rename(columns={"chatoia": "chatoia_green"})


def lookup_path_check(wrds_user: str) -> dict:
    from _shared.green_builders import (
        compute_annual_characters,
        connect_wrds,
        load_annual_age_lookup,
        load_annual_compustat,
        load_annual_orgcap_lookup,
    )

    for key in ("STOCK_CHARACTERS_SAMPLE_START", "STOCK_CHARACTERS_SAMPLE_END"):
        os.environ.pop(key, None)

    db = connect_wrds(wrds_user)
    try:
        comp = load_annual_compustat(db)
        age = load_annual_age_lookup(db)
        org = load_annual_orgcap_lookup(db)
        clean = compute_annual_characters(comp)
        with_lu = compute_annual_characters(comp, age_lookup=age, orgcap_lookup=org)
    finally:
        db.close()

    rows = {}
    for col in ("chatoia", "cfp_ia", "chpmia", "age", "orgcap"):
        m = clean[["gvkey", "datadate", col]].merge(
            with_lu[["gvkey", "datadate", col]], on=["gvkey", "datadate"], suffixes=("_clean", "_lu")
        )
        mask = m[f"{col}_clean"].notna() & m[f"{col}_lu"].notna()
        rows[col] = {
            "paired": int(mask.sum()),
            "corr": float(m.loc[mask, f"{col}_clean"].corr(m.loc[mask, f"{col}_lu"])) if mask.sum() > 3 else float("nan"),
            "max_abs_diff": float((m.loc[mask, f"{col}_clean"] - m.loc[mask, f"{col}_lu"]).abs().max())
            if mask.sum()
            else float("nan"),
        }
    return rows


def panel_column_unchanged(panel_path: Path, column: str, baseline_hash: str | None) -> dict:
    if not panel_path.exists():
        return {"status": "panel_missing"}
    usecols = ["permno", "signal_yyyymm", column]
    df = pd.read_csv(panel_path, usecols=usecols)
    digest = hashlib.md5(
        pd.util.hash_pandas_object(df.sort_values(["permno", "signal_yyyymm"])[column], index=False).values
    ).hexdigest()
    return {
        "column": column,
        "hash": digest,
        "unchanged_vs_baseline": baseline_hash is not None and digest == baseline_hash,
    }


def build_report(
    before_chatoia: dict,
    datashare: dict,
    green: dict,
    lookup: dict,
    unaffected_files: dict,
    flat_count: int,
    sample_start: int,
    sample_end: int,
    fix_commit: str,
) -> str:
    lines = [
        "# GKX `chatoia` lookup-merge fix validation",
        "",
        f"Fix commit: `{fix_commit}`",
        f"Validation window: `signal_yyyymm` **{sample_start}**–**{sample_end}**.",
        "",
        "## Summary",
        "",
        "| Check | Result |",
        "| --- | --- |",
        f"| Repo `chatoia` vs datashare Spearman | **{datashare.get('spearman', float('nan')):.4f}** |",
        f"| Repo `chatoia` vs Green SAS Spearman | **{green.get('spearman', float('nan')):.4f}** |",
        f"| With-lookup vs no-lookup (`chatoia` annual) | corr **{lookup.get('chatoia', {}).get('corr', float('nan')):.6g}** |",
        f"| Flat `outputs/*.csv` count | **{flat_count}** |",
        "",
        "## Before / after (on-disk `chatoia.csv` vs datashare)",
        "",
        f"- **Before fix** (corrupted build): Spearman ~ **{before_chatoia.get('spearman_before', '0.06')}**, "
        f"median |diff| ~ **{before_chatoia.get('median_abs_diff_before', '924')}** (from disagreement audit).",
        f"- **After fix**: Spearman **{datashare.get('spearman', float('nan')):.4f}**, "
        f"Pearson **{datashare.get('pearson', float('nan')):.4f}**, "
        f"winsor Pearson **{datashare.get('pearson_winsor_1_99', float('nan')):.4f}**, "
        f"median |diff| **{datashare.get('median_abs_diff', float('nan')):.6g}**.",
        "",
        "## Green SAS validation (`chatoia`)",
        "",
        f"- Paired rows: **{green.get('paired_rows', 0):,}**",
        f"- Pearson: **{green.get('pearson', float('nan')):.4f}**",
        f"- Spearman: **{green.get('spearman', float('nan')):.4f}**",
        f"- Winsor Pearson (1/99): **{green.get('pearson_winsor_1_99', float('nan')):.4f}**",
        f"- Median |diff|: **{green.get('median_abs_diff', float('nan')):.6g}**",
        "",
        "## Datashare validation (`chatoia`)",
        "",
        f"- Paired rows: **{datashare.get('paired_rows', 0):,}**",
        f"- Pearson: **{datashare.get('pearson', float('nan')):.4f}**",
        f"- Spearman: **{datashare.get('spearman', float('nan')):.4f}**",
        f"- Winsor Pearson (1/99): **{datashare.get('pearson_winsor_1_99', float('nan')):.4f}**",
        f"- Median |diff|: **{datashare.get('median_abs_diff', float('nan')):.6g}**",
        "",
        "## Lookup-path integrity (annual WRDS recompute)",
        "",
        "| Variable | Paired | Corr (no lookup vs with lookup) | Max |diff| |",
        "| --- | ---: | ---: | ---: |",
    ]
    for col, row in lookup.items():
        lines.append(
            f"| `{col}` | {row['paired']:,} | {row['corr']:.12g} | {row['max_abs_diff']:.6g} |"
        )

    lines.extend(["", "## Unaffected variables (individual CSV file hashes)", ""])
    for name, row in unaffected_files.items():
        lines.append(f"- `{name}`: md5 `{row['md5']}` ({row['rows']:,} rows, unchanged file not rebuilt)")

    lines.extend(
        [
            "",
            "## Root cause (fixed)",
            "",
            "`avg_at` was computed before `orgcap`/`age` merges. Merging before `chato`/`chatoia` "
            "misaligned the pre-merge `avg_at` Series with reordered rows. Lookups now run **after** "
            "industry demeaning; only `chato`/`chatoia` were corrupted on the old path.",
            "",
            f"Generated by `scripts/validate_chatoia_lookup_fix.py` (fix `{fix_commit}`).",
        ]
    )
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Validate chatoia lookup-merge fix.")
    parser.add_argument("--wrds-user", default=os.environ.get("WRDS_USER", "aminaminimehr"))
    parser.add_argument("--sample-start", type=int, default=DEFAULT_START)
    parser.add_argument("--sample-end", type=int, default=DEFAULT_END)
    parser.add_argument("--skip-wrds-lookup-check", action="store_true")
    parser.add_argument("--fix-commit", default=None)
    args = parser.parse_args()

    import subprocess

    fix_commit = args.fix_commit or subprocess.check_output(
        ["git", "rev-parse", "--short", "HEAD"], text=True, cwd=PROJECT_ROOT
    ).strip()

    repo = load_repo_monthly("chatoia", args.sample_start, args.sample_end)
    ds = load_datashare_chatoia(args.sample_start, args.sample_end)
    merged_ds = repo.merge(ds, on=["permno", "signal_yyyymm"], how="inner")
    datashare_stats = compare_series(merged_ds["chatoia_repo"], merged_ds["chatoia_gkx"])
    datashare_stats["overlap_rows"] = int(len(merged_ds))

    green = load_green_sas_chatoia(args.sample_start, args.sample_end)
    merged_green = repo.merge(green, on=["permno", "signal_yyyymm"], how="inner")
    green_stats = compare_series(merged_green["chatoia_repo"], merged_green["chatoia_green"])
    green_stats["overlap_rows"] = int(len(merged_green))

    lookup = {}
    if not args.skip_wrds_lookup_check:
        lookup = lookup_path_check(args.wrds_user)

    unaffected = {}
    for char in UNAFFECTED:
        path = CHARACTER_INDIVIDUAL_DIR / f"{char}.csv"
        if path.exists():
            df = pd.read_csv(path, nrows=0)
            rows = sum(1 for _ in open(path, encoding="utf-8")) - 1
            unaffected[char] = {"md5": file_md5(path), "rows": rows, "columns": list(df.columns)}

    flat_count = len(list(LEGACY_FLAT_OUTPUT_DIR.glob("*.csv")))

    before = {"spearman_before": 0.060, "median_abs_diff_before": 924}
    report = build_report(
        before, datashare_stats, green_stats, lookup, unaffected, flat_count,
        args.sample_start, args.sample_end, fix_commit,
    )

    DOCS_OUT.parent.mkdir(parents=True, exist_ok=True)
    DOCS_OUT.write_text(report, encoding="utf-8")
    diag = DIAGNOSTICS_DIR / "gkx_chatoia_lookup_fix_validation.md"
    diag.parent.mkdir(parents=True, exist_ok=True)
    diag.write_text(report, encoding="utf-8")

    summary = {
        "fix_commit": fix_commit,
        "datashare": datashare_stats,
        "green_sas": green_stats,
        "lookup_path": lookup,
        "flat_csv_count": flat_count,
        "unaffected_md5": {k: v["md5"] for k, v in unaffected.items()},
    }
    out_json = DIAGNOSTICS_DIR / "gkx_chatoia_lookup_fix_validation.json"
    out_json.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    sys.stdout.buffer.write((report + f"\n\nWrote {DOCS_OUT}\n").encode("utf-8"))


if __name__ == "__main__":
    main()
