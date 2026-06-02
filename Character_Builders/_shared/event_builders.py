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
    trading = np.sort(pd.to_datetime(trading_days).to_numpy(dtype="datetime64[ns]"))
    rdq = pd.to_datetime(rdq_series).to_numpy(dtype="datetime64[ns]")
    aligned = np.full(len(rdq), np.datetime64("NaT"), dtype="datetime64[ns]")
    valid = ~pd.isna(rdq_series).to_numpy()
    if not valid.any():
        return pd.Series(aligned, index=rdq_series.index)

    idx = np.searchsorted(trading, rdq[valid], side="left")
    in_range = idx < len(trading)
    aligned[valid] = np.datetime64("NaT")
    aligned[np.where(valid)[0][in_range]] = trading[idx[in_range]]
    return pd.Series(aligned, index=rdq_series.index)


def _summarize_abr_events(comp, daily):
    comp = comp[comp["rdq_trad"].notna()].copy()
    comp["permno"] = pd.to_numeric(comp["permno"], errors="coerce").astype("int64")
    daily = daily.sort_values(["permno", "date"])
    daily_by_permno = {
        int(permno): group
        for permno, group in daily.groupby("permno", sort=False)
    }

    event_rows = []
    for permno, events in comp.groupby("permno", sort=False):
        stock_daily = daily_by_permno.get(int(permno))
        if stock_daily is None or stock_daily.empty:
            continue

        dates = stock_daily["date"].to_numpy(dtype="datetime64[ns]")
        abrd = stock_daily["abrd"].to_numpy(dtype=float)
        for row in events.itertuples(index=False):
            rdq_trad = row.rdq_trad
            if pd.isna(rdq_trad):
                continue
            rdq64 = np.datetime64(rdq_trad)
            window_mask = (dates >= rdq64 - np.timedelta64(10, "D")) & (
                dates <= rdq64 + np.timedelta64(5, "D")
            )
            if not window_mask.any():
                continue
            offsets = (dates[window_mask] - rdq64).astype("timedelta64[D]").astype(int)
            abr_mask = (offsets >= -2) & (offsets <= 1)
            if not abr_mask.any():
                continue
            event_rows.append(
                {
                    "permno": int(permno),
                    "gvkey": row.gvkey,
                    "datadate": row.datadate,
                    "rdq": row.rdq,
                    "rdq_trad": rdq_trad,
                    "abr": float(abrd[window_mask][abr_mask].sum()),
                }
            )

    return pd.DataFrame(event_rows)


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
    daily["permno"] = pd.to_numeric(daily["permno"], errors="coerce").astype("int64")
    daily["ret"] = pd.to_numeric(daily["ret"], errors="coerce").fillna(0)
    daily["sprtrn"] = pd.to_numeric(daily["sprtrn"], errors="coerce").fillna(0)
    daily["abrd"] = daily["ret"] - daily["sprtrn"]

    events = _summarize_abr_events(comp, daily)
    if events.empty:
        raise ValueError("No ABR events were constructed. Check WRDS inputs and CCM links.")

    monthly = load_crsp_monthly(db)[
        ["permno", "permco", "date", "signal_yyyymm", "target_yyyymm", "siccd", "exchcd", "shrcd"]
    ].rename(columns={"siccd": "sic"})
    events["valid_through"] = events["datadate"] + pd.DateOffset(months=12) + pd.offsets.MonthEnd(0)
    events["anchor_date"] = events["rdq_trad"] + pd.Timedelta(days=1)

    return _attach_abr_to_monthly(monthly, events)


def _attach_abr_to_monthly(monthly, events):
    monthly = monthly.copy()
    monthly["permno"] = pd.to_numeric(monthly["permno"], errors="coerce").astype("int64")
    monthly["date"] = pd.to_datetime(monthly["date"]).astype("datetime64[ns]")
    monthly = monthly.sort_values(["permno", "date"])

    events = events.copy()
    events["permno"] = pd.to_numeric(events["permno"], errors="coerce").astype("int64")
    events["anchor_date"] = pd.to_datetime(events["anchor_date"]).astype("datetime64[ns]")
    events["valid_through"] = pd.to_datetime(events["valid_through"]).astype("datetime64[ns]")
    events["datadate"] = pd.to_datetime(events["datadate"]).astype("datetime64[ns]")
    events = events.sort_values(["permno", "anchor_date", "datadate"])

    monthly = monthly[monthly["permno"].isin(events["permno"].unique())]
    events_by_permno = {
        permno: grp[["anchor_date", "valid_through", "datadate", "abr"]]
        for permno, grp in events.groupby("permno", sort=False)
    }

    parts = []
    for permno, m_grp in monthly.groupby("permno", sort=False):
        e_grp = events_by_permno.get(permno)
        if e_grp is None or e_grp.empty:
            continue
        m_grp = m_grp.sort_values("date")
        part = pd.merge_asof(
            m_grp,
            e_grp,
            left_on="date",
            right_on="anchor_date",
            direction="backward",
        )
        part = part[
            part["anchor_date"].notna()
            & (part["anchor_date"] < part["date"])
            & (part["date"] <= part["valid_through"])
        ]
        if part.empty:
            continue
        part = (
            part.sort_values(["date", "datadate"])
            .drop_duplicates(["signal_yyyymm"], keep="last")
        )
        parts.append(part)

    if not parts:
        raise ValueError("No ABR monthly rows were constructed after event alignment.")

    merged = pd.concat(parts, ignore_index=True)
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


if __name__ == "__main__":
    run_abr_cli()
