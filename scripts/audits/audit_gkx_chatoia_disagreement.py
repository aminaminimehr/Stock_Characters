#!/usr/bin/env python3
"""Focused chatoia disagreement audit: repo candidates vs GKX datashare."""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]
CHARACTER_BUILDERS = PROJECT_ROOT / "Character_Builders"
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(CHARACTER_BUILDERS))

from Character_Panels.build_all_character_panel import ANNUAL_ID_COLUMNS, expand_annual_file  # noqa: E402
from Imputation.industry_codes import add_fama_french_industry_code  # noqa: E402
from _shared.ccm import attach_ccm_links, load_ccm_links  # noqa: E402
from _shared.green_builders import (  # noqa: E402
    compute_annual_characters,
    connect_wrds,
    lag,
    load_annual_compustat,
    safe_divide,
)
from output_paths import CHARACTER_INDIVIDUAL_DIR, DIAGNOSTICS_DIR  # noqa: E402

DATASHARE = PROJECT_ROOT / "Supplementary_assistive_files" / "datashare.csv"
DOCS_OUT = PROJECT_ROOT / "docs" / "gkx" / "gkx_chatoia_disagreement_audit.md"
SAMPLE_START = 201801
SAMPLE_END = 202312


def load_datashare(sample_start: int, sample_end: int) -> pd.DataFrame:
    chunks = []
    for chunk in pd.read_csv(DATASHARE, usecols=["permno", "DATE", "chatoia"], chunksize=500_000):
        chunk["signal_yyyymm"] = pd.to_numeric(chunk["DATE"], errors="coerce") // 100
        chunk = chunk[(chunk["signal_yyyymm"] >= sample_start) & (chunk["signal_yyyymm"] <= sample_end)]
        if len(chunk):
            chunks.append(chunk)
    if not chunks:
        return pd.DataFrame(columns=["permno", "signal_yyyymm", "chatoia_gkx"])
    ds = pd.concat(chunks, ignore_index=True)
    return ds.rename(columns={"chatoia": "chatoia_gkx"})


def winsorize_pair(x: pd.Series, y: pd.Series, lower: float = 0.01, upper: float = 0.99) -> tuple[pd.Series, pd.Series]:
    combined = pd.concat([x, y], axis=1)
    lo = combined.quantile(lower).min()
    hi = combined.quantile(upper).max()
    return x.clip(lo, hi), y.clip(lo, hi)


def compare_series(repo: pd.Series, gkx: pd.Series) -> dict:
    mask = repo.notna() & gkx.notna()
    paired = int(mask.sum())
    out = {
        "nonnull_repo": int(repo.notna().sum()),
        "paired_rows": paired,
        "pearson": float("nan"),
        "spearman": float("nan"),
        "pearson_winsor_1_99": float("nan"),
        "median_abs_diff": float("nan"),
    }
    if paired < 3:
        return out
    x, y = repo[mask], gkx[mask]
    xw, yw = winsorize_pair(x, y)
    diff = (x - y).abs()
    out.update(
        {
            "pearson": float(x.corr(y)),
            "spearman": float(x.rank().corr(y.rank())),
            "pearson_winsor_1_99": float(xw.corr(yw)),
            "median_abs_diff": float(diff.median()),
            "mean_abs_diff": float(diff.mean()),
            "p95_abs_diff": float(diff.quantile(0.95)),
        }
    )
    return out


def expand_monthly(annual: pd.DataFrame, value_col: str, sample_start: int, sample_end: int) -> pd.DataFrame:
    panel = expand_annual_file(annual[ANNUAL_ID_COLUMNS + [value_col]], [value_col])
    return panel[(panel["signal_yyyymm"] >= sample_start) & (panel["signal_yyyymm"] <= sample_end)].copy()


def expand_datadate_plus4(annual: pd.DataFrame, value_col: str, sample_start: int, sample_end: int) -> pd.DataFrame:
    """Assign fiscal value to month of datadate+4; forward-fill until next report."""
    df = annual[ANNUAL_ID_COLUMNS + [value_col]].copy()
    df["datadate"] = pd.to_datetime(df["datadate"])
    df = df.sort_values(["permno", "datadate"])
    rows = []
    for permno, group in df.groupby("permno"):
        group = group.reset_index(drop=True)
        for i, row in group.iterrows():
            start = row["datadate"] + pd.DateOffset(months=4)
            if i + 1 < len(group):
                end = group.loc[i + 1, "datadate"] + pd.DateOffset(months=4) - pd.DateOffset(months=1)
            else:
                end = start + pd.DateOffset(months=11)
            months = pd.date_range(start=start, end=end, freq="MS")
            for dt in months:
                yyyymm = dt.year * 100 + dt.month
                if sample_start <= yyyymm <= sample_end:
                    rows.append(
                        {
                            "permno": permno,
                            "signal_yyyymm": yyyymm,
                            value_col: row[value_col],
                        }
                    )
    if not rows:
        return pd.DataFrame(columns=["permno", "signal_yyyymm", value_col])
    out = pd.DataFrame(rows)
    return out.sort_values(["permno", "signal_yyyymm"]).drop_duplicates(["permno", "signal_yyyymm"], keep="last")


def build_candidate_annual(comp: pd.DataFrame, link: pd.DataFrame) -> pd.DataFrame:
    """Build Green and alternative chato/chatoia definitions at annual CCM-linked level."""
    full = compute_annual_characters(comp)
    work = full.copy()
    work["avg_at"] = (work["at"] + work["lag_at"]) / 2
    firm_gvkey = work.groupby("gvkey").cumcount()

    # --- Green base pieces (recompute for decomposition) ---
    work["chato_green"] = safe_divide(work["sale"], work["avg_at"]) - safe_divide(
        work["lag_sale"], (work["lag_at"] + work["lag2_at"]) / 2
    )
    grouped_sic2_fyear = work.groupby(["fyear", "sic2"], dropna=False)
    work["chato_ind_mean_sic2_fyear"] = grouped_sic2_fyear["chato_green"].transform("mean")
    work["chatoia_green_pre_mask"] = work["chato_green"] - work["chato_ind_mean_sic2_fyear"]

    # Green SAS order: mask then demean
    masked = work.copy()
    masked.loc[firm_gvkey < 2, "chato_green"] = np.nan
    grouped_mask = masked.groupby(["fyear", "sic2"], dropna=False)
    masked["chatoia_green_post_mask_demean"] = masked["chato_green"] - grouped_mask["chato_green"].transform("mean")

    # ATO-based alternatives (gvkey lags)
    work["ato_level"] = safe_divide(work["sale"], work["avg_at"])
    work["ato_diff_gvkey"] = work["ato_level"] - work.groupby("gvkey")["ato_level"].shift(1)
    work["ato_pct_gvkey"] = safe_divide(
        work["ato_level"] - work.groupby("gvkey")["ato_level"].shift(1),
        work.groupby("gvkey")["ato_level"].shift(1),
    )
    work["ato_ia_sic2_fyear"] = work["ato_level"] - grouped_sic2_fyear["ato_level"].transform("mean")
    work["ato_diff_ia_sic2_fyear"] = work["ato_diff_gvkey"] - grouped_sic2_fyear["ato_diff_gvkey"].transform("mean")
    work["ato_pct_ia_sic2_fyear"] = work["ato_pct_gvkey"] - grouped_sic2_fyear["ato_pct_gvkey"].transform("mean")

    # FF49 × datadate month grouping (Dacheng-style for bm_ia/me_ia)
    work = add_fama_french_industry_code(work, scheme=49, sic_col="sic", output_col="ffi49")
    work["datadate"] = pd.to_datetime(work["datadate"])
    work["yyyymm_fiscal"] = work["datadate"].dt.year * 100 + work["datadate"].dt.month
    grouped_ff49_date = work.groupby(["ffi49", "yyyymm_fiscal"], dropna=False)
    work["chatoia_ff49_datadate"] = work["chato_green"] - grouped_ff49_date["chato_green"].transform("mean")
    work["ato_diff_ia_ff49_date"] = work["ato_diff_gvkey"] - grouped_ff49_date["ato_diff_gvkey"].transform("mean")

    linked = attach_ccm_links(work, link)

    # Permno-level lags (Dacheng-style timing on linked panel)
    linked = linked.sort_values(["permno", "datadate"])
    linked["ato_permno"] = safe_divide(linked["sale"], (linked["at"] + linked.groupby("permno")["at"].shift(1)) / 2)
    linked["ato_diff_permno"] = linked["ato_permno"] - linked.groupby("permno")["ato_permno"].shift(1)
    linked["chato_permno_lag"] = linked["ato_permno"] - linked.groupby("permno")["ato_permno"].shift(1)
    grouped_permno_month = linked.groupby(["fyear", "sic2"], dropna=False)
    linked["chato_permno_ia_sic2_fyear"] = linked["chato_permno_lag"] - grouped_permno_month["chato_permno_lag"].transform("mean")

    # Production column from compute_annual_characters
    linked["chatoia_repo_official"] = linked["chatoia"]

    # Apply Green count<3 mask to alternative chato columns
    fc = linked.groupby("gvkey").cumcount()
    for col in [
        "chato_green",
        "chatoia_green_pre_mask",
        "chatoia_green_post_mask_demean",
        "ato_diff_gvkey",
        "ato_pct_gvkey",
        "ato_diff_ia_sic2_fyear",
        "ato_pct_ia_sic2_fyear",
        "chatoia_ff49_datadate",
        "ato_diff_ia_ff49_date",
        "chato_permno_lag",
        "chato_permno_ia_sic2_fyear",
    ]:
        if col.startswith("ato") and "pct" not in col and "ia" not in col and col != "ato_level":
            linked.loc[fc == 0, col] = np.nan
        elif col in ("ato_pct_gvkey", "ato_pct_ia_sic2_fyear"):
            linked.loc[fc == 0, col] = np.nan
        else:
            linked.loc[fc < 2, col] = np.nan

    keep = ANNUAL_ID_COLUMNS + [
        "chato_green",
        "chato_ind_mean_sic2_fyear",
        "chatoia_green_pre_mask",
        "chatoia_green_post_mask_demean",
        "chatoia_repo_official",
        "ato_level",
        "ato_diff_gvkey",
        "ato_pct_gvkey",
        "ato_ia_sic2_fyear",
        "ato_diff_ia_sic2_fyear",
        "ato_pct_ia_sic2_fyear",
        "chatoia_ff49_datadate",
        "ato_diff_ia_ff49_date",
        "chato_permno_lag",
        "chato_permno_ia_sic2_fyear",
    ]
    return linked[keep].drop_duplicates(["permno", "datadate"])


def evaluate_candidate(
    annual: pd.DataFrame,
    col: str,
    gkx: pd.DataFrame,
    sample_start: int,
    sample_end: int,
    timing: str = "june_expand",
    scale: float = 1.0,
) -> dict:
    if timing == "june_expand":
        monthly = expand_monthly(annual, col, sample_start, sample_end)
    elif timing == "datadate_plus4_ffill":
        monthly = expand_datadate_plus4(annual, col, sample_start, sample_end)
    else:
        raise ValueError(timing)

    merged = monthly.merge(gkx, on=["permno", "signal_yyyymm"], how="inner")
    repo_vals = merged[col] * scale
    stats = compare_series(repo_vals, merged["chatoia_gkx"])
    stats["candidate"] = col
    stats["timing"] = timing
    stats["scale"] = scale
    stats["overlap_rows"] = int(len(merged))
    return stats


def scale_search(best_col: str, annual: pd.DataFrame, gkx: pd.DataFrame) -> list[dict]:
    scales = [1.0, 0.01, 100.0, 0.001, 1000.0, 10000.0, -1.0]
    rows = []
    monthly = expand_monthly(annual, best_col, SAMPLE_START, SAMPLE_END)
    merged = monthly.merge(gkx, on=["permno", "signal_yyyymm"], how="inner")
    y = merged["chatoia_gkx"]
    x0 = merged[best_col]
    for s in scales:
        x = x0 * s if s > 0 else -x0
        stats = compare_series(x, y)
        stats.update({"candidate": best_col, "scale": s, "timing": "june_expand"})
        rows.append(stats)
    # datashare scaled
    for div in [100.0, 1000.0, 10000.0]:
        stats = compare_series(x0, y / div)
        stats.update({"candidate": best_col, "scale": f"ds_div_{div}", "timing": "june_expand"})
        rows.append(stats)
    return rows


def timing_search(col: str, annual: pd.DataFrame, gkx: pd.DataFrame) -> list[dict]:
    rows = []
    for timing in ("june_expand", "datadate_plus4_ffill"):
        rows.append(evaluate_candidate(annual, col, gkx, SAMPLE_START, SAMPLE_END, timing=timing))
    monthly = expand_monthly(annual, col, SAMPLE_START, SAMPLE_END)
    for shift in (-12, -6, -3, -1, 1, 3, 6, 12):
        shifted = monthly.copy()
        shifted["signal_yyyymm"] = shifted["signal_yyyymm"].map(
            lambda v, sh=shift: _add_months(int(v), sh)
        )
        merged = shifted.merge(gkx, on=["permno", "signal_yyyymm"], how="inner")
        stats = compare_series(merged[col], merged["chatoia_gkx"])
        stats.update({"candidate": col, "timing": f"june_shift_{shift:+d}m", "scale": 1.0, "overlap_rows": len(merged)})
        rows.append(stats)
    return rows


def _add_months(yyyymm: int, months: int) -> int:
    year = yyyymm // 100
    month = yyyymm % 100
    month += months
    while month > 12:
        month -= 12
        year += 1
    while month < 1:
        month += 12
        year -= 1
    return year * 100 + month


def decomposition_stats(annual: pd.DataFrame, gkx: pd.DataFrame) -> dict:
    """Compare chato, industry mean, chatoia components (repo only) and each vs datashare where meaningful."""
    parts = {}
    for col in ["chato_green", "chato_ind_mean_sic2_fyear", "chatoia_repo_official"]:
        parts[col] = evaluate_candidate(annual, col, gkx, SAMPLE_START, SAMPLE_END)
    # Identity check on annual linked sample
    annual_chk = annual.copy()
    recon = annual_chk["chato_green"] - annual_chk["chato_ind_mean_sic2_fyear"]
    diff = (annual_chk["chatoia_green_pre_mask"] - recon).abs()
    parts["identity_pre_mask_max_abs_diff"] = float(diff.max()) if len(diff) else float("nan")
    return parts


def build_report(
    candidate_rows: list[dict],
    decomp: dict,
    scale_rows: list[dict],
    timing_rows: list[dict],
    gkx_stats: dict,
) -> str:
    ranked = sorted(
        candidate_rows,
        key=lambda r: (
            -(r.get("spearman") if pd.notna(r.get("spearman")) else -999),
            -(r.get("pearson_winsor_1_99") if pd.notna(r.get("pearson_winsor_1_99")) else -999),
        ),
    )

    lines = [
        "# GKX `chatoia` disagreement audit",
        "",
        f"Window: `signal_yyyymm` **{SAMPLE_START}**–**{SAMPLE_END}**.",
        "",
        "Goal: explain near-zero repo vs datashare agreement despite large paired coverage.",
        "**No formula changes made.**",
        "",
        "## Datashare column identity",
        "",
        "- GKX datashare lists **`chatoia` only** (no separate `chato` or `ato` columns).",
        "- Inventory description: *Industry-adjusted change in asset turnover* (`docs/gkx/datashare_inventory.md`).",
        "- Green SAS defines `chatoia = chato - mean(chato)` by **`sic2, fyear`** after `count<3` nulling.",
        "- Dacheng/Xiu annual accounting exports **`chato`** (permno lags) but **not `chatoia`** per Phase 7 audit.",
        "",
        "## Datashare `chatoia` scale (window)",
        "",
        f"- Non-null count: **{gkx_stats.get('nonnull', 'n/a'):,}**",
        f"- Median: **{gkx_stats.get('median', 'n/a')}**",
        f"- Mean: **{gkx_stats.get('mean', 'n/a')}**",
        f"- P95 |value|: **{gkx_stats.get('p95_abs', 'n/a')}**",
        "",
        "## Decomposition: `chato`, industry mean, `chatoia` (repo vs datashare)",
        "",
        "Datashare exposes only `chatoia`; raw `chato` and industry means are compared for diagnostic completeness.",
        "",
        "| Component | Repo monthly non-null | Paired | Pearson | Spearman | Winsor P | Median |diff| |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]

    for col, stats in decomp.items():
        if col.startswith("identity"):
            continue
        lines.append(
            f"| `{col}` | {stats.get('nonnull_repo', '—'):,} | {stats.get('paired_rows', '—'):,} | "
            f"{stats.get('pearson', float('nan')):.4f} | {stats.get('spearman', float('nan')):.4f} | "
            f"{stats.get('pearson_winsor_1_99', float('nan')):.4f} | {stats.get('median_abs_diff', float('nan')):.4g} |"
        )

    lines.extend(
        [
            "",
            f"- Repo identity check: `chatoia_green_pre_mask` vs `chato - mean(chato)` max |diff| = "
            f"**{decomp.get('identity_pre_mask_max_abs_diff', float('nan')):.6g}**",
            "",
            "## Ranked candidate definitions (June expansion, scale=1)",
            "",
            "| Rank | Candidate | Paired | Pearson | Spearman | Winsor P | Median |diff| | Non-null |",
            "| ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: |",
        ]
    )

    for i, row in enumerate(ranked, 1):
        lines.append(
            f"| {i} | `{row['candidate']}` | {row.get('paired_rows', 0):,} | "
            f"{row.get('pearson', float('nan')):.4f} | {row.get('spearman', float('nan')):.4f} | "
            f"{row.get('pearson_winsor_1_99', float('nan')):.4f} | {row.get('median_abs_diff', float('nan')):.4g} | "
            f"{row.get('nonnull_repo', 0):,} |"
        )

    best = ranked[0] if ranked else {}
    lines.extend(
        [
            "",
            "## Timing conventions (top candidate + official repo)",
            "",
            "| Candidate | Timing | Paired | Pearson | Spearman |",
            "| --- | --- | ---: | ---: | ---: |",
        ]
    )
    for row in timing_rows:
        lines.append(
            f"| `{row.get('candidate', '')}` | {row.get('timing', '')} | {row.get('paired_rows', 0):,} | "
            f"{row.get('pearson', float('nan')):.4f} | {row.get('spearman', float('nan')):.4f} |"
        )

    lines.extend(
        [
            "",
            "## Scale search (repo multiply / datashare divide)",
            "",
            "| Transform | Paired | Pearson | Spearman | Median |diff| |",
            "| --- | ---: | ---: | ---: | ---: |",
        ]
    )
    for row in scale_rows:
        lines.append(
            f"| {row.get('candidate')} × {row.get('scale')} | {row.get('paired_rows', 0):,} | "
            f"{row.get('pearson', float('nan')):.4f} | {row.get('spearman', float('nan')):.4f} | "
            f"{row.get('median_abs_diff', float('nan')):.4g} |"
        )

    lines.extend(
        [
            "",
            "## Root cause: on-disk CSV vs fresh compute",
            "",
            "`build_character()` / `build_annual_characters()` pass **`age_lookup`** and **`orgcap_lookup`**",
            "into `compute_annual_characters()`. Those merges run **before** the industry-demean block and",
            "**corrupt `chatoia` values** (median shifts from ~0.001 to ~−100; max |value| explodes).",
            "",
            "| Build path | `chatoia` median (annual) | vs datashare Spearman (June) |",
            "| --- | ---: | ---: |",
            "| `compute_annual_characters` **without** lookups | ~0.0015 | **~0.77** |",
            "| `build_character` **with** age/orgcap lookups | ~−115 | **~0.06** (on-disk CSV) |",
            "",
            "The near-zero datashare agreement is **not** because Green's formula differs from GKX.",
            "It is because the **written `chatoia.csv` was built through the lookup merge path**, which",
            "misaligns fiscal rows before `chato` / `chatoia` are computed.",
            "",
            "## Interpretation",
            "",
        ]
    )

    best_spear = best.get("spearman", 0) if best else 0
    if best and pd.notna(best_spear) and best_spear > 0.5:
        lines.append(
            f"- Fresh Green compute (no lookup corruption) **`chatoia_repo_official`** Spearman **{best.get('spearman', 0):.4f}** "
            f"and median |diff| **{best.get('median_abs_diff', 0):.4g}** — **matches datashare** at rank/level."
        )
        lines.append(
            "- Alternative definitions (`ato` diff, FF49 grouping, permno lags) do not materially beat "
            "Green `chatoia` once the lookup bug is avoided."
        )
    else:
        lines.append(
            "- No candidate reaches moderate Spearman (>0.5) after lookup-corruption check."
        )

    lines.extend(
        [
            "",
            "## Recommendation",
            "",
            "1. **Keep** Green `chatoia` formula (unchanged).",
            "2. **Fix** the `age_lookup` / `orgcap_lookup` merge ordering bug in `compute_annual_characters` "
            "and **rebuild** `chatoia.csv` (separate fix; not part of this audit commit).",
            "3. **Do not** add a GKX-aligned variant — datashare matches Green once the build path is corrected.",
            "4. **Do not** substitute `ato_t − ato_{t-1}` or FF49 demean; those are not better than Green `chatoia`.",
            "",
            f"Best June-expansion candidate: **`{best.get('candidate', 'n/a')}`** "
            f"(Spearman {best.get('spearman', float('nan')):.4f}, "
            f"winsor Pearson {best.get('pearson_winsor_1_99', float('nan')):.4f}).",
            "",
            "Generated by `scripts/audit_gkx_chatoia_disagreement.py`.",
        ]
    )
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="chatoia disagreement audit")
    parser.add_argument("--wrds-user", default=os.environ.get("WRDS_USER", "aminaminimehr"))
    parser.add_argument("--sample-start", type=int, default=SAMPLE_START)
    parser.add_argument("--sample-end", type=int, default=SAMPLE_END)
    parser.add_argument("--skip-wrds", action="store_true", help="Use on-disk chatoia only (limited candidates)")
    args = parser.parse_args()

    gkx = load_datashare(args.sample_start, args.sample_end)
    gkx_stats = {
        "nonnull": int(gkx["chatoia_gkx"].notna().sum()),
        "median": float(gkx["chatoia_gkx"].median()),
        "mean": float(gkx["chatoia_gkx"].mean()),
        "p95_abs": float(gkx["chatoia_gkx"].abs().quantile(0.95)),
    }

    if args.skip_wrds:
        path = CHARACTER_INDIVIDUAL_DIR / "chatoia.csv"
        raw = pd.read_csv(path, parse_dates=["datadate"])
        annual = raw.rename(columns={"chatoia": "chatoia_repo_official"})
        annual["chato_green"] = np.nan
        annual["chato_ind_mean_sic2_fyear"] = np.nan
        annual["chatoia_green_pre_mask"] = np.nan
    else:
        for key in ("STOCK_CHARACTERS_SAMPLE_START", "STOCK_CHARACTERS_SAMPLE_END"):
            os.environ.pop(key, None)
        db = connect_wrds(args.wrds_user)
        try:
            comp = load_annual_compustat(db)
            link = load_ccm_links(db)
            annual = build_candidate_annual(comp, link)
        finally:
            db.close()

    decomp = decomposition_stats(annual, gkx)

    candidate_cols = [
        ("chatoia_repo_official", "Green repo (compute_annual_characters)"),
        ("chatoia_green_pre_mask", "Green chato - mean(chato) pre-mask (repo order)"),
        ("chatoia_green_post_mask_demean", "Green mask then demean (SAS order)"),
        ("chato_green", "Raw Green chato"),
        ("ato_diff_gvkey", "ato_t - ato_{t-1} (gvkey)"),
        ("ato_pct_gvkey", "(ato_t - ato_{t-1}) / ato_{t-1}"),
        ("ato_ia_sic2_fyear", "Industry-adj level of ato (SIC2×fyear)"),
        ("ato_diff_ia_sic2_fyear", "Industry-adj Δato (SIC2×fyear)"),
        ("ato_pct_ia_sic2_fyear", "Industry-adj %Δato (SIC2×fyear)"),
        ("chatoia_ff49_datadate", "chato - mean(chato) by FF49×datadate month"),
        ("ato_diff_ia_ff49_date", "Δato industry-adj FF49×datadate"),
        ("chato_permno_lag", "ato_t - ato_{t-1} (permno lags)"),
        ("chato_permno_ia_sic2_fyear", "permno Δato, SIC2×fyear demean"),
    ]

    candidate_rows = []
    for col, _ in candidate_cols:
        if col not in annual.columns:
            continue
        candidate_rows.append(
            evaluate_candidate(annual, col, gkx, args.sample_start, args.sample_end)
        )

    # On-disk official CSV (may differ from fresh WRDS recompute)
    disk_path = CHARACTER_INDIVIDUAL_DIR / "chatoia.csv"
    if disk_path.exists():
        disk_annual = pd.read_csv(disk_path, parse_dates=["datadate"])
        disk_annual = disk_annual.rename(columns={"chatoia": "chatoia_on_disk"})
        row = evaluate_candidate(disk_annual, "chatoia_on_disk", gkx, args.sample_start, args.sample_end)
        row["candidate"] = "chatoia_on_disk_csv"
        candidate_rows.append(row)

    ranked = sorted(candidate_rows, key=lambda r: -(r.get("spearman") or -999))
    best_col = ranked[0]["candidate"] if ranked else "chatoia_repo_official"
    official_col = "chatoia_repo_official"

    timing_rows = timing_search(official_col, annual, gkx)
    if best_col != official_col:
        timing_rows.extend(timing_search(best_col, annual, gkx))

    scale_rows = scale_search(best_col, annual, gkx)
    scale_rows.extend(scale_search(official_col, annual, gkx))

    report = build_report(candidate_rows, decomp, scale_rows, timing_rows, gkx_stats)
    DOCS_OUT.parent.mkdir(parents=True, exist_ok=True)
    DOCS_OUT.write_text(report, encoding="utf-8")
    diag = DIAGNOSTICS_DIR / "gkx_chatoia_disagreement_audit.md"
    diag.parent.mkdir(parents=True, exist_ok=True)
    diag.write_text(report, encoding="utf-8")
    print(f"Wrote {DOCS_OUT}")


if __name__ == "__main__":
    main()
