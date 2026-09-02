"""HXZ book-to-market and operating profitability builders."""
from __future__ import annotations

import pandas as pd

from ccm import attach_ccm_links_hxz, load_ccm_links_hxz
from constants import ANNUAL_ID_COLUMNS
from firm_nulling import dedupe_annual_compustat
from paths import SINGLE_CHARACTERS_DIR
from sql_templates import company_sic_sql, hxz_funda_bm_sql, hxz_funda_operprof_sql
from wrds_io import crsp_universe_filter, maybe_load_cache, maybe_save_cache, raw_sql_with_retry
from writers import write_character


def fetch_hxz_funda(db, stem: str, sql: str, use_cache: bool = True) -> pd.DataFrame:
    if use_cache:
        cached = maybe_load_cache(stem, "hxz_funda")
        if cached is not None:
            return cached
    comp = dedupe_annual_compustat(raw_sql_with_retry(db, sql))
    company = raw_sql_with_retry(db, company_sic_sql())
    comp = comp.merge(company, on="gvkey", how="left")
    if use_cache:
        maybe_save_cache(stem, "hxz_funda", comp)
    return comp


def fetch_crsp_december_me(db, stem: str, use_cache: bool = True) -> pd.DataFrame:
    if use_cache:
        cached = maybe_load_cache(stem, "crsp_dec_me")
        if cached is not None:
            return cached
    crsp = raw_sql_with_retry(
        db,
        f"""
        SELECT m.permno, m.permco, m.date, m.prc, m.shrout, n.exchcd, n.shrcd
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
    crsp = crsp.sort_values(["permno", "date"])
    crsp["market_equity"] = crsp["prc"].abs() * crsp["shrout"]
    crsp = crsp[crsp["market_equity"].notna() & (crsp["market_equity"] > 0)].copy()
    december = crsp[crsp["month"] == 12].groupby(["permco", "year"], as_index=False)["market_equity"].sum()
    december = december.rename(columns={"year": "calendar_year"})
    if use_cache:
        maybe_save_cache(stem, "crsp_dec_me", december)
    return december


def _book_equity(comp: pd.DataFrame) -> pd.Series:
    preferred = comp["pstkrv"].fillna(comp["pstkl"]).fillna(comp["pstk"]).fillna(0)
    seq = comp["seq"].copy()
    seq = seq.fillna(comp["ceq"] + preferred)
    seq = seq.fillna(comp["at"] - comp["lt"])
    return (seq + comp["txditc"].fillna(0) - preferred) * 1000


def build_bm_panel(db, use_cache: bool = True) -> pd.DataFrame:
    comp = fetch_hxz_funda(db, "bm", hxz_funda_bm_sql(), use_cache=use_cache)
    comp["preferred_stock"] = comp["pstkrv"].fillna(comp["pstkl"]).fillna(comp["pstk"]).fillna(0)
    comp["book_equity"] = _book_equity(comp)
    comp = comp[comp["book_equity"] > 0].copy()
    comp["calendar_year"] = comp["datadate"].dt.year
    comp = comp.sort_values(["gvkey", "calendar_year", "datadate"]).drop_duplicates(["gvkey", "calendar_year"], keep="last")
    link = load_ccm_links_hxz(db)
    comp_linked = attach_ccm_links_hxz(comp, link)
    dec_me = fetch_crsp_december_me(db, "bm", use_cache=use_cache)
    bm = comp_linked.merge(dec_me, on=["permco", "calendar_year"], how="inner")
    bm["bm"] = bm["book_equity"] / bm["market_equity"]
    bm = bm[bm["bm"] > 0].copy()
    bm = bm.sort_values(["permno", "datadate", "market_equity"], ascending=[True, True, False]).drop_duplicates(
        ["permno", "datadate"], keep="first"
    )
    return bm[["permno", "permco", "gvkey", "datadate", "sic", "fyear", "bm"]]


def build_operprof_panel(db, use_cache: bool = True) -> pd.DataFrame:
    comp = fetch_hxz_funda(db, "operprof", hxz_funda_operprof_sql(), use_cache=use_cache)
    comp["preferred_stock"] = comp["pstkrv"].fillna(comp["pstkl"]).fillna(comp["pstk"]).fillna(0)
    comp["book_equity"] = comp["seq"].fillna(comp["ceq"] + comp["pstk"].fillna(0)).fillna(comp["at"] - comp["lt"])
    comp["book_equity"] = comp["book_equity"] + comp["txditc"].fillna(0) - comp["preferred_stock"]
    comp = comp[comp["book_equity"] > 0].copy()
    expense_available = comp[["cogs", "xsga", "xint"]].notna().any(axis=1)
    operating_profit = comp["revt"] - comp["cogs"].fillna(0) - comp["xsga"].fillna(0) - comp["xint"].fillna(0)
    comp["operprof"] = operating_profit / comp["book_equity"]
    comp.loc[~expense_available, "operprof"] = pd.NA
    comp = comp[comp["operprof"].notna()].copy()
    comp["calendar_year"] = comp["datadate"].dt.year
    comp = comp.sort_values(["gvkey", "calendar_year", "datadate"]).drop_duplicates(["gvkey", "calendar_year"], keep="last")
    link = load_ccm_links_hxz(db)
    out = attach_ccm_links_hxz(comp, link)
    out = out.sort_values(["permno", "datadate"]).drop_duplicates(["permno", "datadate"], keep="last")
    return out[["permno", "permco", "gvkey", "datadate", "sic", "fyear", "operprof"]]


def write_hxz_annual(df: pd.DataFrame, stem: str) -> None:
    cols = [c for c in ANNUAL_ID_COLUMNS + [stem] if c in df.columns]
    write_character(df[cols], stem, SINGLE_CHARACTERS_DIR)
