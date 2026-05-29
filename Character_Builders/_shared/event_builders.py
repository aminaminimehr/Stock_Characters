import argparse
from pathlib import Path

import numpy as np
import pandas as pd

from _shared.ccm import add_ccm_arguments, attach_ccm_links, load_ccm_links
from _shared.green_builders import OUTPUT_DIR, connect_wrds, load_crsp_monthly


PROJECT_ROOT = Path(__file__).resolve().parents[2]


def load_quarterly_announcements(db):
    comp = db.raw_sql("""
        SELECT c.gvkey, f.datadate, f.rdq
        FROM comp.company AS c
        JOIN comp.fundq AS f
          ON c.gvkey = f.gvkey
        WHERE f.indfmt = 'INDL'
          AND f.datafmt = 'STD'
          AND f.popsrc = 'D'
          AND f.consol = 'C'
          AND f.rdq IS NOT NULL
          AND f.datadate >= DATE '1959-01-01'
    """)
    comp["datadate"] = pd.to_datetime(comp["datadate"])
    comp["rdq"] = pd.to_datetime(comp["rdq"])
    return comp.drop_duplicates(["gvkey", "datadate"])


def align_rdq_to_trading_day(rdq_series, trading_days):
    aligned = pd.Series(pd.NaT, index=rdq_series.index, dtype="datetime64[ns]")
    trading = np.array(sorted(trading_days))
    for idx, rdq in rdq_series.items():
        if pd.isna(rdq):
            continue
        on_or_after = trading[trading >= np.datetime64(rdq)]
        if len(on_or_after):
            aligned.loc[idx] = pd.Timestamp(on_or_after[0])
    return aligned


def build_abr_character(db, ccm_linktypes=None, ccm_linkprim=None):
    comp = load_quarterly_announcements(db)
    comp = attach_ccm_links(comp, load_ccm_links(db, ccm_linktypes, ccm_linkprim))
    comp = comp[comp["permno"].notna() & comp["rdq"].notna()].copy()

    trading_days = db.raw_sql("""
        SELECT DISTINCT date
        FROM crsp.dsi
        WHERE date >= DATE '1959-01-01'
    """)
    trading_days = pd.to_datetime(trading_days["date"])
    comp["rdq_trad"] = align_rdq_to_trading_day(comp["rdq"], trading_days)

    daily = db.raw_sql("""
        SELECT d.permno, d.date, d.ret, s.sprtrn
        FROM crsp.dsf AS d
        LEFT JOIN crsp.dsi AS s
          ON d.date = s.date
        WHERE d.date >= DATE '1959-01-01'
    """)
    daily["date"] = pd.to_datetime(daily["date"])
    daily["ret"] = pd.to_numeric(daily["ret"], errors="coerce").fillna(0)
    daily["sprtrn"] = pd.to_numeric(daily["sprtrn"], errors="coerce").fillna(0)
    daily["abrd"] = daily["ret"] - daily["sprtrn"]

    event_rows = []
    for _, row in comp.iterrows():
        permno = int(row["permno"])
        rdq_trad = row["rdq_trad"]
        if pd.isna(rdq_trad):
            continue
        window = daily[
            (daily["permno"] == permno)
            & (daily["date"] >= rdq_trad - pd.Timedelta(days=10))
            & (daily["date"] <= rdq_trad + pd.Timedelta(days=5))
        ].copy()
        if window.empty:
            continue
        window["offset"] = (window["date"] - rdq_trad).dt.days
        abr_window = window[window["offset"].between(-2, 1)]
        if abr_window.empty:
            continue
        event_rows.append(
            {
                "permno": permno,
                "gvkey": row["gvkey"],
                "datadate": row["datadate"],
                "rdq": row["rdq"],
                "rdq_trad": rdq_trad,
                "abr": abr_window["abrd"].sum(),
            }
        )

    events = pd.DataFrame(event_rows)
    if events.empty:
        raise ValueError("No ABR events were constructed. Check WRDS inputs and CCM links.")

    monthly = load_crsp_monthly(db)[
        ["permno", "permco", "date", "signal_yyyymm", "target_yyyymm", "siccd", "exchcd", "shrcd"]
    ].rename(columns={"siccd": "sic"})
    events["valid_through"] = events["datadate"] + pd.DateOffset(months=12) + pd.offsets.MonthEnd(0)
    events["anchor_date"] = events["rdq_trad"] + pd.Timedelta(days=1)

    merged = monthly.merge(events, on="permno", how="inner")
    merged = merged[
        (merged["anchor_date"] < merged["date"])
        & (merged["date"] <= merged["valid_through"])
    ]
    merged = (
        merged.sort_values(["permno", "date", "datadate"])
        .drop_duplicates(["permno", "signal_yyyymm"], keep="last")
    )
    merged = merged[merged["abr"].replace([np.inf, -np.inf], np.nan).notna()].copy()
    return merged[
        ["permno", "permco", "date", "signal_yyyymm", "target_yyyymm", "sic", "exchcd", "shrcd", "abr"]
    ]


def run_abr_cli():
    parser = argparse.ArgumentParser(
        description="Build cumulative abnormal returns around earnings announcements (ABR)."
    )
    parser.add_argument("--wrds-user", default=None)
    parser.add_argument("--output", default=OUTPUT_DIR / "abr.csv")
    add_ccm_arguments(parser)
    args = parser.parse_args()

    output = Path(args.output)
    if not output.is_absolute():
        output = PROJECT_ROOT / output
    output.parent.mkdir(parents=True, exist_ok=True)

    db = connect_wrds(args.wrds_user)
    try:
        result = build_abr_character(db, args.ccm_linktypes, args.ccm_linkprim)
    finally:
        db.close()

    result.to_csv(output, index=False)
    print(f"Saved abr to: {output.resolve()}")
    print(f"Rows: {len(result):,}")
