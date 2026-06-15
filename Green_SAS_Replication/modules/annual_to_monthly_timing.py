"""Annual Compustat to monthly CRSP alignment (Greens_code.sas L475-523)."""
from __future__ import annotations

import numpy as np
import pandas as pd
import wrds

from config import GREEN_ANNUAL_END_LAG_MONTHS, GREEN_ANNUAL_START_LAG_MONTHS
from wrds_utils import debug_log, intnx_month, retry_wrds_query, sql_between_date

_DELIST_REQUIRED = ("dlret", "dlstcd", "exchcd")


def _require_columns(df: pd.DataFrame, required: tuple[str, ...], context: str) -> None:
    missing = [col for col in required if col not in df.columns]
    if missing:
        available = ", ".join(sorted(df.columns))
        raise KeyError(f"{context}: missing {missing}. Available columns: {available}")


def _normalize_delist_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Ensure dlret, dlstcd, exchcd are plain names from the mseall merge."""
    out = df.copy()
    for col in _DELIST_REQUIRED:
        if col not in out.columns:
            for candidate in (f"{col}_mse", f"{col}_y", f"{col}_mseall"):
                if candidate in out.columns:
                    out[col] = out[candidate]
                    break
    drop = [
        c
        for c in out.columns
        if c.endswith(("_mse", "_y", "_mseall"))
        and c.rsplit("_", 1)[0] in {"dlret", "dlstcd", "exchcd"}
    ]
    out = out.drop(columns=drop, errors="ignore")
    if "exchcd_ccm" in out.columns and "exchcd" not in out.columns:
        out["exchcd"] = out["exchcd_ccm"]
    return out


def _apply_delist_adjustment(df: pd.DataFrame) -> pd.DataFrame:
    """SAS L493-503 delisting return adjustment."""
    out = _normalize_delist_columns(df)
    _require_columns(out, _DELIST_REQUIRED, "before delist adjustment")

    dlret = out["dlret"].copy()
    dlstcd = out["dlstcd"]
    exchcd = out["exchcd"]
    missing_dl = dlret.isna()
    cond_nyse_amex = missing_dl & dlstcd.isin([500] + list(range(520, 585))) & exchcd.isin([1, 2])
    cond_nasdaq = missing_dl & dlstcd.isin([500] + list(range(520, 585))) & (exchcd == 3)
    dlret = dlret.mask(cond_nyse_amex, -0.35)
    dlret = dlret.mask(cond_nasdaq, -0.55)
    dlret = dlret.mask(dlret < -1, -1)
    dlret = dlret.fillna(0)
    out["dlret"] = dlret
    out["ret"] = out["ret"].fillna(0) + dlret
    out.loc[out["ret"].isna() & (dlret != 0), "ret"] = dlret
    return out


def align_annual_to_monthly(
    db: wrds.Connection,
    annual_linked: pd.DataFrame,
    sample_start: str | None,
    sample_end: str | None,
) -> pd.DataFrame:
    """Join annual characteristics to CRSP monthly using Green timing window."""
    annual = annual_linked.copy()
    annual["datadate"] = pd.to_datetime(annual["datadate"])
    annual["window_start"] = intnx_month(annual["datadate"], GREEN_ANNUAL_START_LAG_MONTHS, "end")
    annual["window_end_excl"] = intnx_month(annual["datadate"], GREEN_ANNUAL_END_LAG_MONTHS, "end")

    permnos = annual["permno"].dropna().astype(int).unique().tolist()
    if not permnos:
        return pd.DataFrame()

    date_filter = sql_between_date("date", sample_start, sample_end)
    permno_list = ",".join(str(p) for p in permnos[:5000])
    msf = retry_wrds_query(
        db,
        lambda conn: conn.raw_sql(f"""
            SELECT permno, date, ret, ABS(prc) AS prc, shrout, vol
            FROM crsp.msf
            WHERE permno IN ({permno_list})
              AND {date_filter}
        """),
    )
    if len(permnos) > 5000:
        for i in range(5000, len(permnos), 5000):
            chunk_ids = ",".join(str(p) for p in permnos[i : i + 5000])
            extra = retry_wrds_query(
                db,
                lambda conn, ids=chunk_ids: conn.raw_sql(f"""
                    SELECT permno, date, ret, ABS(prc) AS prc, shrout, vol
                    FROM crsp.msf
                    WHERE permno IN ({ids}) AND {date_filter}
                """),
            )
            msf = pd.concat([msf, extra], ignore_index=True)

    msf.columns = [str(c).lower() for c in msf.columns]
    msf["date"] = pd.to_datetime(msf["date"])

    merged = annual.merge(msf, on="permno", how="inner", suffixes=("", "_msf"))
    ok = (merged["date"] >= merged["window_start"]) & (merged["date"] < merged["window_end_excl"])
    merged = merged[ok].copy()
    debug_log(f"annual_monthly after msf merge: rows={len(merged):,} columns={list(merged.columns)}")

    # Green SAS second merge: b.dlret, b.dlstcd, b.exchcd from crsp.mseall at permno x date.
    # Rename CCM-screen exchcd so monthly mseall exchcd is unambiguous for delisting.
    if "exchcd" in merged.columns:
        merged = merged.rename(columns={"exchcd": "exchcd_ccm"})

    mse = retry_wrds_query(
        db,
        lambda conn: conn.raw_sql(f"""
            SELECT permno, date, dlret, dlstcd, exchcd
            FROM crsp.mseall
            WHERE permno IN ({permno_list})
              AND {date_filter}
        """),
    )
    mse.columns = [str(c).lower() for c in mse.columns]
    mse["date"] = pd.to_datetime(mse["date"])
    debug_log(f"annual_monthly mseall pull columns={list(mse.columns)} rows={len(mse):,}")

    merged = merged.merge(mse, on=["permno", "date"], how="left", suffixes=("", "_mse"))
    debug_log(f"annual_monthly after mseall merge: rows={len(merged):,} columns={list(merged.columns)}")

    merged = _apply_delist_adjustment(merged)
    debug_log(f"annual_monthly after delist adjustment: rows={len(merged):,}")

    merged = merged.sort_values(["permno", "date", "datadate"], ascending=[True, True, False])
    merged = merged.drop_duplicates(["permno", "date"], keep="first")
    debug_log(f"annual_monthly after permno-date dedup: rows={len(merged):,}")

    g = merged.groupby("permno", sort=False)
    merged["mve_m"] = g["prc"].shift(1).abs() * g["shrout"].shift(1)
    merged["mve"] = np.log(merged["mve_m"])
    merged["pps"] = np.log(g["prc"].shift(1).abs())
    merged = merged[~merged.groupby("permno").cumcount().eq(0)].copy()
    debug_log(f"annual_monthly final rows={len(merged):,}")

    drop_cols = ["window_start", "window_end_excl"]
    merged = merged.drop(columns=[c for c in drop_cols if c in merged.columns])
    return merged
