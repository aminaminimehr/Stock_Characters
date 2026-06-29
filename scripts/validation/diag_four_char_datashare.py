#!/usr/bin/env python3
"""Diagnose panel vs datashare gaps for ms, indmom, chpmia, pchcapx_ia.

Uses a narrow sample window by default to keep I/O small. Tests:
  - signal vs target month alignment
  - monthly 1/99 winsorization (Green SAS final step)
  - formula recomputation where panel has components (indmom, chpmia, pchcapx_ia)
  - ms integer score diff patterns
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_PANEL = ROOT / "outputs" / "panels" / "all_character_signal_panel_for_GKX_comparison.csv"
DEFAULT_DS = ROOT / "Supplementary_assistive_files" / "datashare.csv"
OUT_MD = ROOT / "docs" / "gkx" / "four_char_mismatch_diagnosis.md"

FOCUS = {
    "ms": "ms",
    "indmom": "indmom",
    "chpmia": "chpmia",
    "pchcapx_ia": "pchcapx_ia",
}

COMPONENTS = {
    "indmom": ["mom12m", "sic2"],
    "chpmia": ["chpm"],
    "pchcapx_ia": ["pchcapx"],
}


def month_bounds(ds_path: Path) -> tuple[int, int]:
    months = []
    for chunk in pd.read_csv(ds_path, usecols=["DATE"], chunksize=500_000):
        months.append(chunk["DATE"] // 100)
    m = pd.concat(months, ignore_index=True)
    return int(m.min()), int(m.max())


def load_datashare(
    ds_path: Path,
    month_min: int,
    month_max: int,
    extra_cols: list[str],
) -> pd.DataFrame:
    usecols = ["permno", "DATE"] + sorted(set(extra_cols))
    parts = []
    for chunk in pd.read_csv(ds_path, usecols=usecols, chunksize=500_000):
        chunk["month"] = (pd.to_numeric(chunk["DATE"], errors="coerce") // 100).astype("Int64")
        chunk = chunk[(chunk["month"] >= month_min) & (chunk["month"] <= month_max)]
        if len(chunk):
            parts.append(chunk.drop(columns=["DATE"]))
    return pd.concat(parts, ignore_index=True) if parts else pd.DataFrame(columns=["permno", "month"])


def load_panel(
    panel_path: Path,
    month_min: int,
    month_max: int,
    cols: list[str],
) -> pd.DataFrame:
    usecols = ["permno", "signal_yyyymm", "target_yyyymm"] + cols
    parts = []
    for chunk in pd.read_csv(panel_path, usecols=usecols, chunksize=300_000):
        chunk["permno"] = pd.to_numeric(chunk["permno"], errors="coerce").astype("Int64")
        chunk["signal_yyyymm"] = pd.to_numeric(chunk["signal_yyyymm"], errors="coerce").astype("Int64")
        chunk["target_yyyymm"] = pd.to_numeric(chunk["target_yyyymm"], errors="coerce").astype("Int64")
        in_window = chunk["signal_yyyymm"].between(month_min, month_max) | chunk["target_yyyymm"].between(
            month_min, month_max
        )
        chunk = chunk.loc[in_window]
        if len(chunk):
            parts.append(chunk)
    return pd.concat(parts, ignore_index=True) if parts else pd.DataFrame(columns=usecols)


def monthly_winsor(df: pd.DataFrame, col: str, month_col: str = "month") -> pd.Series:
    """Green-style cross-sectional 1/99 winsor by month."""

    def _w(g: pd.Series) -> pd.Series:
        if g.notna().sum() < 10:
            return g
        lo, hi = g.quantile(0.01), g.quantile(0.99)
        return g.clip(lo, hi)

    return df.groupby(month_col, group_keys=False)[col].apply(_w)


def spearman(x: pd.Series, y: pd.Series) -> float:
    m = x.notna() & y.notna()
    if m.sum() < 3:
        return float("nan")
    return float(x[m].corr(y[m], method="spearman"))


def exact_rate(x: pd.Series, y: pd.Series, tol: float = 1e-4) -> float:
    m = x.notna() & y.notna()
    if not m.any():
        return float("nan")
    return float((x[m] - y[m]).abs().le(tol).mean())


def compare_pair(panel: pd.DataFrame, ds: pd.DataFrame, pcol: str, dcol: str, month_col: str) -> dict:
    m = panel.merge(ds, left_on=["permno", month_col], right_on=["permno", "month"], how="inner")
    m = m.dropna(subset=[pcol, dcol])
    if len(m) < 3:
        return {"paired": len(m)}
    pv, dv = m[pcol].astype(float), m[dcol].astype(float)
    diff = pv - dv
    out = {
        "paired": len(m),
        "spearman": spearman(pv, dv),
        "exact_rate": exact_rate(pv, dv),
        "median_abs_diff": float(diff.abs().median()),
        "mean_abs_diff": float(diff.abs().mean()),
    }
    # winsorized panel side only (datashare already winsorized in Green export)
    m2 = m.copy()
    m2["pv_w"] = monthly_winsor(m2.assign(month=m2[month_col]), "pv", month_col=month_col)
    if "pv" not in m2.columns:
        m2["pv"] = pv
    m2["pv_w"] = monthly_winsor(
        m2.rename(columns={pcol: "pv"}), "pv", month_col=month_col
    )
    out["spearman_panel_winsor"] = spearman(m2["pv_w"], dv)
    return out


def diagnose_ms(panel: pd.DataFrame, ds: pd.DataFrame) -> list[str]:
    lines = ["## ms (Mohanram 0–8 score)", ""]
    best = None
    ds_ms = ds[["permno", "month", "ms"]].rename(columns={"ms": "ds_ms"})
    for align, mcol in [("signal", "signal_yyyymm"), ("target", "target_yyyymm")]:
        m = panel[["permno", mcol, "ms"]].merge(
            ds_ms, left_on=["permno", mcol], right_on=["permno", "month"], how="inner"
        )
        m = m.dropna(subset=["ms", "ds_ms"])
        if m.empty:
            continue
        pv, dv = m["ms"].astype(float), m["ds_ms"].astype(float)
        diff = (pv - dv).astype(int)
        row = {
            "align": align,
            "paired": len(m),
            "spearman": spearman(pv, dv),
            "exact": exact_rate(pv, dv),
            "exact_int": float((pv.round() == dv.round()).mean()),
        }
        if best is None or (pd.notna(row["spearman"]) and row["spearman"] > best["spearman"]):
            best = row
        lines.append(
            f"- **{align} month**: paired={row['paired']:,}, ρ={row['spearman']:.3f}, "
            f"exact={100*row['exact']:.1f}%, integer-match={100*row['exact_int']:.1f}%"
        )
        vc = diff.value_counts().head(8)
        lines.append(f"  - Top score diffs (panel − datashare): " + ", ".join(f"{k:+d}:{v:,}" for k, v in vc.items()))
    if best:
        lines.append(f"- **Best alignment**: {best['align']}")
    lines.append(
        "- **Likely drivers**: (1) m7/m8 quarterly merge on `date` vs annual m1–m6 on "
        "`signal_yyyymm`; (2) component-level disagreement; (3) datashare/Green may "
        "winsorize `ms` monthly (L1167) though scores are discrete."
    )
    lines.append("")
    return lines


def diagnose_indmom(panel: pd.DataFrame, ds: pd.DataFrame) -> list[str]:
    lines = ["## indmom (equal-weight mean mom12m by sic2 × month)", ""]
    m = panel[["permno", "signal_yyyymm", "indmom", "mom12m", "sic2"]].merge(
        ds[["permno", "month", "indmom", "mom12m", "sic2"]].rename(
            columns={"indmom": "ds_indmom", "mom12m": "ds_mom12m", "sic2": "ds_sic2"}
        ),
        left_on=["permno", "signal_yyyymm"],
        right_on=["permno", "month"],
        how="inner",
    )
    m = m.dropna(subset=["indmom", "ds_indmom", "mom12m"])
    lines.append(
        f"- Raw panel vs datashare: paired={len(m):,}, ρ={spearman(m['indmom'], m['ds_indmom']):.3f}, "
        f"exact={100*exact_rate(m['indmom'], m['ds_indmom']):.1f}%"
    )
    lines.append(
        f"- Panel mom12m vs datashare mom12m (same rows): ρ={spearman(m['mom12m'], m['ds_mom12m']):.3f}"
    )

    # Recompute industry mean from panel mom12m using panel sic2
    m["sic2_panel"] = m["sic2"].astype(str).str.zfill(2)
    ind_panel = m.groupby(["sic2_panel", "signal_yyyymm"], as_index=False)["mom12m"].mean().rename(
        columns={"mom12m": "re_indmom_panel_sic"}
    )
    m = m.merge(ind_panel, on=["sic2_panel", "signal_yyyymm"], how="left")
    lines.append(
        f"- Recomputed mean(mom12m)|panel sic2: ρ vs datashare indmom = "
        f"{spearman(m['re_indmom_panel_sic'], m['ds_indmom']):.3f}; vs panel indmom = "
        f"{spearman(m['re_indmom_panel_sic'], m['indmom']):.3f}"
    )

    # Recompute using datashare sic2
    m["ds_sic2_str"] = pd.to_numeric(m["ds_sic2"], errors="coerce").astype("Int64").astype(str)
    ind_ds = m.groupby(["ds_sic2_str", "signal_yyyymm"], as_index=False)["mom12m"].mean().rename(
        columns={"mom12m": "re_indmom_ds_sic"}
    )
    m = m.merge(ind_ds, on=["ds_sic2_str", "signal_yyyymm"], how="left")
    lines.append(
        f"- Recomputed mean(mom12m)|datashare sic2: ρ vs datashare indmom = "
        f"{spearman(m['re_indmom_ds_sic'], m['ds_indmom']):.3f}"
    )

    sic_agree = (m["sic2_panel"] == m["ds_sic2_str"].str.zfill(2)).mean()
    lines.append(f"- Panel sic2 == datashare sic2 (same permno-month): {100*sic_agree:.1f}%")

    # Universe effect: use datashare mom12m for industry mean
    ds_only = ds.dropna(subset=["mom12m", "sic2"]).copy()
    ds_only["sic2_str"] = pd.to_numeric(ds_only["sic2"], errors="coerce").astype("Int64").astype(str).str.zfill(2)
    ind_ds_univ = ds_only.groupby(["sic2_str", "month"], as_index=False)["mom12m"].mean().rename(
        columns={"mom12m": "re_indmom_ds_univ"}
    )
    m = m.merge(ind_ds_univ, left_on=["ds_sic2_str", "signal_yyyymm"], right_on=["sic2_str", "month"], how="left")
    lines.append(
        f"- Recomputed mean(datashare mom12m)|datashare universe: ρ vs datashare indmom = "
        f"{spearman(m['re_indmom_ds_univ'], m['ds_indmom']):.3f}"
    )

    m2 = m.copy()
    m2["month"] = m2["signal_yyyymm"]
    m2["indmom_w"] = monthly_winsor(m2.rename(columns={"indmom": "indmom"}), "indmom")
    lines.append(
        f"- Panel indmom after monthly 1/99 winsor: ρ vs datashare = "
        f"{spearman(m2['indmom_w'], m2['ds_indmom']):.3f}"
    )
    lines.append(
        "- **Likely drivers**: sic2 source/timing; firm set entering industry mean (datashare "
        "universe vs full CRSP); monthly winsorization of indmom in datashare."
    )
    lines.append("")
    return lines


def diagnose_ia(panel: pd.DataFrame, ds: pd.DataFrame, char: str, base: str) -> list[str]:
    lines = [f"## {char} (industry-demeaned {base})", ""]
    ds_col = char
    ds_sub = ds[["permno", "month", ds_col]].rename(columns={ds_col: f"ds_{char}"})
    for align, mcol in [("signal", "signal_yyyymm"), ("target", "target_yyyymm")]:
        cols = ["permno", mcol, char, base]
        sub = panel[cols].merge(ds_sub, left_on=["permno", mcol], right_on=["permno", "month"], how="inner")
        sub = sub.dropna(subset=[char, f"ds_{char}"])
        if sub.empty:
            continue
        lines.append(
            f"- **{align}** {char}: paired={len(sub):,}, ρ={spearman(sub[char], sub[f'ds_{char}']):.3f}, "
            f"exact={100*exact_rate(sub[char], sub[f'ds_{char}']):.1f}%"
        )
        if base in sub.columns:
            lines.append(
                f"  - Panel base `{base}` on overlap: non-null={sub[base].notna().sum():,}, "
                f"median={sub[base].median():.4f}, p99={sub[base].quantile(0.99):.4f}"
            )
        sub = sub.copy()
        sub["month"] = sub[mcol]
        sub["pv_w"] = monthly_winsor(sub.rename(columns={char: char}), char)
        lines.append(
            f"  - After monthly 1/99 winsor on panel {char}: ρ={spearman(sub['pv_w'], sub[f'ds_{char}']):.3f}"
        )
    if char == "pchcapx_ia":
        lines.append(
            "- **Note**: negative `lag(capx)` denominators affect `pchcapx` (~1.6k permnos); "
            "industry mean uses SIC2×fyear at fiscal datadate, then Green months 7–19."
        )
    lines.append("")
    return lines


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--panel", type=Path, default=DEFAULT_PANEL)
    parser.add_argument("--datashare", type=Path, default=DEFAULT_DS)
    parser.add_argument("--month-min", type=int, default=201001)
    parser.add_argument("--month-max", type=int, default=201512)
    parser.add_argument("--full-window", action="store_true", help="Use full datashare month span")
    args = parser.parse_args()

    if args.full_window:
        args.month_min, args.month_max = month_bounds(args.datashare)

    extra_ds = ["ms", "indmom", "chpmia", "pchcapx_ia", "mom12m", "sic2"]
    panel_cols = ["ms", "indmom", "chpmia", "pchcapx_ia", "mom12m", "sic2", "chpm", "pchcapx"]

    print(f"Window {args.month_min}-{args.month_max}", flush=True)
    print("Loading datashare...", flush=True)
    ds = load_datashare(args.datashare, args.month_min, args.month_max, extra_ds)
    print(f"  datashare rows={len(ds):,}", flush=True)
    print("Loading panel...", flush=True)
    panel = load_panel(args.panel, args.month_min, args.month_max, panel_cols)
    print(f"  panel rows={len(panel):,}", flush=True)

    lines = [
        "# Four-character mismatch diagnosis (panel vs datashare)",
        "",
        f"- Window: **{args.month_min}–{args.month_max}**",
        f"- Panel: `{args.panel.name}`",
        f"- Datashare: `{args.datashare.name}`",
        "",
    ]
    lines.extend(diagnose_ms(panel, ds))
    lines.extend(diagnose_indmom(panel, ds))
    lines.extend(diagnose_ia(panel, ds, "chpmia", "chpm"))
    lines.extend(diagnose_ia(panel, ds, "pchcapx_ia", "pchcapx"))

    OUT_MD.parent.mkdir(parents=True, exist_ok=True)
    OUT_MD.write_text("\n".join(lines), encoding="utf-8")
    print(f"Wrote {OUT_MD}", flush=True)


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    main()
