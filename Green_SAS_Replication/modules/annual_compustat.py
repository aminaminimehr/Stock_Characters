"""Annual Compustat extraction and characteristic construction (Greens_code.sas L39-398)."""
from __future__ import annotations

import numpy as np
import pandas as pd
import wrds

from config import ANNUAL_OUTPUT_COLS, CPI_BY_YEAR
from wrds_utils import month_end, retry_wrds_query, sql_between_date


ANNUAL_RAW_SQL = """
SELECT
    SUBSTR(REPLACE(f.cusip, ' ', ''), 1, 6) AS cnum,
    c.gvkey,
    f.datadate,
    f.fyear,
    c.cik,
    SUBSTR(c.sic, 1, 2) AS sic2,
    c.sic,
    c.naics,
    f.sale, f.revt, f.cogs, f.xsga, f.dp, f.xrd, f.xad, f.ib, f.ebitda, f.ebit, f.nopi, f.spi,
    f.pi, f.txp, f.ni, f.txfed, f.txfo, f.txt, f.xint,
    f.capx, f.oancf, f.dvt, f.ob, f.gdwlia, f.gdwlip, f.gwo,
    f.rect, f.act, f.che, f.ppegt, f.invt, f.at, f.aco, f.intan, f.ao, f.ppent, f.gdwl,
    f.fatb, f.fatl,
    f.lct, f.dlc, f.dltt, f.lt, f.dm, f.dcvt, f.cshrc, f.dcpstk, f.pstk, f.ap, f.lco, f.lo,
    f.drc, f.drlt, f.txdi,
    f.ceq, f.scstkc, f.emp, f.csho,
    ABS(f.prcc_f) AS prcc_f,
    f.csho * ABS(f.prcc_f) AS mve_f
FROM comp.company AS c
INNER JOIN comp.funda AS f ON f.gvkey = c.gvkey
WHERE NOT f.at IS NULL
  AND NOT f.prcc_f IS NULL
  AND NOT f.ni IS NULL
  AND f.datadate >= '1975-01-01'
  AND f.indfmt = 'INDL'
  AND f.datafmt = 'STD'
  AND f.popsrc = 'D'
  AND f.consol = 'C'
"""


def _tax_rate(fyear: pd.Series) -> pd.Series:
    tr = pd.Series(np.nan, index=fyear.index, dtype=float)
    tr = tr.mask(fyear <= 1978, 0.48)
    tr = tr.mask((fyear >= 1979) & (fyear <= 1986), 0.46)
    tr = tr.mask(fyear == 1987, 0.40)
    tr = tr.mask((fyear >= 1988) & (fyear <= 1992), 0.34)
    tr = tr.mask(fyear >= 1993, 0.35)
    return tr


def _accrual_fallback(df: pd.DataFrame) -> pd.Series:
  g = df.groupby("gvkey", sort=False)
  act = df["act"]
  che = df["che"]
  lct = df["lct"]
  dlc = df["dlc"]
  txp = df["txp"]
  dp = df["dp"]
  return (
      (act - g["act"].shift(1) - (che - g["che"].shift(1)))
      - ((lct - g["lct"].shift(1)) - (dlc - g["dlc"].shift(1)) - (txp - g["txp"].shift(1)) - dp)
  )


def fetch_annual_compustat(db: wrds.Connection, sample_start: str | None, sample_end: str | None) -> pd.DataFrame:
    date_filter = sql_between_date("f.datadate", sample_start, sample_end)
    sql = ANNUAL_RAW_SQL
    if date_filter != "1=1":
        sql = sql.replace("AND f.consol = 'C'", f"AND f.consol = 'C'\n  AND {date_filter}")
    df = retry_wrds_query(db, lambda conn: conn.raw_sql(sql))
    df["datadate"] = pd.to_datetime(df["datadate"])
    df = df.sort_values(["gvkey", "datadate"]).drop_duplicates(["gvkey", "datadate"], keep="first")
    return df


def build_annual_characteristics(raw: pd.DataFrame) -> pd.DataFrame:
    """Replicate SAS data -> data2 -> orgcap pipeline."""
    df = raw.copy()
    for col in df.columns:
        if col in {"gvkey", "cnum", "sic", "sic2", "naics", "splticrm", "datadate"}:
            continue
        df[col] = pd.to_numeric(df[col], errors="coerce")
    g = df.groupby("gvkey", sort=False)

    df["count"] = g.cumcount() + 1

    # L88-100 cleanup
    df["dr"] = np.nan
    both = df["drc"].notna() & df["drlt"].notna()
    df.loc[both, "dr"] = df.loc[both, "drc"] + df.loc[both, "drlt"]
    df.loc[df["drc"].notna() & df["drlt"].isna(), "dr"] = df.loc[df["drc"].notna() & df["drlt"].isna(), "drc"]
    df.loc[df["drlt"].notna() & df["drc"].isna(), "dr"] = df.loc[df["drlt"].notna() & df["drc"].isna(), "drlt"]

    df["dc"] = np.nan
    m1 = df["dcvt"].isna() & df["dcpstk"].notna() & df["pstk"].notna() & (df["dcpstk"] > df["pstk"])
    df.loc[m1, "dc"] = df.loc[m1, "dcpstk"] - df.loc[m1, "pstk"]
    m2 = df["dcvt"].isna() & df["dcpstk"].notna() & df["pstk"].isna()
    df.loc[m2, "dc"] = df.loc[m2, "dcpstk"]
    df.loc[df["dc"].isna(), "dc"] = df.loc[df["dc"].isna(), "dcvt"].astype(float)

    df["xint0"] = df["xint"].fillna(0)
    df["xsga0"] = df["xsga"].fillna(0)

    lag_at = g["at"].shift(1)
    lag_ceq = g["ceq"].shift(1)
    lag_lt = g["lt"].shift(1)
    lag_csho = g["csho"].shift(1)
    lag_sale = g["sale"].shift(1)
    lag_ib = g["ib"].shift(1)
    lag_invt = g["invt"].shift(1)
    lag_rect = g["rect"].shift(1)
    lag_cogs = g["cogs"].shift(1)
    lag_xsga = g["xsga"].shift(1)
    lag_xad = g["xad"].shift(1)
    lag_ppegt = g["ppegt"].shift(1)
    lag_ppent = g["ppent"].shift(1)
    lag_capx = g["capx"].shift(1)
    lag_gdwl = g["gdwl"].shift(1)
    lag_emp = g["emp"].shift(1)
    lag_ob = g["ob"].shift(1)
    lag_dr = g["dr"].shift(1)
    lag_xrd = g["xrd"].shift(1)
    lag2_at = g["at"].shift(2)
    lag2_capx = g["capx"].shift(2)
    lag2_sale = g["sale"].shift(2)
    lag_act = g["act"].shift(1)
    lag_che = g["che"].shift(1)
    lag_lct = g["lct"].shift(1)
    lag_dlc = g["dlc"].shift(1)
    lag_txp = g["txp"].shift(1)
    lag_dltt = g["dltt"].shift(1)
    lag_ni = g["ni"].shift(1)
    lag_ap = g["ap"].shift(1)
    lag_lco = g["lco"].shift(1)
    lag_lo = g["lo"].shift(1)
    lag_aco = g["aco"].shift(1)
    lag_intan = g["intan"].shift(1)
    lag_ao = g["ao"].shift(1)
    lag_dp = g["dp"].shift(1)
    lag_ppent_d = g["ppent"].shift(1)

    avg_at = (df["at"] + lag_at) / 2

    acc_fb = _accrual_fallback(df)
    df["bm"] = df["ceq"] / df["mve_f"]
    df["ep"] = df["ib"] / df["mve_f"]
    df["cashpr"] = (df["mve_f"] + df["dltt"] - df["at"]) / df["che"]
    df["dy"] = df["dvt"] / df["mve_f"]
    df["lev"] = df["lt"] / df["mve_f"]
    df["sp"] = df["sale"] / df["mve_f"]
    df["roic"] = (df["ebit"] - df["nopi"]) / (df["ceq"] + df["lt"] - df["che"])
    df["rd_sale"] = df["xrd"] / df["sale"]
    df["rd_mve"] = df["xrd"] / df["mve_f"]
    df["agr"] = df["at"] / lag_at - 1
    df["gma"] = (df["revt"] - df["cogs"]) / lag_at
    df["chcsho"] = df["csho"] / lag_csho - 1
    df["lgr"] = df["lt"] / lag_lt - 1

    df["acc"] = (df["ib"] - df["oancf"]) / avg_at
    df.loc[df["oancf"].isna(), "acc"] = acc_fb / avg_at

    df["pctacc"] = (df["ib"] - df["oancf"]) / df["ib"].abs()
    df.loc[df["ib"] == 0, "pctacc"] = (df.loc[df["ib"] == 0, "ib"] - df.loc[df["ib"] == 0, "oancf"]) / 0.01
    miss_oancf = df["oancf"].isna()
    df.loc[miss_oancf, "pctacc"] = acc_fb / df.loc[miss_oancf, "ib"].abs()
    df.loc[miss_oancf & (df["ib"] == 0), "pctacc"] = acc_fb / 0.01

    cfp_fb = (df["ib"] - acc_fb) / df["mve_f"]
    df["cfp"] = cfp_fb
    df.loc[df["oancf"].notna(), "cfp"] = df.loc[df["oancf"].notna(), "oancf"] / df.loc[df["oancf"].notna(), "mve_f"]

    df["absacc"] = df["acc"].abs()
    df["age"] = df["count"]
    df["chinv"] = (df["invt"] - lag_invt) / avg_at
    df["spii"] = np.where((df["spi"] != 0) & df["spi"].notna(), 1, 0)
    df["spi"] = df["spi"] / avg_at
    df["cf"] = df["oancf"] / avg_at
    df.loc[df["oancf"].isna(), "cf"] = (df["ib"] - acc_fb) / avg_at

    df["hire"] = (df["emp"] - lag_emp) / lag_emp
    df.loc[df["emp"].isna() | lag_emp.isna(), "hire"] = 0

    df["sgr"] = df["sale"] / lag_sale - 1
    df["chpm"] = (df["ib"] / df["sale"]) - (lag_ib / lag_sale)
    df["chato"] = (df["sale"] / avg_at) - (lag_sale / ((lag_at + lag2_at) / 2))
    df["pchsale_pchinvt"] = (df["sale"] - lag_sale) / lag_sale - (df["invt"] - lag_invt) / lag_invt
    df["pchsale_pchrect"] = (df["sale"] - lag_sale) / lag_sale - (df["rect"] - lag_rect) / lag_rect
    df["pchgm_pchsale"] = (
        ((df["sale"] - df["cogs"]) - (lag_sale - lag_cogs)) / (lag_sale - lag_cogs)
        - (df["sale"] - lag_sale) / lag_sale
    )
    df["pchsale_pchxsga"] = (df["sale"] - lag_sale) / lag_sale - (df["xsga"] - lag_xsga) / lag_xsga
    df["depr"] = df["dp"] / df["ppent"]
    df["pchdepr"] = ((df["dp"] / df["ppent"]) - (lag_dp / lag_ppent_d)) / (lag_dp / lag_ppent_d)
    df["chadv"] = np.log1p(df["xad"]) - np.log1p(lag_xad)

    df["invest"] = ((df["ppegt"] - lag_ppegt) + (df["invt"] - lag_invt)) / lag_at
    df.loc[df["ppegt"].isna(), "invest"] = ((df["ppent"] - lag_ppent) + (df["invt"] - lag_invt)) / lag_at

    df["egr"] = (df["ceq"] - lag_ceq) / lag_ceq
    df.loc[df["capx"].isna() & (df["count"] >= 2), "capx"] = df["ppent"] - lag_ppent
    df["pchcapx"] = (df["capx"] - lag_capx) / lag_capx
    df["grcapx"] = (df["capx"] - lag2_capx) / lag2_capx
    df["grGW"] = (df["gdwl"] - lag_gdwl) / lag_gdwl
    df.loc[df["gdwl"].isna() | (df["gdwl"] == 0), "grGW"] = 0
    df.loc[(df["gdwl"] != 0) & df["gdwl"].notna() & df["grGW"].isna(), "grGW"] = 1

    wo = (
        (df["gdwlia"].notna() & (df["gdwlia"] != 0))
        | (df["gdwlip"].notna() & (df["gdwlip"] != 0))
        | (df["gwo"].notna() & (df["gwo"] != 0))
    )
    df["woGW"] = np.where(wo, 1, 0)
    df["tang"] = (df["che"] + df["rect"] * 0.715 + df["invt"] * 0.547 + df["ppent"] * 0.535) / df["at"]

    sic = pd.to_numeric(df["sic"], errors="coerce")
    sin_naics = df["naics"].astype(str).isin(
        ["7132", "71312", "713210", "71329", "713290", "72112", "721120"]
    )
    df["sin"] = np.where(
        ((sic >= 2100) & (sic <= 2199))
        | ((sic >= 2080) & (sic <= 2085))
        | sin_naics,
        1,
        0,
    )

    df.loc[df["act"].isna(), "act"] = df["che"] + df["rect"] + df["invt"]
    df.loc[df["lct"].isna(), "lct"] = df["ap"]
    df["currat"] = df["act"] / df["lct"]
    df["pchcurrat"] = ((df["act"] / df["lct"]) - (lag_act / lag_lct)) / (lag_act / lag_lct)
    df["quick"] = (df["act"] - df["invt"]) / df["lct"]
    df["pchquick"] = ((df["act"] - df["invt"]) / df["lct"] - (lag_act - lag_invt) / lag_lct) / (
        (lag_act - lag_invt) / lag_lct
    )
    df["salecash"] = df["sale"] / df["che"]
    df["salerec"] = df["sale"] / df["rect"]
    df["saleinv"] = df["sale"] / df["invt"]
    df["pchsaleinv"] = ((df["sale"] / df["invt"]) - (lag_sale / lag_invt)) / (lag_sale / lag_invt)
    df["cashdebt"] = (df["ib"] + df["dp"]) / ((df["lt"] + lag_lt) / 2)
    df["realestate"] = (df["fatb"] + df["fatl"]) / df["ppegt"]
    df.loc[df["ppegt"].isna(), "realestate"] = (df["fatb"] + df["fatl"]) / df["ppent"]

    lag_dvt = g["dvt"].shift(1)
    df["divi"] = np.where(
        (df["dvt"].notna() & (df["dvt"] > 0)) & (lag_dvt.isna() | (lag_dvt == 0)),
        1,
        0,
    )
    df["divo"] = np.where(
        ((df["dvt"].isna() | (df["dvt"] == 0)) & lag_dvt.notna() & (lag_dvt > 0)),
        1,
        0,
    )

    df["obklg"] = df["ob"] / avg_at
    df["chobklg"] = (df["ob"] - lag_ob) / avg_at
    df["securedind"] = np.where(df["dm"].notna() & (df["dm"] != 0), 1, 0)
    df["secured"] = df["dm"] / df["dltt"]
    convind = (df["dc"].notna() & (df["dc"] != 0)) | (df["cshrc"].notna() & (df["cshrc"] != 0))
    df["convind"] = np.where(convind, 1, 0)
    df["conv"] = df["dc"] / df["dltt"]

    noa = df["rect"] + df["invt"] + df["ppent"] + df["aco"] + df["intan"] + df["ao"] - df["ap"] - df["lco"] - df["lo"]
    lag_noa = lag_rect + lag_invt + lag_ppent + lag_aco + lag_intan + lag_ao - lag_ap - lag_lco - lag_lo
    df["grltnoa"] = (
        (noa - lag_noa)
        - (
            (df["rect"] - lag_rect)
            + (df["invt"] - lag_invt)
            + (df["aco"] - lag_aco)
            - ((df["ap"] - lag_ap) + (df["lco"] - lag_lco))
            - df["dp"]
        )
    ) / avg_at
    df["chdrc"] = (df["dr"] - lag_dr) / avg_at
    lag_xrd_at = (lag_xrd / lag_at).astype(float)
    rd_ratio = (((df["xrd"] / df["at"]) - lag_xrd_at) / lag_xrd_at).astype(float)
    df["rd"] = np.where(rd_ratio > 0.05, 1, 0)
    df["rdbias"] = (df["xrd"] / lag_xrd - 1) - df["ib"] / lag_ceq
    df["roe"] = df["ib"] / lag_ceq
    df["operprof"] = (df["revt"] - df["cogs"] - df["xsga0"] - df["xint0"]) / lag_ceq

    def _score(mask: pd.Series) -> pd.Series:
        return mask.fillna(False).astype(int)

    df["ps"] = (
        _score(df["ni"] > 0)
        + _score(df["oancf"] > 0)
        + _score((df["ni"] / df["at"]) > (lag_ni / lag_at))
        + _score(df["oancf"] > df["ni"])
        + _score((df["dltt"] / df["at"]) < (lag_dltt / lag_at))
        + _score((df["act"] / df["lct"]) > (lag_act / lag_lct))
        + _score(((df["sale"] - df["cogs"]) / df["sale"]) > ((lag_sale - lag_cogs) / lag_sale))
        + _score((df["sale"] / df["at"]) > (lag_sale / lag_at))
        + _score(df["scstkc"] == 0)
    )

    tr = _tax_rate(df["fyear"])
    df["tb_1"] = ((df["txfo"] + df["txfed"]) / tr) / df["ib"]
    df.loc[df["txfo"].isna() | df["txfed"].isna(), "tb_1"] = (
        (df["txt"] - df["txdi"]) / tr / df["ib"]
    )
    tax_cond = ((df["txfo"] + df["txfed"] > 0) | (df["txt"] > df["txdi"])) & (df["ib"] <= 0)
    df.loc[tax_cond, "tb_1"] = 1

    df["roa"] = df["ni"] / avg_at
    df["cfroa"] = df["oancf"] / avg_at
    df.loc[df["oancf"].isna(), "cfroa"] = (df["ib"] + df["dp"]) / avg_at
    df["xrdint"] = df["xrd"] / avg_at
    df["capxint"] = df["capx"] / avg_at
    df["xadint"] = df["xad"] / avg_at

    req_cols = [
        "chadv", "agr", "invest", "gma", "chcsho", "lgr", "egr", "chpm", "chinv", "hire", "cf", "acc",
        "pctacc", "absacc", "spi", "sgr", "pchsale_pchinvt", "pchsale_pchrect", "pchgm_pchsale",
        "pchsale_pchxsga", "pchcapx", "ps", "roa", "cfroa", "xrdint", "capxint", "xadint", "divi", "divo",
        "obklg", "chobklg", "grltnoa", "chdrc", "rd", "pchdepr", "grGW", "pchcurrat", "pchquick",
        "pchsaleinv", "roe", "operprof",
    ]
    df.loc[df["count"] == 1, req_cols] = np.nan
    df.loc[df["count"] < 3, ["chato", "grcapx"]] = np.nan

    # Industry adjustments L242-256
    grp = df.groupby(["sic2", "fyear"], dropna=False)
    df["chpmia"] = df["chpm"] - grp["chpm"].transform("mean")
    df["chatoia"] = df["chato"] - grp["chato"].transform("mean")
    df["indsale"] = grp["sale"].transform("sum")
    df["chempia"] = df["hire"] - grp["hire"].transform("mean")
    df["bm_ia"] = df["bm"] - grp["bm"].transform("mean")
    df["pchcapx_ia"] = df["pchcapx"] - grp["pchcapx"].transform("mean")
    df["tb"] = df["tb_1"] - grp["tb_1"].transform("mean")
    df["cfp_ia"] = df["cfp"] - grp["cfp"].transform("mean")
    df["mve_ia"] = df["mve_f"] - grp["mve_f"].transform("mean")
    share = df["sale"] / df["indsale"]
    df["herf"] = (share ** 2).groupby([df["sic2"], df["fyear"]]).transform("sum")

    # Mohanram medians L261-285
    med = df.groupby(["fyear", "sic2"], dropna=False)[["roa", "cfroa", "xrdint", "capxint", "xadint"]].transform(
        "median"
    )
    med.columns = ["md_roa", "md_cfroa", "md_xrdint", "md_capxint", "md_xadint"]
    df = pd.concat([df, med], axis=1)
    df["m1"] = np.where(df["roa"].gt(df["md_roa"]).fillna(False), 1, 0)
    df["m2"] = np.where(df["cfroa"].gt(df["md_cfroa"]).fillna(False), 1, 0)
    df["m3"] = np.where(df["oancf"].gt(df["ni"]).fillna(False), 1, 0)
    df["m4"] = np.where(df["xrdint"].gt(df["md_xrdint"]).fillna(False), 1, 0)
    df["m5"] = np.where(df["capxint"].gt(df["md_capxint"]).fillna(False), 1, 0)
    df["m6"] = np.where(df["xadint"].gt(df["md_xadint"]).fillna(False), 1, 0)

    df = df.sort_values(["gvkey", "datadate"]).drop_duplicates(["gvkey", "datadate"], keep="first")

    rating_map = {
        "D": 1, "C": 2, "CC": 3, "CCC-": 4, "CCC": 5, "CCC+": 6, "B-": 7, "B": 8, "B+": 9,
        "BB-": 10, "BB": 11, "BB+": 12, "BBB-": 13, "BBB": 14, "BBB+": 15, "A-": 16, "A": 17,
        "A+": 18, "AA-": 19, "AA": 20, "AA+": 21, "AAA": 22,
    }
    df["credrat"] = df["splticrm"].map(rating_map)
    lag_cred = df.groupby("gvkey", sort=False)["credrat"].shift(1)
    df["credrat_dwn"] = np.where(df["credrat"] < lag_cred, 1, 0)
    df.loc[df["count"] == 1, "credrat_dwn"] = 0

    # CPI / orgcap L347-398
    df["cpi"] = df["fyear"].map(CPI_BY_YEAR)

    def _orgcap_group(gdf: pd.DataFrame) -> pd.Series:
        prev = np.nan
        vals = []
        for i, row in gdf.iterrows():
            if row["count"] == 1:
                prev = (row["xsga"] / row["cpi"]) / 0.25 if pd.notna(row["cpi"]) and pd.notna(row["xsga"]) else np.nan
            elif pd.notna(row["xsga"]) and pd.notna(row["cpi"]):
                prev = prev * 0.85 + row["xsga"] / row["cpi"]
            vals.append(prev)
        return pd.Series(vals, index=gdf.index)

    df["orgcap_1"] = df.groupby("gvkey", sort=False, group_keys=False).apply(_orgcap_group)
    df["orgcap"] = df["orgcap_1"] / avg_at
    df.loc[df["count"] == 1, "orgcap"] = np.nan

    keep = [c for c in ANNUAL_OUTPUT_COLS if c in df.columns]
    return df[keep].copy()


def run_annual_compustat(
    db: wrds.Connection,
    sample_start: str | None = None,
    sample_end: str | None = None,
) -> pd.DataFrame:
    raw = fetch_annual_compustat(db, sample_start, sample_end)
    rates = retry_wrds_query(
        db,
        lambda conn: conn.raw_sql("SELECT gvkey, datadate, splticrm FROM comp.adsprate"),
    )
    rates["datadate"] = pd.to_datetime(rates["datadate"])
    rates["fyear"] = rates["datadate"].dt.year
    rates = rates.sort_values(["gvkey", "fyear", "datadate"]).drop_duplicates(["gvkey", "fyear"], keep="last")
    raw = raw.merge(rates[["gvkey", "fyear", "splticrm"]], on=["gvkey", "fyear"], how="left")
    return build_annual_characteristics(raw)
