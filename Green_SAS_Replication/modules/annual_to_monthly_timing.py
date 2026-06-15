"""Annual Compustat to monthly CRSP alignment (Greens_code.sas L475-523)."""
from __future__ import annotations

import numpy as np
import pandas as pd
import wrds

from config import GREEN_ANNUAL_END_LAG_MONTHS, GREEN_ANNUAL_START_LAG_MONTHS
from wrds_utils import intnx_month, retry_wrds_query, sql_between_date


def _apply_delist_adjustment(df: pd.DataFrame) -> pd.DataFrame:
    """SAS L493-503 delisting return adjustment."""
    out = df.copy()
    dlret = out["dlret"].copy()
    missing_dl = dlret.isna()
    cond_nyse_amex = missing_dl & out["dlstcd"].isin([500] + list(range(520, 585))) & out["exchcd"].isin([1, 2])
    cond_nasdaq = missing_dl & out["dlstcd"].isin([500] + list(range(520, 585))) & (out["exchcd"] == 3)
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
        lambda: db.raw_sql(f"""
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
                lambda ids=chunk_ids: db.raw_sql(f"""
                    SELECT permno, date, ret, ABS(prc) AS prc, shrout, vol
                    FROM crsp.msf
                    WHERE permno IN ({ids}) AND {date_filter}
                """),
            )
            msf = pd.concat([msf, extra], ignore_index=True)

    msf["date"] = pd.to_datetime(msf["date"])

    # Cross join filter: intnx(MONTH, datadate, 7) <= date < intnx(MONTH, datadate, 20)
    merged = annual.merge(msf, on="permno", how="inner", suffixes=("", "_msf"))
    ok = (merged["date"] >= merged["window_start"]) & (merged["date"] < merged["window_end_excl"])
    merged = merged[ok].copy()

    mse = retry_wrds_query(
        db,
        lambda: db.raw_sql(f"""
            SELECT permno, date, dlret, dlstcd, exchcd
            FROM crsp.mseall
            WHERE permno IN ({permno_list})
              AND {date_filter}
        """),
    )
    mse["date"] = pd.to_datetime(mse["date"])
    merged = merged.merge(mse, on=["permno", "date"], how="left")
    merged = _apply_delist_adjustment(merged)

    merged = merged.sort_values(["permno", "date", "datadate"], ascending=[True, True, False])
    merged = merged.drop_duplicates(["permno", "date"], keep="first")

    g = merged.groupby("permno", sort=False)
    merged["mve_m"] = g["prc"].shift(1).abs() * g["shrout"].shift(1)
    merged["mve"] = np.log(merged["mve_m"])
    merged["pps"] = np.log(g["prc"].shift(1).abs())
    merged = merged[~merged.groupby("permno").cumcount().eq(0)].copy()

    drop_cols = ["window_start", "window_end_excl"]
    merged = merged.drop(columns=[c for c in drop_cols if c in merged.columns])
    return merged
