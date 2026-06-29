#!/usr/bin/env python3
"""Deep formula diagnosis for ms, indmom, chpmia, pchcapx_ia (panel vs Green vs datashare)."""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pyreadstat

ROOT = Path(__file__).resolve().parents[2]
GREEN = ROOT / "Supplementary_assistive_files" / "Output_From_Greens_SAS_code.sas7bdat"
PANEL = ROOT / "outputs" / "panels" / "all_character_signal_panel_for_GKX_comparison.csv"
DS = ROOT / "Supplementary_assistive_files" / "datashare.csv"
OUT = ROOT / "docs" / "gkx" / "four_char_deep_diagnosis.md"

MONTH_MIN, MONTH_MAX = 201001, 201512


def rho(a: pd.Series, b: pd.Series) -> float:
    m = a.notna() & b.notna()
    return float(a[m].corr(b[m], method="spearman")) if m.sum() > 10 else float("nan")


def monthly_winsor(s: pd.Series, month: pd.Series) -> pd.Series:
    out = s.copy()
    for m, grp in s.groupby(month):
        v = grp.dropna()
        if len(v) < 10:
            continue
        lo, hi = v.quantile(0.01), v.quantile(0.99)
        out.loc[grp.index] = grp.clip(lo, hi)
    return out


def load_green(cols: list[str]) -> pd.DataFrame:
    g, _ = pyreadstat.read_sas7bdat(str(GREEN), usecols=cols)
    g["month"] = pd.to_datetime(g["DATE"]).dt.year * 100 + pd.to_datetime(g["DATE"]).dt.month
    g = g[g["month"].between(MONTH_MIN, MONTH_MAX)].copy()
    g["permno"] = pd.to_numeric(g["permno"], errors="coerce").astype("Int64")
    return g


def load_panel(cols: list[str]) -> pd.DataFrame:
    parts = []
    for chunk in pd.read_csv(PANEL, usecols=cols, chunksize=300_000):
        chunk = chunk[chunk["signal_yyyymm"].between(MONTH_MIN, MONTH_MAX)]
        parts.append(chunk)
    p = pd.concat(parts, ignore_index=True)
    p["permno"] = pd.to_numeric(p["permno"], errors="coerce").astype("Int64")
    return p


def load_datashare(cols: list[str]) -> pd.DataFrame:
    parts = []
    for chunk in pd.read_csv(DS, usecols=cols, chunksize=500_000):
        chunk["month"] = chunk["DATE"] // 100
        chunk = chunk[chunk["month"].between(MONTH_MIN, MONTH_MAX)]
        parts.append(chunk.drop(columns=["DATE"]))
    d = pd.concat(parts, ignore_index=True)
    d["permno"] = pd.to_numeric(d["permno"], errors="coerce").astype("Int64")
    return d


def merge_three(g: pd.DataFrame, p: pd.DataFrame, d: pd.DataFrame, char: str) -> pd.DataFrame:
    m = (
        g[["permno", "month", char]].rename(columns={char: "green"})
        .merge(p[["permno", "signal_yyyymm", char]].rename(columns={"signal_yyyymm": "month", char: "panel"}), on=["permno", "month"], how="inner")
        .merge(d[["permno", "month", char]].rename(columns={char: "datashare"}), on=["permno", "month"], how="inner")
    )
    return m.dropna(subset=["green", "panel", "datashare"])


def diagnose_chpmia(g, p, d) -> list[str]:
    lines = ["## chpmia — formula decomposition", ""]
    m = merge_three(g, p, d, "chpmia")
    lines.append(f"- Three-way overlap (non-null): **{len(m):,}** rows")
    lines.append(f"- Spearman: panel–Green={rho(m['panel'], m['green']):.3f}, "
                 f"datashare–Green={rho(m['datashare'], m['green']):.3f}, "
                 f"panel–datashare={rho(m['panel'], m['datashare']):.3f}")

    # Green has raw chpm; panel has chpm
    gc = g[["permno", "month", "chpm", "chpmia"]].rename(columns={"chpm": "green_chpm", "chpmia": "green_chpmia"})
    pc = p[["permno", "signal_yyyymm", "chpm", "chpmia"]].rename(
        columns={"signal_yyyymm": "month", "chpm": "panel_chpm", "chpmia": "panel_chpmia"}
    )
    dc = d[["permno", "month", "chpmia"]].rename(columns={"chpmia": "ds_chpmia"})
    x = gc.merge(pc, on=["permno", "month"], how="inner").merge(dc, on=["permno", "month"], how="inner")
    x = x.dropna(subset=["green_chpm", "panel_chpm", "ds_chpmia"])

    lines.extend([
        "",
        "### Cross-column checks (same permno-month)",
        "",
        f"- panel `chpm` vs datashare `chpmia`: ρ={rho(x['panel_chpm'], x['ds_chpmia']):.3f}",
        f"- Green `chpm` vs datashare `chpmia`: ρ={rho(x['green_chpm'], x['ds_chpmia']):.3f}",
        f"- panel `chpm` vs Green `chpm`: ρ={rho(x['panel_chpm'], x['green_chpm']):.3f}",
        f"- panel `chpmia` vs Green `chpm`: ρ={rho(x['panel_chpmia'], x['green_chpm']):.3f}",
        f"- Green `chpmia` vs Green `chpm` (demean sanity): ρ={rho(x['green_chpmia'], x['green_chpm']):.3f}",
    ])

    # Winsorization test on Green chpmia toward datashare
    gw = monthly_winsor(x["green_chpmia"], x["month"])
    pw = monthly_winsor(x["panel_chpmia"], x["month"])
    lines.extend([
        "",
        "### Monthly 1/99 winsor",
        "",
        f"- winsor(Green chpmia) vs datashare chpmia: ρ={rho(gw, x['ds_chpmia']):.3f}",
        f"- winsor(panel chpmia) vs datashare chpmia: ρ={rho(pw, x['ds_chpmia']):.3f}",
    ])

    # Target-month shift for datashare
    d_tgt = d.copy()
    d_tgt["month_signal"] = d_tgt["month"] - 1  # crude: only works within year
    # proper: merge panel target_yyyymm
    pt = p[["permno", "target_yyyymm", "chpmia"]].rename(columns={"target_yyyymm": "month", "chpmia": "panel_tgt"})
    dt = d[["permno", "month", "chpmia"]].rename(columns={"chpmia": "ds_val"})
    tgt = pt.merge(dt, on=["permno", "month"], how="inner").dropna()
    sig = p[["permno", "signal_yyyymm", "chpmia"]].rename(
        columns={"signal_yyyymm": "month", "chpmia": "panel_sig"}
    ).merge(dt, on=["permno", "month"], how="inner").dropna()
    lines.extend([
        "",
        "### Month alignment (panel signal vs target vs datashare DATE//100)",
        "",
        f"- panel signal vs datashare: ρ={rho(sig['panel_sig'], sig['ds_val']):.3f} (n={len(sig):,})",
        f"- panel target vs datashare: ρ={rho(tgt['panel_tgt'], tgt['ds_val']):.3f} (n={len(tgt):,})",
    ])

    lines.extend([
        "",
        "**Interpretation:** Panel matches Green `chpmia` (SIC2×fyear mean demean of `chpm`). "
        "If datashare `chpmia` ρ≪1 vs Green, datashare uses a different construction "
        "(not our Green formula) despite the column name.",
        "",
    ])
    return lines


def diagnose_pchcapx_ia(g, p, d) -> list[str]:
    lines = ["## pchcapx_ia — formula decomposition", ""]
    m = merge_three(g, p, d, "pchcapx_ia")
    lines.append(f"- Three-way overlap: **{len(m):,}** rows")
    lines.append(f"- Spearman: panel–Green={rho(m['panel'], m['green']):.3f}, "
                 f"datashare–Green={rho(m['datashare'], m['green']):.3f}, "
                 f"panel–datashare={rho(m['panel'], m['datashare']):.3f}")

    gc = g[["permno", "month", "pchcapx", "pchcapx_ia"]].rename(
        columns={"pchcapx": "green_pchcapx", "pchcapx_ia": "green_ia"}
    )
    pc = p[["permno", "signal_yyyymm", "pchcapx", "pchcapx_ia"]].rename(
        columns={"signal_yyyymm": "month", "pchcapx": "panel_pchcapx", "pchcapx_ia": "panel_ia"}
    )
    dc = d[["permno", "month", "pchcapx_ia"]].rename(columns={"pchcapx_ia": "ds_ia"})
    x = gc.merge(pc, on=["permno", "month"], how="inner").merge(dc, on=["permno", "month"], how="inner")
    x = x.dropna(subset=["green_pchcapx", "panel_pchcapx", "ds_ia"])

    lines.extend([
        "",
        f"- panel `pchcapx` vs Green `pchcapx`: ρ={rho(x['panel_pchcapx'], x['green_pchcapx']):.3f}",
        f"- panel `pchcapx` vs datashare `pchcapx_ia`: ρ={rho(x['panel_pchcapx'], x['ds_ia']):.3f}",
        f"- Green `pchcapx` vs datashare `pchcapx_ia`: ρ={rho(x['green_pchcapx'], x['ds_ia']):.3f}",
        f"- winsor(panel ia) vs datashare ia: ρ={rho(monthly_winsor(x['panel_ia'], x['month']), x['ds_ia']):.3f}",
        f"- winsor(Green ia) vs datashare ia: ρ={rho(monthly_winsor(x['green_ia'], x['month']), x['ds_ia']):.3f}",
        "",
        "**Interpretation:** Decompose base `pchcapx` agreement first; then industry demean; "
        "Green winsorizes `pchcapx_ia` monthly (L1164–1182).",
        "",
    ])
    return lines


def diagnose_ms(g, p, d) -> list[str]:
    lines = ["## ms — Mohanram score", ""]
    m = merge_three(g, p, d, "ms")
    lines.append(f"- Three-way overlap: **{len(m):,}** rows")
    lines.append(f"- Spearman: panel–Green={rho(m['panel'], m['green']):.3f}, "
                 f"datashare–Green={rho(m['datashare'], m['green']):.3f}, "
                 f"panel–datashare={rho(m['panel'], m['datashare']):.3f}")

    m["panel_i"] = m["panel"].round().astype("Int64")
    m["green_i"] = m["green"].round().astype("Int64")
    m["ds_i"] = m["datashare"].round().astype("Int64")
    m["diff_pg"] = m["panel_i"] - m["green_i"]
    m["diff_dg"] = m["ds_i"] - m["green_i"]

    lines.extend([
        "",
        "### Integer score diffs",
        "",
        f"- panel vs Green exact match: {(m['diff_pg'] == 0).mean()*100:.1f}%",
        f"- datashare vs Green exact match: {(m['diff_dg'] == 0).mean()*100:.1f}%",
        "",
        "Top panel−Green diffs:",
    ])
    for val, cnt in m["diff_pg"].value_counts().head(8).items():
        lines.append(f"- {val:+d}: {cnt:,}")

    lines.extend([
        "",
        "Top datashare−Green diffs:",
    ])
    for val, cnt in m["diff_dg"].value_counts().head(8).items():
        lines.append(f"- {val:+d}: {cnt:,}")

    # When panel < green, often missing m7/m8?
    low = m[m["diff_pg"] < 0]
    high = m[m["diff_pg"] > 0]
    lines.extend([
        "",
        f"- Rows where panel < Green: {len(low):,} (mean gap {(-low['diff_pg']).mean():.2f})",
        f"- Rows where panel > Green: {len(high):,} (mean gap {high['diff_pg'].mean():.2f})",
        "",
        "**Interpretation:** Datashare tracks Green; panel diverges → repo `ms_builder.py` bug "
        "(annual m1–m6 on `signal_yyyymm` + quarterly m7–m8 on `date`, or component formulas).",
        "",
    ])
    return lines


def diagnose_indmom(g, p, d) -> list[str]:
    lines = ["## indmom — industry momentum", ""]
    m = merge_three(g, p, d, "indmom")
    lines.append(f"- Three-way overlap: **{len(m):,}** rows")
    lines.append(f"- Spearman: panel–Green={rho(m['panel'], m['green']):.3f}, "
                 f"datashare–Green={rho(m['datashare'], m['green']):.3f}, "
                 f"panel–datashare={rho(m['panel'], m['datashare']):.3f}")

    x = p[["permno", "signal_yyyymm", "indmom", "mom12m", "sic2"]].merge(
        d[["permno", "month", "indmom", "mom12m", "sic2"]].rename(
            columns={"indmom": "ds_indmom", "mom12m": "ds_mom12m", "sic2": "ds_sic2", "month": "signal_yyyymm"}
        ),
        on=["permno", "signal_yyyymm"],
        how="inner",
    ).dropna(subset=["indmom", "ds_indmom", "mom12m"])

    x["sic2_n"] = pd.to_numeric(x["sic2"], errors="coerce")
    x["ds_sic2_n"] = pd.to_numeric(x["ds_sic2"], errors="coerce")
    sic_match = (x["sic2_n"] == x["ds_sic2_n"]).mean() * 100

    # Recompute indmom from mom12m
    def recompute_indmom(df, mom_col, sic_col):
        tmp = df.dropna(subset=[mom_col, sic_col]).copy()
        tmp[sic_col] = pd.to_numeric(tmp[sic_col], errors="coerce")
        return tmp.groupby(["signal_yyyymm", sic_col])[mom_col].transform("mean")

    x["re_panel"] = recompute_indmom(x, "mom12m", "sic2_n")
    x["re_ds"] = recompute_indmom(x, "ds_mom12m", "ds_sic2_n")

    lines.extend([
        "",
        f"- panel mom12m vs datashare mom12m: ρ={rho(x['mom12m'], x['ds_mom12m']):.3f}",
        f"- numeric sic2 match rate: {sic_match:.1f}%",
        f"- recomputed mean(mom12m)|panel sic2 vs panel indmom: ρ={rho(x['re_panel'], x['indmom']):.3f}",
        f"- recomputed mean(mom12m)|panel sic2 vs datashare indmom: ρ={rho(x['re_panel'], x['ds_indmom']):.3f}",
        f"- recomputed mean(ds_mom12m)|ds sic2 vs datashare indmom: ρ={rho(x['re_ds'], x['ds_indmom']):.3f}",
        "",
        "**Interpretation:** 2010–2015 formula is fine; full-window gap (median ρ=0.835) likely "
        "sic2 source/timing or universe entering industry mean in other years.",
        "",
    ])
    return lines


def main() -> None:
    print("Loading Green...", flush=True)
    g = load_green(["permno", "DATE", "ms", "indmom", "chpmia", "chpm", "pchcapx_ia", "pchcapx", "mom12m", "sic2"])
    print("Loading panel...", flush=True)
    p = load_panel(["permno", "signal_yyyymm", "target_yyyymm", "ms", "indmom", "chpmia", "chpm",
                    "pchcapx_ia", "pchcapx", "mom12m", "sic2"])
    print("Loading datashare...", flush=True)
    d = load_datashare(["permno", "DATE", "ms", "indmom", "chpmia", "pchcapx_ia", "mom12m", "sic2"])

    lines = [
        "# Four-character deep diagnosis",
        "",
        f"Window: **{MONTH_MIN}–{MONTH_MAX}**",
        "",
    ]
    lines.extend(diagnose_ms(g, p, d))
    lines.extend(diagnose_indmom(g, p, d))
    lines.extend(diagnose_chpmia(g, p, d))
    lines.extend(diagnose_pchcapx_ia(g, p, d))

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text("\n".join(lines), encoding="utf-8")
    print(f"Wrote {OUT}", flush=True)


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    main()
