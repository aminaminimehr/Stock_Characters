import argparse
from pathlib import Path

import numpy as np
import pandas as pd

from _shared.ccm import add_ccm_arguments, attach_ccm_links, load_ccm_links
from _shared.green_builders import (
    OUTPUT_DIR,
    connect_wrds,
    load_crsp_monthly,
    safe_divide,
)


PROJECT_ROOT = Path(__file__).resolve().parents[2]

QUARTERLY_CHARACTER_INFO = {
    "chtx": "Change in tax expense scaled by lagged assets",
    "cinvest": "Corporate investment",
    "ni": "Net stock issues",
    "nincr": "Number of consecutive quarterly earnings increases",
    "rna": "Return on net operating assets",
    "roa1": "Return on assets",
    "rsup": "Revenue surprise",
    "sue": "Unexpected quarterly earnings",
}

QUARTERLY_ID_COLUMNS = ["permno", "permco", "gvkey", "datadate", "sic", "fyearq", "fqtr"]

_MONTHLY_CRSP_PANEL = None


def get_monthly_crsp_panel(db):
    global _MONTHLY_CRSP_PANEL
    if _MONTHLY_CRSP_PANEL is None:
        _MONTHLY_CRSP_PANEL = load_crsp_monthly(db)[
            ["permno", "permco", "date", "signal_yyyymm", "target_yyyymm", "siccd", "exchcd", "shrcd"]
        ].rename(columns={"siccd": "sic"})
    return _MONTHLY_CRSP_PANEL


def lag_by_gvkey(df, column, periods=1):
    return df.groupby("gvkey")[column].shift(periods)


def load_quarterly_compustat(db):
    comp = db.raw_sql("""
        SELECT c.gvkey, SUBSTR(REPLACE(f.cusip, ' ', ''), 1, 6) AS cusip6, f.datadate, f.fyearq, f.fqtr, f.rdq, c.sic,
               f.ibq, f.saleq, f.txtq, f.revtq, f.cogsq, f.xsgaq, f.xintq,
               f.atq, f.actq, f.cheq, f.lctq, f.dlcq, f.dlttq, f.ppentq,
               f.ceqq, f.seqq, f.pstkq, f.pstkrq, f.ltq,
               ABS(f.prccq) AS prccq, f.cshoq, f.oiadpq, f.epspxq, f.ajexq,
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
    """)
    comp["datadate"] = pd.to_datetime(comp["datadate"])
    comp["rdq"] = pd.to_datetime(comp["rdq"], errors="coerce")
    comp = (
        comp.sort_values(["gvkey", "datadate"])
        .drop_duplicates(["gvkey", "datadate"], keep="last")
        .sort_values(["gvkey", "datadate"])
    )
    return comp


def load_quarterly_ibes(db):
    return db.raw_sql("""
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
    return comp.merge(ibes, on=["cusip6", "datadate"], how="left", suffixes=("", "_ibes"))


def compute_quarterly_characters(comp):
    comp = comp.copy()
    comp["count"] = comp.groupby("gvkey").cumcount() + 1

    for col in [
        "ibq", "saleq", "txtq", "atq", "actq", "cheq", "lctq", "dlcq", "ppentq",
        "ceqq", "seqq", "pstkq", "pstkrq", "ltq", "cshoq", "ajexq", "rectq",
        "invtq", "acoq", "intanq", "aoq", "apq", "lcoq", "loq",
    ]:
        if col in comp.columns:
            for lag in (1, 2, 3, 4, 5, 6, 7, 8):
                comp[f"lag{lag}_{col}"] = lag_by_gvkey(comp, col, lag)

    pstk = comp["pstkrq"].fillna(comp["pstkq"])
    scal = comp["seqq"].copy()
    scal = scal.fillna(comp["ceqq"] + pstk)
    scal = scal.fillna(comp["atq"] - comp["ltq"])

    comp["chtx"] = safe_divide(comp["txtq"] - comp["lag4_txtq"], comp["lag4_atq"])
    comp["roa1"] = safe_divide(comp["ibq"], comp["lag1_atq"])
    comp["rsup"] = safe_divide(comp["saleq"] - comp["lag4_saleq"], comp["prccq"] * comp["cshoq"])

    operating_assets = comp["atq"] - comp["cheq"]
    operating_liabilities = comp["atq"] - comp["dlcq"].fillna(0) - comp["dlttq"].fillna(0) - pstk - comp["ceqq"]
    comp["noa_level"] = operating_assets - operating_liabilities
    comp["rna"] = safe_divide(comp["oiadpq"], lag_by_gvkey(comp, "noa_level", 4))

    pp_change = safe_divide(comp["ppentq"] - comp["lag1_ppentq"], comp["saleq"])
    pp_mean = pd.concat(
        [
            safe_divide(comp["lag1_ppentq"] - comp["lag2_ppentq"], comp["lag1_saleq"]),
            safe_divide(comp["lag2_ppentq"] - comp["lag3_ppentq"], comp["lag2_saleq"]),
            safe_divide(comp["lag3_ppentq"] - comp["lag4_ppentq"], comp["lag3_saleq"]),
        ],
        axis=1,
    ).mean(axis=1)
    comp["cinvest"] = pp_change - pp_mean
    low_sale = comp["saleq"] <= 0
    comp.loc[low_sale, "cinvest"] = (
        (comp.loc[low_sale, "ppentq"] - comp.loc[low_sale, "lag1_ppentq"]) / 0.01
        - pp_mean.loc[low_sale]
    )

    def qinc(left, right):
        return (left > right).fillna(False).astype(int)

    increases = [
        qinc(comp["ibq"], comp["lag1_ibq"]),
        qinc(comp["lag1_ibq"], comp["lag2_ibq"]),
        qinc(comp["lag2_ibq"], comp["lag3_ibq"]),
        qinc(comp["lag3_ibq"], comp["lag4_ibq"]),
        qinc(comp["lag4_ibq"], comp["lag5_ibq"]),
        qinc(comp["lag5_ibq"], comp["lag6_ibq"]),
        qinc(comp["lag6_ibq"], comp["lag7_ibq"]),
        qinc(comp["lag7_ibq"], comp["lag8_ibq"]),
    ]
    comp["nincr"] = increases[0]
    for extra in increases[1:]:
        comp["nincr"] = comp["nincr"] + comp["nincr"] * extra

    shares = comp["cshoq"] * comp["ajexq"]
    lag_shares = comp["lag4_cshoq"] * comp["lag4_ajexq"]
    comp["ni"] = np.log(shares.replace(0, np.nan)) - np.log(lag_shares.replace(0, np.nan))

    comp["che"] = comp["ibq"] - comp["lag4_ibq"]
    mveq = comp["prccq"] * comp["cshoq"]
    comp["sue"] = safe_divide(comp["che"], mveq)
    has_ibes = comp["medest"].notna() & comp["actual"].notna()
    comp.loc[has_ibes, "sue"] = safe_divide(
        comp.loc[has_ibes, "actual"] - comp.loc[has_ibes, "medest"],
        comp.loc[has_ibes, "prccq"].abs(),
    )

    comp.loc[comp["count"] < 5, ["chtx", "che", "cinvest"]] = np.nan
    comp.loc[comp["count"] == 1, "roa1"] = np.nan
    comp.loc[comp["count"] < 5, "ni"] = np.nan

    return comp


def expand_quarterly_to_monthly(db, quarterly, character):
    monthly = get_monthly_crsp_panel(db)[
        ["permno", "permco", "date", "signal_yyyymm", "target_yyyymm", "sic", "exchcd", "shrcd"]
    ].copy()
    monthly["date"] = pd.to_datetime(monthly["date"])
    monthly["permno"] = pd.to_numeric(monthly["permno"], errors="coerce").astype("int64")
    monthly = monthly.drop_duplicates(["permno", "date"], keep="last")

    q = quarterly[["permno", "datadate", character]].copy()
    q["permno"] = pd.to_numeric(q["permno"], errors="coerce").astype("int64")
    q["datadate"] = pd.to_datetime(q["datadate"])
    q["valid_through"] = q["datadate"] + pd.DateOffset(months=12) + pd.offsets.MonthEnd(0)
    q = q[q[character].replace([np.inf, -np.inf], np.nan).notna()].copy()
    q = q.sort_values(["permno", "datadate"])

    valid_permnos = q["permno"].unique()
    monthly = monthly[monthly["permno"].isin(valid_permnos)]

    q_by_permno = {
        permno: grp[["datadate", "valid_through", character]]
        for permno, grp in q.groupby("permno", sort=False)
    }
    parts = []
    for permno, m_grp in monthly.groupby("permno", sort=False):
        q_grp = q_by_permno.get(permno)
        if q_grp is None or q_grp.empty:
            continue
        m_grp = m_grp.sort_values("date")
        part = pd.merge_asof(
            m_grp,
            q_grp,
            left_on="date",
            right_on="datadate",
            direction="backward",
        )
        part = part[part["datadate"].notna() & (part["date"] <= part["valid_through"])]
        if not part.empty:
            parts.append(part)

    if not parts:
        return pd.DataFrame(
            columns=[
                "permno",
                "permco",
                "date",
                "signal_yyyymm",
                "target_yyyymm",
                "sic",
                "exchcd",
                "shrcd",
                character,
            ]
        )

    merged = pd.concat(parts, ignore_index=True)
    merged = merged.drop(columns=["valid_through", "datadate"], errors="ignore")
    return merged[
        ["permno", "permco", "date", "signal_yyyymm", "target_yyyymm", "sic", "exchcd", "shrcd", character]
    ]


def prepare_quarterly_compustat_panel(
    db, ccm_linktypes=None, ccm_linkprim=None, use_ibes=True
):
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
    comp = attach_ccm_links(comp, load_ccm_links(db, ccm_linktypes, ccm_linkprim))
    return comp[comp["permno"].notna()].copy()


def build_quarterly_character(
    db, character, ccm_linktypes=None, ccm_linkprim=None, use_ibes=True, comp=None
):
    if comp is None:
        comp = prepare_quarterly_compustat_panel(
            db, ccm_linktypes, ccm_linkprim, use_ibes=use_ibes
        )
    return expand_quarterly_to_monthly(db, comp, character)


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
