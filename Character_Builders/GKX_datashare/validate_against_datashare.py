"""Validate GKX/datashare-style output against Supplementary_assistive_files/datashare.csv."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_BUILT = PROJECT_ROOT / "outputs" / "characteristics" / "datashare_style" / "datashare_chars.csv"
DATASHARE = PROJECT_ROOT / "Supplementary_assistive_files" / "datashare.csv"
COLS = ["bm", "bm_ia", "operprof", "cfp"]
DC_TO_RAW = {
    "bm_dc": "bm",
    "bm_ia_dc": "bm_ia",
    "operprof_dc": "operprof",
    "cfp_dc": "cfp",
}


def month_add(yyyymm: pd.Series, shift: int) -> pd.Series:
    yy = yyyymm // 100
    mm = yyyymm % 100
    mm = mm + shift
    while True:
        over = mm > 12
        under = mm < 1
        if not (over.any() or under.any()):
            break
        yy = yy + over.astype(int) - under.astype(int)
        mm = np.where(over, mm - 12, mm)
        mm = np.where(under, mm + 12, mm)
    return (yy * 100 + mm).astype("Int64")


def load_built(path: Path) -> tuple[pd.DataFrame, str]:
    header = pd.read_csv(path, nrows=0)
    columns = set(header.columns)

    raw_cols = [c for c in COLS if c in columns]
    dc_cols = [c for c in DC_TO_RAW if c in columns]
    if not raw_cols and not dc_cols:
        raise ValueError(f"{path} has none of the expected raw or _dc datashare columns.")

    if "DATE" in columns:
        month_col = "DATE"
        usecols = ["permno", "DATE"] + raw_cols + dc_cols
        source = "DATE"
    elif "target_yyyymm" in columns:
        month_col = "target_yyyymm"
        usecols = ["permno", "target_yyyymm"] + raw_cols + dc_cols
        source = "target_yyyymm"
    elif "yyyymm" in columns:
        month_col = "yyyymm"
        usecols = ["permno", "yyyymm"] + raw_cols + dc_cols
        source = "yyyymm"
    elif "signal_yyyymm" in columns:
        month_col = "signal_yyyymm"
        usecols = ["permno", "signal_yyyymm"] + raw_cols + dc_cols
        source = "signal_yyyymm"
    else:
        raise ValueError(f"{path} needs DATE, target_yyyymm, yyyymm, or signal_yyyymm for alignment.")

    df = pd.read_csv(path, usecols=usecols)
    df["permno"] = pd.to_numeric(df["permno"], errors="coerce").astype("Int64")
    if month_col == "DATE":
        df["month"] = (pd.to_numeric(df["DATE"], errors="coerce") // 100).astype("Int64")
        df = df.drop(columns=["DATE"])
    else:
        df["month"] = pd.to_numeric(df[month_col], errors="coerce").astype("Int64")
        df = df.drop(columns=[month_col])
    if dc_cols:
        df = df.rename(columns={k: v for k, v in DC_TO_RAW.items() if k in df.columns})
    return df, source


def load_datashare(sample_start: int | None, sample_end: int | None) -> pd.DataFrame:
    frames = []
    for chunk in pd.read_csv(DATASHARE, usecols=["permno", "DATE"] + COLS, chunksize=500_000):
        chunk["permno"] = pd.to_numeric(chunk["permno"], errors="coerce").astype("Int64")
        chunk["month"] = (pd.to_numeric(chunk["DATE"], errors="coerce") // 100).astype("Int64")
        if sample_start is not None:
            chunk = chunk[chunk["month"] >= sample_start]
        if sample_end is not None:
            chunk = chunk[chunk["month"] <= sample_end]
        if len(chunk):
            frames.append(chunk.drop(columns=["DATE"]))
    if not frames:
        return pd.DataFrame(columns=["permno", "month"] + COLS)
    return pd.concat(frames, ignore_index=True)


def monthly_spearman(m: pd.DataFrame, a: str, b: str) -> tuple[float, int]:
    vals = []
    for _, g in m.groupby("month", sort=True):
        sub = g[[a, b]].dropna()
        if len(sub) < 50:
            continue
        rho = sub[a].corr(sub[b], method="spearman")
        if pd.notna(rho):
            vals.append(rho)
    return (float(np.median(vals)), len(vals)) if vals else (np.nan, 0)


def compare_once(built: pd.DataFrame, ds: pd.DataFrame, shift: int) -> list[dict]:
    b = built.copy()
    if shift:
        b["month"] = month_add(b["month"], shift)

    results = []
    for col in COLS:
        sp = b[["permno", "month", col]].dropna(subset=[col]).rename(columns={col: "built"})
        sg = ds[["permno", "month", col]].dropna(subset=[col]).rename(columns={col: "datashare"})
        merged = sp.merge(sg, on=["permno", "month"], how="inner").dropna(subset=["built", "datashare"])
        if len(merged) >= 2:
            pooled = float(merged["built"].corr(merged["datashare"], method="spearman"))
            diff = (merged["built"].astype("float64") - merged["datashare"].astype("float64")).abs()
            exact = float((diff <= 1e-4).mean()) * 100
            med, months = monthly_spearman(merged, "built", "datashare")
            mad = float(diff.median())
            p95 = float(diff.quantile(0.95))
        else:
            pooled = exact = med = mad = p95 = np.nan
            months = 0
        results.append(
            {
                "col": col,
                "shift": shift,
                "med_rho": med,
                "pooled_rho": pooled,
                "exact_pct": exact,
                "median_abs_diff": mad,
                "p95_abs_diff": p95,
                "paired": len(merged),
                "months": months,
            }
        )
    return results


def format_report(results: list[dict], built_path: Path, source: str, built_rows: int, ds_rows: int) -> str:
    lines = [
        f"Built: {built_path}",
        f"Built month source: {source}",
        f"built rows={built_rows:,}  datashare rows={ds_rows:,}",
        "",
    ]
    for shift in sorted({r["shift"] for r in results}):
        lines.append(f"=== alignment shift = {shift:+d} month(s) ===")
        lines.append(
            f"{'col':<10}{'med_rho':>10}{'pool_rho':>10}{'exact%':>9}"
            f"{'med_abs':>12}{'p95_abs':>12}{'months':>8}{'paired':>12}"
        )
        for r in [x for x in results if x["shift"] == shift]:
            lines.append(
                f"{r['col']:<10}{r['med_rho']:>10.4f}{r['pooled_rho']:>10.4f}"
                f"{r['exact_pct']:>9.2f}{r['median_abs_diff']:>12.6g}"
                f"{r['p95_abs_diff']:>12.6g}{r['months']:>8,}{r['paired']:>12,}"
            )
        lines.append("")
    return "\n".join(lines)


def main() -> None:
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

    parser = argparse.ArgumentParser(description="Validate datashare-style chars against datashare.csv.")
    parser.add_argument("built", nargs="?", default=str(DEFAULT_BUILT))
    parser.add_argument("--sample-start", type=int, default=None)
    parser.add_argument("--sample-end", type=int, default=None)
    parser.add_argument("--report", default=None)
    args = parser.parse_args()

    built_path = Path(args.built)
    if not built_path.is_absolute():
        built_path = PROJECT_ROOT / built_path

    built, source = load_built(built_path)
    ds = load_datashare(args.sample_start, args.sample_end)

    shifts = [0]
    if source != "DATE":
        shifts = [0, 1, -1]
    results = []
    for shift in shifts:
        results.extend(compare_once(built, ds, shift))

    report = format_report(results, built_path, source, len(built), len(ds))
    print(report)
    if args.report:
        report_path = Path(args.report)
        if not report_path.is_absolute():
            report_path = PROJECT_ROOT / report_path
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(report, encoding="utf-8")


if __name__ == "__main__":
    main()
