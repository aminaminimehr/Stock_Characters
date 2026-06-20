#!/usr/bin/env python3
"""Validate Green timing migration against Green SAS output and datashare."""
from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd
import pyreadstat

PROJECT_ROOT = Path(__file__).resolve().parents[2]
import sys

sys.path.insert(0, str(PROJECT_ROOT))

from Character_Panels.timing import expand_annual_file_green, expand_annual_file_june  # noqa: E402
from output_paths import CHARACTER_INDIVIDUAL_DIR  # noqa: E402

GREEN_SAS = PROJECT_ROOT / "Supplementary_assistive_files/Output_From_Greens_SAS_code.sas7bdat"
DATASHARE = PROJECT_ROOT / "Supplementary_assistive_files/datashare.csv"
DEFAULT_VARS = ["chatoia", "cfp_ia", "bm", "bm_ia", "invest", "age", "orgcap", "absacc"]
WIN = (201801, 202312)


def winsorize(series: pd.Series, lower=0.01, upper=0.99) -> pd.Series:
    lo = series.quantile(lower)
    hi = series.quantile(upper)
    return series.clip(lo, hi)


def load_green(columns: list[str], win=WIN) -> pd.DataFrame:
    _, meta = pyreadstat.read_sas7bdat(str(GREEN_SAS), metadataonly=True)
    usecols = ["permno", "DATE"] + [c for c in columns if c in meta.column_names]
    frames = []
    for off in range(0, meta.number_rows, 400_000):
        chunk, _ = pyreadstat.read_sas7bdat(
            str(GREEN_SAS), usecols=usecols, row_offset=off, row_limit=400_000
        )
        frames.append(chunk)
    g = pd.concat(frames, ignore_index=True)
    g["DATE"] = pd.to_datetime(g["DATE"])
    g["signal_yyyymm"] = g["DATE"].dt.year * 100 + g["DATE"].dt.month
    g["permno"] = pd.to_numeric(g["permno"]).astype("Int64")
    return g[(g["signal_yyyymm"] >= win[0]) & (g["signal_yyyymm"] <= win[1])]


def load_repo_annual(var: str) -> pd.DataFrame:
    path = CHARACTER_INDIVIDUAL_DIR / f"{var}.csv"
    if not path.exists():
        raise FileNotFoundError(path)
    df = pd.read_csv(path, parse_dates=["datadate"])
    df["permno"] = pd.to_numeric(df["permno"]).astype("Int64")
    return df


def compare_series(repo: pd.Series, green: pd.Series) -> dict:
    paired = repo.notna() & green.notna()
    n = int(paired.sum())
    if n == 0:
        return {"paired": 0}
    r = repo[paired]
    g = green[paired]
    out = {
        "paired": n,
        "pearson": float(r.corr(g, method="pearson")),
        "spearman": float(r.corr(g, method="spearman")),
        "winsor_pearson": float(winsorize(r).corr(winsorize(g), method="pearson")),
        "median_abs_diff": float((r - g).abs().median()),
        "exact_rate": float(np.isclose(r, g, rtol=0, atol=1e-6).mean()),
        "near_rate": float((np.isclose(r, g, rtol=0, atol=1e-2)).mean()),
        "repo_coverage": int(repo.notna().sum()),
        "green_coverage": int(green.notna().sum()),
    }
    return out


def validate_var(var: str, green: pd.DataFrame, crsp_index: pd.DataFrame | None) -> dict:
    annual = load_repo_annual(var)
    id_cols = ["permno", "permco", "gvkey", "datadate", "sic", "fyear"]
    panel_green = expand_annual_file_green(annual[id_cols + [var]], [var], crsp_month_index=crsp_index)
    panel_june = expand_annual_file_june(annual[id_cols + [var]], [var])

    g = green[["permno", "signal_yyyymm", var]].rename(columns={var: "green"})
    mg = panel_green.merge(g, on=["permno", "signal_yyyymm"], how="inner")
    mj = panel_june.merge(g, on=["permno", "signal_yyyymm"], how="inner")

    return {
        "variable": var,
        "green_timing": compare_series(mg[var], mg["green"]),
        "june_timing": compare_series(mj[var], mj["green"]),
    }


def main():
    parser = argparse.ArgumentParser(description="Validate Green timing migration.")
    parser.add_argument("--vars", nargs="*", default=DEFAULT_VARS)
    parser.add_argument("--win-start", type=int, default=WIN[0])
    parser.add_argument("--win-end", type=int, default=WIN[1])
    args = parser.parse_args()

    win = (args.win_start, args.win_end)
    green = load_green(args.vars, win=win)

    # CRSP month index from me.csv if present
    crsp_index = None
    me_path = CHARACTER_INDIVIDUAL_DIR / "me.csv"
    if me_path.exists():
        me = pd.read_csv(me_path, usecols=["permno", "signal_yyyymm"])
        crsp_index = me.drop_duplicates()

    rows = []
    for var in args.vars:
        if var not in green.columns:
            print(f"skip {var}: not in Green SAS output")
            continue
        try:
            result = validate_var(var, green, crsp_index)
            rows.append(result)
            gt = result["green_timing"]
            jt = result["june_timing"]
            gs = gt.get("spearman")
            js = jt.get("spearman")
            gs_txt = f"{gs:.4f}" if isinstance(gs, (int, float)) else "n/a"
            js_txt = f"{js:.4f}" if isinstance(js, (int, float)) else "n/a"
            print(
                f"{var}: green_timing Spearman={gs_txt} "
                f"paired={gt.get('paired', 0):,} | june Spearman={js_txt}"
            )
        except FileNotFoundError as exc:
            print(f"skip {var}: {exc}")

    out = PROJECT_ROOT / "docs/gkx/gkx_green_timing_migration_validation.md"
    lines = [
        "# Green timing migration validation",
        "",
        f"Window: {win[0]}–{win[1]}. Green SAS: `{GREEN_SAS.name}`.",
        "",
        "| Variable | Timing | Paired | Spearman | Pearson | Winsor P | Median |diff| | Exact | Near |",
        "|----------|--------|-------:|---------:|--------:|---------:|---------------:|------:|-----:|",
    ]
    for row in rows:
        for label, key in [("Green rolling", "green_timing"), ("June legacy", "june_timing")]:
            s = row[key]
            if s.get("paired", 0) == 0:
                continue
            lines.append(
                f"| {row['variable']} | {label} | {s['paired']:,} | {s['spearman']:.4f} | "
                f"{s['pearson']:.4f} | {s['winsor_pearson']:.4f} | {s['median_abs_diff']:.6g} | "
                f"{100*s['exact_rate']:.1f}% | {100*s['near_rate']:.1f}% |"
            )
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Wrote {out}")


if __name__ == "__main__":
    main()
