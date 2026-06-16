import argparse
from pathlib import Path

import numpy as np
import pandas as pd

from _shared.ccm import add_ccm_arguments, attach_ccm_links, load_ccm_links
from _shared.green_builders import OUTPUT_DIR, connect_wrds, load_crsp_monthly, raw_sql_with_retry
from _shared.quarterly_builders import load_quarterly_compustat

# Green SAS EAR monthly mapping (Related_to_Dachengs_EAPVML_paper.sas L1274):
#   intnx('MONTH', a.date, -12) <= b.datadate <= intnx('MONTH', a.date, -3, 'E')
# Distinct from shared quarterly timing (-10 .. -5) used by sue/rsup/nincr etc.
EAR_MONTH_START_LAG = -12
EAR_MONTH_END_LAG = -3


PROJECT_ROOT = Path(__file__).resolve().parents[2]


def _intnx_month(ts: pd.Series, n: int, alignment: str = "end") -> pd.Series:
    """SAS-like intnx('MONTH', date, n [, 'beg'|'end']) helper local to EAR builder."""
    shifted = pd.to_datetime(ts) + pd.DateOffset(months=n)
    if alignment == "beg":
        return shifted.dt.to_period("M").dt.to_timestamp("s")
    return shifted.dt.to_period("M").dt.to_timestamp("h")


def _intnx_weekday(ts: pd.Series, n: int) -> pd.Series:
    return pd.to_datetime(ts) + pd.tseries.offsets.BDay(n)


def _compute_ear_events(comp: pd.DataFrame, db) -> pd.DataFrame:
    """Green SAS ear: sum of daily returns from intnx(WEEKDAY, rdq, -1) to intnx(WEEKDAY, rdq, 1)."""
    df = comp[comp["rdq"].notna() & comp["permno"].notna()].copy()
    if df.empty:
        return pd.DataFrame(columns=["permno", "datadate", "rdq", "ear"])

    permnos = df["permno"].astype(int).unique().tolist()
    chunks = []
    for i in range(0, len(permnos), 3000):
        ids = ",".join(str(p) for p in permnos[i : i + 3000])
        part = raw_sql_with_retry(
            db,
            f"""
            SELECT permno, date, ret
            FROM crsp.dsf
            WHERE permno IN ({ids})
            """,
        )
        chunks.append(part)
    dsf = pd.concat(chunks, ignore_index=True)
    dsf["date"] = pd.to_datetime(dsf["date"])
    dsf["ret"] = pd.to_numeric(dsf["ret"], errors="coerce")

    records = []
    for _, row in df[["permno", "datadate", "rdq"]].drop_duplicates().iterrows():
        rdq = row["rdq"]
        win_start = _intnx_weekday(pd.Series([rdq]), -1).iloc[0]
        win_end = _intnx_weekday(pd.Series([rdq]), 1).iloc[0]
        sub = dsf[(dsf["permno"] == int(row["permno"])) & (dsf["date"] >= win_start) & (dsf["date"] <= win_end)]
        ear = sub["ret"].sum(skipna=True)
        if pd.isna(ear):
            continue
        records.append(
            {
                "permno": int(row["permno"]),
                "datadate": row["datadate"],
                "rdq": row["rdq"],
                "ear": float(ear),
            }
        )
    return pd.DataFrame(records)


def build_ear_character(db, ccm_linktypes=None, ccm_linkprim=None):
    comp = load_quarterly_compustat(db)
    comp = attach_ccm_links(comp, load_ccm_links(db, ccm_linktypes, ccm_linkprim))
    comp = comp[comp["permno"].notna()].copy()
    events = _compute_ear_events(comp, db)
    if events.empty:
        raise ValueError("No EAR events were constructed. Check WRDS inputs and CCM links.")

    monthly = load_crsp_monthly(db)[
        ["permno", "permco", "date", "signal_yyyymm", "target_yyyymm", "siccd", "exchcd", "shrcd"]
    ].rename(columns={"siccd": "sic"})
    monthly["date"] = pd.to_datetime(monthly["date"])
    monthly["permno"] = pd.to_numeric(monthly["permno"], errors="coerce").astype("int64")

    left = monthly.copy()
    left["win_start"] = _intnx_month(left["date"], EAR_MONTH_START_LAG, "end")
    left["win_end"] = _intnx_month(left["date"], EAR_MONTH_END_LAG, "end")
    merged = left.merge(events, on="permno", how="left")
    in_window = merged["datadate"].notna() & (merged["datadate"] >= merged["win_start"]) & (
        merged["datadate"] <= merged["win_end"]
    )
    matched = (
        merged.loc[in_window]
        .sort_values(["permno", "date", "datadate"], ascending=[True, True, False])
        .drop_duplicates(["permno", "date"], keep="first")
    )
    out = left.merge(matched[["permno", "date", "ear"]], on=["permno", "date"], how="inner")
    out = out[out["ear"].replace([np.inf, -np.inf], np.nan).notna()].copy()
    return out[
        ["permno", "permco", "date", "signal_yyyymm", "target_yyyymm", "sic", "exchcd", "shrcd", "ear"]
    ]


def build_abr_character(db, ccm_linktypes=None, ccm_linkprim=None):
    """Legacy diagnostic alias: EAR values exported under historical abr name."""
    out = build_ear_character(db, ccm_linktypes, ccm_linkprim).rename(columns={"ear": "abr"})
    return out


def run_ear_cli():
    parser = argparse.ArgumentParser(
        description="Build earnings announcement return (EAR) aligned with Green SAS."
    )
    parser.add_argument("--wrds-user", default=None)
    parser.add_argument("--output", default=OUTPUT_DIR / "ear.csv")
    add_ccm_arguments(parser)
    args = parser.parse_args()

    output = Path(args.output)
    if not output.is_absolute():
        output = PROJECT_ROOT / output
    output.parent.mkdir(parents=True, exist_ok=True)

    db = connect_wrds(args.wrds_user)
    try:
        result = build_ear_character(db, args.ccm_linktypes, args.ccm_linkprim)
    finally:
        db.close()

    result.to_csv(output, index=False)
    print(f"Saved ear to: {output.resolve()}")
    print(f"Rows: {len(result):,}")


if __name__ == "__main__":
    run_ear_cli()
