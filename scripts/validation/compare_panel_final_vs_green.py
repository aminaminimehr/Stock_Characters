#!/usr/bin/env python3
"""Comprehensive similarity of the server panel vs Green SAS, over datashare columns.

For every column in datashare.csv (the production universe) that exists in BOTH the
server panel and Green's SAS output, compute:
  - pooled Spearman (all overlapping permno-month cells)
  - median monthly cross-sectional Spearman
  - exact-match rate (abs diff <= 1e-4) and near-match rate (abs diff <= 1e-2)
  - non-missing sample counts in each dataset (full period) and paired counts

Plus dataset-level: unique permnos, rows, month coverage, permno overlap.

Comparison is on raw overlapping (permno, month) cells; no universe screen is applied,
so this reflects how similar the two files are as delivered.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pyreadstat

ROOT = Path(__file__).resolve().parents[2]
PANEL = ROOT / "outputs" / "panels" / "all_character_signal_panel_final.csv"
GREEN = ROOT / "Supplementary_assistive_files" / "Output_From_Greens_SAS_code.sas7bdat"
DATASHARE = ROOT / "Supplementary_assistive_files" / "datashare.csv"
OUT_CSV = ROOT / "docs" / "gkx" / "panel_final_vs_green_full_comparison.csv"
OUT_MD = ROOT / "docs" / "gkx" / "panel_final_vs_green_full_comparison.md"

MIN_PAIRS = 50  # minimum paired obs for a month to count in monthly Spearman

# datashare column -> (panel column, green column) when names differ from datashare.
PANEL_ALIAS = {"mve_ia": "me_ia", "rd_mve": "rdm", "retvol": "rvar_mean"}
GREEN_ALIAS = {"mvel1": "mve"}


def green_month(series: pd.Series) -> pd.Series:
    if np.issubdtype(series.dtype, np.datetime64):
        dt = pd.to_datetime(series)
    elif np.issubdtype(series.dtype, np.number):
        dt = pd.to_datetime(series, unit="D", origin="1960-01-01")
    else:
        dt = pd.to_datetime(series, errors="coerce")
    return (dt.dt.year * 100 + dt.dt.month).astype("Int64")


def build_pairs():
    ds_cols = [c for c in pd.read_csv(DATASHARE, nrows=0).columns if c not in ("permno", "DATE")]
    panel_cols = set(pd.read_csv(PANEL, nrows=0).columns)
    _, gmeta = pyreadstat.read_sas7bdat(str(GREEN), metadataonly=True)
    green_cols = set(gmeta.column_names)

    pairs, skipped = [], []
    for ds in ds_cols:
        pcol = PANEL_ALIAS.get(ds, ds)
        gcol = GREEN_ALIAS.get(ds, ds)
        if pcol in panel_cols and gcol in green_cols:
            pairs.append((ds, pcol, gcol))
        else:
            why = []
            if pcol not in panel_cols:
                why.append(f"panel missing '{pcol}'")
            if gcol not in green_cols:
                why.append(f"green missing '{gcol}'")
            skipped.append((ds, "; ".join(why)))
    return ds_cols, pairs, skipped, gmeta.number_rows


def load_panel(panel_cols):
    usecols = ["permno", "signal_yyyymm"] + panel_cols
    frames = []
    for chunk in pd.read_csv(PANEL, usecols=usecols, chunksize=1_000_000):
        chunk["permno"] = pd.to_numeric(chunk["permno"], errors="coerce").astype("Int64")
        chunk["month"] = pd.to_numeric(chunk["signal_yyyymm"], errors="coerce").astype("Int64")
        for c in panel_cols:
            chunk[c] = pd.to_numeric(chunk[c], errors="coerce").astype("float32")
        frames.append(chunk.drop(columns=["signal_yyyymm"]))
    return pd.concat(frames, ignore_index=True)


def load_green(green_cols, nrows):
    usecols = ["permno", "DATE"] + green_cols
    frames = []
    for offset in range(0, nrows, 400_000):
        chunk, _ = pyreadstat.read_sas7bdat(
            str(GREEN), usecols=usecols, row_offset=offset, row_limit=400_000
        )
        chunk["permno"] = pd.to_numeric(chunk["permno"], errors="coerce").astype("Int64")
        chunk["month"] = green_month(chunk["DATE"])
        for c in green_cols:
            chunk[c] = pd.to_numeric(chunk[c], errors="coerce").astype("float32")
        frames.append(chunk.drop(columns=["DATE"]))
    return pd.concat(frames, ignore_index=True)


def monthly_median_spearman(df, a, b):
    vals = []
    for _, grp in df.groupby("month", sort=True):
        sub = grp[[a, b]].dropna()
        if len(sub) < MIN_PAIRS:
            continue
        r = sub[a].corr(sub[b], method="spearman")
        if pd.notna(r):
            vals.append(r)
    return (float(np.median(vals)), len(vals)) if vals else (np.nan, 0)


def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    ds_cols, pairs, skipped, green_rows = build_pairs()
    panel_cols = sorted({p[1] for p in pairs})
    green_cols = sorted({p[2] for p in pairs})

    print(f"datashare predictors: {len(ds_cols)} | comparable pairs: {len(pairs)} | skipped: {len(skipped)}")
    print("Loading panel...", flush=True)
    panel = load_panel(panel_cols)
    print(f"  panel rows={len(panel):,}", flush=True)
    print("Loading Green SAS...", flush=True)
    green = load_green(green_cols, green_rows)
    print(f"  green rows={len(green):,}", flush=True)

    # Dataset-level stats
    p_permnos = set(panel["permno"].dropna().unique())
    g_permnos = set(green["permno"].dropna().unique())
    p_months = panel["month"].dropna()
    g_months = green["month"].dropna()
    overlap_keys = pd.merge(
        panel[["permno", "month"]].drop_duplicates(),
        green[["permno", "month"]].drop_duplicates(),
        on=["permno", "month"], how="inner",
    )
    overlap_permnos = set(overlap_keys["permno"].dropna().unique())

    rows = []
    for ds, pcol, gcol in pairs:
        sp = panel[["permno", "month", pcol]].dropna(subset=[pcol]).rename(columns={pcol: "pv"})
        sg = green[["permno", "month", gcol]].dropna(subset=[gcol]).rename(columns={gcol: "gv"})
        m = sp.merge(sg, on=["permno", "month"], how="inner")
        m = m.dropna(subset=["pv", "gv"])
        n_pair = len(m)
        if n_pair >= 2:
            diff = (m["pv"].astype("float64") - m["gv"].astype("float64")).abs()
            denom = 1.0 + m["gv"].astype("float64").abs()
            pooled = m["pv"].corr(m["gv"], method="spearman")
            match_1e4 = float((diff <= 1e-4).mean())
            match_rel = float((diff <= 1e-3 * denom).mean())
            mm, mm_n = monthly_median_spearman(m, "pv", "gv")
        else:
            pooled = np.nan
            match_1e4 = match_rel = np.nan
            mm, mm_n = np.nan, 0
        rows.append({
            "datashare_col": ds,
            "panel_col": pcol,
            "green_col": gcol,
            "panel_nonnull": int(panel[pcol].notna().sum()),
            "green_nonnull": int(green[gcol].notna().sum()),
            "paired_obs": int(n_pair),
            "pooled_spearman": pooled,
            "median_monthly_spearman": mm,
            "spearman_months": mm_n,
            "match_rate_abs1e-4": match_1e4,
            "match_rate_rel1e-3": match_rel,
        })

    res = pd.DataFrame(rows).sort_values("median_monthly_spearman", ascending=False, na_position="last")
    OUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    res.to_csv(OUT_CSV, index=False)

    # Console report
    def f(x, d=4):
        return "nan" if pd.isna(x) else f"{x:.{d}f}"

    print("\n===== DATASET-LEVEL =====")
    print(f"Panel : rows={len(panel):,}  unique_permnos={len(p_permnos):,}  months={int(p_months.min())}..{int(p_months.max())}")
    print(f"Green : rows={len(green):,}  unique_permnos={len(g_permnos):,}  months={int(g_months.min())}..{int(g_months.max())}")
    print(f"Overlap (permno x month) cells: {len(overlap_keys):,}")
    print(f"Permnos in both: {len(overlap_permnos):,}  | panel-only: {len(p_permnos-g_permnos):,}  | green-only: {len(g_permnos-p_permnos):,}")

    print("\n===== PER-COLUMN (sorted by median monthly Spearman) =====")
    hdr = f"{'datashare':<16}{'panelcol':<14}{'medR':>8}{'poolR':>8}{'exact%':>8}{'rel%':>8}{'paired':>11}{'panelN':>11}{'greenN':>11}"
    print(hdr)
    print("-" * len(hdr))
    for _, r in res.iterrows():
        print(f"{r['datashare_col']:<16}{r['panel_col']:<14}{f(r['median_monthly_spearman'],3):>8}"
              f"{f(r['pooled_spearman'],3):>8}{f(r['match_rate_abs1e-4']*100,1) if pd.notna(r['match_rate_abs1e-4']) else 'nan':>8}"
              f"{f(r['match_rate_rel1e-3']*100,1) if pd.notna(r['match_rate_rel1e-3']) else 'nan':>8}"
              f"{r['paired_obs']:>11,}{r['panel_nonnull']:>11,}{r['green_nonnull']:>11,}")

    if skipped:
        print("\n===== SKIPPED (no comparable column in panel or green) =====")
        for ds, why in skipped:
            print(f"  {ds}: {why}")

    # Markdown report
    write_md(res, skipped, panel, green, p_permnos, g_permnos, overlap_keys, overlap_permnos, p_months, g_months)
    print(f"\nWrote {OUT_CSV}")
    print(f"Wrote {OUT_MD}")


def write_md(res, skipped, panel, green, p_permnos, g_permnos, overlap_keys, overlap_permnos, p_months, g_months):
    def f(x, d=4):
        return "—" if pd.isna(x) else f"{x:.{d}f}"

    lines = [
        "# Server panel vs Green SAS — full-period similarity (datashare columns)",
        "",
        f"- Panel: `{PANEL.name}`",
        f"- Green SAS: `{GREEN.name}`",
        f"- Column universe: `datashare.csv` (95 predictors + `sic2`)",
        "- Comparison: raw overlapping `permno × YYYYMM` cells, **no universe screen**.",
        "- `operprof` is expected to diverge by design (Green output drops `xsga0`; repo follows SAS code).",
        "",
        "## Dataset-level",
        "",
        "| Dataset | Rows | Unique permnos | Month range |",
        "|---------|-----:|---------------:|-------------|",
        f"| Panel | {len(panel):,} | {len(p_permnos):,} | {int(p_months.min())}–{int(p_months.max())} |",
        f"| Green | {len(green):,} | {len(g_permnos):,} | {int(g_months.min())}–{int(g_months.max())} |",
        "",
        f"- Overlapping `permno × month` cells: **{len(overlap_keys):,}**",
        f"- Permnos in both: **{len(overlap_permnos):,}**; panel-only: **{len(p_permnos - g_permnos):,}**; "
        f"green-only: **{len(g_permnos - p_permnos):,}**",
        "",
        "## Per-column similarity",
        "",
        "Sorted by median monthly Spearman. `exact%` = share of paired cells with |Δ| ≤ 1e-4; "
        "`rel%` = |Δ| ≤ 1e-3·(1+|green|).",
        "",
        "| datashare | panel col | green col | median ρ | pooled ρ | exact% | rel% | paired | panel N | green N |",
        "|-----------|-----------|-----------|---------:|---------:|-------:|-----:|-------:|--------:|--------:|",
    ]
    for _, r in res.iterrows():
        em = f(r["match_rate_abs1e-4"] * 100, 1) if pd.notna(r["match_rate_abs1e-4"]) else "—"
        rl = f(r["match_rate_rel1e-3"] * 100, 1) if pd.notna(r["match_rate_rel1e-3"]) else "—"
        lines.append(
            f"| `{r['datashare_col']}` | `{r['panel_col']}` | `{r['green_col']}` | "
            f"{f(r['median_monthly_spearman'],3)} | {f(r['pooled_spearman'],3)} | {em} | {rl} | "
            f"{r['paired_obs']:,} | {r['panel_nonnull']:,} | {r['green_nonnull']:,} |"
        )

    num = pd.to_numeric(res["median_monthly_spearman"], errors="coerce")
    lines += [
        "",
        "## Summary buckets (median monthly Spearman vs Green)",
        "",
        f"- ρ ≥ 0.99 (essentially identical): **{int((num >= 0.99).sum())}**",
        f"- 0.95 ≤ ρ < 0.99: **{int(((num >= 0.95) & (num < 0.99)).sum())}**",
        f"- 0.90 ≤ ρ < 0.95: **{int(((num >= 0.90) & (num < 0.95)).sum())}**",
        f"- ρ < 0.90 (investigate): **{int((num < 0.90).sum())}**",
        "",
        "### Below 0.95 (review)",
        "",
        "| datashare | median ρ | pooled ρ | exact% | note |",
        "|-----------|---------:|---------:|-------:|------|",
    ]
    low = res[num < 0.95].sort_values("median_monthly_spearman")
    for _, r in low.iterrows():
        em = f(r["match_rate_abs1e-4"] * 100, 1) if pd.notna(r["match_rate_abs1e-4"]) else "—"
        note = "by design (xsga0 typo in Green output)" if r["datashare_col"] == "operprof" else ""
        lines.append(
            f"| `{r['datashare_col']}` | {f(r['median_monthly_spearman'],3)} | "
            f"{f(r['pooled_spearman'],3)} | {em} | {note} |"
        )
    if skipped:
        lines += ["", "## Skipped datashare columns", ""]
        for ds, why in skipped:
            lines.append(f"- `{ds}`: {why}")

    OUT_MD.parent.mkdir(parents=True, exist_ok=True)
    OUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
