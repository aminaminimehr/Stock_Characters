import argparse
from pathlib import Path

import numpy as np
import pandas as pd

from _shared.ccm import add_ccm_arguments, attach_ccm_links_green, load_ccm_links_green
from _shared.green_builders import OUTPUT_DIR, connect_wrds, load_crsp_monthly, raw_sql_with_retry
from output_paths import sql_date_filter
from _shared.parallel_daily_windows import run_permno_parallel
from _shared.quarterly_builders import (
    QUARTERLY_MONTH_END_LAG,
    QUARTERLY_MONTH_START_LAG,
    load_quarterly_compustat,
)

# Green SAS Greens_code.sas L768: same quarterly window as sue/rsup/nincr (-10 .. -5).
EAR_MONTH_START_LAG = QUARTERLY_MONTH_START_LAG
EAR_MONTH_END_LAG = QUARTERLY_MONTH_END_LAG

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def _intnx_month(ts: pd.Series, n: int, alignment: str = "end") -> pd.Series:
    shifted = pd.to_datetime(ts) + pd.DateOffset(months=n)
    if alignment == "beg":
        return shifted.dt.to_period("M").dt.to_timestamp("s")
    return shifted.dt.to_period("M").dt.to_timestamp("h")


def _intnx_weekday_scalar(ts) -> tuple[pd.Timestamp, pd.Timestamp]:
    rdq = pd.Timestamp(ts)
    win_start = rdq + pd.tseries.offsets.BDay(-1)
    win_end = rdq + pd.tseries.offsets.BDay(1)
    return win_start, win_end


def _load_dsf_for_permnos(db, permnos: list[int]) -> pd.DataFrame:
    chunks = []
    for i in range(0, len(permnos), 3000):
        ids = ",".join(str(p) for p in permnos[i : i + 3000])
        part = raw_sql_with_retry(
            db,
            f"""
            SELECT permno, date, ret, vol
            FROM crsp.dsf
            WHERE permno IN ({ids})
              AND {sql_date_filter("date")}
            """,
        )
        chunks.append(part)
    if not chunks:
        return pd.DataFrame(columns=["permno", "date", "ret", "vol"])
    dsf = pd.concat(chunks, ignore_index=True)
    dsf["date"] = pd.to_datetime(dsf["date"])
    dsf["ret"] = pd.to_numeric(dsf["ret"], errors="coerce")
    dsf["vol"] = pd.to_numeric(dsf["vol"], errors="coerce")
    dsf["permno"] = pd.to_numeric(dsf["permno"], errors="coerce").astype("int64")
    return dsf.sort_values(["permno", "date"]).reset_index(drop=True)


def _earnings_events_for_permno(permno: int, events_p: pd.DataFrame, dsf_p: pd.DataFrame) -> list[dict]:
    if events_p.empty or dsf_p.empty:
        return []
    dates = dsf_p["date"].to_numpy(dtype="datetime64[ns]")
    rets = dsf_p["ret"].to_numpy(dtype=float)
    vols = dsf_p["vol"].to_numpy(dtype=float)
    rows: list[dict] = []
    events_p = events_p.drop_duplicates(["datadate", "rdq"])
    for row in events_p.itertuples(index=False):
        win_start, win_end = _intnx_weekday_scalar(row.rdq)
        i0 = int(np.searchsorted(dates, np.datetime64(win_start), side="left"))
        i1 = int(np.searchsorted(dates, np.datetime64(win_end), side="right"))
        if i1 <= i0:
            continue
        ear = float(np.nansum(rets[i0:i1]))
        if not np.isfinite(ear):
            continue

        rdq = pd.Timestamp(row.rdq)
        pre_start = rdq + pd.tseries.offsets.BDay(-30)
        pre_end = rdq + pd.tseries.offsets.BDay(-10)
        j0 = int(np.searchsorted(dates, np.datetime64(pre_start), side="left"))
        j1 = int(np.searchsorted(dates, np.datetime64(pre_end), side="right"))
        pre_vol = vols[j0:j1]
        evt_vol = vols[i0:i1]
        pre_mean = float(np.nanmean(pre_vol)) if len(pre_vol) else np.nan
        evt_mean = float(np.nanmean(evt_vol)) if len(evt_vol) else np.nan
        if not np.isfinite(pre_mean) or pre_mean == 0 or not np.isfinite(evt_mean):
            aeavol = np.nan
        else:
            aeavol = (evt_mean - pre_mean) / pre_mean

        rows.append(
            {
                "permno": int(permno),
                "datadate": row.datadate,
                "rdq": row.rdq,
                "ear": ear,
                "aeavol": aeavol,
            }
        )
    return rows


def _ear_events_for_permno(permno: int, events_p: pd.DataFrame, dsf_p: pd.DataFrame) -> list[dict]:
    return [
        {k: v for k, v in row.items() if k != "aeavol"}
        for row in _earnings_events_for_permno(permno, events_p, dsf_p)
    ]


def _earnings_events_chunk_worker(args: tuple) -> pd.DataFrame:
    permno_chunk, events, dsf = args
    events = events[events["permno"].isin(permno_chunk)]
    dsf = dsf[dsf["permno"].isin(permno_chunk)]
    records: list[dict] = []
    for permno in permno_chunk:
        records.extend(
            _earnings_events_for_permno(
                permno,
                events[events["permno"] == permno],
                dsf[dsf["permno"] == permno],
            )
        )
    if not records:
        return pd.DataFrame(columns=["permno", "datadate", "rdq", "ear", "aeavol"])
    return pd.DataFrame(records)


def _ear_events_chunk_worker(args: tuple) -> pd.DataFrame:
    out = _earnings_events_chunk_worker(args)
    if out.empty:
        return pd.DataFrame(columns=["permno", "datadate", "rdq", "ear"])
    return out.drop(columns=["aeavol"], errors="ignore")


def _compute_earnings_events(comp: pd.DataFrame, db, workers: int | None = None) -> pd.DataFrame:
    """Green SAS ear/aeavol from daily CRSP around rdq."""
    df = comp[comp["rdq"].notna() & comp["permno"].notna()].copy()
    if df.empty:
        return pd.DataFrame(columns=["permno", "datadate", "rdq", "ear", "aeavol"])

    df["permno"] = pd.to_numeric(df["permno"], errors="coerce").astype("int64")
    df["datadate"] = pd.to_datetime(df["datadate"])
    df["rdq"] = pd.to_datetime(df["rdq"])
    events = df[["permno", "datadate", "rdq"]].drop_duplicates()
    permnos = events["permno"].astype(int).unique().tolist()
    print(f"EAR/aeavol: {len(events):,} events / {len(permnos):,} permnos...", flush=True)

    print("EAR/aeavol: loading CRSP daily from WRDS...", flush=True)
    dsf = _load_dsf_for_permnos(db, permnos)
    print(f"EAR/aeavol: loaded {len(dsf):,} daily rows", flush=True)

    frames = run_permno_parallel(
        permnos,
        _earnings_events_chunk_worker,
        lambda chunk: (
            chunk,
            events[events["permno"].isin(chunk)],
            dsf[dsf["permno"].isin(chunk)],
        ),
        workers=workers,
        label="earnings event windows",
    )
    if not frames:
        return pd.DataFrame(columns=["permno", "datadate", "rdq", "ear", "aeavol"])
    out = pd.concat(frames, ignore_index=True)
    print(f"EAR/aeavol: constructed {len(out):,} event-level rows", flush=True)
    return out


def _compute_ear_events(comp: pd.DataFrame, db, workers: int | None = None) -> pd.DataFrame:
    out = _compute_earnings_events(comp, db, workers=workers)
    return out.drop(columns=["aeavol"], errors="ignore")


def _monthly_event_merge_worker(args: tuple) -> pd.DataFrame:
    permno_chunk, monthly_p, events_p, value_col, start_lag, end_lag = args
    monthly_p = monthly_p[monthly_p["permno"].isin(permno_chunk)].copy()
    events_p = events_p[events_p["permno"].isin(permno_chunk)].copy()
    if monthly_p.empty or events_p.empty:
        return pd.DataFrame()
    monthly_p["win_start"] = _intnx_month(monthly_p["date"], start_lag, "end")
    monthly_p["win_end"] = _intnx_month(monthly_p["date"], end_lag, "beg")
    merged = monthly_p.merge(events_p, on="permno", how="inner")
    merged = merged[
        merged["datadate"].notna()
        & (merged["datadate"] >= merged["win_start"])
        & (merged["datadate"] <= merged["win_end"])
    ]
    if merged.empty:
        return pd.DataFrame()
    matched = (
        merged.sort_values(["permno", "date", "datadate"], ascending=[True, True, False])
        .drop_duplicates(["permno", "date"], keep="first")
    )
    return matched[
        [
            "permno",
            "permco",
            "date",
            "signal_yyyymm",
            "target_yyyymm",
            "sic",
            "exchcd",
            "shrcd",
            value_col,
        ]
    ]


def _merge_events_to_monthly(
    monthly: pd.DataFrame, events: pd.DataFrame, value_col: str, workers: int | None = None
) -> pd.DataFrame:
    permnos = sorted(set(monthly["permno"].astype(int)) & set(events["permno"].astype(int)))
    print(f"{value_col}: mapping events to monthly panel for {len(permnos):,} permnos...", flush=True)

    frames = run_permno_parallel(
        permnos,
        _monthly_event_merge_worker,
        lambda chunk: (
            chunk,
            monthly[monthly["permno"].isin(chunk)],
            events[events["permno"].isin(chunk)],
            value_col,
            EAR_MONTH_START_LAG,
            EAR_MONTH_END_LAG,
        ),
        workers=workers,
        label=f"{value_col} monthly alignment",
    )
    if not frames:
        return pd.DataFrame()
    out = pd.concat(frames, ignore_index=True)
    out = out[out[value_col].replace([np.inf, -np.inf], np.nan).notna()].copy()
    print(f"{value_col}: monthly panel rows: {len(out):,}", flush=True)
    return out


def _merge_ear_to_monthly(monthly: pd.DataFrame, events: pd.DataFrame, workers: int | None = None) -> pd.DataFrame:
    return _merge_events_to_monthly(monthly, events, "ear", workers=workers)


def build_ear_character(db, ccm_linktypes=None, ccm_linkprim=None, workers: int | None = None):
    print("EAR: loading quarterly Compustat + CCM links...", flush=True)
    comp = load_quarterly_compustat(db)
    comp = attach_ccm_links_green(comp, load_ccm_links_green(db))
    comp = comp[comp["permno"].notna()].copy()
    events = _compute_ear_events(comp, db, workers=workers)
    if events.empty:
        raise ValueError("No EAR events were constructed. Check WRDS inputs and CCM links.")

    print("EAR: loading CRSP monthly alignment frame...", flush=True)
    monthly = load_crsp_monthly(db)[
        ["permno", "permco", "date", "signal_yyyymm", "target_yyyymm", "siccd", "exchcd", "shrcd"]
    ].rename(columns={"siccd": "sic"})
    monthly["date"] = pd.to_datetime(monthly["date"])
    monthly["permno"] = pd.to_numeric(monthly["permno"], errors="coerce").astype("int64")
    events["permno"] = pd.to_numeric(events["permno"], errors="coerce").astype("int64")
    events["datadate"] = pd.to_datetime(events["datadate"])

    out = _merge_ear_to_monthly(monthly, events, workers=workers)
    if out.empty:
        raise ValueError("No monthly EAR rows after alignment.")
    return out[
        ["permno", "permco", "date", "signal_yyyymm", "target_yyyymm", "sic", "exchcd", "shrcd", "ear"]
    ]


def build_aeavol_character(db, ccm_linktypes=None, ccm_linkprim=None, workers: int | None = None):
    print("aeavol: loading quarterly Compustat + CCM links...", flush=True)
    comp = load_quarterly_compustat(db)
    comp = attach_ccm_links_green(comp, load_ccm_links_green(db))
    comp = comp[comp["permno"].notna()].copy()
    events = _compute_earnings_events(comp, db, workers=workers)
    if events.empty:
        raise ValueError("No aeavol events were constructed.")

    monthly = load_crsp_monthly(db)[
        ["permno", "permco", "date", "signal_yyyymm", "target_yyyymm", "siccd", "exchcd", "shrcd"]
    ].rename(columns={"siccd": "sic"})
    monthly["date"] = pd.to_datetime(monthly["date"])
    monthly["permno"] = pd.to_numeric(monthly["permno"], errors="coerce").astype("int64")
    events["permno"] = pd.to_numeric(events["permno"], errors="coerce").astype("int64")
    events["datadate"] = pd.to_datetime(events["datadate"])

    out = _merge_events_to_monthly(monthly, events, "aeavol", workers=workers)
    if out.empty:
        raise ValueError("No monthly aeavol rows after alignment.")
    return out


def build_abr_character(db, ccm_linktypes=None, ccm_linkprim=None, workers: int | None = None):
    """Legacy diagnostic alias: EAR values exported under historical abr name."""
    out = build_ear_character(db, ccm_linktypes, ccm_linkprim, workers=workers).rename(columns={"ear": "abr"})
    return out


def run_ear_cli():
    parser = argparse.ArgumentParser(
        description="Build earnings announcement return (EAR) aligned with Green SAS."
    )
    parser.add_argument("--wrds-user", default=None)
    parser.add_argument("--output", default=OUTPUT_DIR / "ear.csv")
    parser.add_argument(
        "--workers",
        type=int,
        default=None,
        help="Parallel worker count (default: STOCK_CHARACTERS_WORKERS or min(cpu, 8)).",
    )
    add_ccm_arguments(parser)
    args = parser.parse_args()

    output = Path(args.output)
    if not output.is_absolute():
        output = PROJECT_ROOT / output
    output.parent.mkdir(parents=True, exist_ok=True)

    db = connect_wrds(args.wrds_user)
    try:
        result = build_ear_character(db, args.ccm_linktypes, args.ccm_linkprim, workers=args.workers)
    finally:
        db.close()

    result.to_csv(output, index=False)
    print(f"Saved ear to: {output.resolve()}")
    print(f"Rows: {len(result):,}")


if __name__ == "__main__":
    run_ear_cli()
