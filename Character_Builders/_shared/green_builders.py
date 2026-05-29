import argparse
from pathlib import Path

import numpy as np
import pandas as pd
import wrds

from _shared.ccm import add_ccm_arguments, attach_ccm_links, load_ccm_links


PROJECT_ROOT = Path(__file__).resolve().parents[2]
OUTPUT_DIR = PROJECT_ROOT / "outputs"


ANNUAL_CHARACTER_INFO = {
    "acc": "Operating accruals",
    "adm": "Advertising expense-to-market",
    "agr": "Asset growth",
    "alm": "Asset liquidity",
    "ato": "Asset turnover",
    "bm": "Book-to-market equity",
    "bm_ia": "Industry-adjusted book-to-market",
    "cash": "Cash holdings",
    "cashdebt": "Cash to debt",
    "cfp": "Cash-flow-to-price",
    "chcsho": "Change in shares outstanding",
    "chpm": "Industry-adjusted change in profit margin",
    "depr": "Depreciation / PP&E",
    "dy": "Dividend yield",
    "ep": "Earnings-to-price",
    "gma": "Gross profitability",
    "grltnoa": "Growth in long-term net operating assets",
    "herf": "Industry sales concentration",
    "hire": "Employee growth rate",
    "lev": "Leverage",
    "lgr": "Growth in long-term debt",
    "me_ia": "Industry-adjusted size",
    "noa": "Net operating assets",
    "op": "Operating profitability",
    "pctacc": "Percent operating accruals",
    "pm": "Profit margin",
    "ps": "Performance score",
    "rd_sale": "R&D to sales",
    "rdm": "R&D expense-to-market",
    "roe": "Return on equity",
    "sgr": "Sales growth",
    "sp": "Sales-to-price",
}

MONTHLY_CHARACTER_INFO = {
    "dolvol": "Dollar trading volume",
    "me": "Market equity",
    "mvel1": "Log lagged market equity",
    "mom1m": "One-month momentum",
    "mom6m": "Six-month momentum",
    "mom12m": "Twelve-month momentum",
    "mom36m": "Thirty-six-month momentum",
    "mom60m": "Sixty-month momentum",
    "seas1a": "Seasonality (lagged 11-month return)",
    "turn": "Share turnover",
}

DAILY_MONTHLY_CHARACTER_INFO = {
    "baspread": "Bid-ask spread, rolling month",
    "ill": "Illiquidity, rolling month",
    "maxret": "Maximum daily return, rolling month",
    "rvar_mean": "Daily return variance, rolling month",
    "std_dolvol": "Standard deviation of dollar trading volume, rolling month",
    "std_turn": "Standard deviation of share turnover, rolling month",
    "zerotrade": "Zero-trading days, rolling month",
}

SUPPORTED_CHARACTERS = {
    **ANNUAL_CHARACTER_INFO,
    **MONTHLY_CHARACTER_INFO,
    **DAILY_MONTHLY_CHARACTER_INFO,
}

PLANNED_CHARACTERS = {}


def safe_divide(numerator, denominator):
    return numerator / denominator.replace(0, np.nan)


def lag(df, column, periods=1):
    return df.groupby("gvkey")[column].shift(periods)


def indicator(condition):
    return condition.fillna(False).astype(int)


def add_one_month(yyyymm):
    year = yyyymm // 100
    month = yyyymm % 100
    next_month = month + 1
    next_year = year + (next_month == 13)
    next_month = 1 if next_month == 13 else next_month
    return next_year * 100 + next_month


def connect_wrds(wrds_user):
    return wrds.Connection(wrds_username=wrds_user) if wrds_user else wrds.Connection()


def attach_permno(comp, link):
    return attach_ccm_links(comp, link)


def load_annual_compustat(db):
    comp = db.raw_sql("""
        SELECT c.gvkey, f.datadate, f.fyear, c.sic,
               f.sale, f.revt, f.cogs, f.xsga, f.dp, f.xrd, f.xad,
               f.ib, f.oancf, f.dvt, f.ni, f.txp, f.txt, f.xint,
               f.rect, f.act, f.che, f.ppegt, f.invt, f.at, f.aco,
               f.intan, f.ao, f.ppent,
               f.lct, f.dlc, f.dltt, f.lt, f.ap, f.lco, f.lo,
               f.ceq, f.seq, f.pstk, f.pstkl, f.pstkrv, f.txditc,
               f.scstkc, f.emp, f.csho, ABS(f.prcc_f) AS prcc_f
        FROM comp.company AS c
        JOIN comp.funda AS f
          ON c.gvkey = f.gvkey
        WHERE f.indfmt = 'INDL'
          AND f.datafmt = 'STD'
          AND f.popsrc = 'D'
          AND f.consol = 'C'
          AND f.at IS NOT NULL
          AND f.prcc_f IS NOT NULL
          AND f.ni IS NOT NULL
          AND f.datadate >= DATE '1975-01-01'
    """)
    comp["datadate"] = pd.to_datetime(comp["datadate"])
    comp["sic2"] = pd.to_numeric(comp["sic"], errors="coerce") // 100
    comp["calendar_year"] = comp["datadate"].dt.year
    comp = (
        comp.sort_values(["gvkey", "datadate"])
        .drop_duplicates(["gvkey", "datadate"], keep="last")
        .sort_values(["gvkey", "datadate"])
    )
    return comp


def add_book_equity(comp):
    preferred = comp["pstkrv"].fillna(comp["pstkl"]).fillna(comp["pstk"]).fillna(0)
    stockholders_equity = comp["seq"].copy()
    stockholders_equity = stockholders_equity.fillna(comp["ceq"] + preferred)
    stockholders_equity = stockholders_equity.fillna(comp["at"] - comp["lt"])
    comp["book_equity"] = stockholders_equity + comp["txditc"].fillna(0) - preferred
    return comp


def compute_annual_characters(comp):
    comp = comp.copy()
    comp = add_book_equity(comp)
    comp["mve_f"] = comp["prcc_f"] * comp["csho"]
    comp["xsga0"] = comp["xsga"].fillna(0)
    comp["xint0"] = comp["xint"].fillna(0)

    for col in [
        "at", "act", "che", "lct", "dlc", "txp", "dp", "ib", "csho", "lt",
        "sale", "revt", "cogs", "emp", "rect", "invt", "ppent", "aco",
        "intan", "ao", "ap", "lco", "lo", "ceq", "dltt", "ni",
    ]:
        if col in comp:
            comp[f"lag_{col}"] = lag(comp, col)
            comp[f"lag2_{col}"] = lag(comp, col, 2)

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

    comp["bm"] = safe_divide(comp["ceq"], comp["mve_f"])
    comp["ep"] = safe_divide(comp["ib"], comp["mve_f"])
    comp["adm"] = safe_divide(comp["xad"], comp["mve_f"])
    comp["rdm"] = safe_divide(comp["xrd"], comp["mve_f"])
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
    comp["cfp"] = safe_divide(comp["ib"] - working_capital_accrual, comp["mve_f"])
    comp.loc[comp["oancf"].notna(), "cfp"] = safe_divide(comp["oancf"], comp["mve_f"])
    comp["hire"] = safe_divide(comp["emp"] - comp["lag_emp"], comp["lag_emp"]).fillna(0)
    comp["sgr"] = safe_divide(comp["sale"], comp["lag_sale"]) - 1
    comp["chpm"] = safe_divide(comp["ib"], comp["sale"]) - safe_divide(comp["lag_ib"], comp["lag_sale"])
    comp["ato"] = safe_divide(comp["sale"], avg_at)
    comp["depr"] = safe_divide(comp["dp"], comp["ppent"])
    comp["cashdebt"] = safe_divide(comp["ib"] + comp["dp"], avg_lt)
    comp["cash"] = safe_divide(comp["che"], comp["at"])
    comp["pm"] = safe_divide(comp["ib"], comp["sale"])
    comp["roe"] = safe_divide(comp["ib"], comp["lag_ceq"])
    comp["op"] = safe_divide(comp["revt"] - comp["cogs"] - comp["xsga0"] - comp["xint0"], comp["lag_ceq"])
    comp["noa"] = safe_divide(
        (comp["at"] - comp["che"]) - (comp["at"] - comp["dlc"] - comp["dltt"] - comp["pstk"] - comp["ceq"]),
        comp["lag_at"],
    )
    comp["alm"] = safe_divide(
        comp["che"] + 0.75 * (comp["act"] - comp["che"]) + 0.5 * (comp["at"] - comp["act"]),
        comp["at"],
    )
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
    comp["ps"] = (
        indicator(comp["ni"] > 0)
        + indicator(comp["oancf"] > 0)
        + indicator(safe_divide(comp["ni"], comp["at"]) > safe_divide(comp["lag_ni"], comp["lag_at"]))
        + indicator(comp["oancf"] > comp["ni"])
        + indicator(safe_divide(comp["dltt"], comp["at"]) < safe_divide(comp["lag_dltt"], comp["lag_at"]))
        + indicator(safe_divide(comp["act"], comp["lct"]) > safe_divide(comp["lag_act"], comp["lag_lct"]))
        + indicator(safe_divide(comp["sale"] - comp["cogs"], comp["sale"]) > safe_divide(comp["lag_sale"] - comp["lag_cogs"], comp["lag_sale"]))
        + indicator(safe_divide(comp["sale"], comp["at"]) > safe_divide(comp["lag_sale"], comp["lag_at"]))
        + indicator(comp["scstkc"].fillna(0) == 0)
    )

    grouped = comp.groupby(["fyear", "sic2"], dropna=False)
    comp["bm_ia"] = comp["bm"] - grouped["bm"].transform("mean")
    comp["chpm"] = comp["chpm"] - grouped["chpm"].transform("mean")
    comp["me_ia"] = comp["mve_f"] - grouped["mve_f"].transform("mean")
    industry_sales = grouped["sale"].transform("sum")
    comp["sales_share_sq"] = (comp["sale"] / industry_sales.replace(0, np.nan)) ** 2
    comp["herf"] = grouped["sales_share_sq"].transform("sum")

    comp.loc[comp.groupby("gvkey").cumcount() == 0, [
        "agr", "gma", "chcsho", "lgr", "acc", "pctacc", "hire", "sgr",
        "chpm", "ato", "cashdebt", "roe", "noa", "grltnoa", "ps",
    ]] = np.nan
    return comp


def write_character(df, character, output_dir):
    out = df.copy()
    out = out[out[character].replace([np.inf, -np.inf], np.nan).notna()].copy()
    output_path = Path(output_dir) / f"{character}.csv"
    out.to_csv(output_path, index=False)
    print(f"{character}: {len(out):,} rows -> {output_path}")


def build_annual_character(db, character, ccm_linktypes=None, ccm_linkprim=None):
    comp = compute_annual_characters(load_annual_compustat(db))
    link = load_ccm_links(db, ccm_linktypes, ccm_linkprim)
    comp = attach_permno(comp, link)
    comp = comp.rename(columns={character: "character_value"})
    comp = comp[comp["character_value"].replace([np.inf, -np.inf], np.nan).notna()].copy()
    return comp[
        ["permno", "permco", "gvkey", "datadate", "sic", "fyear", "character_value"]
    ].rename(columns={"character_value": character})


def load_crsp_monthly(db):
    crsp = db.raw_sql("""
        SELECT m.permno, m.permco, m.date, m.ret, m.retx, m.prc, m.shrout, m.vol,
               n.exchcd, n.shrcd, n.siccd
        FROM crsp.msf AS m
        JOIN crsp.msenames AS n
          ON m.permno = n.permno
         AND n.namedt <= m.date
         AND m.date <= COALESCE(n.nameendt, DATE '9999-12-31')
        WHERE n.shrcd IN (10, 11)
          AND n.exchcd IN (1, 2, 3)
    """)
    crsp["date"] = pd.to_datetime(crsp["date"])
    crsp = crsp.sort_values(["permno", "date"])
    crsp["ret"] = pd.to_numeric(crsp["ret"], errors="coerce")
    crsp["prc_abs"] = crsp["prc"].abs()
    crsp["market_equity"] = crsp["prc_abs"] * crsp["shrout"]
    crsp["signal_yyyymm"] = crsp["date"].dt.year * 100 + crsp["date"].dt.month
    crsp["target_yyyymm"] = crsp["signal_yyyymm"].map(add_one_month)
    return crsp


def rolling_return_product(crsp, start_lag, end_lag):
    lagged_returns = pd.concat(
        [crsp.groupby("permno")["ret"].shift(period) for period in range(start_lag, end_lag + 1)],
        axis=1,
    )
    return (1 + lagged_returns).prod(axis=1, min_count=end_lag - start_lag + 1) - 1


def build_monthly_character(db, character):
    crsp = load_crsp_monthly(db)
    crsp = crsp[crsp["ret"].notna()].copy()
    crsp["return_count"] = crsp.groupby("permno").cumcount() + 1
    crsp["me"] = np.log(crsp.groupby("permno")["market_equity"].shift(1))
    crsp["mvel1"] = crsp["me"]
    crsp["mom1m"] = crsp.groupby("permno")["ret"].shift(1)
    crsp["mom6m"] = rolling_return_product(crsp, 2, 6)
    crsp["mom12m"] = rolling_return_product(crsp, 2, 12)
    crsp["mom36m"] = rolling_return_product(crsp, 13, 36)
    crsp["mom60m"] = rolling_return_product(crsp, 13, 60)
    crsp["seas1a"] = crsp.groupby("permno")["ret"].shift(11)
    crsp.loc[crsp["return_count"] == 1, "mom1m"] = np.nan
    crsp.loc[crsp["return_count"] < 7, "mom6m"] = np.nan
    crsp.loc[crsp["return_count"] < 13, "mom12m"] = np.nan
    crsp.loc[crsp["return_count"] < 37, "mom36m"] = np.nan
    crsp.loc[crsp["return_count"] < 61, "mom60m"] = np.nan
    crsp.loc[crsp["return_count"] < 12, "seas1a"] = np.nan
    crsp["dolvol"] = np.log(
        crsp.groupby("permno")["vol"].shift(2) * crsp.groupby("permno")["prc_abs"].shift(2)
    )
    vol_lags = [crsp.groupby("permno")["vol"].shift(i) for i in range(1, 4)]
    crsp["turn"] = pd.concat(vol_lags, axis=1).mean(axis=1) / crsp["shrout"]

    crsp = crsp.rename(columns={"siccd": "sic"})
    crsp = crsp[crsp[character].replace([np.inf, -np.inf], np.nan).notna()].copy()
    if character in {"mom36m", "mom60m"} and crsp[character].nunique(dropna=True) == 1:
        only_value = crsp[character].dropna().iloc[0]
        if np.isclose(only_value, -1):
            raise ValueError(
                f"{character} is degenerate at -1. Recheck the long-horizon momentum input returns."
            )
    return crsp[
        ["permno", "permco", "date", "signal_yyyymm", "target_yyyymm", "sic", "exchcd", "shrcd", character]
    ]


def load_daily_monthly(db):
    daily = db.raw_sql("""
        SELECT permno,
               DATE_TRUNC('month', date)::date AS month_start,
               MAX(ret) AS maxret,
               STDDEV_SAMP(ret) AS rvar_mean,
               AVG((askhi - bidlo) / NULLIF(((askhi + bidlo) / 2), 0)) AS baspread,
               STDDEV_SAMP(LOG(NULLIF(ABS(prc * vol), 0))) AS std_dolvol,
               STDDEV_SAMP(vol / NULLIF(shrout, 0)) AS std_turn,
               AVG(ABS(ret) / NULLIF(ABS(prc) * vol, 0)) AS ill,
               SUM(CASE WHEN vol = 0 THEN 1 ELSE 0 END)::double precision AS countzero,
               COUNT(*)::double precision AS ndays,
               SUM(vol / NULLIF(shrout, 0))::double precision AS turn_sum
        FROM crsp.dsf
        GROUP BY permno, DATE_TRUNC('month', date)::date
    """)
    daily["month_start"] = pd.to_datetime(daily["month_start"])
    daily["source_yyyymm"] = daily["month_start"].dt.year * 100 + daily["month_start"].dt.month
    daily["zerotrade"] = (daily["countzero"] + ((1 / daily["turn_sum"]) / 480000)) * 21 / daily["ndays"]
    return daily


def build_daily_monthly_character(db, character):
    daily = load_daily_monthly(db)
    monthly = load_crsp_monthly(db)[
        ["permno", "permco", "date", "signal_yyyymm", "target_yyyymm", "siccd", "exchcd", "shrcd"]
    ].rename(columns={"siccd": "sic"})
    monthly["source_yyyymm"] = monthly.groupby("permno")["signal_yyyymm"].shift(1)
    out = monthly.merge(daily[["permno", "source_yyyymm", character]], on=["permno", "source_yyyymm"], how="left")
    out = out[out[character].replace([np.inf, -np.inf], np.nan).notna()].copy()
    return out[["permno", "permco", "date", "signal_yyyymm", "target_yyyymm", "sic", "exchcd", "shrcd", character]]


def build_character(db, character, ccm_linktypes=None, ccm_linkprim=None):
    if character in ANNUAL_CHARACTER_INFO:
        return build_annual_character(db, character, ccm_linktypes, ccm_linkprim)
    if character in MONTHLY_CHARACTER_INFO:
        return build_monthly_character(db, character)
    if character in DAILY_MONTHLY_CHARACTER_INFO:
        return build_daily_monthly_character(db, character)

    from _shared.quarterly_builders import QUARTERLY_CHARACTER_INFO, build_quarterly_character

    if character in QUARTERLY_CHARACTER_INFO:
        return build_quarterly_character(db, character, ccm_linktypes, ccm_linkprim)
    if character == "beta":
        from _shared.beta_builder import build_beta_character

        return build_beta_character(db)
    if character == "abr":
        from _shared.event_builders import build_abr_character

        return build_abr_character(db, ccm_linktypes, ccm_linkprim)
    if character == "re":
        from _shared.ibes_builders import build_re_character

        return build_re_character(db)
    if character in PLANNED_CHARACTERS:
        raise NotImplementedError(
            f"{character} needs an additional specialized data source or event-time routine. "
            f"Note: {PLANNED_CHARACTERS[character]}"
        )
    raise ValueError(f"Unknown character: {character}")


def run_character_cli(character, description):
    parser = argparse.ArgumentParser(description=f"Build {character}: {description}.")
    parser.add_argument("--wrds-user", default=None)
    parser.add_argument("--output", default=f"{character}.csv")
    add_ccm_arguments(parser)
    args = parser.parse_args()

    db = connect_wrds(args.wrds_user)
    try:
        out = build_character(db, character, args.ccm_linktypes, args.ccm_linkprim)
    finally:
        db.close()

    output_path = Path(args.output)
    if not output_path.is_absolute():
        output_path = OUTPUT_DIR / output_path
    output_path.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(output_path, index=False)
    print(f"Saved {character} to: {output_path.resolve()}")
    print(f"Rows: {len(out):,}")
