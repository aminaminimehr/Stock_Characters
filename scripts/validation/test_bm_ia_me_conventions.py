#!/usr/bin/env python3
"""Test bm_ia market-equity source, timing lag, and demeaning universe vs datashare.

Follow-up to test_bm_ia_2x2_matrix.py, which established shrcd=ALL and showed
that 6-month rolling timing reproduces datashare's monthly change frequency but
lowers Spearman. The conventions tested here come from the two reference
implementations:

  Supplementary_assistive_files/SAS_codes/Related_to_Dachengs_EAPVML_paper.sas
    L142  mve_f = csho * abs(prcc_f)              (Compustat ME)
    L264  mve_f replaced by CRSP me at the datadate month-end
    L544  bm_ia = bm - mean(bm) GROUP BY sic2, fyear   (annual demean)

  Supplementary_assistive_files/Python_codes/Dacheng_Xiu_or_Xin_he/accounting_60.py
    L204  jdate = datadate + MonthEnd(4)          (4-month rolling lag)
    L1087 annual me dropped, replaced by monthly permno-level CRSP me
    L1113 bm = be / monthly me                    (bm varies every month)

WRDS pulls are cached to outputs/cache/bm_ia_wrds/ so re-runs are fast.

Usage:
  python scripts/validation/test_bm_ia_me_conventions.py --wrds-user YOUR_USER
  python scripts/validation/test_bm_ia_me_conventions.py --variants B0,M3,M4
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import spearmanr

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "Character_Builders"))

from Character_Panels.timing import expand_annual_file_june  # noqa: E402
from _shared.bm_ia_builder import demean_by_industry_month  # noqa: E402
from _shared.ccm import attach_ccm_links, load_ccm_links  # noqa: E402
from output_paths import crsp_universe_filter, read_wrds_sql  # noqa: E402

DEFAULT_DATASHARE = ROOT / "Supplementary_assistive_files" / "datashare.csv"
CACHE_DIR = ROOT / "outputs" / "cache" / "bm_ia_wrds"
MIN_PAIRS = 50
BM = "bm"
BM_IA = "bm_ia"

# (label, me_source, timing, demean_mode)
VARIANTS = {
    "B0": ("dec_permco ME / june / monthly sic2", "dec_permco", "june", "monthly_sic2"),
    "M1": ("datadate ME / june / monthly sic2", "datadate_permno", "june", "monthly_sic2"),
    "M2": ("datadate ME / roll6 / monthly sic2", "datadate_permno", "rolling6", "monthly_sic2"),
    "M3": ("monthly ME / roll4 / monthly sic2", "monthly_permno", "rolling4", "monthly_sic2"),
    "M4": ("monthly ME / roll6 / monthly sic2", "monthly_permno", "rolling6", "monthly_sic2"),
    "M5": ("monthly ME / june / monthly sic2", "monthly_permno", "june", "monthly_sic2"),
    "C1": ("compustat ME / june / monthly sic2", "compustat_mve_f", "june", "monthly_sic2"),
    "S1": ("compustat ME / june / annual sic2xfyear post-CCM", "compustat_mve_f", "june", "annual_post"),
    "S2": ("compustat ME / june / annual sic2xfyear PRE-CCM", "compustat_mve_f", "june", "annual_pre"),
    "S3": ("dec_permco ME / june / annual sic2xfyear post-CCM", "dec_permco", "june", "annual_post"),
}

# Rolling-lag sweep over the two annual ME sources that survived the main grid.
for _lag in (3, 4, 5, 6, 7, 8, 9, 12, 18):
    VARIANTS[f"L{_lag}"] = (
        f"datadate ME / roll{_lag} / monthly sic2",
        "datadate_permno",
        f"rolling{_lag}",
        "monthly_sic2",
    )
    VARIANTS[f"D{_lag}"] = (
        f"dec_permco ME / roll{_lag} / monthly sic2",
        "dec_permco",
        f"rolling{_lag}",
        "monthly_sic2",
    )
MAIN_VARIANTS = ["B0", "M1", "M2", "M3", "M4", "M5", "C1", "S1", "S2", "S3"]


def add_one_month_vec(s: pd.Series) -> pd.Series:
    year, month = s // 100, s % 100
    nxt = month + 1
    return (year + (nxt == 13)) * 100 + np.where(nxt == 13, 1, nxt)


def cached(name: str, refresh: bool, loader):
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    path = CACHE_DIR / f"{name}.parquet"
    if path.exists() and not refresh:
        print(f"  cache hit: {path.name}", flush=True)
        return pd.read_parquet(path)
    print(f"  pulling {name} from WRDS...", flush=True)
    df = loader()
    df.to_parquet(path, index=False)
    return df


def load_compustat(db) -> pd.DataFrame:
    """Annual Compustat with book equity and Compustat market equity, in $M."""
    comp = read_wrds_sql(
        db,
        """
        SELECT f.gvkey, f.datadate, f.fyear,
               f.seq, f.ceq, f.at, f.lt,
               f.pstk, f.pstkl, f.pstkrv,
               f.txditc, f.csho, abs(f.prcc_f) AS prcc_f,
               c.sic
        FROM comp.funda AS f
        LEFT JOIN comp.company AS c ON f.gvkey = c.gvkey
        WHERE f.indfmt = 'INDL'
          AND f.datafmt = 'STD'
          AND f.popsrc = 'D'
          AND f.consol = 'C'
        """,
    )
    comp["datadate"] = pd.to_datetime(comp["datadate"])
    comp["preferred_stock"] = (
        comp["pstkrv"].fillna(comp["pstkl"]).fillna(comp["pstk"]).fillna(0)
    )
    comp["stockholders_equity"] = comp["seq"]
    comp.loc[comp["stockholders_equity"].isna(), "stockholders_equity"] = (
        comp["ceq"] + comp["preferred_stock"]
    )
    comp.loc[comp["stockholders_equity"].isna(), "stockholders_equity"] = (
        comp["at"] - comp["lt"]
    )
    comp["txditc"] = comp["txditc"].fillna(0)
    comp["book_equity"] = (
        comp["stockholders_equity"] + comp["txditc"] - comp["preferred_stock"]
    )
    comp = comp[comp["book_equity"] > 0].copy()

    comp["csho"] = comp["csho"].replace(0, np.nan)
    comp["mve_f"] = comp["csho"] * comp["prcc_f"]
    comp["calendar_year"] = comp["datadate"].dt.year
    comp["datadate_yyyymm"] = (
        comp["datadate"].dt.year * 100 + comp["datadate"].dt.month
    ).astype("int64")

    return (
        comp.sort_values(["gvkey", "calendar_year", "datadate"])
        .drop_duplicates(["gvkey", "calendar_year"], keep="last")
        .reset_index(drop=True)
    )


def load_crsp_monthly(db) -> pd.DataFrame:
    crsp = read_wrds_sql(
        db,
        f"""
        SELECT m.permno, m.permco, m.date, m.prc, m.shrout,
               n.exchcd, n.shrcd
        FROM crsp.msf AS m
        JOIN crsp.msenames AS n
          ON m.permno = n.permno
         AND n.namedt <= m.date
         AND m.date <= COALESCE(n.nameendt, DATE '9999-12-31')
        WHERE {crsp_universe_filter("n")}
        """,
    )
    crsp["date"] = pd.to_datetime(crsp["date"])
    crsp["year"] = crsp["date"].dt.year
    crsp["month"] = crsp["date"].dt.month
    crsp["yyyymm"] = (crsp["year"] * 100 + crsp["month"]).astype("int64")
    crsp = crsp.sort_values(["permno", "date"])
    # $M, matching Compustat units
    crsp["market_equity"] = crsp["prc"].abs() * crsp["shrout"] / 1000.0
    crsp = crsp[crsp["market_equity"].notna() & (crsp["market_equity"] > 0)]
    return crsp.reset_index(drop=True)


def december_permco_me(crsp: pd.DataFrame) -> pd.DataFrame:
    dec = crsp[crsp["month"] == 12]
    return (
        dec.groupby(["permco", "year"], as_index=False)["market_equity"]
        .sum()
        .rename(columns={"year": "calendar_year", "market_equity": "me"})
    )


def datadate_permno_me(crsp: pd.DataFrame) -> pd.DataFrame:
    """CRSP ME at a given permno-month, permno level (SAS L262-268)."""
    return (
        crsp.groupby(["permno", "yyyymm"], as_index=False)["market_equity"]
        .max()
        .rename(columns={"yyyymm": "datadate_yyyymm", "market_equity": "me"})
    )


def monthly_permno_me(crsp: pd.DataFrame) -> pd.DataFrame:
    """Monthly permno-level ME keyed by signal month (accounting_60.py L1041)."""
    return (
        crsp.groupby(["permno", "yyyymm"], as_index=False)["market_equity"]
        .max()
        .rename(columns={"yyyymm": "signal_yyyymm", "market_equity": "me_month"})
    )


def crsp_month_index(crsp: pd.DataFrame) -> pd.DataFrame:
    out = crsp[["permno", "yyyymm"]].drop_duplicates()
    return out.rename(columns={"yyyymm": "signal_yyyymm"})


def expand_annual_rolling(
    df: pd.DataFrame,
    character_columns: list[str],
    months: pd.DataFrame,
    lag_months: int,
) -> pd.DataFrame:
    """Per-firm lag of ``lag_months`` after datadate, forward-filled to the next FY."""
    df = df.copy()
    df["datadate"] = pd.to_datetime(df["datadate"])
    avail = df["datadate"] + pd.DateOffset(months=lag_months)
    df["signal_yyyymm"] = (avail.dt.year * 100 + avail.dt.month).astype("int64")
    df["permno"] = df["permno"].astype("int64")

    carry = ["permco", "gvkey", "datadate", "sic", "fyear"] + list(character_columns)
    ann = (
        df[["permno", "signal_yyyymm"] + carry]
        .sort_values(["permno", "signal_yyyymm", "datadate"])
        .drop_duplicates(["permno", "signal_yyyymm"], keep="last")
    )

    obs = months[["permno", "signal_yyyymm"]].drop_duplicates().copy()
    obs["permno"] = obs["permno"].astype("int64")
    obs["signal_yyyymm"] = obs["signal_yyyymm"].astype("int64")
    obs["_observed"] = True

    grid = ann[["permno", "signal_yyyymm"]].merge(
        obs, on=["permno", "signal_yyyymm"], how="outer"
    )
    grid["_observed"] = grid["_observed"].notna()

    out = grid.merge(ann, on=["permno", "signal_yyyymm"], how="left")
    out = out.sort_values(["permno", "signal_yyyymm"])
    out[carry] = out.groupby("permno", sort=False)[carry].ffill()

    out = out[out["_observed"].astype(bool)].dropna(subset=list(character_columns))
    out["target_yyyymm"] = add_one_month_vec(out["signal_yyyymm"])
    keep = ["permno", "signal_yyyymm", "target_yyyymm", "permco", "gvkey", "sic"]
    return out[keep + list(character_columns)]


def expand(annual: pd.DataFrame, cols: list[str], timing: str, months: pd.DataFrame) -> pd.DataFrame:
    if timing == "june":
        return expand_annual_file_june(annual, cols)
    if timing.startswith("rolling"):
        return expand_annual_rolling(annual, cols, months, int(timing.replace("rolling", "")))
    raise ValueError(f"Unknown timing {timing!r}")


def annual_demean(annual: pd.DataFrame, universe: pd.DataFrame) -> pd.DataFrame:
    """SAS L544: bm_ia = bm - mean(bm) grouped by (sic2, fyear), computed on ``universe``."""
    def sic2(frame):
        return (pd.to_numeric(frame["sic"], errors="coerce") // 100).astype("Int64")

    u = universe.copy()
    u["_sic2"] = sic2(u)
    means = (
        u.groupby(["_sic2", "fyear"], dropna=False, as_index=False)[BM]
        .mean()
        .rename(columns={BM: "_ind_mean"})
    )
    out = annual.copy()
    out["_sic2"] = sic2(out)
    out = out.merge(means, on=["_sic2", "fyear"], how="left")
    out[BM_IA] = out[BM] - out["_ind_mean"]
    return out.drop(columns=["_sic2", "_ind_mean"])


def build_variant(
    *,
    me_source: str,
    timing: str,
    demean_mode: str,
    comp: pd.DataFrame,
    link: pd.DataFrame,
    crsp: pd.DataFrame,
    months: pd.DataFrame,
) -> pd.DataFrame:
    linked = attach_ccm_links(comp, link)

    if me_source == "dec_permco":
        annual = linked.merge(december_permco_me(crsp), on=["permco", "calendar_year"], how="inner")
        annual[BM] = annual["book_equity"] / annual["me"]
    elif me_source == "datadate_permno":
        annual = linked.merge(datadate_permno_me(crsp), on=["permno", "datadate_yyyymm"], how="inner")
        annual[BM] = annual["book_equity"] / annual["me"]
    elif me_source == "compustat_mve_f":
        annual = linked.copy()
        annual[BM] = annual["book_equity"] / annual["mve_f"]
    elif me_source == "monthly_permno":
        annual = linked.copy()
        annual[BM] = np.nan  # filled after expansion from monthly ME
    else:
        raise ValueError(f"Unknown me_source {me_source!r}")

    if me_source == "monthly_permno":
        expanded = expand(annual, ["book_equity"], timing, months)
        expanded = expanded.merge(monthly_permno_me(crsp), on=["permno", "signal_yyyymm"], how="inner")
        expanded[BM] = expanded["book_equity"] / expanded["me_month"]
        expanded = expanded[expanded[BM] > 0]
        monthly = demean_by_industry_month(
            expanded, value_column=BM, industry_digits=2, stat="mean", output_column=BM_IA
        )
        return monthly[["permno", "signal_yyyymm", BM_IA]]

    annual = annual[annual[BM].notna() & (annual[BM] > 0)]
    annual = annual.sort_values(["permno", "datadate"]).drop_duplicates(["permno", "datadate"], keep="last")

    if demean_mode == "monthly_sic2":
        expanded = expand(annual, [BM], timing, months)
        monthly = demean_by_industry_month(
            expanded, value_column=BM, industry_digits=2, stat="mean", output_column=BM_IA
        )
        return monthly[["permno", "signal_yyyymm", BM_IA]]

    if demean_mode in ("annual_post", "annual_pre"):
        if demean_mode == "annual_pre":
            if me_source != "compustat_mve_f":
                raise ValueError("annual_pre requires compustat_mve_f (no permno needed)")
            universe = comp.copy()
            universe[BM] = universe["book_equity"] / universe["mve_f"]
            universe = universe[universe[BM].notna() & (universe[BM] > 0)]
        else:
            universe = annual
        annual_ia = annual_demean(annual, universe)
        expanded = expand(annual_ia, [BM_IA], timing, months)
        return expanded[["permno", "signal_yyyymm", BM_IA]]

    raise ValueError(f"Unknown demean_mode {demean_mode!r}")


def load_datashare(path: Path) -> pd.DataFrame:
    ds = pd.read_csv(path, usecols=["permno", "DATE", BM_IA])
    ds[BM_IA] = pd.to_numeric(ds[BM_IA], errors="coerce")
    ds = ds.dropna(subset=[BM_IA])
    ds["signal_yyyymm"] = (pd.to_numeric(ds["DATE"], errors="coerce") // 100).astype("int64")
    return ds[["permno", "signal_yyyymm", BM_IA]]


def dynamics(panel: pd.DataFrame) -> dict:
    p = panel.sort_values(["permno", "signal_yyyymm"])
    lag = p.groupby("permno")[BM_IA].shift(1)
    changed = (p[BM_IA] != lag)[lag.notna()]
    distinct = panel.groupby("permno")[BM_IA].nunique()
    return {
        "change_pct": float(changed.mean() * 100) if len(changed) else np.nan,
        "distinct_avg": float(distinct.mean()),
    }


def compare(panel: pd.DataFrame, ds: pd.DataFrame) -> dict:
    panel = panel.dropna(subset=[BM_IA])
    m = panel.merge(ds, on=["permno", "signal_yyyymm"], how="inner", suffixes=("_p", "_d"))
    if m.empty:
        return {"paired_rows": 0}

    rhos = []
    for _, g in m.groupby("signal_yyyymm"):
        if len(g) < MIN_PAIRS:
            continue
        r, _ = spearmanr(g[f"{BM_IA}_p"], g[f"{BM_IA}_d"])
        if not np.isnan(r):
            rhos.append(r)
    rhos = np.array(rhos)
    pooled, _ = spearmanr(m[f"{BM_IA}_p"], m[f"{BM_IA}_d"])

    return {
        "sample_n": int(len(panel)),
        "unique_permnos": int(panel["permno"].nunique()),
        "paired_rows": int(len(m)),
        "paired_permnos": int(m["permno"].nunique()),
        "pooled_spearman": float(pooled),
        "median_monthly_spearman": float(np.median(rhos)) if len(rhos) else np.nan,
        "share_months_gt_095": float((rhos > 0.95).mean()) if len(rhos) else np.nan,
        **dynamics(panel),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--wrds-user", default=None)
    parser.add_argument("--datashare", type=Path, default=DEFAULT_DATASHARE)
    parser.add_argument("--shrcd", default="ALL", help="STOCK_CHARACTERS_CRSP_SHRCD value")
    parser.add_argument("--sample-start", default="1950-01-01")
    parser.add_argument("--ccm-linktypes", default="L*")
    parser.add_argument("--ccm-linkprim", default="P,C")
    parser.add_argument("--variants", default=",".join(MAIN_VARIANTS), help="comma-separated variant ids")
    parser.add_argument("--refresh-cache", action="store_true")
    args = parser.parse_args()

    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

    selected = [v.strip().upper() for v in args.variants.split(",") if v.strip()]
    unknown = [v for v in selected if v not in VARIANTS]
    if unknown:
        raise SystemExit(f"Unknown variants: {unknown}. Choose from {list(VARIANTS)}")

    os.environ["STOCK_CHARACTERS_SAMPLE_START"] = args.sample_start
    os.environ["STOCK_CHARACTERS_CRSP_EXCHCD"] = "1,2,3"
    os.environ["STOCK_CHARACTERS_CRSP_SHRCD"] = args.shrcd

    print("Loading WRDS inputs (cached)...", flush=True)
    db = None

    def connect():
        nonlocal db
        if db is None:
            import wrds

            db = wrds.Connection(wrds_username=args.wrds_user) if args.wrds_user else wrds.Connection()
        return db

    try:
        comp = cached("comp_annual", args.refresh_cache, lambda: load_compustat(connect()))
        link = cached(
            "ccm_link",
            args.refresh_cache,
            lambda: load_ccm_links(connect(), args.ccm_linktypes, args.ccm_linkprim),
        )
        crsp = cached(
            f"crsp_monthly_shrcd_{args.shrcd.replace(',', '')}",
            args.refresh_cache,
            lambda: load_crsp_monthly(connect()),
        )
    finally:
        if db is not None:
            db.close()

    comp["datadate"] = pd.to_datetime(comp["datadate"])
    crsp["date"] = pd.to_datetime(crsp["date"])
    months = crsp_month_index(crsp)

    print(
        f"comp: {len(comp):,} rows / {comp['gvkey'].nunique():,} gvkeys | "
        f"crsp: {len(crsp):,} rows / {crsp['permno'].nunique():,} permnos",
        flush=True,
    )

    ds = load_datashare(args.datashare)
    ds_dyn = dynamics(ds)
    print(
        f"\ndatashare: {len(ds):,} rows, {ds['permno'].nunique():,} permnos, "
        f"change {ds_dyn['change_pct']:.1f}%, distinct/permno {ds_dyn['distinct_avg']:.1f}",
        flush=True,
    )

    results = []
    for vid in selected:
        label, me_source, timing, demean_mode = VARIANTS[vid]
        print(f"\nBuilding {vid}: {label}", flush=True)
        try:
            panel = build_variant(
                me_source=me_source,
                timing=timing,
                demean_mode=demean_mode,
                comp=comp,
                link=link,
                crsp=crsp,
                months=months,
            )
        except Exception as exc:  # keep the sweep going if one variant is infeasible
            print(f"  FAILED: {exc}", flush=True)
            continue
        m = compare(panel, ds)
        m["id"], m["label"] = vid, label
        results.append(m)
        if m.get("paired_rows", 0) == 0:
            print("  no paired rows vs datashare", flush=True)
            continue
        print(
            f"  median rho {m['median_monthly_spearman']:.4f} | pooled {m['pooled_spearman']:.4f} | "
            f"change {m['change_pct']:.1f}% | distinct {m['distinct_avg']:.1f} | "
            f"paired {m['paired_rows']:,} | permnos {m['paired_permnos']:,}",
            flush=True,
        )

    print("\n=== SUMMARY ===")
    header = f"{'ID':<4} {'Convention':<50} {'Med rho':>8} {'Pooled':>8} {'Chg%':>7} {'Dist':>7} {'Paired N':>12}"
    print(header)
    print("-" * len(header))
    print(
        f"{'--':<4} {'DATASHARE (target)':<50} {1.0:>8.4f} {1.0:>8.4f} "
        f"{ds_dyn['change_pct']:>6.1f}% {ds_dyn['distinct_avg']:>7.1f} {len(ds):>12,}"
    )
    for m in results:
        if m.get("paired_rows", 0) == 0:
            print(f"{m['id']:<4} {m['label']:<50} {'-':>8} {'-':>8} {'-':>7} {'-':>7} {0:>12,}")
            continue
        print(
            f"{m['id']:<4} {m['label']:<50} "
            f"{m['median_monthly_spearman']:>8.4f} {m['pooled_spearman']:>8.4f} "
            f"{m['change_pct']:>6.1f}% {m['distinct_avg']:>7.1f} {m['paired_rows']:>12,}"
        )


if __name__ == "__main__":
    main()
