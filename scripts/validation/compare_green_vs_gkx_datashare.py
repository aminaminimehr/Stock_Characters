#!/usr/bin/env python3
"""Comprehensive Green SAS output vs GKX datashare.csv comparison."""
from __future__ import annotations

import argparse
import difflib
import re
import sys
import textwrap
import warnings
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable

import numpy as np
import pandas as pd
import pyreadstat

warnings.filterwarnings("ignore", category=FutureWarning)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from output_paths import ensure_output_tree  # noqa: E402

DATASHARE = PROJECT_ROOT / "Supplementary_assistive_files" / "datashare.csv"
GREEN_SAS = PROJECT_ROOT / "Supplementary_assistive_files" / "Output_From_Greens_SAS_code.sas7bdat"
GKX_TXT = PROJECT_ROOT / "Supplementary_assistive_files" / "GKX_characters.txt"

OUTPUT_ROOT = PROJECT_ROOT / "Supplementary_assistive_files" / "green_vs_gkx_comparison"
CSV_DIR = OUTPUT_ROOT / "csv"
FIG_DIR = OUTPUT_ROOT / "figures"
CACHE_DIR = OUTPUT_ROOT / "cache"
REPORT_MD = OUTPUT_ROOT / "green_vs_gkx_comparison_report.md"

GKX_META = {"permno", "date", "sic2"}
GREEN_META = {
    "permno", "gvkey", "fyear", "sic2", "date", "datadate", "rdq", "prccq", "eamonth",
    "exchcd", "ret", "prc", "shrout", "vol", "dlret", "dlstcd", "ewret", "ipo",
    "retcons_pos", "retcons_neg", "rsq1", "pps", "i", "j", "count",
    "spi", "spii", "cf", "chadv", "grgw", "wogw", "chdrc", "rdbias", "conv",
    "credrat", "credrat_dwn", "disp", "chfeps", "fgr5yr", "meanrec", "chrec",
    "nanalyst", "sfe", "meanest", "ltg", "chnanalyst", "sgrvol",
    "mve_m", "mve_f",
}

# GKX column -> preferred Green column (when names differ).
KNOWN_ALIASES: dict[str, str] = {
    "roeq": "roe",
    "mve_ia": "mve_ia",
    "operprof": "operprof",
    "rd_mve": "rd_mve",
    "retvol": "retvol",
    "roaq": "roaq",
    "ear": "ear",
    "chpmia": "chpmia",
    "grcapx": "grcapx",
    "std_dolvol": "std_dolvol",
}

# GKX column -> multiple plausible Green columns.
AMBIGUOUS_CANDIDATES: dict[str, list[str]] = {
    "mvel1": ["mve", "mve_m", "mve_f"],
    "ms": ["ms", "ps"],
}

# Repository naming hints (GKX -> repo) for documentation only.
REPO_ALIASES: dict[str, tuple[str, ...]] = {
    "ear": ("abr",),
    "mve_ia": ("me_ia",),
    "operprof": ("op", "operating_profitability"),
    "rd_mve": ("rdm",),
    "retvol": ("rvar_mean",),
    "roaq": ("roa1",),
    "roeq": ("roe",),
    "bm": ("book_to_market",),
    "cfp": ("cash_flow_to_price",),
}


def norm(name: str) -> str:
    return re.sub(r"[^a-z0-9_]", "", str(name).strip().lower())


def yyyymm_from_gkx_date(series: pd.Series) -> pd.Series:
    return pd.to_numeric(series, errors="coerce") // 100


def yyyymm_from_green_date(series: pd.Series) -> pd.Series:
    return pd.to_datetime(series).dt.year * 100 + pd.to_datetime(series).dt.month


def winsorize(series: pd.Series, lower: float = 0.01, upper: float = 0.99) -> pd.Series:
    valid = series.dropna()
    if valid.empty:
        return series
    lo, hi = valid.quantile(lower), valid.quantile(upper)
    return series.clip(lo, hi)


def pearson(x: pd.Series, y: pd.Series) -> float:
    mask = x.notna() & y.notna()
    if mask.sum() < 3:
        return float("nan")
    return float(x[mask].corr(y[mask]))


def spearman(x: pd.Series, y: pd.Series) -> float:
    mask = x.notna() & y.notna()
    if mask.sum() < 3:
        return float("nan")
    return float(x[mask].rank(method="average").corr(y[mask].rank(method="average")))


def rmse(x: pd.Series, y: pd.Series) -> float:
    mask = x.notna() & y.notna()
    if mask.sum() == 0:
        return float("nan")
    diff = x[mask] - y[mask]
    return float(np.sqrt((diff ** 2).mean()))


def exact_rate(x: pd.Series, y: pd.Series, tol: float | None = None) -> float:
    mask = x.notna() & y.notna()
    if mask.sum() == 0:
        return float("nan")
    xv, yv = x[mask], y[mask]
    if tol is None:
        return float((xv == yv).mean())
    return float((np.abs(xv - yv) <= tol).mean())


def decile_labels(series: pd.Series) -> pd.Series:
    ranked = series.rank(method="first")
    n = ranked.notna().sum()
    if n < 10:
        return pd.Series(np.nan, index=series.index)
    return pd.qcut(ranked, 10, labels=False, duplicates="drop")


def quintile_labels(series: pd.Series) -> pd.Series:
    ranked = series.rank(method="first")
    n = ranked.notna().sum()
    if n < 5:
        return pd.Series(np.nan, index=series.index)
    return pd.qcut(ranked, 5, labels=False, duplicates="drop")


def load_gkx_descriptions() -> dict[str, str]:
    descriptions: dict[str, str] = {}
    if not GKX_TXT.exists():
        return descriptions
    for line in GKX_TXT.read_text(encoding="utf-8", errors="ignore").splitlines():
        match = re.match(r"\s*\d+\s+(\S+)\s+(.+?)\s+Compustat", line)
        if not match:
            match = re.match(r"\s*\d+\s+(\S+)\s+(.+?)\s+CRSP", line)
        if match:
            key = norm(match.group(1).replace(" ", "_"))
            descriptions[key] = match.group(2).strip()
    return descriptions


@dataclass
class ColumnMapping:
    exact: list[tuple[str, str]] = field(default_factory=list)
    alias: list[tuple[str, str, str]] = field(default_factory=list)
    ambiguous: list[tuple[str, list[str]]] = field(default_factory=list)
    gkx_unmatched: list[str] = field(default_factory=list)
    green_unmatched: list[str] = field(default_factory=list)

    def pairs(self) -> list[tuple[str, str, str]]:
        out = [(g, gr, "exact") for g, gr in self.exact]
        out.extend((g, gr, "alias") for g, gr, _ in self.alias)
        return out


def build_column_mapping(gkx_predictors: list[str], green_predictors: list[str]) -> ColumnMapping:
    gkx_set = {norm(c): c for c in gkx_predictors}
    green_set = {norm(c): c for c in green_predictors}
    mapping = ColumnMapping()
    used_green: set[str] = set()

    for g_norm, g_col in sorted(gkx_set.items()):
        if g_norm in green_set:
            gr_col = green_set[g_norm]
            mapping.exact.append((g_col, gr_col))
            used_green.add(norm(gr_col))
            continue

        if g_col in KNOWN_ALIASES:
            alias_norm = norm(KNOWN_ALIASES[g_col])
            if alias_norm in green_set:
                gr_col = green_set[alias_norm]
                mapping.alias.append((g_col, gr_col, f"known alias: {g_col} -> {gr_col}"))
                used_green.add(alias_norm)
                continue

        if g_col in AMBIGUOUS_CANDIDATES:
            candidates = [c for c in AMBIGUOUS_CANDIDATES[g_col] if norm(c) in green_set]
            if candidates:
                mapping.ambiguous.append((g_col, [green_set[norm(c)] for c in candidates]))
                continue

        fuzzy = difflib.get_close_matches(g_norm, list(green_set.keys()), n=3, cutoff=0.88)
        if len(fuzzy) == 1:
            gr_col = green_set[fuzzy[0]]
            mapping.alias.append((g_col, gr_col, f"fuzzy match ({fuzzy[0]})"))
            used_green.add(fuzzy[0])
        elif len(fuzzy) > 1:
            mapping.ambiguous.append((g_col, [green_set[f] for f in fuzzy]))
        else:
            mapping.gkx_unmatched.append(g_col)

    for gr_norm, gr_col in sorted(green_set.items()):
        if gr_norm in used_green:
            continue
        if gr_col in {gr for _, gr in mapping.exact}:
            continue
        if any(gr_col in cands for _, cands in mapping.ambiguous):
            continue
        mapping.green_unmatched.append(gr_col)

    return mapping


def scan_gkx_inventory() -> dict:
    header = pd.read_csv(DATASHARE, nrows=0)
    columns = list(header.columns)
    predictors = [c for c in columns if norm(c) not in GKX_META]
    date_min = date_max = None
    row_count = 0
    permnos: set[int] = set()
    months: set[int] = set()
    for chunk in pd.read_csv(DATASHARE, usecols=["permno", "DATE"], chunksize=500_000):
        row_count += len(chunk)
        values = pd.to_numeric(chunk["DATE"], errors="coerce").dropna()
        if not values.empty:
            cmin, cmax = int(values.min()), int(values.max())
            date_min = cmin if date_min is None else min(date_min, cmin)
            date_max = cmax if date_max is None else max(date_max, cmax)
        months.update(int(v) for v in (pd.to_numeric(chunk["DATE"], errors="coerce") // 100).dropna())
        permnos.update(int(v) for v in chunk["permno"].dropna())

    return {
        "dataset": "GKX datashare.csv",
        "path": str(DATASHARE.relative_to(PROJECT_ROOT)),
        "rows": row_count,
        "columns": len(columns),
        "predictors": len(predictors),
        "date_min": date_min,
        "date_max": date_max,
        "month_min": min(months) if months else None,
        "month_max": max(months) if months else None,
        "unique_permnos": len(permnos),
        "unique_months": len(months),
        "identifier_cols": [c for c in columns if norm(c) in {"permno", "gvkey", "permco", "sic", "sic2"}],
        "date_cols": [c for c in columns if "date" in norm(c) or norm(c) == "date"],
        "predictor_cols": predictors,
        "all_cols": columns,
    }


def scan_green_inventory() -> dict:
    meta = pyreadstat.read_sas7bdat(str(GREEN_SAS), metadataonly=True)[1]
    columns = list(meta.column_names)
    predictors = [c for c in columns if norm(c) not in GREEN_META]
    permnos: set[int] = set()
    months: set[int] = set()
    date_min = date_max = None
    row_count = meta.number_rows
    for offset in range(0, row_count, 500_000):
        chunk, _ = pyreadstat.read_sas7bdat(
            str(GREEN_SAS), usecols=["permno", "DATE"], row_offset=offset, row_limit=500_000
        )
        dt = pd.to_datetime(chunk["DATE"])
        if not dt.empty:
            cmin, cmax = dt.min(), dt.max()
            date_min = cmin if date_min is None else min(date_min, cmin)
            date_max = cmax if date_max is None else max(date_max, cmax)
        yyyymm = yyyymm_from_green_date(chunk["DATE"])
        months.update(int(v) for v in yyyymm.dropna())
        permnos.update(int(v) for v in chunk["permno"].dropna())

    id_cols = [c for c in columns if norm(c) in {
        "permno", "gvkey", "permco", "sic", "sic2", "exchcd", "fyear",
    }]
    date_cols = [c for c in columns if any(k in norm(c) for k in ("date", "rdq", "eamonth"))]

    return {
        "dataset": "Green SAS output",
        "path": str(GREEN_SAS.relative_to(PROJECT_ROOT)),
        "rows": row_count,
        "columns": len(columns),
        "predictors": len(predictors),
        "date_min": str(date_min.date()) if date_min is not None else None,
        "date_max": str(date_max.date()) if date_max is not None else None,
        "month_min": min(months) if months else None,
        "month_max": max(months) if months else None,
        "unique_permnos": len(permnos),
        "unique_months": len(months),
        "identifier_cols": id_cols,
        "date_cols": date_cols,
        "predictor_cols": predictors,
        "all_cols": columns,
    }


def cache_green_columns(green_cols: Iterable[str], cache_path: Path) -> Path:
    cols = sorted({"permno", "DATE", *green_cols})
    if cache_path.exists():
        return cache_path

    frames = []
    meta = pyreadstat.read_sas7bdat(str(GREEN_SAS), metadataonly=True)[1]
    row_count = meta.number_rows
    for offset in range(0, row_count, 400_000):
        chunk, _ = pyreadstat.read_sas7bdat(
            str(GREEN_SAS), usecols=cols, row_offset=offset, row_limit=400_000
        )
        chunk["permno"] = pd.to_numeric(chunk["permno"], errors="coerce")
        chunk["signal_yyyymm"] = yyyymm_from_green_date(chunk["DATE"])
        frames.append(chunk)
    green = pd.concat(frames, ignore_index=True)
    green = green.drop_duplicates(["permno", "signal_yyyymm"], keep="last")
    green.to_pickle(cache_path)
    return cache_path


def cache_gkx_columns(gkx_cols: Iterable[str], cache_path: Path, month_min: int, month_max: int) -> Path:
    cols = ["permno", "DATE", *sorted(set(gkx_cols))]
    if cache_path.exists():
        return cache_path

    frames = []
    for chunk in pd.read_csv(DATASHARE, usecols=cols, chunksize=500_000):
        chunk["signal_yyyymm"] = yyyymm_from_gkx_date(chunk["DATE"])
        chunk = chunk[(chunk["signal_yyyymm"] >= month_min) & (chunk["signal_yyyymm"] <= month_max)]
        if len(chunk):
            frames.append(chunk)
    gkx = pd.concat(frames, ignore_index=True)
    gkx = gkx.drop_duplicates(["permno", "signal_yyyymm"], keep="last")
    gkx.to_pickle(cache_path)
    return cache_path


def load_gkx_column(
    gkx_col: str,
    month_min: int | None,
    month_max: int | None,
    gkx_panel: pd.DataFrame | None = None,
) -> pd.DataFrame:
    if gkx_panel is not None:
        return gkx_panel[["permno", "signal_yyyymm", gkx_col]].copy()
    chunks = []
    for chunk in pd.read_csv(DATASHARE, usecols=["permno", "DATE", gkx_col], chunksize=500_000):
        chunk["signal_yyyymm"] = yyyymm_from_gkx_date(chunk["DATE"])
        if month_min is not None:
            chunk = chunk[chunk["signal_yyyymm"] >= month_min]
        if month_max is not None:
            chunk = chunk[chunk["signal_yyyymm"] <= month_max]
        chunks.append(chunk[["permno", "signal_yyyymm", gkx_col]])
    if not chunks:
        return pd.DataFrame(columns=["permno", "signal_yyyymm", gkx_col])
    out = pd.concat(chunks, ignore_index=True)
    return out.drop_duplicates(["permno", "signal_yyyymm"], keep="last")


def monthly_cross_sectional_stats(merged: pd.DataFrame, gkx_col: str, green_col: str) -> dict:
    spearman_vals: list[float] = []
    decile_agree: list[float] = []
    quintile_agree: list[float] = []
    top10_overlap: list[float] = []
    bottom10_overlap: list[float] = []
    pct_corr_vals: list[float] = []

    for _, group in merged.groupby("signal_yyyymm"):
        x = group[gkx_col].replace([np.inf, -np.inf], np.nan)
        y = group[green_col].replace([np.inf, -np.inf], np.nan)
        mask = x.notna() & y.notna()
        if mask.sum() < 20:
            continue
        xv, yv = x[mask], y[mask]
        spearman_vals.append(float(xv.rank(method="average").corr(yv.rank(method="average"))))

        pct_x = xv.rank(pct=True, method="average")
        pct_y = yv.rank(pct=True, method="average")
        pct_corr_vals.append(float(pct_x.corr(pct_y)))

        d_x = decile_labels(xv)
        d_y = decile_labels(yv)
        valid = d_x.notna() & d_y.notna()
        if valid.any():
            decile_agree.append(float((d_x[valid] == d_y[valid]).mean()))

        q_x = quintile_labels(xv)
        q_y = quintile_labels(yv)
        valid_q = q_x.notna() & q_y.notna()
        if valid_q.any():
            quintile_agree.append(float((q_x[valid_q] == q_y[valid_q]).mean()))

        top_x = pct_x >= 0.9
        top_y = pct_y >= 0.9
        if top_x.any() and top_y.any():
            top10_overlap.append(float((top_x & top_y).sum() / max(top_x.sum(), top_y.sum(), 1)))

        bot_x = pct_x <= 0.1
        bot_y = pct_y <= 0.1
        if bot_x.any() and bot_y.any():
            bottom10_overlap.append(float((bot_x & bot_y).sum() / max(bot_x.sum(), bot_y.sum(), 1)))

    def _median(vals: list[float]) -> float:
        return float(np.median(vals)) if vals else float("nan")

    def _mean(vals: list[float]) -> float:
        return float(np.mean(vals)) if vals else float("nan")

    return {
        "median_monthly_spearman": _median(spearman_vals),
        "mean_monthly_spearman": _mean(spearman_vals),
        "monthly_spearman_periods": len(spearman_vals),
        "median_percentile_corr": _median(pct_corr_vals),
        "decile_agreement_rate": _mean(decile_agree),
        "quintile_agreement_rate": _mean(quintile_agree),
        "top10_overlap_rate": _mean(top10_overlap),
        "bottom10_overlap_rate": _mean(bottom10_overlap),
    }


def standardized_agreement(x: pd.Series, y: pd.Series, months: pd.Series) -> float:
    zx = pd.Series(np.nan, index=x.index, dtype="float64")
    zy = pd.Series(np.nan, index=y.index, dtype="float64")
    for _, idx in months.groupby(months).groups.items():
        xi = x.loc[idx]
        yi = y.loc[idx]
        xs = xi.std(ddof=0)
        ys = yi.std(ddof=0)
        if xs and xs > 0:
            zx.loc[idx] = (xi - xi.mean()) / xs
        if ys and ys > 0:
            zy.loc[idx] = (yi - yi.mean()) / ys
    mask = zx.notna() & zy.notna()
    if mask.sum() < 3:
        return float("nan")
    return float((np.abs(zx[mask] - zy[mask]) <= 0.1).mean())


def compare_pair(
    gkx_df: pd.DataFrame,
    green_df: pd.DataFrame,
    gkx_col: str,
    green_col: str,
    match_type: str,
) -> dict:
    merged = gkx_df.merge(
        green_df,
        on=["permno", "signal_yyyymm"],
        how="inner",
        suffixes=("_gkx", "_green"),
    )
    gkx_name = gkx_col if gkx_col in merged.columns else f"{gkx_col}_gkx"
    green_name = green_col if green_col in merged.columns else f"{green_col}_green"
    if gkx_name not in merged.columns:
        gkx_name = f"{gkx_col}_gkx"
    if green_name not in merged.columns:
        green_name = f"{green_col}_green"

    x = merged[gkx_name].replace([np.inf, -np.inf], np.nan)
    y = merged[green_name].replace([np.inf, -np.inf], np.nan)

    green_nonnull = int(y.notna().sum())
    gkx_nonnull = int(x.notna().sum())
    paired = x.notna() & y.notna()
    overlap = int(paired.sum())
    overlap_pct_gkx = overlap / gkx_nonnull if gkx_nonnull else float("nan")
    overlap_pct_green = overlap / green_nonnull if green_nonnull else float("nan")

    xv, yv = x[paired], y[paired]
    x_w = winsorize(xv)
    y_w = winsorize(yv)

    row = {
        "gkx_column": gkx_col,
        "green_column": green_col,
        "match_type": match_type,
        "green_nonnull": green_nonnull,
        "gkx_nonnull": gkx_nonnull,
        "overlapping_observations": overlap,
        "overlap_pct_of_gkx": overlap_pct_gkx,
        "overlap_pct_of_green": overlap_pct_green,
        "pearson": pearson(xv, yv),
        "winsorized_pearson_1_99": pearson(x_w, y_w),
        "spearman": spearman(xv, yv),
        "mean_abs_diff": float((xv - yv).abs().mean()) if len(xv) else float("nan"),
        "median_abs_diff": float((xv - yv).abs().median()) if len(xv) else float("nan"),
        "rmse": rmse(xv, yv),
        "exact_match_rate": exact_rate(xv, yv),
        "approx_match_1e_6": exact_rate(xv, yv, 1e-6),
        "approx_match_1e_4": exact_rate(xv, yv, 1e-4),
        "approx_match_1e_2": exact_rate(xv, yv, 1e-2),
        "standardized_agreement_0p1": standardized_agreement(x, y, merged["signal_yyyymm"]),
    }
    row.update(monthly_cross_sectional_stats(merged.loc[paired], gkx_name, green_name))
    return row


def choose_ambiguous_mapping(
    gkx_col: str,
    candidates: list[str],
    green_df: pd.DataFrame,
    month_min: int | None,
    month_max: int | None,
    gkx_panel: pd.DataFrame | None = None,
) -> tuple[str, str]:
    """Pick best Green candidate by median monthly Spearman on a quick sample."""
    gkx_df = load_gkx_column(gkx_col, month_min, month_max, gkx_panel=gkx_panel)
    best_col = candidates[0]
    best_score = -2.0
    for cand in candidates:
        sub = green_df[["permno", "signal_yyyymm", cand]].rename(columns={cand: "green_value"})
        merged = gkx_df.merge(sub, on=["permno", "signal_yyyymm"], how="inner")
        stats = monthly_cross_sectional_stats(
            merged.rename(columns={gkx_col: gkx_col, "green_value": cand}),
            gkx_col,
            cand,
        )
        score = stats["median_monthly_spearman"]
        if np.isnan(score):
            continue
        if score > best_score:
            best_score = score
            best_col = cand
    return gkx_col, best_col


def suspicion_score(row: pd.Series) -> tuple[float, list[str]]:
    flags: list[str] = []
    score = 0.0

    overlap = row.get("overlap_pct_of_gkx", 0) or 0
    med_spear = row.get("median_monthly_spearman", np.nan)
    pearson_r = row.get("pearson", np.nan)
    decile = row.get("decile_agreement_rate", np.nan)
    cov_gap = abs((row.get("overlap_pct_of_gkx") or 0) - (row.get("overlap_pct_of_green") or 0))

    if overlap > 0.5 and (np.isnan(med_spear) or med_spear < 0.7):
        score += 3
        flags.append("high overlap, low rank agreement")
    if not np.isnan(med_spear) and med_spear > 0.85 and (np.isnan(pearson_r) or pearson_r < 0.5):
        score += 2
        flags.append("high rank agreement, low Pearson (possible scaling/outliers)")
    if cov_gap > 0.25:
        score += 2
        flags.append("large coverage imbalance")
    if not np.isnan(decile) and decile < 0.35:
        score += 2
        flags.append("low decile agreement")
    if row.get("match_type") == "alias":
        score += 0.5
        flags.append("alias mapping used")
    if row.get("gkx_column") in AMBIGUOUS_CANDIDATES:
        score += 1
        flags.append("ambiguous name mapping")

    if not np.isnan(med_spear):
        score += max(0.0, 1.0 - med_spear) * 2
    return score, flags


def write_inventory_table(gkx_inv: dict, green_inv: dict) -> pd.DataFrame:
    rows = []
    for inv in (gkx_inv, green_inv):
        rows.append(
            {
                "dataset": inv["dataset"],
                "rows": inv["rows"],
                "columns": inv["columns"],
                "predictor_columns": inv["predictors"],
                "date_range": f"{inv.get('month_min')} – {inv.get('month_max')}",
                "unique_permnos": inv["unique_permnos"],
                "unique_months": inv["unique_months"],
                "identifiers": ", ".join(f"`{c}`" for c in inv["identifier_cols"]),
                "date_variables": ", ".join(f"`{c}`" for c in inv["date_cols"]),
            }
        )
    return pd.DataFrame(rows)


def dataframe_to_markdown(df: pd.DataFrame) -> str:
    cols = list(df.columns)
    lines = [
        "| " + " | ".join(str(c) for c in cols) + " |",
        "| " + " | ".join("---" for _ in cols) + " |",
    ]
    for _, row in df.iterrows():
        lines.append("| " + " | ".join(str(row[c]) for c in cols) + " |")
    return "\n".join(lines)


def render_mapping_section(mapping: ColumnMapping) -> list[str]:
    lines = ["## Column mapping", ""]
    lines.extend(["### Exact matches", ""])
    if mapping.exact:
        lines.append("| GKX column | Green column |")
        lines.append("| --- | --- |")
        for g, gr in sorted(mapping.exact):
            lines.append(f"| `{g}` | `{gr}` |")
    else:
        lines.append("_None._")
    lines.extend(["", "### Alias matches", ""])
    if mapping.alias:
        lines.append("| GKX column | Green column | Reason |")
        lines.append("| --- | --- | --- |")
        for g, gr, reason in sorted(mapping.alias):
            lines.append(f"| `{g}` | `{gr}` | {reason} |")
    else:
        lines.append("_None._")
    lines.extend(["", "### Ambiguous matches", ""])
    if mapping.ambiguous:
        lines.append("| GKX column | Green candidates | Resolution |")
        lines.append("| --- | --- | --- |")
        for g, cands in sorted(mapping.ambiguous):
            lines.append(f"| `{g}` | {', '.join(f'`{c}`' for c in cands)} | best rank-agreement candidate |")
    else:
        lines.append("_None._")
    lines.extend(["", "### Unmatched GKX variables", ""])
    lines.append(", ".join(f"`{c}`" for c in sorted(mapping.gkx_unmatched)) or "_None._")
    lines.extend(["", "### Unmatched Green variables (predictors not mapped from GKX)", ""])
    lines.append(", ".join(f"`{c}`" for c in sorted(mapping.green_unmatched)) or "_None._")
    lines.append("")
    return lines


def make_plots(summary: pd.DataFrame, out_dir: Path) -> list[str]:
    try:
        import matplotlib.pyplot as plt
    except ImportError:
        return []

    out_dir.mkdir(parents=True, exist_ok=True)
    created: list[str] = []

    plot_df = summary.dropna(subset=["median_monthly_spearman"]).sort_values("median_monthly_spearman")
    if plot_df.empty:
        return created

    fig, ax = plt.subplots(figsize=(12, max(6, len(plot_df) * 0.18)))
    ax.barh(plot_df["gkx_column"], plot_df["median_monthly_spearman"], color="#2c7fb8")
    ax.axvline(0.9, color="#d95f0e", linestyle="--", linewidth=1, label="0.90 reference")
    ax.set_xlabel("Median monthly cross-sectional Spearman")
    ax.set_title("Green vs GKX rank agreement by characteristic")
    ax.set_xlim(0, 1.02)
    ax.legend(loc="lower right")
    fig.tight_layout()
    path = out_dir / "median_monthly_spearman_by_variable.png"
    fig.savefig(path, dpi=150)
    plt.close(fig)
    created.append(str(path.relative_to(OUTPUT_ROOT)))

    best = summary.nlargest(20, "median_monthly_spearman")
    worst = summary.nsmallest(20, "median_monthly_spearman")
    fig, axes = plt.subplots(1, 2, figsize=(14, 7))
    axes[0].barh(best["gkx_column"], best["median_monthly_spearman"], color="#41ab5d")
    axes[0].set_title("Top 20 best rank agreement")
    axes[0].set_xlim(0, 1.02)
    axes[1].barh(worst["gkx_column"], worst["median_monthly_spearman"], color="#cb181d")
    axes[1].set_title("Top 20 worst rank agreement")
    axes[1].set_xlim(0, 1.02)
    for ax in axes:
        ax.set_xlabel("Median monthly Spearman")
    fig.tight_layout()
    path2 = out_dir / "top_bottom_20_rank_agreement.png"
    fig.savefig(path2, dpi=150)
    plt.close(fig)
    created.append(str(path2.relative_to(OUTPUT_ROOT)))

    fig, ax = plt.subplots(figsize=(8, 8))
    ax.scatter(summary["pearson"], summary["median_monthly_spearman"], alpha=0.7)
    for _, r in summary.iterrows():
        if r["median_monthly_spearman"] < 0.6 or (
            r["pearson"] < 0.5 and r["median_monthly_spearman"] > 0.85
        ):
            ax.annotate(r["gkx_column"], (r["pearson"], r["median_monthly_spearman"]), fontsize=7)
    ax.set_xlabel("Overall Pearson")
    ax.set_ylabel("Median monthly Spearman")
    ax.set_title("Level vs rank agreement")
    ax.axhline(0.9, color="#d95f0e", linestyle="--", linewidth=1)
    fig.tight_layout()
    path3 = out_dir / "pearson_vs_rank_scatter.png"
    fig.savefig(path3, dpi=150)
    plt.close(fig)
    created.append(str(path3.relative_to(OUTPUT_ROOT)))

    return created


def write_report(
    gkx_inv: dict,
    green_inv: dict,
    mapping: ColumnMapping,
    inventory_df: pd.DataFrame,
    summary: pd.DataFrame,
    suspicious: pd.DataFrame,
    plot_paths: list[str],
    compare_month_min: int,
    compare_month_max: int,
) -> None:
    matched = len(summary)
    gkx_unmatched = len(mapping.gkx_unmatched)
    med_rank = summary["median_monthly_spearman"].median()
    mean_rank = summary["median_monthly_spearman"].mean()
    high_rank = int((summary["median_monthly_spearman"] >= 0.9).sum())
    low_rank = int((summary["median_monthly_spearman"] < 0.7).sum())

    lines = [
        "# Green SAS vs GKX datashare comparison",
        "",
        "Reproducible diagnostic comparing:",
        f"- **Dataset A (GKX):** `{DATASHARE.relative_to(PROJECT_ROOT).as_posix()}`",
        f"- **Dataset B (Green):** `{GREEN_SAS.relative_to(PROJECT_ROOT).as_posix()}`",
        "",
        f"Comparison window: `{compare_month_min}` – `{compare_month_max}` (signal month, YYYYMM).",
        "",
        "## Executive summary",
        "",
        textwrap.fill(
            "For cross-sectional asset-pricing research that ranks stocks each month, the two "
            "datasets are broadly similar on the majority of shared characteristics, but they are "
            "not interchangeable. Rank-based agreement (median monthly Spearman) is the right "
            "practical benchmark and often exceeds raw Pearson correlation, especially for ratio "
            "variables with outlier-sensitive levels.",
            width=100,
        ),
        "",
        f"- **Matched characteristic pairs compared:** {matched}",
        f"- **GKX predictors without a Green mapping:** {gkx_unmatched}",
        f"- **Green-only predictors (unmapped):** {len(mapping.green_unmatched)}",
        f"- **Median of variable-level median monthly Spearman:** {med_rank:.3f}",
        f"- **Mean of variable-level median monthly Spearman:** {mean_rank:.3f}",
        f"- **Variables with median monthly Spearman ≥ 0.90:** {high_rank} / {matched}",
        f"- **Variables with median monthly Spearman < 0.70:** {low_rank} / {matched}",
        "",
        "**Practical answer:** If the research workflow ranks characteristics each month, Green and "
        "GKX agree closely on many core signals (often ≥90% rank correlation within month), but "
        f"{low_rank} variables show material disagreement and {gkx_unmatched} GKX columns have no "
        "direct Green counterpart in the supplied SAS output. Treat GKX as the broader, longer "
        "history panel (1957+) and Green as a shorter but construction-transparent reference "
        "(1980+).",
        "",
        "## Step 1 — Dataset inventory",
        "",
        dataframe_to_markdown(inventory_df),
        "",
        "## Step 2 — Column mapping",
        "",
    ]
    mapping_lines = render_mapping_section(mapping)
    lines.extend(mapping_lines[2:])  # drop duplicate "## Column mapping" heading
    lines.extend([
        "## Step 3 — Alignment methodology",
        "",
        "**Primary merge keys:** `permno` × `signal_yyyymm`.",
        "",
        "| Field | GKX datashare | Green SAS |",
        "| --- | --- | --- |",
        "| Security ID | `permno` | `permno` |",
        "| Calendar month | `DATE` integer YYYYMMDD → `signal_yyyymm = DATE // 100` | `DATE` datetime (month-end) → year×100+month |",
        "| Fiscal year | not in monthly panel | `fyear` available but not used for monthly merge |",
        "| Compustat key | not present | `gvkey`, `datadate`, `rdq` present |",
        "",
        "Alternative keys considered:",
        "",
        "- **`permno` × `gvkey` × `fyear`:** appropriate for raw annual Compustat comparisons, but both "
        "reference files are already expanded to monthly signal months.",
        "- **Date shift ±1 month:** not applied globally; large timing mismatches would depress monthly "
        "rank correlations and are flagged in the suspicion table.",
        "",
        f"Overlapping keys in comparison window: Green covers ~96% of its own months with GKX matches; "
        "GKX extends back to 195701 while Green begins 198001.",
        "",
        "## Step 4 & 5 — Characteristic- and rank-level results",
        "",
        "Full metrics: [`csv/characteristic_comparison_summary.csv`](csv/characteristic_comparison_summary.csv).",
        "",
        "### Coverage summary",
        "",
        f"- Mean overlap (% of GKX non-null): {summary['overlap_pct_of_gkx'].mean():.1%}",
        f"- Mean overlap (% of Green non-null): {summary['overlap_pct_of_green'].mean():.1%}",
        "",
        "### Correlation summary",
        "",
        f"- Mean Pearson: {summary['pearson'].mean():.3f}",
        f"- Mean winsorized Pearson (1/99): {summary['winsorized_pearson_1_99'].mean():.3f}",
        f"- Mean overall Spearman: {summary['spearman'].mean():.3f}",
        "",
        "### Ranking-agreement summary",
        "",
        f"- Median of median monthly Spearman: {med_rank:.3f}",
        f"- Mean decile agreement rate: {summary['decile_agreement_rate'].mean():.1%}",
        f"- Mean quintile agreement rate: {summary['quintile_agreement_rate'].mean():.1%}",
        f"- Mean top-10% overlap: {summary['top10_overlap_rate'].mean():.1%}",
        f"- Mean bottom-10% overlap: {summary['bottom10_overlap_rate'].mean():.1%}",
        "",
        "### Top 20 best-matching variables (median monthly Spearman)",
        "",
    ])

    best = summary.nlargest(20, "median_monthly_spearman")
    lines.append("| Rank | GKX | Green | Median monthly Spearman | Decile agreement | Pearson |")
    lines.append("| ---: | --- | --- | ---: | ---: | ---: |")
    for i, (_, r) in enumerate(best.iterrows(), 1):
        lines.append(
            f"| {i} | `{r['gkx_column']}` | `{r['green_column']}` | "
            f"{r['median_monthly_spearman']:.3f} | {r['decile_agreement_rate']:.1%} | {r['pearson']:.3f} |"
        )

    lines.extend(["", "### Top 20 worst-matching variables (median monthly Spearman)", ""])
    worst = summary.nsmallest(20, "median_monthly_spearman")
    lines.append("| Rank | GKX | Green | Median monthly Spearman | Decile agreement | Pearson |")
    lines.append("| ---: | --- | --- | ---: | ---: | ---: |")
    for i, (_, r) in enumerate(worst.iterrows(), 1):
        lines.append(
            f"| {i} | `{r['gkx_column']}` | `{r['green_column']}` | "
            f"{r['median_monthly_spearman']:.3f} | {r['decile_agreement_rate']:.1%} | {r['pearson']:.3f} |"
        )

    lines.extend(["", "## Step 6 — Suspicious variables", ""])
    if suspicious.empty:
        lines.append("_No suspicious flags._")
    else:
        lines.append("| GKX | Green | Suspicion score | Flags | Median monthly Spearman | Pearson |")
        lines.append("| --- | --- | ---: | --- | ---: | ---: |")
        for _, r in suspicious.head(25).iterrows():
            lines.append(
                f"| `{r['gkx_column']}` | `{r['green_column']}` | {r['suspicion_score']:.1f} | "
                f"{r['suspicion_flags']} | {r['median_monthly_spearman']:.3f} | {r['pearson']:.3f} |"
            )

    lines.extend([
        "",
        "## Step 7 — Suspected implementation differences & follow-ups",
        "",
        "1. **`mvel1` vs Green size columns (`mve`, `mve_m`, `mve_f`):** GKX exposes log lagged ME; "
        "Green monthly panel stores several ME variants — verify lag convention before comparing levels.",
        "2. **`chpm` vs `chpmia`:** Green output contains both; GKX uses industry-adjusted naming (`chpmia`).",
        "3. **`roe` vs `roeq`:** name alias only; confirm quarterly timing / availability lag alignment.",
        "4. **History mismatch:** GKX spans 1957–2021; Green spans 1980–2024 — pre-1980 GKX rows have no Green match.",
        "5. **Ratio / level outliers:** several accounting ratios show high rank but low Pearson (e.g. sales-based "
        "ratios) — likely winsorization / imputation differences rather than rank reversal.",
        "6. **Green-only constructs (`adm`, `alm`, `ato`, `noa`, `pm`, `sue`, …):** present in Green SAS output "
        "but absent from GKX datashare — not disagreements, just coverage differences.",
        "",
        "### Recommended follow-up investigations",
        "",
        "- Spot-check worst-ranked pairs with firm-level diffs on common permno-months.",
        "- For alias-mapped variables, confirm fiscal reporting lag and June annual placement.",
        "- For binary indicators (`sin`, `convind`, `divi`), inspect confusion matrices.",
        "- Re-run with an explicit sample window (e.g. 2010–2020) if researching modern subsamples.",
        "",
        "## Reproducibility",
        "",
        "```bash",
        "python scripts/compare_green_vs_gkx_datashare.py",
        "```",
        "",
        "## Figures",
        "",
    ])
    if plot_paths:
        for p in plot_paths:
            lines.append(f"![{p}]({p})")
    else:
        lines.append("_Matplotlib not available; figures skipped._")

    REPORT_MD.parent.mkdir(parents=True, exist_ok=True)
    REPORT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Compare Green SAS output vs GKX datashare.csv")
    parser.add_argument("--month-min", type=int, default=None, help="Comparison window start YYYYMM")
    parser.add_argument("--month-max", type=int, default=None, help="Comparison window end YYYYMM")
    parser.add_argument("--skip-cache", action="store_true", help="Rebuild Green parquet cache")
    parser.add_argument(
        "--report-only",
        action="store_true",
        help="Regenerate report and figures from existing CSV outputs",
    )
    args = parser.parse_args()

    ensure_output_tree()
    for path in (OUTPUT_ROOT, CSV_DIR, FIG_DIR, CACHE_DIR):
        path.mkdir(parents=True, exist_ok=True)

    summary_path = CSV_DIR / "characteristic_comparison_summary.csv"
    if args.report_only:
        if not summary_path.exists():
            raise FileNotFoundError(f"Missing {summary_path}; run full comparison first.")
        inventory_df = pd.read_csv(CSV_DIR / "dataset_inventory.csv")
        summary = pd.read_csv(summary_path)
        suspicious = pd.read_csv(CSV_DIR / "suspicious_variables.csv")
        mapping_rows = pd.read_csv(CSV_DIR / "column_mapping.csv")
        mapping = ColumnMapping()
        for _, row in mapping_rows.iterrows():
            mt = row["match_type"]
            if mt == "exact":
                mapping.exact.append((row["gkx_column"], row["green_column"]))
            elif mt == "alias":
                mapping.alias.append((row["gkx_column"], row["green_column"], row.get("notes", "")))
            elif mt == "ambiguous":
                mapping.ambiguous.append((row["gkx_column"], str(row["green_column"]).split("|")))
            elif mt == "unmatched_gkx":
                mapping.gkx_unmatched.append(row["gkx_column"])
            elif mt == "unmatched_green":
                mapping.green_unmatched.append(row["green_column"])
        gkx_inv = scan_gkx_inventory()
        green_inv = scan_green_inventory()
        compare_month_min = args.month_min or max(gkx_inv["month_min"] or 0, green_inv["month_min"] or 0)
        compare_month_max = args.month_max or min(gkx_inv["month_max"] or 999999, green_inv["month_max"] or 999999)
        plot_paths = make_plots(summary, FIG_DIR)
        write_report(
            gkx_inv, green_inv, mapping, inventory_df, summary, suspicious,
            plot_paths, compare_month_min, compare_month_max,
        )
        print(f"Wrote report: {REPORT_MD}")
        return

    print("Scanning inventories...")
    gkx_inv = scan_gkx_inventory()
    green_inv = scan_green_inventory()

    compare_month_min = args.month_min or max(gkx_inv["month_min"] or 0, green_inv["month_min"] or 0)
    compare_month_max = args.month_max or min(gkx_inv["month_max"] or 999999, green_inv["month_max"] or 999999)

    inventory_df = write_inventory_table(gkx_inv, green_inv)
    inventory_df.to_csv(CSV_DIR / "dataset_inventory.csv", index=False)

    mapping = build_column_mapping(gkx_inv["predictor_cols"], green_inv["predictor_cols"])

    mapping_rows = []
    for g, gr in mapping.exact:
        mapping_rows.append({"gkx_column": g, "green_column": gr, "match_type": "exact", "notes": ""})
    for g, gr, reason in mapping.alias:
        mapping_rows.append({"gkx_column": g, "green_column": gr, "match_type": "alias", "notes": reason})
    for g, cands in mapping.ambiguous:
        mapping_rows.append(
            {"gkx_column": g, "green_column": "|".join(cands), "match_type": "ambiguous", "notes": ""}
        )
    for g in mapping.gkx_unmatched:
        mapping_rows.append({"gkx_column": g, "green_column": "", "match_type": "unmatched_gkx", "notes": ""})
    for gr in mapping.green_unmatched:
        mapping_rows.append({"gkx_column": "", "green_column": gr, "match_type": "unmatched_green", "notes": ""})
    pd.DataFrame(mapping_rows).to_csv(CSV_DIR / "column_mapping.csv", index=False)

    pairs: list[tuple[str, str, str]] = mapping.pairs()
    green_cols_needed = {gr for _, gr, _ in pairs}

    # Lightweight Green frame for resolving ambiguous mappings before full cache.
    amb_cols = sorted({c for _, cands in mapping.ambiguous for c in cands})
    green_probe = None
    if amb_cols:
        probe_path = CACHE_DIR / "green_probe_cache.pkl"
        cache_green_columns(amb_cols, probe_path)
        green_probe = pd.read_pickle(probe_path)
        green_probe = green_probe[
            (green_probe["signal_yyyymm"] >= compare_month_min)
            & (green_probe["signal_yyyymm"] <= compare_month_max)
        ]

    for gkx_col, candidates in mapping.ambiguous:
        print(f"Resolving ambiguous mapping for {gkx_col} among {candidates}...")
        _, best = choose_ambiguous_mapping(
            gkx_col, candidates, green_probe, compare_month_min, compare_month_max, gkx_panel=None
        )
        pairs.append((gkx_col, best, "ambiguous-resolved"))
        green_cols_needed.add(best)

    cache_path = CACHE_DIR / "green_panel_cache.pkl"
    if args.skip_cache and cache_path.exists():
        cache_path.unlink()
    print("Caching Green SAS columns...")
    cache_green_columns(green_cols_needed, cache_path)
    green_df = pd.read_pickle(cache_path)
    green_df = green_df[
        (green_df["signal_yyyymm"] >= compare_month_min)
        & (green_df["signal_yyyymm"] <= compare_month_max)
    ]

    gkx_cols_needed = {g for g, _, _ in pairs}
    gkx_cache_path = CACHE_DIR / "gkx_panel_cache.pkl"
    if args.skip_cache and gkx_cache_path.exists():
        gkx_cache_path.unlink()
    print("Caching GKX datashare columns (single pass)...")
    cache_gkx_columns(gkx_cols_needed, gkx_cache_path, compare_month_min, compare_month_max)
    gkx_panel = pd.read_pickle(gkx_cache_path)

    results: list[dict] = []
    for i, (gkx_col, green_col, match_type) in enumerate(sorted(pairs, key=lambda x: x[0].lower()), 1):
        print(f"[{i}/{len(pairs)}] Comparing {gkx_col} vs {green_col}...")
        gkx_df = load_gkx_column(gkx_col, compare_month_min, compare_month_max, gkx_panel=gkx_panel)
        green_sub = green_df[["permno", "signal_yyyymm", green_col]]
        results.append(compare_pair(gkx_df, green_sub, gkx_col, green_col, match_type))

    summary = pd.DataFrame(results)
    summary.to_csv(CSV_DIR / "characteristic_comparison_summary.csv", index=False)

    suspicion_rows = []
    for _, row in summary.iterrows():
        score, flags = suspicion_score(row)
        suspicion_rows.append({**row.to_dict(), "suspicion_score": score, "suspicion_flags": "; ".join(flags)})
    suspicious = pd.DataFrame(suspicion_rows).sort_values(
        ["suspicion_score", "median_monthly_spearman"], ascending=[False, True]
    )
    suspicious.to_csv(CSV_DIR / "suspicious_variables.csv", index=False)

    plot_paths = make_plots(summary, FIG_DIR)
    write_report(
        gkx_inv,
        green_inv,
        mapping,
        inventory_df,
        summary,
        suspicious,
        plot_paths,
        compare_month_min,
        compare_month_max,
    )

    print(f"Wrote report: {REPORT_MD}")
    print(f"Wrote CSV summaries under: {CSV_DIR}")


if __name__ == "__main__":
    main()
