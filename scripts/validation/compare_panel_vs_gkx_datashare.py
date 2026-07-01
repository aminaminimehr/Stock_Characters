#!/usr/bin/env python3
"""Full-period similarity: server panel vs GKX datashare.csv (all predictors).

For every column in datashare.csv that maps to a panel column, compute:
  - dataset-level permno / month coverage
  - per-column key overlap (datashare-only, panel-only, both)
  - pooled Spearman and median monthly cross-sectional Spearman
  - exact match |Δ| ≤ 1e-4 and round-to-4-decimal match

All panel-side counts and comparisons are restricted to the datashare calendar
window (min/max ``DATE // 100`` in datashare.csv) so post-2021 panel tail rows
do not inflate panel-only keys or coverage stats.

Month alignment: datashare ``DATE`` → ``YYYYMM`` via ``DATE // 100``; auto-pick panel
``signal_yyyymm`` vs ``target_yyyymm`` per column (whichever yields higher median ρ).
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_PANEL = ROOT / "outputs" / "panels" / "all_character_signal_panel_for_GKX_comparison.csv"
DEFAULT_DATASHARE = ROOT / "Supplementary_assistive_files" / "datashare.csv"
OUT_CSV = ROOT / "docs" / "gkx" / "panel_gkx_datashare_full_comparison.csv"
OUT_MD = ROOT / "docs" / "gkx" / "panel_gkx_datashare_full_comparison.md"

MIN_PAIRS = 50

PANEL_META = {
    "permno",
    "permco",
    "gvkey",
    "date",
    "datadate",
    "source_date",
    "source_yyyymm",
    "signal_yyyymm",
    "target_yyyymm",
    "yyyymm",
    "sic",
    "exchcd",
    "shrcd",
    "fyear",
    "availability_date",
    "calendar_year",
    "excess_return",
    "ffi49",
}

# datashare name -> panel column (when they differ).
# Only true name remaps live here; all other datashare predictors are compared
# directly against the Green-style panel columns (chtx, cinvest, bm_ia, cfp_ia,
# cfp, pchcapx_ia, chpmia, ...).  The earlier experimental _gkx / _dc variants
# have been removed from the repo.
PANEL_ALIAS: dict[str, str] = {
    "bm": "book_to_market",
    "operprof": "operating_profitability",
    "mve_ia": "me_ia",
    "rd_mve": "rdm",
    "retvol": "rvar_mean",
    "ear": "abr",
}


def datashare_predictors(datashare_path: Path = DEFAULT_DATASHARE) -> list[str]:
    cols = list(pd.read_csv(datashare_path, nrows=0).columns)
    return sorted(c for c in cols if c not in ("permno", "DATE"))


def panel_column(ds_col: str, panel_cols: set[str]) -> str | None:
    pcol = PANEL_ALIAS.get(ds_col, ds_col)
    if pcol in panel_cols:
        return pcol
    return None


def build_pairs(panel_cols: set[str], datashare_path: Path) -> tuple[list[tuple[str, str]], list[str]]:
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


def restrict_panel_to_datashare_window(
    panel: pd.DataFrame,
    month_min: int,
    month_max: int,
) -> pd.DataFrame:
    """Drop panel rows whose signal and target months both fall outside datashare span."""
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


def monthly_median_spearman(df: pd.DataFrame, a: str, b: str) -> tuple[float, int]:
    vals = []
    for _, grp in df.groupby("month", sort=True):
        sub = grp[[a, b]].dropna()
        if len(sub) < MIN_PAIRS:
            continue
        r = sub[a].corr(sub[b], method="spearman")
        if pd.notna(r):
            vals.append(r)
    return (float(np.median(vals)), len(vals)) if vals else (np.nan, 0)


def compare_column(
    ds: pd.DataFrame,
    panel: pd.DataFrame,
    ds_col: str,
    pcol: str,
    month_min: int,
    month_max: int,
) -> dict:
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
            mm, mm_n = monthly_median_spearman(m, "pv", "dv")
        else:
            pooled = match_1e4 = match_round4 = match_rel = np.nan
            mm, mm_n = np.nan, 0

        both = ds_keys & panel_keys
        row = {
            "datashare_col": ds_col,
            "panel_col": pcol,
            "month_align": month_col,
            "datashare_nonnull": len(ds_keys),
            "panel_nonnull": len(panel_keys),
            "keys_both": len(both),
            "datashare_only": len(ds_keys - panel_keys),
            "panel_only": len(panel_keys - ds_keys),
            "permno_datashare": int(ds_sub.loc[ds_sub["dv"].notna(), "permno"].nunique()),
            "permno_panel": int(ps.loc[ps["pv"].notna(), "permno"].nunique()),
            "permno_both": int(m["permno"].nunique()) if n_pair else 0,
            "paired_obs": int(n_pair),
            "pooled_spearman": pooled,
            "median_monthly_spearman": mm,
            "spearman_months": mm_n,
            "match_rate_abs1e-4": match_1e4,
            "match_rate_round4": match_round4,
            "match_rate_rel1e-3": match_rel,
        }
        if best_row is None or (pd.notna(mm) and (pd.isna(best_row["median_monthly_spearman"]) or mm > best_row["median_monthly_spearman"])):
            best_row = row
    return best_row or {}


def write_md(
    res: pd.DataFrame,
    skipped: list[str],
    panel: pd.DataFrame,
    ds: pd.DataFrame,
    panel_path: Path,
    month_min: int,
    month_max: int,
) -> None:
    def f(x, d=4):
        return "—" if pd.isna(x) else f"{x:.{d}f}"

    p_permnos = set(panel["permno"].dropna().unique())
    d_permnos = set(ds["permno"].dropna().unique())
    p_months = panel["signal_yyyymm"].dropna()
    d_months = ds["month"].dropna()
    panel_signal = panel[["permno", "signal_yyyymm"]].rename(columns={"signal_yyyymm": "month"})
    panel_signal = panel_signal[panel_signal["month"].between(month_min, month_max)]
    overlap_keys = pd.merge(
        panel_signal.drop_duplicates(),
        ds[["permno", "month"]].drop_duplicates(),
        on=["permno", "month"],
        how="inner",
    )
    overlap_permnos = set(overlap_keys["permno"].dropna().unique())

    lines = [
        "# Server panel vs GKX datashare.csv — full-period comparison",
        "",
        f"- Panel: `{panel_path.name}`",
        f"- Datashare: `{DEFAULT_DATASHARE.name}`",
        f"- Column universe: all **{len(res)}** mapped datashare predictors (of 95 excl. `permno`, `DATE`)",
        f"- Comparison window: datashare months **{month_min}–{month_max}** only (panel rows/month keys outside this span excluded).",
        "- Month: datashare `DATE // 100`; per-column best of panel `signal_yyyymm` vs `target_yyyymm`.",
        "- `exact%` = |Δ| ≤ 1e-4; `round4%` = values equal when rounded to 4 decimal places.",
        "",
        "## Dataset-level (datashare window)",
        "",
        "| Dataset | Rows | Unique permnos | Month range |",
        "|---------|-----:|---------------:|-------------|",
        f"| Panel (restricted) | {len(panel):,} | {len(p_permnos):,} | {int(p_months.min())}–{int(p_months.max())} |",
        f"| Datashare | {len(ds):,} | {len(d_permnos):,} | {int(d_months.min())}–{int(d_months.max())} |",
        "",
        f"- Overlapping `permno × month` cells (signal month): **{len(overlap_keys):,}**",
        f"- Permnos in both: **{len(overlap_permnos):,}**; panel-only: **{len(p_permnos - d_permnos):,}**; "
        f"datashare-only: **{len(d_permnos - p_permnos):,}**",
        "",
        "## Per-column similarity (sorted by median monthly Spearman)",
        "",
        "| datashare | panel col | align | median ρ | pooled ρ | exact% | round4% | rel% | paired | ds N | panel N | ds-only keys | panel-only keys | permno both |",
        "|-----------|-----------|-------|---------:|---------:|-------:|--------:|-----:|-------:|-----:|--------:|-------------:|----------------:|------------:|",
    ]
    for _, r in res.iterrows():
        em = f(r["match_rate_abs1e-4"] * 100, 1) if pd.notna(r["match_rate_abs1e-4"]) else "—"
        r4 = f(r["match_rate_round4"] * 100, 1) if pd.notna(r["match_rate_round4"]) else "—"
        rl = f(r["match_rate_rel1e-3"] * 100, 1) if pd.notna(r["match_rate_rel1e-3"]) else "—"
        align = "signal" if r["month_align"] == "signal_yyyymm" else "target"
        lines.append(
            f"| `{r['datashare_col']}` | `{r['panel_col']}` | {align} | "
            f"{f(r['median_monthly_spearman'], 3)} | {f(r['pooled_spearman'], 3)} | {em} | {r4} | {rl} | "
            f"{r['paired_obs']:,} | {r['datashare_nonnull']:,} | {r['panel_nonnull']:,} | "
            f"{r['datashare_only']:,} | {r['panel_only']:,} | {r['permno_both']:,} |"
        )

    num = pd.to_numeric(res["median_monthly_spearman"], errors="coerce")
    lines += [
        "",
        "## Summary buckets (median monthly Spearman vs datashare)",
        "",
        f"- ρ ≥ 0.99: **{int((num >= 0.99).sum())}**",
        f"- 0.95 ≤ ρ < 0.99: **{int(((num >= 0.95) & (num < 0.99)).sum())}**",
        f"- 0.90 ≤ ρ < 0.95: **{int(((num >= 0.90) & (num < 0.95)).sum())}**",
        f"- ρ < 0.90 (investigate): **{int((num < 0.90).sum())}**",
        "",
        "### Below ρ = 0.95 (review)",
        "",
        "| datashare | panel col | median ρ | pooled ρ | exact% | round4% | note |",
        "|-----------|-----------|---------:|---------:|-------:|--------:|------|",
    ]
    low = res[num < 0.95].sort_values("median_monthly_spearman")
    notes = {
        "bm_ia": "out of scope — no reliable replication",
        "bm": "HXZ `book_to_market` mapping",
        "operprof": "HXZ `operating_profitability` mapping",
        "cfp": "Green `cfp` mapping",
    }
    for _, r in low.iterrows():
        em = f(r["match_rate_abs1e-4"] * 100, 1) if pd.notna(r["match_rate_abs1e-4"]) else "—"
        r4 = f(r["match_rate_round4"] * 100, 1) if pd.notna(r["match_rate_round4"]) else "—"
        note = notes.get(r["datashare_col"], "")
        lines.append(
            f"| `{r['datashare_col']}` | `{r['panel_col']}` | {f(r['median_monthly_spearman'], 3)} | "
            f"{f(r['pooled_spearman'], 3)} | {em} | {r4} | {note} |"
        )

    high_rho_low_exact = res[(num >= 0.95) & (res["match_rate_round4"] < 0.5)].sort_values(
        "match_rate_round4"
    )
    if not high_rho_low_exact.empty:
        lines += [
            "",
            "### High rank agreement (ρ ≥ 0.95) but low round-4 match (level/units differ)",
            "",
            "| datashare | median ρ | round4% | exact% |",
            "|-----------|---------:|--------:|-------:|",
        ]
        for _, r in high_rho_low_exact.iterrows():
            em = f(r["match_rate_abs1e-4"] * 100, 1) if pd.notna(r["match_rate_abs1e-4"]) else "—"
            r4 = f(r["match_rate_round4"] * 100, 1) if pd.notna(r["match_rate_round4"]) else "—"
            lines.append(
                f"| `{r['datashare_col']}` | {f(r['median_monthly_spearman'], 3)} | {r4} | {em} |"
            )

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
        f"months={month_min}–{month_max}",
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
