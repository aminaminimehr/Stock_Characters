"""Build GKX datashare-style bm, bm_ia, operprof, and cfp.

This ports the relevant annual/quarterly accounting pieces from GKX /
Jianxin He's ``accounting_60.py`` and the blend from
``impute_rank_output_bchmk_60.py``. It intentionally leaves the Green-style
columns alone and writes:

* a datashare-named comparison file:
  ``outputs/characteristics/datashare_style/datashare_chars.csv``
* repo-panel-safe individual files with ``_dc`` suffixes:
  ``outputs/characteristics/individual/{bm_dc,bm_ia_dc,operprof_dc,cfp_dc}.csv``

The comparison file includes ``DATE`` using GKX's final convention: the
return month after the predictor ``jdate``.
"""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
import wrds
from pandas.tseries.offsets import MonthEnd, YearEnd

PROJECT_ROOT = Path(__file__).resolve().parents[2]

# Use the repo's own Fama-French industry mapper (no external files required)
sys.path.insert(0, str(PROJECT_ROOT))
from Imputation.industry_codes import add_fama_french_industry_code  # noqa: E402

DEFAULT_OUTPUT = PROJECT_ROOT / "outputs" / "characteristics" / "datashare_style" / "datashare_chars.csv"
DEFAULT_INDIVIDUAL_DIR = PROJECT_ROOT / "outputs" / "characteristics" / "individual"
DATASHARE_COLS = ["bm", "bm_ia", "operprof", "cfp", "cfp_ia"]
DC_NAMES = {
    "bm": "bm_dc",
    "bm_ia": "bm_ia_dc",
    "operprof": "operprof_dc",
    "cfp": "cfp_dc",
    "cfp_ia": "cfp_ia_dc",
}



def raw_sql_with_retry(db, sql: str, attempts: int = 5, pause_seconds: int = 60) -> pd.DataFrame:
    last = None
    for attempt in range(1, attempts + 1):
        try:
            return db.raw_sql(sql)
        except Exception as exc:  # noqa: BLE001 - WRDS raises several DB/API exception classes.
            last = exc
            msg = str(exc).lower()
            retryable = any(
                token in msg
                for token in ("timeout", "timed out", "connection", "ssl", "closed", "reset", "rollback")
            )
            if attempt == attempts or not retryable:
                raise
            print(f"WRDS query failed ({attempt}/{attempts}): {exc}; retrying in {pause_seconds}s", flush=True)
            time.sleep(pause_seconds)
    raise last


def ttm4(series: str, df: pd.DataFrame) -> pd.Series:
    """Trailing four-quarter sum, matching GKX's current + three lags."""
    result = df[series].copy()
    grouped = df.groupby("permno")[series]
    for lag in range(1, 4):
        result = result + grouped.shift(lag)
    return result


def add_month_int(df: pd.DataFrame, source: str = "jdate", target: str = "signal_yyyymm") -> pd.DataFrame:
    df[target] = df[source].dt.year * 100 + df[source].dt.month
    return df


def coerce_numeric(df: pd.DataFrame, cols: list[str]) -> pd.DataFrame:
    for col in cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").astype("float64")
    return df


# --------------------------------------------------------------------------- CRSP
def load_crsp_monthly(db, start: str = "1959-01-01") -> pd.DataFrame:
    """CRSP monthly frame with permco-aggregated market equity.

    ``me`` is in $millions for accounting ratios. ``mvel1`` keeps the CRSP
    dollar-thousand convention used by datashare's size column.
    """
    crsp = raw_sql_with_retry(
        db,
        f"""
        select a.permno, a.permco, a.date, a.prc, a.shrout, a.ret, a.retx,
               b.shrcd, b.exchcd
        from crsp.msf as a
        left join crsp.msenames as b
          on a.permno=b.permno and b.namedt<=a.date and a.date<=b.nameendt
        where a.date >= '{start}' and b.exchcd between 1 and 3
        """,
    )
    crsp["date"] = pd.to_datetime(crsp["date"])
    crsp["jdate"] = crsp["date"] + MonthEnd(0)
    crsp = crsp.dropna(subset=["prc"]).sort_values(["permno", "date"]).drop_duplicates()
    for col in ("permno", "permco", "shrcd", "exchcd"):
        crsp[col] = crsp[col].astype("Int64")

    crsp["me_raw"] = crsp["prc"].abs() * crsp["shrout"]
    crsp["me_raw"] = crsp.groupby("permno")["me_raw"].ffill()

    summe = crsp.groupby(["jdate", "permco"], as_index=False)["me_raw"].sum()
    maxme = crsp.groupby(["jdate", "permco"], as_index=False)["me_raw"].max()
    holder = crsp.merge(maxme, how="inner", on=["jdate", "permco", "me_raw"])
    holder = holder.drop(columns=["me_raw"])
    crsp2 = holder.merge(summe, how="inner", on=["jdate", "permco"])
    crsp2 = crsp2.sort_values(["permno", "jdate"]).drop_duplicates(["permno", "jdate"])
    crsp2["mvel1"] = crsp2["me_raw"].replace(0, np.nan)
    crsp2["me"] = crsp2["mvel1"] / 1000.0
    crsp2 = crsp2.dropna(subset=["me"])
    crsp2["next_date"] = crsp2.groupby("permno")["jdate"].shift(-1)
    return crsp2[
        ["permno", "permco", "jdate", "next_date", "shrcd", "exchcd", "ret", "retx", "me", "mvel1"]
    ]


def load_ccm(db) -> pd.DataFrame:
    ccm = raw_sql_with_retry(
        db,
        """
        select gvkey, lpermno as permno, linktype, linkprim, linkdt, linkenddt
        from crsp.ccmxpf_linktable
        where substr(linktype,1,1)='L' and (linkprim='C' or linkprim='P')
        """,
    )
    ccm["linkdt"] = pd.to_datetime(ccm["linkdt"])
    ccm["linkenddt"] = pd.to_datetime(ccm["linkenddt"]).fillna(pd.Timestamp("today"))
    ccm["permno"] = ccm["permno"].astype("Int64")
    return ccm


def _link_to_months(comp: pd.DataFrame, ccm: pd.DataFrame, crsp_monthly: pd.DataFrame, lag_months: int) -> pd.DataFrame:
    """Link an accounting frame to its first available CRSP month."""
    comp = comp.merge(ccm, how="left", on="gvkey")
    comp["yearend"] = comp["datadate"] + YearEnd(0)
    comp["jdate"] = comp["datadate"] + MonthEnd(lag_months)
    comp = comp[(comp["jdate"] >= comp["linkdt"]) & (comp["jdate"] <= comp["linkenddt"])]
    comp["permno"] = comp["permno"].astype("Int64")

    link_base = crsp_monthly[["permno", "jdate", "shrcd", "exchcd", "me"]]
    merged = link_base.merge(comp, how="inner", on=["permno", "jdate"])
    merged = merged[merged["exchcd"].isin([1, 2, 3]) & merged["shrcd"].isin([10, 11])]
    merged = merged.dropna(subset=["me"])

    merged = (
        merged.sort_values(["datadate", "permno", "linkprim"])
        .drop_duplicates(["datadate", "permno", "linkprim"], keep="first")
        .sort_values(["permno", "yearend", "datadate"])
        .drop_duplicates(["permno", "yearend", "datadate"], keep="last")
    )
    return merged.sort_values(["permno", "jdate"]).reset_index(drop=True)


# ------------------------------------------------------------------------- annual
def build_annual_components(db, ccm: pd.DataFrame, crsp_monthly: pd.DataFrame) -> pd.DataFrame:
    comp = raw_sql_with_retry(
        db,
        """
        select c.gvkey, f.datadate, f.fyear, c.sic,
               f.revt, f.cogs, f.xsga, f.xint, f.ib, f.dp,
               f.seq, f.at, f.pstk, f.pstkrv, f.pstkl, f.txditc
        from comp.funda as f
        left join comp.company as c on f.gvkey=c.gvkey
        where f.indfmt='INDL' and f.datafmt='STD' and f.popsrc='D' and f.consol='C'
          and f.datadate >= '01/01/1959'
        """,
    )
    comp["datadate"] = pd.to_datetime(comp["datadate"])
    coerce_numeric(comp, ["revt", "cogs", "xsga", "xint", "ib", "dp", "seq", "at", "pstk", "pstkrv", "pstkl", "txditc"])
    comp = comp.sort_values(["gvkey", "datadate"]).drop_duplicates()
    comp["at"] = comp["at"].replace(0, np.nan)
    comp = comp.dropna(subset=["at"])

    comp["ps"] = comp["pstkrv"].fillna(comp["pstkl"]).fillna(comp["pstk"]).fillna(0)
    comp["txditc"] = comp["txditc"].fillna(0)
    comp["be"] = comp["seq"] + comp["txditc"] - comp["ps"]
    positive_be = comp["be"].gt(0).fillna(False)
    comp.loc[~positive_be, "be"] = np.nan

    comp["cogs0"] = comp["cogs"].fillna(0)
    comp["xint0"] = comp["xint"].fillna(0)
    comp["xsga0"] = comp["xsga"].fillna(0)
    comp["op"] = np.where(
        comp["revt"].isna() | comp["be"].isna(),
        np.nan,
        (comp["revt"] - comp["cogs0"] - comp["xsga0"] - comp["xint0"]) / comp["be"],
    )

    linked = _link_to_months(comp, ccm, crsp_monthly, 4)
    coerce_numeric(linked, ["be", "op", "ib", "dp"])
    linked["sic"] = pd.to_numeric(linked["sic"], errors="coerce")
    linked = add_fama_french_industry_code(linked, scheme=49, sic_col="sic", output_col="ffi49", unmatched_value=pd.NA)
    linked["ffi49"] = linked["ffi49"].fillna(49).astype("Int64")
    return linked[["gvkey", "permno", "jdate", "datadate", "sic", "ffi49", "be", "op", "ib", "dp", "me"]]


def finalize_annual_monthly(annual: pd.DataFrame, crsp_monthly: pd.DataFrame) -> pd.DataFrame:
    # Step 1: compute bm and cfp at the initial jdate (point-in-time market equity).
    # Industry means are then computed cross-sectionally at this single point to avoid
    # the bug of averaging monthly-varying bm values within a datadate group.
    annual = annual.copy()
    annual["bm"] = annual["be"] / annual["me"]
    annual["cfp"] = np.select(
        [annual["dp"].isna(), annual["ib"].isna()],
        [annual["ib"] / annual["me"], np.nan],
        default=(annual["ib"] + annual["dp"]) / annual["me"],
    )
    # Industry means: one obs per permno-datadate, grouped by (datadate, FF49)
    ind_bm = annual.groupby(["datadate", "ffi49"], as_index=False)["bm"].mean().rename(
        columns={"bm": "bm_ind"}
    )
    ind_cfp = annual.groupby(["datadate", "ffi49"], as_index=False)["cfp"].mean().rename(
        columns={"cfp": "cfp_ind"}
    )
    annual = annual.merge(ind_bm, how="left", on=["datadate", "ffi49"])
    annual = annual.merge(ind_cfp, how="left", on=["datadate", "ffi49"])
    # bm_ia and cfp_ia at jdate level — these will be forward-filled across months
    annual["bm_ia"] = annual["bm"] - annual["bm_ind"]
    annual["cfp_ia"] = annual["cfp"] - annual["cfp_ind"]

    # Step 2: expand to monthly. Forward-fill bm_ia and cfp_ia (holding them constant
    # within each fiscal year), and recompute bm/cfp using monthly market equity.
    value_cols = ["gvkey", "datadate", "sic", "ffi49", "be", "op", "ib", "dp", "bm_ia", "cfp_ia"]
    out = expand_monthly(annual, value_cols, crsp_monthly)
    # Monthly bm and cfp use current market equity (out["me"] from crsp_monthly)
    out["bm"] = out["be"] / out["me"]
    out["cfp"] = np.select(
        [out["dp"].isna(), out["ib"].isna()],
        [out["ib"] / out["me"], np.nan],
        default=(out["ib"] + out["dp"]) / out["me"],
    )
    return out[["gvkey", "permno", "jdate", "datadate", "sic", "bm", "bm_ia", "cfp_ia", "op", "cfp"]]


# ----------------------------------------------------------------------- quarterly
def build_quarterly_components(db, ccm: pd.DataFrame, crsp_monthly: pd.DataFrame) -> pd.DataFrame:
    comp = raw_sql_with_retry(
        db,
        """
        select c.gvkey, f.datadate, f.fyearq, c.sic,
               f.revtq, f.cogsq, f.xsgaq, f.xintq, f.ibq, f.dpq,
               f.seqq, f.txditcq, f.pstkq, f.atq
        from comp.fundq as f
        left join comp.company as c on f.gvkey=c.gvkey
        where f.indfmt='INDL' and f.datafmt='STD' and f.popsrc='D' and f.consol='C'
          and f.datadate >= '01/01/1959'
        """,
    )
    comp["datadate"] = pd.to_datetime(comp["datadate"])
    coerce_numeric(comp, ["revtq", "cogsq", "xsgaq", "xintq", "ibq", "dpq", "seqq", "txditcq", "pstkq", "atq"])
    comp = comp.dropna(subset=["ibq"]).sort_values(["gvkey", "datadate"]).drop_duplicates()
    comp["atq"] = comp["atq"].replace(0, np.nan)
    comp = comp.dropna(subset=["atq"])

    linked = _link_to_months(comp, ccm, crsp_monthly, 3)
    coerce_numeric(linked, ["revtq", "cogsq", "xsgaq", "xintq", "ibq", "dpq", "seqq", "txditcq", "pstkq", "atq"])
    linked["beq"] = np.nan
    positive_seqq = linked["seqq"].gt(0).fillna(False)
    linked.loc[positive_seqq, "beq"] = (
        linked.loc[positive_seqq, "seqq"]
        + linked.loc[positive_seqq, "txditcq"]
        - linked.loc[positive_seqq, "pstkq"]
    )
    positive_beq = linked["beq"].gt(0).fillna(False)
    linked.loc[~positive_beq, "beq"] = np.nan

    linked["ibq4"] = ttm4("ibq", linked)
    linked["dpq4"] = ttm4("dpq", linked)
    linked["xintq0"] = linked["xintq"].fillna(0)
    linked["xsgaq0"] = linked["xsgaq"].fillna(0)
    linked["beq_l4"] = linked.groupby("permno")["beq"].shift(4)
    linked["op"] = (
        ttm4("revtq", linked) - ttm4("cogsq", linked) - ttm4("xsgaq0", linked) - ttm4("xintq0", linked)
    ) / linked["beq_l4"]

    return linked[["gvkey", "permno", "jdate", "datadate", "sic", "beq", "op", "ibq4", "dpq4", "dpq"]]


def finalize_quarterly_monthly(quarterly: pd.DataFrame, crsp_monthly: pd.DataFrame) -> pd.DataFrame:
    value_cols = ["gvkey", "datadate", "sic", "beq", "op", "ibq4", "dpq4", "dpq"]
    out = expand_monthly(quarterly, value_cols, crsp_monthly)
    out["bm"] = out["beq"] / out["me"]
    out["cfp"] = np.where(
        out["dpq"].isna(),
        out["ibq4"] / out["me"],
        (out["ibq4"] + out["dpq4"]) / out["me"],
    )
    return out[["gvkey", "permno", "jdate", "datadate", "sic", "bm", "op", "cfp"]]


# ------------------------------------------------------------------ monthly/blend
def expand_monthly(frame: pd.DataFrame, value_cols: list[str], crsp_monthly: pd.DataFrame) -> pd.DataFrame:
    """Forward-fill statement values across CRSP months within permno/datadate."""
    base = crsp_monthly[["permno", "jdate", "me", "mvel1", "next_date"]].drop_duplicates(["permno", "jdate"])
    out = base.merge(frame, how="left", on=["permno", "jdate"])
    out = out.sort_values(["permno", "jdate"]).reset_index(drop=True)
    out["datadate"] = out.groupby("permno")["datadate"].ffill()
    out[["_permno_ff", "_datadate_ff"]] = out[["permno", "datadate"]]
    fill_cols = [col for col in value_cols if col != "datadate"]
    out[fill_cols] = out.groupby(["_permno_ff", "_datadate_ff"], dropna=True)[fill_cols].ffill()
    return out.drop(columns=["_permno_ff", "_datadate_ff"])


def blend(annual_m: pd.DataFrame, quarterly_m: pd.DataFrame) -> pd.DataFrame:
    chars = ["bm", "op", "cfp"]
    # bm_ia and cfp_ia come only from the annual frame (no quarterly equivalent)
    a = annual_m.rename(columns={**{c: f"a_{c}" for c in chars}, "datadate": "a_datadate", "sic": "a_sic"})
    q = quarterly_m.rename(columns={**{c: f"q_{c}" for c in chars}, "datadate": "q_datadate", "sic": "q_sic"})

    df = a.merge(q, how="left", on=["gvkey", "permno", "jdate"])
    for c in chars:
        ac, qc = f"a_{c}", f"q_{c}"
        have_a = df[ac].notna()
        have_q = df[qc].notna()
        both = have_a & have_q
        latest = np.where(df["q_datadate"] < df["a_datadate"], df[ac], df[qc])
        available = np.where(have_a, df[ac], df[qc])
        df[c] = np.where(both, latest, available)

    df["datadate"] = df["a_datadate"]
    df["sic"] = df["a_sic"].combine_first(df["q_sic"])
    df = df.rename(columns={"op": "operprof"})
    return df[["gvkey", "permno", "jdate", "datadate", "sic", "bm", "operprof", "cfp", "bm_ia", "cfp_ia"]]


def add_datashare_dates(df: pd.DataFrame, crsp_monthly: pd.DataFrame) -> pd.DataFrame:
    next_dates = crsp_monthly[["permno", "jdate", "next_date"]].drop_duplicates(["permno", "jdate"])
    out = df.merge(next_dates, how="left", on=["permno", "jdate"])
    out = out.dropna(subset=["next_date"])
    out["DATE"] = out["next_date"].dt.strftime("%Y%m%d").astype("int64")
    add_month_int(out, "jdate", "signal_yyyymm")
    out["target_yyyymm"] = out["next_date"].dt.year * 100 + out["next_date"].dt.month
    return out.drop(columns=["next_date"])


def write_individual_files(df: pd.DataFrame, individual_dir: Path) -> None:
    individual_dir.mkdir(parents=True, exist_ok=True)
    base_cols = ["permno", "gvkey", "jdate", "DATE", "signal_yyyymm", "target_yyyymm", "datadate", "sic"]
    for source, dest in DC_NAMES.items():
        out = df[base_cols + [source]].rename(columns={source: dest})
        out = out.dropna(subset=[dest])
        out.to_csv(individual_dir / f"{dest}.csv", index=False)
        print(f"Saved {dest}: {individual_dir / f'{dest}.csv'} rows={len(out):,}", flush=True)


def build_datashare_chars(db, start: str) -> pd.DataFrame:
    print("Loading CRSP monthly market equity...", flush=True)
    crsp_monthly = load_crsp_monthly(db, start)
    print(f"CRSP monthly rows: {len(crsp_monthly):,}", flush=True)

    print("Loading CCM links...", flush=True)
    ccm = load_ccm(db)
    print("Building annual components...", flush=True)
    annual = build_annual_components(db, ccm, crsp_monthly)
    print(f"Annual linked rows: {len(annual):,}", flush=True)
    print("Building quarterly components...", flush=True)
    quarterly = build_quarterly_components(db, ccm, crsp_monthly)
    print(f"Quarterly linked rows: {len(quarterly):,}", flush=True)

    print("Expanding annual and quarterly components to monthly...", flush=True)
    annual_m = finalize_annual_monthly(annual, crsp_monthly)
    quarterly_m = finalize_quarterly_monthly(quarterly, crsp_monthly)
    print("Blending annual/quarterly values...", flush=True)
    blended = blend(annual_m, quarterly_m)
    blended = add_datashare_dates(blended, crsp_monthly)
    blended = blended.replace([np.inf, -np.inf], np.nan)
    return blended.dropna(subset=DATASHARE_COLS, how="all").reset_index(drop=True)


def main() -> None:
    parser = argparse.ArgumentParser(description="Build GKX/datashare-style _dc characteristics.")
    parser.add_argument("--wrds-user", default=None)
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    parser.add_argument("--individual-dir", default=str(DEFAULT_INDIVIDUAL_DIR))
    parser.add_argument("--start", default="1959-01-01")
    parser.add_argument(
        "--skip-individual",
        action="store_true",
        help="Only write the datashare-named comparison file.",
    )
    args = parser.parse_args()

    db = wrds.Connection(wrds_username=args.wrds_user) if args.wrds_user else wrds.Connection()
    try:
        out = build_datashare_chars(db, args.start)
    finally:
        db.close()

    out_path = Path(args.output)
    if not out_path.is_absolute():
        out_path = PROJECT_ROOT / out_path
    out_path.parent.mkdir(parents=True, exist_ok=True)

    ordered = [
        "permno",
        "DATE",
        "jdate",
        "signal_yyyymm",
        "target_yyyymm",
        "gvkey",
        "datadate",
        "sic",
        "bm",
        "bm_ia",
        "operprof",
        "cfp",
        "cfp_ia",
    ]
    out[ordered].to_csv(out_path, index=False)
    print(f"Saved datashare-style comparison file: {out_path} rows={len(out):,}", flush=True)

    if not args.skip_individual:
        individual_dir = Path(args.individual_dir)
        if not individual_dir.is_absolute():
            individual_dir = PROJECT_ROOT / individual_dir
        write_individual_files(out, individual_dir)


if __name__ == "__main__":
    main()
