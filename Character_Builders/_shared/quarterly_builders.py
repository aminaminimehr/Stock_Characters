import argparse

from pathlib import Path



import numpy as np

import pandas as pd



from _shared.ccm import (

    add_ccm_arguments,

    attach_ccm_links_green,

    load_ccm_links_green,

)

from _shared.green_builders import (

    OUTPUT_DIR,

    connect_wrds,

    load_crsp_monthly,

    raw_sql_with_retry,

)

from output_paths import sql_date_filter

from _shared.sas_stats import rolling_sas_std





PROJECT_ROOT = Path(__file__).resolve().parents[2]



QUARTERLY_CHARACTER_INFO = {

    "chtx": "Change in tax expense scaled by lagged assets",

    "cinvest": "Corporate investment",

    "ni": "Net stock issues",

    "nincr": "Number of consecutive quarterly earnings increases",

    "rna": "Return on net operating assets",

    "roaq": "Return on assets (quarterly)",

    "roeq": "Return on equity (quarterly)",

    "rsup": "Revenue surprise",

    "sue": "Unexpected quarterly earnings",

    "cash": "Cash holdings (quarterly Compustat)",

    "stdacc": "Accrual volatility",

    "stdcf": "Cash-flow volatility",

    "roavol": "Earnings volatility",

}

QUARTERLY_ID_COLUMNS = ["permno", "permco", "gvkey", "datadate", "sic", "fyearq", "fqtr"]



_MONTHLY_CRSP_PANEL = None



# SAS Greens_code.sas L768
QUARTERLY_MONTH_START_LAG = -10
QUARTERLY_MONTH_END_LAG = -5





def get_monthly_crsp_panel(db):

    global _MONTHLY_CRSP_PANEL

    if _MONTHLY_CRSP_PANEL is None:

        _MONTHLY_CRSP_PANEL = load_crsp_monthly(db)[

            ["permno", "permco", "date", "signal_yyyymm", "target_yyyymm", "siccd", "exchcd", "shrcd"]

        ].rename(columns={"siccd": "sic"})

    return _MONTHLY_CRSP_PANEL





def intnx_month(ts: pd.Series, n: int, alignment: str = "end") -> pd.Series:

    shifted = pd.to_datetime(ts) + pd.DateOffset(months=n)

    if alignment == "beg":

        return shifted.dt.to_period("M").dt.to_timestamp("s")

    return shifted.dt.to_period("M").dt.to_timestamp("h")





def _bool_to_int(left: pd.Series, right: pd.Series) -> pd.Series:

    return left.gt(right).fillna(False).astype(int)





def load_quarterly_compustat(db):

    comp = raw_sql_with_retry(db, f"""
        SELECT c.gvkey,

               SUBSTR(REPLACE(f.cusip, ' ', ''), 1, 6) AS cusip6,

               f.datadate, f.fyearq, f.fqtr, f.rdq,

               SUBSTR(c.sic, 1, 2) AS sic2,

               c.sic,

               f.ibq, f.saleq, f.txtq, f.revtq, f.cogsq, f.xsgaq, f.xintq,

               f.atq, f.actq, f.cheq, f.lctq, f.dlcq, f.dlttq, f.ppentq,

               f.ceqq, f.seqq, f.pstkq, f.pstkrq, f.ltq,

               ABS(f.prccq) AS prccq,

               ABS(f.prccq) * f.cshoq AS mveq,

               f.cshoq, f.oiadpq, f.epspxq, f.ajexq,

               f.rectq, f.invtq, f.acoq, f.intanq, f.aoq, f.apq, f.lcoq, f.loq, f.dpq

        FROM comp.company AS c

        JOIN comp.fundq AS f

          ON c.gvkey = f.gvkey

        WHERE f.indfmt = 'INDL'

          AND f.datafmt = 'STD'

          AND f.popsrc = 'D'

          AND f.consol = 'C'

          AND f.ibq IS NOT NULL

          AND f.datadate >= DATE '1975-01-01'

          AND {sql_date_filter("f.datadate")}

    """)

    comp["datadate"] = pd.to_datetime(comp["datadate"])

    comp["rdq"] = pd.to_datetime(comp["rdq"], errors="coerce")

    comp = (

        comp.sort_values(["gvkey", "datadate"])

        .drop_duplicates(["gvkey", "datadate"], keep="first")

        .sort_values(["gvkey", "datadate"])

    )

    return comp





def load_quarterly_ibes(db):

    return raw_sql_with_retry(db, """

        SELECT SUBSTR(REPLACE(cusip, ' ', ''), 1, 6) AS cusip6,

               fpedats, statpers, medest, actual

        FROM ibes.statsum_epsus

        WHERE fpi = '6'

          AND statpers < anndats_act

          AND measure = 'EPS'

          AND medest IS NOT NULL

          AND fpedats IS NOT NULL

          AND (fpedats - statpers) >= 0

    """)





def attach_ibes_to_quarterly(comp, ibes):

    ibes = ibes.copy()

    ibes["fpedats"] = pd.to_datetime(ibes["fpedats"])

    ibes = (

        ibes.sort_values(["cusip6", "fpedats", "statpers"], ascending=[True, True, False])

        .drop_duplicates(["cusip6", "fpedats"], keep="first")

    )

    return comp.merge(ibes, left_on=["cusip6", "datadate"], right_on=["cusip6", "fpedats"], how="left")





def compute_quarterly_characters(comp):

    """Green SAS quarterly characteristics (Greens_code.sas L567-641)."""

    df = comp.copy().reset_index(drop=True)

    g = df.groupby("gvkey", sort=False)

    df["count"] = g.cumcount() + 1



    df["pstk"] = np.where(df["pstkrq"].notna(), df["pstkrq"], df["pstkq"])

    scal = df["seqq"].copy()
    scal = scal.fillna(df["ceqq"] + df["pstk"])
    need_at = scal.isna() & (df["ceqq"].isna() | df["pstk"].isna())
    scal = scal.where(~need_at, df["atq"] - df["ltq"])
    df["scal"] = scal



    lag_atq = g["atq"].shift(1)

    lag4_atq = g["atq"].shift(4)

    lag4_txtq = g["txtq"].shift(4)

    lag4_saleq = g["saleq"].shift(4)

    lag_scal = g["scal"].shift(1)



    df["chtx"] = (df["txtq"] - lag4_txtq) / lag4_atq

    df["roaq"] = df["ibq"] / lag_atq

    df["roeq"] = df["ibq"] / lag_scal

    df["rsup"] = (df["saleq"] - lag4_saleq) / df["mveq"]

    df["cash_q"] = df["cheq"] / df["atq"]



    sacc_num = (df["actq"] - g["actq"].shift(1) - (df["cheq"] - g["cheq"].shift(1))) - (

        (df["lctq"] - g["lctq"].shift(1)) - (df["dlcq"] - g["dlcq"].shift(1))

    )

    df["sacc"] = sacc_num / df["saleq"]

    df.loc[df["saleq"] <= 0, "sacc"] = sacc_num / 0.01



    std_lags = list(range(1, 16))

    df["stdacc"] = rolling_sas_std(df, "sacc", std_lags)

    # Green SAS nulls sgrvol/roavol when n < 8 (L268): both variables use exactly
    # 8 quarterly values (current quarter + 7 lags).  Using more lags contaminates
    # the std estimate for firms in the early part of our download window.
    df["sgrvol"] = rolling_sas_std(df, "rsup", list(range(1, 8)))

    df["roavol"] = rolling_sas_std(df, "roaq", list(range(1, 8)))



    df["scf"] = (df["ibq"] / df["saleq"]) - df["sacc"]

    df.loc[df["saleq"] <= 0, "scf"] = (df["ibq"] / 0.01) - df["sacc"]

    df["stdcf"] = rolling_sas_std(df, "scf", std_lags)



    ppent_chg = (df["ppentq"] - g["ppentq"].shift(1)) / df["saleq"]

    ind_mean = (

        (g["ppentq"].shift(1) - g["ppentq"].shift(2)) / g["saleq"].shift(1)

        + (g["ppentq"].shift(2) - g["ppentq"].shift(3)) / g["saleq"].shift(2)

        + (g["ppentq"].shift(3) - g["ppentq"].shift(4)) / g["saleq"].shift(3)

    ) / 3

    df["cinvest"] = ppent_chg - ind_mean

    bad_sale = df["saleq"] <= 0

    df.loc[bad_sale, "cinvest"] = (

        (df["ppentq"] - g["ppentq"].shift(1)) / 0.01

        - (

            (g["ppentq"].shift(1) - g["ppentq"].shift(2)) / 0.01

            + (g["ppentq"].shift(2) - g["ppentq"].shift(3)) / 0.01

            + (g["ppentq"].shift(3) - g["ppentq"].shift(4)) / 0.01

        )

        / 3

    )



    ibq = df["ibq"]

    l1, l2, l3, l4 = g["ibq"].shift(1), g["ibq"].shift(2), g["ibq"].shift(3), g["ibq"].shift(4)

    l5, l6, l7, l8 = g["ibq"].shift(5), g["ibq"].shift(6), g["ibq"].shift(7), g["ibq"].shift(8)

    b01 = _bool_to_int(ibq, l1)

    b12 = _bool_to_int(l1, l2)

    b23 = _bool_to_int(l2, l3)

    b34 = _bool_to_int(l3, l4)

    b45 = _bool_to_int(l4, l5)

    b56 = _bool_to_int(l5, l6)

    b67 = _bool_to_int(l6, l7)

    b78 = _bool_to_int(l7, l8)

    df["nincr"] = (

        b01

        + b01 * b12

        + b01 * b12 * b23

        + b01 * b12 * b23 * b34

        + b01 * b12 * b23 * b34 * b45

        + b01 * b12 * b23 * b34 * b45 * b56

        + b01 * b12 * b23 * b34 * b45 * b56 * b67

        + b01 * b12 * b23 * b34 * b45 * b56 * b67 * b78

    )



    shares = df["cshoq"] * df["ajexq"]

    lag_shares = g["cshoq"].shift(4) * g["ajexq"].shift(4)

    df["ni"] = np.log(shares.replace(0, np.nan)) - np.log(lag_shares.replace(0, np.nan))



    df["che"] = df["ibq"] - g["ibq"].shift(4)

    df["sue"] = df["che"] / df["mveq"]



    operating_assets = df["atq"] - df["cheq"]

    operating_liabilities = (

        df["atq"] - df["dlcq"].fillna(0) - df["dlttq"].fillna(0) - df["pstk"] - df["ceqq"]

    )

    df["noa_level"] = operating_assets - operating_liabilities

    df["rna"] = df["oiadpq"] / g["noa_level"].shift(4)



    # Green SAS L268: if n<8 then do; roavol=.; sgrvol=.; end;
    # Null BEFORE computing medians so that early-history firms are excluded from
    # the industry median (matching SAS proc means / proc sql behaviour).
    df.loc[df["count"] < 8, ["roavol", "sgrvol"]] = np.nan

    med = df.groupby(["fyearq", "fqtr", "sic2"], dropna=False)[["roavol", "sgrvol"]].transform("median")

    med.columns = ["md_roavol", "md_sgrvol"]

    df = pd.concat([df, med], axis=1)

    # SAS comparison semantics: SAS treats missing (.) as −∞, so
    #   missing < non_missing  →  TRUE  →  m7 = 1
    # Replicate: when roavol is NaN but industry median is available, m7=1.
    df["m7"] = np.where(
        df["roavol"].isna() & df["md_roavol"].notna(),
        1,
        np.where(df["roavol"].lt(df["md_roavol"]).fillna(False), 1, 0),
    )
    df["m8"] = np.where(
        df["sgrvol"].isna() & df["md_sgrvol"].notna(),
        1,
        np.where(df["sgrvol"].lt(df["md_sgrvol"]).fillna(False), 1, 0),
    )



    df.loc[df.groupby("gvkey").head(1).index, ["roaq", "roeq"]] = np.nan

    df.loc[df["count"] < 5, ["chtx", "che", "cinvest"]] = np.nan

    df.loc[df["count"] < 5, "ni"] = np.nan

    df.loc[df["count"] < 17, ["stdacc", "stdcf"]] = np.nan
    # roavol/sgrvol already nulled at count < 8 above (kept null in output)



    return df





def expand_quarterly_columns_to_monthly(
    db,
    quarterly,
    characters: list[str],
    *,
    require_rdq: bool = True,
    require_values: bool = True,
):
    """Map quarterly fiscal rows to CRSP months (Greens_code.sas L768).

    When multiple ``characters`` are requested, all values come from the same
    picked ``datadate`` (latest quarter in the availability window).
    """
    characters = list(characters)
    base_cols = ["permno", "permco", "date", "signal_yyyymm", "target_yyyymm", "sic", "exchcd", "shrcd"]
    empty = pd.DataFrame(columns=base_cols + characters)

    monthly = get_monthly_crsp_panel(db)[base_cols].copy()
    monthly["date"] = pd.to_datetime(monthly["date"])
    monthly["permno"] = pd.to_numeric(monthly["permno"], errors="coerce").astype("int64")
    monthly = monthly.drop_duplicates(["permno", "date"], keep="last")

    qcols = ["permno", "datadate", "rdq", *characters]
    q = quarterly[qcols].copy()
    q["permno"] = pd.to_numeric(q["permno"], errors="coerce").astype("int64")
    q["datadate"] = pd.to_datetime(q["datadate"])
    q["rdq"] = pd.to_datetime(q["rdq"], errors="coerce")
    if require_rdq:
        q = q[q["rdq"].notna()].copy()
    if require_values and len(characters) == 1:
        char = characters[0]
        q = q[q[char].replace([np.inf, -np.inf], np.nan).notna()].copy()
    if q.empty:
        return empty

    parts: list[pd.DataFrame] = []
    q_by_permno = {int(p): grp.sort_values("datadate") for p, grp in q.groupby("permno", sort=False)}

    for permno, m_grp in monthly.groupby("permno", sort=False):
        q_grp = q_by_permno.get(int(permno))
        if q_grp is None or q_grp.empty:
            continue

        m_grp = m_grp.sort_values("date").copy()
        win_start = intnx_month(m_grp["date"], QUARTERLY_MONTH_START_LAG, "end")
        win_end = intnx_month(m_grp["date"], QUARTERLY_MONTH_END_LAG, "beg")
        q_dates = q_grp["datadate"].to_numpy(dtype="datetime64[ns]")
        picked = {char: np.full(len(m_grp), np.nan, dtype=float) for char in characters}

        for i, (ws, we) in enumerate(zip(win_start.to_numpy(), win_end.to_numpy())):
            in_window = (q_dates >= ws) & (q_dates <= we)
            if not in_window.any():
                continue
            pick_idx = np.where(in_window)[0][-1]
            for char in characters:
                val = q_grp.iloc[pick_idx][char]
                picked[char][i] = float(val) if pd.notna(val) else np.nan

        valid = np.ones(len(m_grp), dtype=bool)
        if require_values:
            valid = np.isfinite(np.column_stack([picked[c] for c in characters])).all(axis=1)
        if not valid.any():
            continue

        part = m_grp.loc[valid].copy()
        for char in characters:
            part[char] = picked[char][valid]
        parts.append(part)

    if not parts:
        return empty
    return pd.concat(parts, ignore_index=True)[base_cols + characters]


def expand_quarterly_to_monthly(db, quarterly, character, *, require_rdq: bool = True):
    return expand_quarterly_columns_to_monthly(
        db,
        quarterly,
        [character],
        require_rdq=require_rdq,
        require_values=True,
    )


def prepare_quarterly_compustat_panel(db, ccm_linktypes=None, ccm_linkprim=None, use_ibes=True):

    _ = ccm_linktypes, ccm_linkprim

    comp = load_quarterly_compustat(db)

    if use_ibes:

        try:

            ibes = load_quarterly_ibes(db)

            comp = attach_ibes_to_quarterly(comp, ibes)

        except Exception:

            comp["medest"] = np.nan

            comp["actual"] = np.nan

    else:

        comp["medest"] = np.nan

        comp["actual"] = np.nan



    comp = compute_quarterly_characters(comp)

    comp = attach_ccm_links_green(comp, load_ccm_links_green(db))

    return comp[comp["permno"].notna()].copy()





def build_quarterly_character(

    db, character, ccm_linktypes=None, ccm_linkprim=None, use_ibes=True, comp=None

):

    if comp is None:

        comp = prepare_quarterly_compustat_panel(

            db, ccm_linktypes, ccm_linkprim, use_ibes=use_ibes

        )

    value_col = "cash_q" if character == "cash" else character

    monthly = expand_quarterly_to_monthly(db, comp, value_col)

    if character == "cash":

        monthly = monthly.rename(columns={"cash_q": "cash"})

    return monthly





def run_quarterly_cli(character, description):

    parser = argparse.ArgumentParser(description=f"Build {character}: {description}.")

    parser.add_argument("--wrds-user", default=None)

    parser.add_argument("--output", default=f"{character}.csv")

    add_ccm_arguments(parser)

    args = parser.parse_args()



    db = connect_wrds(args.wrds_user)

    try:

        out = build_quarterly_character(

            db, character, args.ccm_linktypes, args.ccm_linkprim

        )

    finally:

        db.close()



    output_path = Path(args.output)

    if not output_path.is_absolute():

        output_path = OUTPUT_DIR / output_path

    output_path.parent.mkdir(parents=True, exist_ok=True)

    out.to_csv(output_path, index=False)

    print(f"Saved {character} to: {output_path.resolve()}")

    print(f"Rows: {len(out):,}")


