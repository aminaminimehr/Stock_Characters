"""Build all Green annual + HXZ (bm, operprof, bm_ia) characters in one flat script."""
from __future__ import annotations

import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
import wrds

PIPELINE_ROOT = Path(__file__).resolve().parents[1]
if str(PIPELINE_ROOT) not in sys.path:
    sys.path.insert(0, str(PIPELINE_ROOT))

from config.conventions import (  # noqa: E402
    ANNUAL_ROLLING_END_LAG,
    ANNUAL_ROLLING_START_LAG,
    CACHE_DIR,
    CHARACTERS_DIR,
    CRSP_EXCHCD,
    MONTHLY_ID_COLUMNS,
    SAMPLE_END,
    SAMPLE_START,
)
from config.reference_tables import (  # noqa: E402
    GREEN_CPI_BY_FYEAR,
    GREEN_SIN_NAICS,
    GREEN_TAX_RATE_BY_FYEAR,
)

#######################################################################################################################
#                                                    Helpers                                                          #
#######################################################################################################################


def wrds_query(conn, sql):
    """Execute WRDS SQL once; on failure reset connection, wait 120s, and retry once."""
    date_cols = ["datadate", "linkdt", "linkenddt", "date"]
    try:
        return conn.raw_sql(sql, date_cols=date_cols)
    except Exception as exc:
        print(f"WRDS query failed: {exc}; resetting connection, waiting 120s and retrying once...", flush=True)
        try:
            conn.connection.rollback()
        except Exception:
            pass
        try:
            conn.close(); conn.connect()
        except Exception as e2:
            print(f"  reconnect failed: {e2}", flush=True)
        time.sleep(120)
        return conn.raw_sql(sql, date_cols=date_cols)


def safe_divide(numerator, denominator):
    """Divide returning NaN where denominator is zero."""
    if isinstance(denominator, pd.Series):
        denom = denominator.replace(0, np.nan)
    else:
        denom = denominator
    return numerator / denom


def add_one_month(yyyymm: int) -> int:
    """Advance yyyymm integer by one calendar month."""
    year = yyyymm // 100
    month = yyyymm % 100
    next_month = month + 1
    next_year = year + (next_month == 13)
    next_month = 1 if next_month == 13 else next_month
    return next_year * 100 + next_month


#######################################################################################################################
# Connect to WRDS                                                                                                     #
#######################################################################################################################
conn = wrds.Connection()

CACHE_DIR.mkdir(parents=True, exist_ok=True)
CHARACTERS_DIR.mkdir(parents=True, exist_ok=True)

GREEN_ANNUAL_CHARS = [
    "absacc", "acc", "age", "agr", "cashdebt", "cashpr", "cfp", "cfp_ia",
    "chatoia", "chempia", "chcsho", "chinv", "chpmia", "convind", "currat",
    "depr", "dy", "divi", "divo", "egr", "ep", "gma", "grcapx", "grltnoa",
    "herf", "hire", "invest", "lev", "lgr", "mve_ia", "orgcap", "pctacc",
    "pchcurrat", "pchdepr", "pchcapx_ia", "pchgm_pchsale", "pchquick",
    "pchsale_pchinvt", "pchsale_pchrect", "pchsale_pchxsga", "pchsaleinv",
    "ps", "quick", "rd", "rd_sale", "rd_mve", "realestate", "roic", "sgr",
    "salecash", "saleinv", "salerec", "secured", "securedind", "sic2", "sin",
    "sp", "tb", "tang",
]
ALL_CHARACTER_COLS = GREEN_ANNUAL_CHARS + ["bm", "operprof", "bm_ia"]

ANNUAL_COMPUSTAT_WHERE = """
    f.indfmt = 'INDL'
    AND f.datafmt = 'STD'
    AND f.popsrc = 'D'
    AND f.consol = 'C'
    AND f.at IS NOT NULL
    AND f.prcc_f IS NOT NULL
    AND f.ni IS NOT NULL
"""

FIRST_YEAR_NULL = [
    "agr", "gma", "chcsho", "lgr", "acc", "pctacc", "hire", "sgr",
    "chpm", "ato", "cashdebt", "roe", "noa", "grltnoa",
    "invest", "egr", "chinv", "absacc", "pchdepr", "pchcurrat",
    "pchcapx", "pchsaleinv", "pchquick", "obklg", "chobklg",
    "pchsale_pchinvt", "pchsale_pchrect", "pchgm_pchsale", "pchsale_pchxsga",
    "divi", "divo", "rd",
]
IA_FIRST_YEAR_NULL = ["chpmia", "chempia", "pchcapx_ia"]

_funda_cache = CACHE_DIR / "annual_funda.parquet"
_orgcap_cache = CACHE_DIR / "annual_orgcap_lookup.parquet"
_age_cache = CACHE_DIR / "annual_age_lookup.parquet"
_ccm_cache = CACHE_DIR / "annual_ccm_links.parquet"
_crsp_dec_me_cache = CACHE_DIR / "annual_crsp_dec_me.parquet"
_crsp_monthly_cache = CACHE_DIR / "annual_crsp_monthly.parquet"

_sample_date_filter = f"f.datadate >= DATE '{SAMPLE_START}'"
if SAMPLE_END:
    _sample_date_filter += f" AND f.datadate <= DATE '{SAMPLE_END}'"

#######################################################################################################################
#                                                  Compustat Block                                                    #
#######################################################################################################################
if _funda_cache.exists():
    print(f"Loading cached funda -> {_funda_cache}", flush=True)
    comp = pd.read_parquet(_funda_cache)
else:
    print("Pulling comp.funda (all Green annual fields)...", flush=True)
    comp = wrds_query(
        conn,
        f"""
        SELECT c.gvkey, f.datadate, f.fyear, c.sic, c.naics,
               f.sale, f.revt, f.cogs, f.xsga, f.dp, f.xrd, f.xad,
               f.ebit, f.nopi, f.txt, f.txfo, f.txfed, f.txdi,
               f.ib, f.oancf, f.dvt, f.ni, f.txp, f.xint, f.capx, f.ob,
               f.rect, f.act, f.che, f.ppegt, f.invt, f.at, f.aco,
               f.intan, f.ao, f.ppent, f.fatb, f.fatl,
               f.lct, f.dlc, f.dltt, f.lt, f.dm, f.dcvt, f.dcpstk, f.cshrc, f.ap, f.lco, f.lo,
               f.ceq, f.seq, f.pstk, f.pstkl, f.pstkrv, f.txditc,
               f.scstkc, f.emp, f.csho, ABS(f.prcc_f) AS prcc_f
        FROM comp.company AS c
        JOIN comp.funda AS f ON c.gvkey = f.gvkey
        WHERE {ANNUAL_COMPUSTAT_WHERE}
          AND {_sample_date_filter}
        """,
    )
    comp.to_parquet(_funda_cache, index=False)
    print(f"Cached funda -> {_funda_cache} ({len(comp):,} rows)", flush=True)

comp["datadate"] = pd.to_datetime(comp["datadate"])
sic_str = (
    pd.to_numeric(comp["sic"], errors="coerce")
    .astype("Int64")
    .astype(str)
    .str.replace("<NA>", "", regex=False)
)
comp["sic2"] = sic_str.str[:2].replace("", np.nan)
comp = (
    comp.sort_values(["gvkey", "datadate"])
    .drop_duplicates(["gvkey", "datadate"], keep="last")
    .sort_values(["gvkey", "datadate"])
    .reset_index(drop=True)
)

#######################################################################################################################
#                                           Orgcap & Age Lookups                                                        #
#######################################################################################################################
if _orgcap_cache.exists():
    orgcap_lookup = pd.read_parquet(_orgcap_cache)
else:
    # TODO: explain why orgcap is needed here even though the same data has been downloaded previously from compustat block
    print("Pulling orgcap history (xsga, at)...", flush=True)
    orgcap_hist = wrds_query(
        conn,
        f"""
        SELECT c.gvkey, f.datadate, f.fyear, f.xsga, f.at
        FROM comp.company AS c
        JOIN comp.funda AS f ON c.gvkey = f.gvkey
        WHERE {ANNUAL_COMPUSTAT_WHERE}
        """,
    )
    orgcap_hist["datadate"] = pd.to_datetime(orgcap_hist["datadate"])
    orgcap_hist = (
        orgcap_hist.sort_values(["gvkey", "datadate"])
        .drop_duplicates(["gvkey", "datadate"], keep="last")
        .sort_values(["gvkey", "datadate"])
    )
    orgcap_hist["lag_at"] = orgcap_hist.groupby("gvkey")["at"].shift(1)
    orgcap_hist["avg_at"] = (orgcap_hist["at"] + orgcap_hist["lag_at"]) / 2
    # TODO: add comment to explain GREEN_CPI_BY_FYEAR
    orgcap_hist["cpi"] = orgcap_hist["fyear"].map(GREEN_CPI_BY_FYEAR)
    orgcap_hist["xsga_cpi"] = safe_divide(orgcap_hist["xsga"], orgcap_hist["cpi"])
    orgcap_parts = []
    # TODO: add comments to the following for loop
    for _, grp in orgcap_hist.groupby("gvkey", sort=False):
        orgcap_1 = np.nan
        values = []
        for xsga_cpi in grp["xsga_cpi"]:
            if pd.isna(xsga_cpi):
                values.append(np.nan)
                continue
            if pd.isna(orgcap_1):
                orgcap_1 = xsga_cpi / 0.25
            else:
                orgcap_1 = orgcap_1 * 0.85 + xsga_cpi
            values.append(orgcap_1)
        grp = grp.copy()
        grp["_orgcap_1"] = values
        orgcap_parts.append(grp)
    orgcap_hist = pd.concat(orgcap_parts, ignore_index=True)
    orgcap_hist["orgcap"] = safe_divide(orgcap_hist["_orgcap_1"], orgcap_hist["avg_at"])
    orgcap_hist.loc[orgcap_hist.groupby("gvkey").cumcount() == 0, "orgcap"] = np.nan
    orgcap_lookup = orgcap_hist[["gvkey", "datadate", "orgcap"]]
    orgcap_lookup.to_parquet(_orgcap_cache, index=False)
    print(f"Cached orgcap lookup -> {_orgcap_cache}", flush=True)

if _age_cache.exists():
    age_lookup = pd.read_parquet(_age_cache)
else:
    print("Pulling age lookup (gvkey x datadate count)...", flush=True)
    age_hist = wrds_query(
        conn,
        f"""
        SELECT c.gvkey, f.datadate
        FROM comp.company AS c
        JOIN comp.funda AS f ON c.gvkey = f.gvkey
        WHERE {ANNUAL_COMPUSTAT_WHERE}
        """,
    )
    age_hist["datadate"] = pd.to_datetime(age_hist["datadate"])
    age_hist = (
        age_hist.sort_values(["gvkey", "datadate"])
        .drop_duplicates(["gvkey", "datadate"], keep="last")
        .sort_values(["gvkey", "datadate"])
    )
    age_hist["age"] = age_hist.groupby("gvkey").cumcount() + 1
    age_lookup = age_hist[["gvkey", "datadate", "age"]]
    age_lookup.to_parquet(_age_cache, index=False)
    print(f"Cached age lookup -> {_age_cache}", flush=True)

comp = comp.merge(
    orgcap_lookup.drop_duplicates(["gvkey", "datadate"], keep="last"),
    on=["gvkey", "datadate"],
    how="left",
)
comp = comp.merge(
    age_lookup.drop_duplicates(["gvkey", "datadate"], keep="last"),
    on=["gvkey", "datadate"],
    how="left",
)

#######################################################################################################################
#                                    Green Annual Character Formulas                                                  #
#######################################################################################################################
print("Computing Green annual characters...", flush=True)

comp["mve_f"] = comp["prcc_f"] * comp["csho"]
comp["xsga0"] = comp["xsga"].fillna(0)
comp["xint0"] = comp["xint"].fillna(0)

for col in [
    "at", "act", "che", "lct", "dlc", "txp", "dp", "ib", "csho", "lt",
    "sale", "revt", "cogs", "emp", "rect", "invt", "ppent", "ppegt", "aco",
    "intan", "ao", "ap", "lco", "lo", "ceq", "dltt", "ni", "capx", "ob",
    "dvt", "xrd", "xsga",
]:
    if col in comp.columns:
        comp[f"lag_{col}"] = comp.groupby("gvkey")[col].shift(1)
        comp[f"lag2_{col}"] = comp.groupby("gvkey")[col].shift(2)

avg_at = (comp["at"] + comp["lag_at"]) / 2
avg_lt = (comp["lt"] + comp["lag_lt"]) / 2
working_capital_accrual = (
    (comp["act"] - comp["lag_act"] - (comp["che"] - comp["lag_che"]))
    - (
        (comp["lct"] - comp["lag_lct"])
        - (comp["dlc"] - comp["lag_dlc"])
        - (comp["txp"] - comp["lag_txp"])
        - comp["dp"]
    )
)

comp["ep"] = safe_divide(comp["ib"], comp["mve_f"])
comp["rd_mve"] = safe_divide(comp["xrd"], comp["mve_f"])
comp["lev"] = safe_divide(comp["lt"], comp["mve_f"])
comp["dy"] = safe_divide(comp["dvt"], comp["mve_f"])
comp["sp"] = safe_divide(comp["sale"], comp["mve_f"])
comp["rd_sale"] = safe_divide(comp["xrd"], comp["sale"])
comp["agr"] = safe_divide(comp["at"], comp["lag_at"]) - 1
comp["gma"] = safe_divide(comp["revt"] - comp["cogs"], comp["lag_at"])
comp["chcsho"] = safe_divide(comp["csho"], comp["lag_csho"]) - 1
comp["lgr"] = safe_divide(comp["lt"], comp["lag_lt"]) - 1
comp["acc"] = safe_divide(comp["ib"] - comp["oancf"], avg_at)
comp.loc[comp["oancf"].isna(), "acc"] = safe_divide(working_capital_accrual, avg_at)
comp["pctacc"] = safe_divide(comp["ib"] - comp["oancf"], comp["ib"].abs().replace(0, 0.01))
comp.loc[comp["oancf"].isna(), "pctacc"] = safe_divide(
    working_capital_accrual, comp["ib"].abs().replace(0, 0.01)
)
comp["absacc"] = comp["acc"].abs()
comp["cfp"] = safe_divide(comp["ib"] - working_capital_accrual, comp["mve_f"])
comp.loc[comp["oancf"].notna(), "cfp"] = safe_divide(comp["oancf"], comp["mve_f"])
comp["hire"] = safe_divide(comp["emp"] - comp["lag_emp"], comp["lag_emp"]).fillna(0)
comp["sgr"] = safe_divide(comp["sale"], comp["lag_sale"]) - 1
comp["chpm"] = safe_divide(comp["ib"], comp["sale"]) - safe_divide(comp["lag_ib"], comp["lag_sale"])
comp["depr"] = safe_divide(comp["dp"], comp["ppent"])
depr_rate = safe_divide(comp["dp"], comp["ppent"])
lag_depr_rate = safe_divide(comp["lag_dp"], comp["lag_ppent"])
comp["pchdepr"] = safe_divide(depr_rate - lag_depr_rate, lag_depr_rate)
comp["cashdebt"] = safe_divide(comp["ib"] + comp["dp"], avg_lt)
comp["cashpr"] = safe_divide(comp["mve_f"] + comp["dltt"] - comp["at"], comp["che"])
ppegt_delta = comp["ppegt"] - comp["lag_ppegt"]
ppent_delta = comp["ppent"] - comp["lag_ppent"]
invt_delta = comp["invt"] - comp["lag_invt"]
comp["invest"] = safe_divide(ppegt_delta + invt_delta, comp["lag_at"])
comp.loc[comp["ppegt"].isna(), "invest"] = safe_divide(ppent_delta + invt_delta, comp["lag_at"])
comp["egr"] = safe_divide(comp["ceq"] - comp["lag_ceq"], comp["lag_ceq"])
comp["chinv"] = safe_divide(comp["invt"] - comp["lag_invt"], avg_at)
comp["grltnoa"] = safe_divide(
    (
        comp["rect"] + comp["invt"] + comp["ppent"] + comp["aco"] + comp["intan"] + comp["ao"]
        - comp["ap"] - comp["lco"] - comp["lo"]
    )
    - (
        comp["lag_rect"] + comp["lag_invt"] + comp["lag_ppent"] + comp["lag_aco"]
        + comp["lag_intan"] + comp["lag_ao"] - comp["lag_ap"] - comp["lag_lco"] - comp["lag_lo"]
    )
    - (
        comp["rect"] - comp["lag_rect"] + comp["invt"] - comp["lag_invt"]
        + comp["aco"] - comp["lag_aco"] - (comp["ap"] - comp["lag_ap"] + comp["lco"] - comp["lag_lco"])
        - comp["dp"]
    ),
    avg_at,
)
currat = safe_divide(comp["act"], comp["lct"])
lag_currat = safe_divide(comp["lag_act"], comp["lag_lct"])
comp["pchcurrat"] = safe_divide(currat - lag_currat, lag_currat)
firm_count = comp.groupby("gvkey").cumcount()
impute_capx_mask = comp["capx"].isna() & (firm_count >= 1)
comp.loc[impute_capx_mask, "capx"] = (
    comp.loc[impute_capx_mask, "ppent"] - comp.loc[impute_capx_mask, "lag_ppent"]
)
comp["grcapx"] = safe_divide(comp["capx"] - comp["lag2_capx"], comp["lag2_capx"])
valid_lag_capx = comp["lag_capx"].where(comp["lag_capx"] > 0)
comp["pchcapx"] = safe_divide(comp["capx"] - valid_lag_capx, valid_lag_capx)
act_i = comp["act"].where(comp["act"].notna(), comp["che"] + comp["rect"] + comp["invt"])
lct_i = comp["lct"].where(comp["lct"].notna(), comp["ap"])
lag_act_i = comp["lag_act"].where(
    comp["lag_act"].notna(),
    comp["lag_che"] + comp["lag_rect"] + comp["lag_invt"],
)
lag_lct_i = comp["lag_lct"].where(comp["lag_lct"].notna(), comp["lag_ap"])
comp["currat"] = safe_divide(act_i, lct_i)
quick = safe_divide(act_i - comp["invt"], lct_i)
lag_quick = safe_divide(lag_act_i - comp["lag_invt"], lag_lct_i)
comp["quick"] = quick
comp["pchquick"] = safe_divide(quick - lag_quick, lag_quick)
sale_invt = safe_divide(comp["sale"], comp["invt"])
lag_sale_invt = safe_divide(comp["lag_sale"], comp["lag_invt"])
comp["pchsaleinv"] = safe_divide(sale_invt - lag_sale_invt, lag_sale_invt)
comp["salecash"] = safe_divide(comp["sale"], comp["che"])
comp["saleinv"] = safe_divide(comp["sale"], comp["invt"])
comp["salerec"] = safe_divide(comp["sale"], comp["rect"])
comp["tang"] = safe_divide(
    comp["che"] + comp["rect"] * 0.715 + comp["invt"] * 0.547 + comp["ppent"] * 0.535,
    comp["at"],
)
comp["roic"] = safe_divide(comp["ebit"] - comp["nopi"], comp["ceq"] + comp["lt"] - comp["che"])
sale_growth = safe_divide(comp["sale"] - comp["lag_sale"], comp["lag_sale"])
invt_growth = safe_divide(comp["invt"] - comp["lag_invt"], comp["lag_invt"])
rect_growth = safe_divide(comp["rect"] - comp["lag_rect"], comp["lag_rect"])
xsga_growth = safe_divide(comp["xsga"] - comp["lag_xsga"], comp["lag_xsga"])
gross_margin = comp["sale"] - comp["cogs"]
lag_gross_margin = comp["lag_sale"] - comp["lag_cogs"]
gross_margin_growth = safe_divide(gross_margin - lag_gross_margin, lag_gross_margin)
comp["pchsale_pchinvt"] = sale_growth - invt_growth
comp["pchsale_pchrect"] = sale_growth - rect_growth
comp["pchgm_pchsale"] = gross_margin_growth - sale_growth
comp["pchsale_pchxsga"] = sale_growth - xsga_growth
comp["divi"] = (
    comp["dvt"].notna()
    & (comp["dvt"] > 0)
    & (comp["lag_dvt"].isna() | (comp["lag_dvt"] == 0))
).astype(float)
comp["divo"] = (
    (comp["dvt"].isna() | (comp["dvt"] == 0))
    & comp["lag_dvt"].notna()
    & (comp["lag_dvt"] > 0)
).astype(float)
xrd_at = safe_divide(comp["xrd"], comp["at"])
lag_xrd_at = safe_divide(comp["lag_xrd"], comp["lag2_at"])
rd_growth = safe_divide(xrd_at - lag_xrd_at, lag_xrd_at).astype(float)
comp["rd"] = np.nan
valid_rd = rd_growth.notna()
comp.loc[valid_rd, "rd"] = np.where(rd_growth.loc[valid_rd] > 0.05, 1.0, 0.0)
comp["dc"] = np.nan
dc_mask1 = (
    comp["dcvt"].isna()
    & comp["dcpstk"].notna()
    & comp["pstk"].notna()
    & (comp["dcpstk"] > comp["pstk"])
)
comp.loc[dc_mask1, "dc"] = comp.loc[dc_mask1, "dcpstk"] - comp.loc[dc_mask1, "pstk"]
dc_mask2 = comp["dcvt"].isna() & comp["dcpstk"].notna() & comp["pstk"].isna()
comp.loc[dc_mask2, "dc"] = comp.loc[dc_mask2, "dcpstk"]
comp["dc"] = comp["dc"].combine_first(pd.to_numeric(comp["dcvt"], errors="coerce"))
comp["convind"] = (
    (comp["dc"].notna() & (comp["dc"] != 0))
    | (comp["cshrc"].notna() & (comp["cshrc"] != 0))
).astype(float)
comp["securedind"] = (comp["dm"].notna() & (comp["dm"] != 0)).astype(float)
comp["secured"] = safe_divide(comp["dm"], comp["dltt"])
tax_rate = comp["fyear"].map(GREEN_TAX_RATE_BY_FYEAR)
tb_primary = safe_divide(comp["txfo"] + comp["txfed"], tax_rate)
tb_fallback = safe_divide(comp["txt"] - comp["txdi"], tax_rate)
tb_numerator = tb_primary.where(comp["txfo"].notna() & comp["txfed"].notna(), tb_fallback)
comp["tb_1"] = safe_divide(tb_numerator, comp["ib"])
tb_special = (
    (comp["txfo"].fillna(0) + comp["txfed"].fillna(0) > 0)
    | (comp["txt"] > comp["txdi"])
) & (comp["ib"] <= 0)
comp.loc[tb_special, "tb_1"] = 1.0
sic_num = pd.to_numeric(comp["sic"], errors="coerce")
sic_sin = ((sic_num >= 2100) & (sic_num <= 2199)) | ((sic_num >= 2080) & (sic_num <= 2085))
naics_norm = comp["naics"].map(
    lambda x: (
        ""
        if pd.isna(x)
        else (
            str(int(pd.to_numeric(x, errors="coerce")))
            if pd.notna(pd.to_numeric(x, errors="coerce"))
            and float(pd.to_numeric(x, errors="coerce")).is_integer()
            else str(x).strip()
        )
    )
)
naics_sin = naics_norm.isin(GREEN_SIN_NAICS)
comp["sin"] = (sic_sin | naics_sin).fillna(False).astype(float)
comp["realestate"] = safe_divide(comp["fatb"] + comp["fatl"], comp["ppegt"])
comp.loc[comp["ppegt"].isna(), "realestate"] = safe_divide(comp["fatb"] + comp["fatl"], comp["ppent"])
comp.loc[comp.groupby("gvkey").cumcount() == 0, "orgcap"] = np.nan
comp["chato"] = safe_divide(comp["sale"], avg_at) - safe_divide(
    comp["lag_sale"], (comp["lag_at"] + comp["lag2_at"]) / 2
)
comp["ps"] = (
    (comp["ni"] > 0).fillna(False).astype(int)
    + (comp["oancf"] > 0).fillna(False).astype(int)
    + (safe_divide(comp["ni"], comp["at"]) > safe_divide(comp["lag_ni"], comp["lag_at"])).fillna(False).astype(int)
    + (comp["oancf"] > comp["ni"]).fillna(False).astype(int)
    + (safe_divide(comp["dltt"], comp["at"]) < safe_divide(comp["lag_dltt"], comp["lag_at"])).fillna(False).astype(int)
    + (safe_divide(comp["act"], comp["lct"]) > safe_divide(comp["lag_act"], comp["lag_lct"])).fillna(False).astype(int)
    + (
        safe_divide(comp["sale"] - comp["cogs"], comp["sale"])
        > safe_divide(comp["lag_sale"] - comp["lag_cogs"], comp["lag_sale"])
    ).fillna(False).astype(int)
    + (safe_divide(comp["sale"], comp["at"]) > safe_divide(comp["lag_sale"], comp["lag_at"])).fillna(False).astype(int)
    + (comp["scstkc"].fillna(0) == 0).astype(int)
)
comp.loc[comp.groupby("gvkey").cumcount() == 0, "ps"] = np.nan
comp["cfp_ia"] = comp["cfp"]
comp["chatoia"] = comp["chato"]
comp["chempia"] = comp["hire"]
comp["chpmia"] = comp["chpm"]
comp["pchcapx_ia"] = comp["pchcapx"]
comp["mve_ia"] = comp["mve_f"]
comp["tb"] = comp["tb_1"]
comp["herf"] = np.nan

#######################################################################################################################
#                                           Firm First-Year Nulling                                                   #
#######################################################################################################################
print("Applying firm-lag nulling rules...", flush=True)
for character in GREEN_ANNUAL_CHARS:
    if character in ("chato", "chatoia"):
        comp.loc[comp.groupby("gvkey").cumcount() < 2, character] = np.nan
    if character in FIRST_YEAR_NULL:
        comp.loc[comp.groupby("gvkey").cumcount() == 0, character] = np.nan
    if character == "grcapx":
        comp.loc[comp.groupby("gvkey").cumcount() < 2, character] = np.nan
    if character in IA_FIRST_YEAR_NULL:
        comp.loc[comp.groupby("gvkey").cumcount() == 0, character] = np.nan
    if character == "ps":
        comp.loc[comp.groupby("gvkey").cumcount() == 0, character] = np.nan
    if character == "orgcap":
        comp.loc[comp.groupby("gvkey").cumcount() == 0, character] = np.nan
comp.loc[comp.groupby("gvkey").cumcount() < 2, "chato"] = np.nan

#######################################################################################################################
#                                                     CCM Block                                                       #
#######################################################################################################################
if _ccm_cache.exists():
    ccm = pd.read_parquet(_ccm_cache)
else:
    print("Pulling CCM link table...", flush=True)
    ccm = wrds_query(
        conn,
        """
        SELECT gvkey, lpermno AS permno, lpermco AS permco, linkdt, linkenddt, linktype
        FROM crsp.ccmxpf_linktable
        WHERE linktype LIKE 'L%%'
          AND linkprim IN ('P', 'C')
          AND lpermno IS NOT NULL
        """,
    )
    ccm.to_parquet(_ccm_cache, index=False)
    print(f"Cached CCM links -> {_ccm_cache}", flush=True)

ccm["linkdt"] = pd.to_datetime(ccm["linkdt"])
ccm["linkenddt"] = pd.to_datetime(ccm["linkenddt"])
linked = comp.merge(ccm, on="gvkey", how="inner")
linkdt_ok = linked["linkdt"].isna() | (linked["linkdt"] <= linked["datadate"])
linkend_ok = linked["linkenddt"].isna() | (linked["datadate"] <= linked["linkenddt"])
linked = linked[linkdt_ok & linkend_ok & linked["permno"].notna()].copy()
linked["permno"] = pd.to_numeric(linked["permno"], errors="coerce").astype("int64")
linked["permco"] = pd.to_numeric(linked["permco"], errors="coerce").astype("Int64")

#######################################################################################################################
#                                    Post-CCM Industry Adjustment (Green)                                             #
#######################################################################################################################
print("Applying post-CCM industry adjustment...", flush=True)
grouped = linked.groupby(["sic2", "fyear"], dropna=False)
linked["cfp_ia"] = linked["cfp"] - grouped["cfp"].transform("mean")
linked["chatoia"] = linked["chato"] - grouped["chato"].transform("mean")
linked["chempia"] = linked["hire"] - grouped["hire"].transform("mean")
linked["chpmia"] = linked["chpm"] - grouped["chpm"].transform("mean")
linked["pchcapx_ia"] = linked["pchcapx"] - grouped["pchcapx"].transform("mean")
linked["mve_ia"] = linked["mve_f"] - grouped["mve_f"].transform("mean")
linked["tb"] = linked["tb_1"] - grouped["tb_1"].transform("mean")
industry_sales = grouped["sale"].transform("sum")
linked["sales_share_sq"] = (linked["sale"] / industry_sales.replace(0, np.nan)) ** 2
linked["herf"] = grouped["sales_share_sq"].transform("sum")
linked.loc[linked.groupby("gvkey").cumcount() < 2, ["chato", "chatoia"]] = np.nan
linked.loc[linked.groupby("gvkey").cumcount() == 0, ["chpmia", "chempia", "pchcapx_ia"]] = np.nan

annual_ids = ["permno", "permco", "gvkey", "datadate", "sic", "fyear"]
green_annual = linked[annual_ids + GREEN_ANNUAL_CHARS].copy()

#######################################################################################################################
#                                    Green Monthly Expansion (lags 7-19)                                              #
#######################################################################################################################
print("Expanding Green annual to monthly (lags 7-19)...", flush=True)
green_chunks = []
for month_lag in range(ANNUAL_ROLLING_START_LAG, ANNUAL_ROLLING_END_LAG):
    chunk = green_annual.copy()
    signal_dates = (
        chunk["datadate"] + pd.DateOffset(months=month_lag)
    ).dt.to_period("M").dt.to_timestamp("M")
    chunk["signal_yyyymm"] = (signal_dates.dt.year * 100 + signal_dates.dt.month).astype(int)
    chunk["target_yyyymm"] = chunk["signal_yyyymm"].map(add_one_month)
    green_chunks.append(chunk)
green_monthly = pd.concat(green_chunks, ignore_index=True)
green_monthly = (
    green_monthly.sort_values(["permno", "signal_yyyymm", "datadate"])
    .drop_duplicates(["permno", "signal_yyyymm"], keep="last")
)

#######################################################################################################################
#                                              HXZ Block (bm, operprof)                                               #
#######################################################################################################################
print("Building HXZ bm and operprof...", flush=True)

hxz_ccm = wrds_query(
    conn,
    """
    SELECT gvkey, lpermno AS permno, lpermco AS permco,
           linktype, linkprim, linkdt, linkenddt
    FROM crsp.ccmxpf_linktable
    WHERE linktype LIKE 'L%%'
      AND linkprim IN ('P', 'C')
      AND lpermno IS NOT NULL
    """,
)
hxz_ccm["linkdt"] = pd.to_datetime(hxz_ccm["linkdt"])
hxz_ccm["linkenddt"] = pd.to_datetime(hxz_ccm["linkenddt"])

hxz_funda = comp[
    [
        "gvkey", "datadate", "fyear", "sic",
        "seq", "ceq", "at", "lt", "pstk", "pstkl", "pstkrv", "txditc",
        "revt", "cogs", "xsga", "xint",
    ]
].copy()

preferred = hxz_funda["pstkrv"].fillna(hxz_funda["pstkl"]).fillna(hxz_funda["pstk"]).fillna(0)
stockholders_equity = hxz_funda["seq"].copy()
stockholders_equity = stockholders_equity.fillna(hxz_funda["ceq"] + preferred)
stockholders_equity = stockholders_equity.fillna(hxz_funda["at"] - hxz_funda["lt"])
hxz_funda["book_equity"] = (stockholders_equity + hxz_funda["txditc"].fillna(0) - preferred) * 1000

# bm panel
bm_comp = hxz_funda[hxz_funda["book_equity"] > 0].copy()
bm_comp["calendar_year"] = bm_comp["datadate"].dt.year
bm_comp = (
    bm_comp.sort_values(["gvkey", "calendar_year", "datadate"])
    .drop_duplicates(["gvkey", "calendar_year"], keep="last")
)
bm_linked = bm_comp.merge(hxz_ccm, on="gvkey", how="inner")
bm_linked = bm_linked[
    (bm_linked["datadate"] >= bm_linked["linkdt"])
    & ((bm_linked["datadate"] <= bm_linked["linkenddt"]) | bm_linked["linkenddt"].isna())
].copy()
bm_linked["linkprim_priority"] = bm_linked["linkprim"].map({"P": 0, "C": 1}).fillna(2)
bm_linked = (
    bm_linked.sort_values(["gvkey", "datadate", "linkprim_priority", "permno", "linkdt"])
    .drop_duplicates(["gvkey", "datadate"], keep="first")
)

if _crsp_dec_me_cache.exists():
    dec_me = pd.read_parquet(_crsp_dec_me_cache)
else:
    print("Pulling December CRSP market equity...", flush=True)
    crsp_dec = wrds_query(
        conn,
        f"""
        SELECT m.permno, m.permco, m.date, m.prc, m.shrout
        FROM crsp.msf AS m
        JOIN crsp.msenames AS n
          ON m.permno = n.permno
         AND n.namedt <= m.date
         AND m.date <= COALESCE(n.nameendt, DATE '9999-12-31')
        WHERE n.exchcd IN ({CRSP_EXCHCD})
          AND m.date >= DATE '{SAMPLE_START}'
        """,
    )
    crsp_dec["date"] = pd.to_datetime(crsp_dec["date"])
    crsp_dec["year"] = crsp_dec["date"].dt.year
    crsp_dec["month"] = crsp_dec["date"].dt.month
    crsp_dec["market_equity"] = crsp_dec["prc"].abs() * crsp_dec["shrout"]
    crsp_dec = crsp_dec[crsp_dec["market_equity"].notna() & (crsp_dec["market_equity"] > 0)].copy()
    dec_me = crsp_dec[crsp_dec["month"] == 12].groupby(["permco", "year"], as_index=False)["market_equity"].sum()
    dec_me = dec_me.rename(columns={"year": "calendar_year"})
    dec_me.to_parquet(_crsp_dec_me_cache, index=False)
    print(f"Cached December ME -> {_crsp_dec_me_cache}", flush=True)

bm_panel = bm_linked.merge(dec_me, on=["permco", "calendar_year"], how="inner")
bm_panel["bm"] = bm_panel["book_equity"] / bm_panel["market_equity"]
bm_panel = bm_panel[bm_panel["bm"] > 0].copy()
bm_panel = (
    bm_panel.sort_values(["permno", "datadate", "market_equity"], ascending=[True, True, False])
    .drop_duplicates(["permno", "datadate"], keep="first")
)
bm_annual = bm_panel[["permno", "permco", "gvkey", "datadate", "sic", "fyear", "bm"]].copy()

# operprof panel
op_comp = hxz_funda.copy()
op_comp["preferred_stock"] = preferred
op_comp["book_equity_op"] = (
    op_comp["seq"].fillna(op_comp["ceq"] + op_comp["pstk"].fillna(0)).fillna(op_comp["at"] - op_comp["lt"])
)
op_comp["book_equity_op"] = op_comp["book_equity_op"] + op_comp["txditc"].fillna(0) - op_comp["preferred_stock"]
op_comp = op_comp[op_comp["book_equity_op"] > 0].copy()
expense_available = op_comp[["cogs", "xsga", "xint"]].notna().any(axis=1)
operating_profit = (
    op_comp["revt"] - op_comp["cogs"].fillna(0) - op_comp["xsga"].fillna(0) - op_comp["xint"].fillna(0)
)
op_comp["operprof"] = operating_profit / op_comp["book_equity_op"]
op_comp.loc[~expense_available, "operprof"] = pd.NA
op_comp = op_comp[op_comp["operprof"].notna()].copy()
op_comp["calendar_year"] = op_comp["datadate"].dt.year
op_comp = (
    op_comp.sort_values(["gvkey", "calendar_year", "datadate"])
    .drop_duplicates(["gvkey", "calendar_year"], keep="last")
)
op_linked = op_comp.merge(hxz_ccm, on="gvkey", how="inner")
op_linked = op_linked[
    (op_linked["datadate"] >= op_linked["linkdt"])
    & ((op_linked["datadate"] <= op_linked["linkenddt"]) | op_linked["linkenddt"].isna())
].copy()
op_linked["linkprim_priority"] = op_linked["linkprim"].map({"P": 0, "C": 1}).fillna(2)
op_linked = (
    op_linked.sort_values(["gvkey", "datadate", "linkprim_priority", "permno", "linkdt"])
    .drop_duplicates(["gvkey", "datadate"], keep="first")
)
operprof_annual = (
    op_linked.sort_values(["permno", "datadate"])
    .drop_duplicates(["permno", "datadate"], keep="last")
    [["permno", "permco", "gvkey", "datadate", "sic", "fyear", "operprof"]]
    .copy()
)

#######################################################################################################################
#                                         HXZ June Expansion & bm_ia                                                    #
#######################################################################################################################
print("Expanding HXZ bm/operprof (June Y+1 for 12 months)...", flush=True)


def expand_june_annual(df, value_cols):
    """Fiscal year Y available June Y+1 for 12 months."""
    df = df.copy()
    df["datadate"] = pd.to_datetime(df["datadate"])
    id_cols = ["permno", "permco", "gvkey", "datadate", "sic", "fyear"]
    value_cols = [c for c in value_cols if c not in id_cols]
    repeated = df.loc[df.index.repeat(12), id_cols + value_cols].copy()
    availability_year = df["datadate"].dt.year + 1
    month_offsets = np.tile(np.arange(12), len(df))
    first_signal_month = availability_year.to_numpy().repeat(12) * 12 + 6
    month_index = first_signal_month + month_offsets
    repeated["signal_yyyymm"] = (month_index // 12) * 100 + (month_index % 12 + 1)
    repeated["target_yyyymm"] = repeated["signal_yyyymm"].map(add_one_month)
    repeated = (
        repeated.sort_values(["permno", "signal_yyyymm", "datadate"])
        .drop_duplicates(["permno", "signal_yyyymm"], keep="last")
    )
    return repeated


bm_monthly = expand_june_annual(bm_annual, ["bm"])
operprof_monthly = expand_june_annual(operprof_annual, ["operprof"])

bm_for_ia = bm_monthly[bm_monthly["bm"].notna()].copy()
sic_ia = pd.to_numeric(bm_for_ia["sic"], errors="coerce")
bm_for_ia["_industry"] = (sic_ia // 100).astype("Int64")
bm_for_ia["bm_ia"] = bm_for_ia["bm"] - bm_for_ia.groupby(
    ["_industry", "signal_yyyymm"], dropna=False
)["bm"].transform("mean")
bm_ia_monthly = bm_for_ia[["permno", "signal_yyyymm", "target_yyyymm", "bm_ia"]]

#######################################################################################################################
#                                           Merge Panels & CRSP Align                                                   #
#######################################################################################################################
print("Merging Green + HXZ panels...", flush=True)
merge_keys = ["permno", "signal_yyyymm", "target_yyyymm"]
panel = green_monthly.merge(
    bm_monthly[merge_keys + ["bm"]],
    on=merge_keys,
    how="outer",
)
panel = panel.merge(
    operprof_monthly[merge_keys + ["operprof"]],
    on=merge_keys,
    how="outer",
)
panel = panel.merge(
    bm_ia_monthly,
    on=merge_keys,
    how="outer",
)

if _crsp_monthly_cache.exists():
    crsp_monthly = pd.read_parquet(_crsp_monthly_cache)
else:
    print("Pulling CRSP monthly for alignment...", flush=True)
    _crsp_date_filter = f"m.date >= DATE '{SAMPLE_START}'"
    if SAMPLE_END:
        _crsp_date_filter += f" AND m.date <= DATE '{SAMPLE_END}'"
    crsp_monthly = wrds_query(
        conn,
        f"""
        SELECT m.permno, m.permco, m.date, n.exchcd, n.shrcd
        FROM crsp.msf AS m
        JOIN crsp.msenames AS n
          ON m.permno = n.permno
         AND n.namedt <= m.date
         AND m.date <= COALESCE(n.nameendt, DATE '9999-12-31')
        WHERE n.exchcd IN ({CRSP_EXCHCD})
          AND {_crsp_date_filter}
        """,
    )
    crsp_monthly["date"] = pd.to_datetime(crsp_monthly["date"])
    crsp_monthly["signal_yyyymm"] = crsp_monthly["date"].dt.year * 100 + crsp_monthly["date"].dt.month
    crsp_monthly = crsp_monthly.sort_values(["permno", "date"]).drop_duplicates(["permno", "signal_yyyymm"], keep="last")
    crsp_monthly.to_parquet(_crsp_monthly_cache, index=False)
    print(f"Cached CRSP monthly -> {_crsp_monthly_cache}", flush=True)

panel = panel.merge(
    crsp_monthly[["permno", "signal_yyyymm", "permco", "date", "exchcd", "shrcd"]],
    on=["permno", "signal_yyyymm"],
    how="left",
    suffixes=("", "_crsp"),
)
if "permco_crsp" in panel.columns:
    panel["permco"] = panel["permco"].fillna(panel["permco_crsp"])
    panel = panel.drop(columns=["permco_crsp"])

char_present = [c for c in ALL_CHARACTER_COLS if c in panel.columns]
all_nan = panel[char_present].replace([np.inf, -np.inf], np.nan).isna().all(axis=1)
panel = panel[~all_nan].copy()

out_cols = [c for c in MONTHLY_ID_COLUMNS if c in panel.columns] + char_present
out_path = CHARACTERS_DIR / "annual.parquet"
panel[out_cols].to_parquet(out_path, index=False)
print(f"Wrote {len(panel):,} rows x {len(out_cols)} cols -> {out_path}", flush=True)

if __name__ == "__main__":
    pass
