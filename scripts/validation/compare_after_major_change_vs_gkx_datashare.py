#!/usr/bin/env python3
"""Panel-vs-GKX datashare closeness comparison for the post-major-change panel.

Same comparison as compare_panel_vs_gkx_datashare.py but pointed at
outputs/panels/all_character_signal_panel_after_major_change.csv, whose
character columns already use datashare-native names (bm, operprof,
mve_ia, rd_mve, retvol, ear, ...). There is no alias mapping: every datashare
predictor is compared directly against the panel column of the same name.

For every datashare predictor that exists in the panel, compute:
  - dataset-level permno / month coverage
  - per-column key overlap (datashare-only, panel-only, both)
  - pooled Spearman and median monthly cross-sectional Spearman
  - mean monthly cross-sectional Spearman and share of months with rho below threshold
  - exact match |delta| <= 1e-4 and round-to-4-decimal match

All panel-side counts and comparisons are restricted to the datashare calendar
window (min/max DATE // 100 in datashare.csv) so post-2021 panel tail rows
do not inflate panel-only keys or coverage stats.

Month alignment: datashare DATE -> YYYYMM via DATE // 100; auto-pick panel
signal_yyyymm vs target_yyyymm per column (whichever yields higher median rho).

To run:

  python scripts/validation/panel_validation_aligning_aliases.py \
      --panel outputs/panels/all_character_signal_panel_after_major_change.csv \
      --datashare Supplementary_assistive_files/datashare.csv
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_PANEL = ROOT / "outputs" / "panels" / "all_character_signal_panel_after_major_change_1.csv"
DEFAULT_DATASHARE = ROOT / "Supplementary_assistive_files" / "datashare.csv"
OUT_CSV = ROOT / "docs" / "gkx" / "panel_gkx_datashare_after_major_change.csv"
OUT_MD = ROOT / "docs" / "gkx" / "panel_gkx_datashare_after_major_change.md"

MIN_PAIRS = 50
LOW_RHO_THRESHOLD = 0.5  # downside cut: share of months whose monthly Spearman < this

PANEL_META = {
    "permno", "permco", "gvkey", "date", "datadate", "source_date",
    "source_yyyymm", "signal_yyyymm", "target_yyyymm", "yyyymm",
    "sic", "exchcd", "shrcd", "fyear", "availability_date",
    "calendar_year", "excess_return", "ffi49",
}

# No alias mapping: the post-major-change panel already stores datashare-native
# column names, so every predictor is compared directly against the panel
# column of the same name.


def datashare_predictors(datashare_path: Path = DEFAULT_DATASHARE) -> list[str]:
    cols = list(pd.read_csv(datashare_path, nrows=0).columns)
    return sorted(c for c in cols if c not in ("permno", "DATE"))


def panel_column(ds_col: str, panel_cols: set[str]) -> str | None:
    """Direct name match (no aliases) - the panel uses datashare names."""
    return ds_col if ds_col in panel_cols else None


def build_pairs(panel_cols: set[str], datashare_path: Path):
    pairs, skipped = [], []
    for ds in datashare_predictors(datashare_path):
        pcol = panel_column(ds, panel_cols)
        if pcol:
            pairs.append((ds, pcol))
        else:
            skipped.append(ds)
    return pairs, skipped


def load_datashare(datashare_path: Path) -> pd.DataFrame:
    frames = []
    for chunk in pd.read_csv(datashare_path, chunksize=500_000):
        chunk["permno"] = pd.to_numeric(chunk["permno"], errors="coerce").astype("Int64")
        chunk["month"] = (pd.to_numeric(chunk["DATE"], errors="coerce") // 100).astype("Int64")
        for c in chunk.columns:
            if c not in ("permno", "DATE", "month"):
                chunk[c] = pd.to_numeric(chunk[c], errors="coerce").astype("float32")
        frames.append(chunk.drop(columns=["DATE"]))
    return pd.concat(frames, ignore_index=True)


def datashare_month_bounds(ds: pd.DataFrame) -> tuple[int, int]:
    months = ds["month"].dropna()
    return int(months.min()), int(months.max())


def restrict_panel_to_datashare_window(panel, month_min, month_max):
    in_window = (
        panel["signal_yyyymm"].between(month_min, month_max)
        | panel["target_yyyymm"].between(month_min, month_max)
    )
    return panel.loc[in_window].copy()


def load_panel(panel_path: Path, panel_cols: list[str]) -> pd.DataFrame:
    usecols = ["permno", "signal_yyyymm", "target_yyyymm"] + panel_cols
    frames = []
    for chunk in pd.read_csv(panel_path, usecols=usecols, chunksize=500_000):
        chunk["permno"] = pd.to_numeric(chunk["permno"], errors="coerce").astype("Int64")
        chunk["signal_yyyymm"] = pd.to_numeric(chunk["signal_yyyymm"], errors="coerce").astype("Int64")
        chunk["target_yyyymm"] = pd.to_numeric(chunk["target_yyyymm"], errors="coerce").astype("Int64")
        for c in panel_cols:
            chunk[c] = pd.to_numeric(chunk[c], errors="coerce").astype("float32")
        frames.append(chunk)
    return pd.concat(frames, ignore_index=True)


def monthly_spearman_values(df: pd.DataFrame, a: str, b: str) -> list[float]:
    vals = []
    for _, grp in df.groupby("month", sort=True):
        sub = grp[[a, b]].dropna()
        if len(sub) < MIN_PAIRS:
            continue
        r = sub[a].corr(sub[b], method="spearman")
        if pd.notna(r):
            vals.append(r)
    return vals


def compare_column(ds, panel, ds_col, pcol, month_min, month_max) -> dict:
    ds_sub = ds[["permno", "month", ds_col]].rename(columns={ds_col: "dv"})
    panel_sub = panel[["permno", "signal_yyyymm", "target_yyyymm", pcol]].rename(columns={pcol: "pv"})
    ds_keys = set(map(tuple, ds_sub.loc[ds_sub["dv"].notna(), ["permno", "month"]].itertuples(index=False, name=None)))
    best_row = None
    for month_col in ("signal_yyyymm", "target_yyyymm"):
        ps = panel_sub.rename(columns={month_col: "month"})[["permno", "month", "pv"]]
        ps = ps[ps["month"].between(month_min, month_max)]
        panel_keys = set(map(tuple, ps.loc[ps["pv"].notna(), ["permno", "month"]].itertuples(index=False, name=None)))
        m = ds_sub.merge(ps, on=["permno", "month"], how="inner").dropna(subset=["dv", "pv"])
        n_pair = len(m)
        if n_pair >= 2:
            pv = m["pv"].astype("float64")
            dv = m["dv"].astype("float64")
            diff = (pv - dv).abs()
            denom = 1.0 + dv.abs()
            pooled = float(pv.corr(dv, method="spearman"))
            match_1e4 = float((diff <= 1e-4).mean())
            match_round4 = float((np.round(pv, 4) == np.round(dv, 4)).mean())
            match_rel = float((diff <= 1e-3 * denom).mean())
            vals = monthly_spearman_values(m, "pv", "dv")
            mm = float(np.median(vals)) if vals else np.nan
            mm_n = len(vals)
            mm_mean = float(np.mean(vals)) if vals else np.nan
            mm_pct_low = float(np.mean([v < LOW_RHO_THRESHOLD for v in vals])) if vals else np.nan
        else:
            pooled = match_1e4 = match_round4 = match_rel = np.nan
            mm = mm_mean = mm_pct_low = np.nan
            mm_n = 0
        both = ds_keys & panel_keys
        row = {
            "datashare_col": ds_col, "panel_col": pcol, "month_align": month_col,
            "datashare_nonnull": len(ds_keys), "panel_nonnull": len(panel_keys),
            "keys_both": len(both),
            "datashare_only": len(ds_keys - panel_keys),
            "panel_only": len(panel_keys - ds_keys),
            "permno_datashare": int(ds_sub.loc[ds_sub["dv"].notna(), "permno"].nunique()),
            "permno_panel": int(ps.loc[ps["pv"].notna(), "permno"].nunique()),
            "permno_both": int(m["permno"].nunique()) if n_pair else 0,
            "paired_obs": int(n_pair),
            "pooled_spearman": pooled, "median_monthly_spearman": mm,
            "mean_monthly_spearman": mm_mean, "pct_months_rho_lt_05": mm_pct_low,
            "spearman_months": mm_n,
            "match_rate_abs1e-4": match_1e4, "match_rate_round4": match_round4,
            "match_rate_rel1e-3": match_rel,
        }
        if best_row is None or (pd.notna(mm) and (pd.isna(best_row["median_monthly_spearman"]) or mm > best_row["median_monthly_spearman"])):
            best_row = row
    return best_row or {}

def write_md(res, skipped, panel, ds, panel_path, month_min, month_max) -> None:
    def f(x, d=4):
        return "---" if pd.isna(x) else f"{x:.{d}f}"

    p_permnos = set(panel["permno"].dropna().unique())
    d_permnos = set(ds["permno"].dropna().unique())
    p_months = panel["signal_yyyymm"].dropna()
    d_months = ds["month"].dropna()
    panel_signal = panel[["permno", "signal_yyyymm"]].rename(columns={"signal_yyyymm": "month"})
    panel_signal = panel_signal[panel_signal["month"].between(month_min, month_max)]
    overlap_keys = pd.merge(
        panel_signal.drop_duplicates(),
        ds[["permno", "month"]].drop_duplicates(),
        on=["permno", "month"], how="inner",
    )
    overlap_permnos = set(overlap_keys["permno"].dropna().unique())

    lines = [
        "# Post-major-change panel vs GKX datashare.csv - full-period comparison",
        "",
        f"- Panel: `{panel_path.name}`",
        f"- Datashare: `{DEFAULT_DATASHARE.name}`",
        f"- Column universe: all **{len(res)}** mapped datashare predictors (of 95 excl. `permno`, `DATE`)",
        f"- Comparison window: datashare months **{month_min}-{month_max}** only (panel rows/month keys outside this span excluded).",
        "- Month: datashare `DATE // 100`; per-column best of panel `signal_yyyymm` vs `target_yyyymm`.",
        "- `exact%` = |delta| <= 1e-4; `round4%` = values equal when rounded to 4 decimal places.",
        f"- `%m_rho<0.5` = share of months whose monthly Spearman rho is below {LOW_RHO_THRESHOLD}.",
        "- No alias mapping: panel columns already use datashare-native names.",
        "",
        "## Dataset-level (datashare window)",
        "",
        "| Dataset | Rows | Unique permnos | Month range |",
        "|---------|-----:|---------------:|-------------|",
        f"| Panel (restricted) | {len(panel):,} | {len(p_permnos):,} | {int(p_months.min())}-{int(p_months.max())} |",
        f"| Datashare | {len(ds):,} | {len(d_permnos):,} | {int(d_months.min())}-{int(d_months.max())} |",
        "",
        f"- Overlapping `permno x month` cells (signal month): **{len(overlap_keys):,}**",
        f"- Permnos in both: **{len(overlap_permnos):,}**; panel-only: **{len(p_permnos - d_permnos):,}**; "
        f"datashare-only: **{len(d_permnos - p_permnos):,}**",
        "",
        "## Per-column similarity (sorted by median monthly Spearman)",
        "",
        "| datashare | panel col | align | median rho | mean rho | %m_rho<0.5 | pooled rho | exact% | round4% | rel% | paired | ds N | panel N | ds-only keys | panel-only keys | permno both |",
        "|-----------|-----------|-------|---------:|-------:|--------:|---------:|-------:|--------:|-----:|-------:|-----:|--------:|-------------:|----------------:|------------:|",
    ]
    for _, r in res.iterrows():
        em = f(r["match_rate_abs1e-4"] * 100, 1) if pd.notna(r["match_rate_abs1e-4"]) else "---"
        r4 = f(r["match_rate_round4"] * 100, 1) if pd.notna(r["match_rate_round4"]) else "---"
        rl = f(r["match_rate_rel1e-3"] * 100, 1) if pd.notna(r["match_rate_rel1e-3"]) else "---"
        pct_low = f(r["pct_months_rho_lt_05"] * 100, 1) if pd.notna(r["pct_months_rho_lt_05"]) else "---"
        align = "signal" if r["month_align"] == "signal_yyyymm" else "target"
        lines.append(
            f"| `{r['datashare_col']}` | `{r['panel_col']}` | {align} | "
            f"{f(r['median_monthly_spearman'], 3)} | {f(r['mean_monthly_spearman'], 3)} | {pct_low} | "
            f"{f(r['pooled_spearman'], 3)} | {em} | {r4} | {rl} | "
            f"{r['paired_obs']:,} | {r['datashare_nonnull']:,} | {r['panel_nonnull']:,} | "
            f"{r['datashare_only']:,} | {r['panel_only']:,} | {r['permno_both']:,} |"
        )

    num = pd.to_numeric(res["median_monthly_spearman"], errors="coerce")
    lines += [
        "",
        "## Summary buckets (median monthly Spearman vs datashare)",
        "",
        f"- rho >= 0.99: **{int((num >= 0.99).sum())}**",
        f"- 0.95 <= rho < 0.99: **{int(((num >= 0.95) & (num < 0.99)).sum())}**",
        f"- 0.90 <= rho < 0.95: **{int(((num >= 0.90) & (num < 0.95)).sum())}**",
        f"- rho < 0.90 (investigate): **{int((num < 0.90).sum())}**",
        "",
        "### Below rho = 0.95 (review)",
        "",
        "| datashare | panel col | median rho | mean rho | %m_rho<0.5 | pooled rho | exact% | round4% | note |",
        "|-----------|-----------|---------:|-------:|--------:|---------:|-------:|--------:|------|",
    ]
    low = res[num < 0.95].sort_values("median_monthly_spearman")
    notes = {
        "bm_ia": "SIC2 x month demean of HXZ bm (datashare convention)",
        "bm": "HXZ bm mapping",
        "operprof": "HXZ operprof mapping",
        "cfp": "Green cfp mapping",
    }
    for _, r in low.iterrows():
        em = f(r["match_rate_abs1e-4"] * 100, 1) if pd.notna(r["match_rate_abs1e-4"]) else "---"
        r4 = f(r["match_rate_round4"] * 100, 1) if pd.notna(r["match_rate_round4"]) else "---"
        pct_low = f(r["pct_months_rho_lt_05"] * 100, 1) if pd.notna(r["pct_months_rho_lt_05"]) else "---"
        note = notes.get(r["datashare_col"], "")
        lines.append(
            f"| `{r['datashare_col']}` | `{r['panel_col']}` | {f(r['median_monthly_spearman'], 3)} | "
            f"{f(r['mean_monthly_spearman'], 3)} | {pct_low} | "
            f"{f(r['pooled_spearman'], 3)} | {em} | {r4} | {note} |"
        )

    high_rho_low_exact = res[(num >= 0.95) & (res["match_rate_round4"] < 0.5)].sort_values("match_rate_round4")
    if not high_rho_low_exact.empty:
        lines += [
            "",
            "### High rank agreement (rho >= 0.95) but low round-4 match (level/units differ)",
            "",
            "| datashare | median rho | round4% | exact% |",
            "|-----------|---------:|--------:|-------:|",
        ]
        for _, r in high_rho_low_exact.iterrows():
            em = f(r["match_rate_abs1e-4"] * 100, 1) if pd.notna(r["match_rate_abs1e-4"]) else "---"
            r4 = f(r["match_rate_round4"] * 100, 1) if pd.notna(r["match_rate_round4"]) else "---"
            lines.append(f"| `{r['datashare_col']}` | {f(r['median_monthly_spearman'], 3)} | {r4} | {em} |")

    if skipped:
        lines += ["", "## Skipped (no panel column)", ""]
        for ds in skipped:
            lines.append(f"- `{ds}`")

    OUT_MD.parent.mkdir(parents=True, exist_ok=True)
    OUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--panel", type=Path, default=DEFAULT_PANEL)
    parser.add_argument("--datashare", type=Path, default=DEFAULT_DATASHARE)
    args = parser.parse_args()

    panel_path = args.panel
    datashare_path = args.datashare

    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

    panel_cols = set(pd.read_csv(panel_path, nrows=0).columns) - PANEL_META
    pairs, skipped = build_pairs(panel_cols, datashare_path)
    needed = sorted({p for _, p in pairs})

    print(f"Mapped {len(pairs)} datashare predictors; skipped {len(skipped)}", flush=True)
    print("Loading datashare...", flush=True)
    ds = load_datashare(datashare_path)
    month_min, month_max = datashare_month_bounds(ds)
    print(
        f"  datashare rows={len(ds):,} permnos={ds['permno'].nunique():,} "
        f"months={month_min}-{month_max}",
        flush=True,
    )
    print("Loading panel (this may take several minutes)...", flush=True)
    panel = load_panel(panel_path, needed)
    panel_full_rows = len(panel)
    panel = restrict_panel_to_datashare_window(panel, month_min, month_max)
    print(
        f"  panel rows={len(panel):,} (restricted from {panel_full_rows:,}) "
        f"permnos={panel['permno'].nunique():,}",
        flush=True,
    )

    rows = []
    for i, (ds_col, pcol) in enumerate(pairs, start=1):
        print(f"  [{i}/{len(pairs)}] {ds_col} -> {pcol}", flush=True)
        rows.append(compare_column(ds, panel, ds_col, pcol, month_min, month_max))

    res = pd.DataFrame(rows).sort_values("median_monthly_spearman", ascending=False, na_position="last")
    OUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    res.to_csv(OUT_CSV, index=False)
    write_md(res, skipped, panel, ds, panel_path, month_min, month_max)

    print(f"\nWrote {OUT_CSV}")
    print(f"Wrote {OUT_MD}")


if __name__ == "__main__":
    main()
