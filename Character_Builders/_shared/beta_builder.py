import argparse

from pathlib import Path



import numpy as np

import pandas as pd



from _shared.green_builders import OUTPUT_DIR, connect_wrds, load_monthly_alignment_frame, raw_sql_with_retry

from _shared.parallel_daily_windows import run_permno_parallel





PROJECT_ROOT = Path(__file__).resolve().parents[2]





def intnx_month(ts: pd.Series, n: int, alignment: str = "end") -> pd.Series:

    shifted = pd.to_datetime(ts) + pd.DateOffset(months=n)

    if alignment == "beg":

        return shifted.dt.to_period("M").dt.to_timestamp("s")

    return shifted.dt.to_period("M").dt.to_timestamp("h")





def _ols_beta(y: np.ndarray, x: np.ndarray) -> float:

    mask = np.isfinite(y) & np.isfinite(x)

    y, x = y[mask], x[mask]

    if len(y) < 2:

        return np.nan

    x_mean = x.mean()

    y_mean = y.mean()

    xc, yc = x - x_mean, y - y_mean

    denom = np.dot(xc, xc)

    if denom == 0:

        return np.nan

    return float(np.dot(xc, yc) / denom)





def _load_weekly_returns(db, permnos: list[int]) -> pd.DataFrame:

    chunks = []

    for i in range(0, len(permnos), 2000):

        ids = ",".join(str(p) for p in permnos[i : i + 2000])

        part = raw_sql_with_retry(

            db,

            f"""

            SELECT permno, date, ret

            FROM crsp.dsf

            WHERE permno IN ({ids})

              AND date >= DATE '1970-01-01'

            """,

        )

        chunks.append(part)

    dsf = pd.concat(chunks, ignore_index=True)

    dsf["date"] = pd.to_datetime(dsf["date"])

    dsf["wkdt"] = dsf["date"] + pd.to_timedelta(4 - dsf["date"].dt.dayofweek, unit="D")

    wk = dsf.groupby(["permno", "wkdt"], as_index=False).agg(

        wkret=("ret", lambda s: float(np.exp(np.log1p(pd.to_numeric(s, errors="coerce").fillna(0)).sum()) - 1))

    )

    wk = wk[wk["wkdt"] >= "1975-01-01"].drop_duplicates(["permno", "wkdt"])

    wk["ewret"] = wk.groupby("wkdt")["wkret"].transform("mean")

    return wk





def _beta_chunk_worker(args: tuple) -> pd.DataFrame:

    """Top-level worker: Green weekly 36-month beta for one permno chunk."""

    permno_chunk, wk, panel_dates = args

    rows = []

    wk_sub = wk[wk["permno"].isin(permno_chunk)]

    panel_sub = panel_dates[panel_dates["permno"].isin(permno_chunk)]

    for permno, m_grp in panel_sub.groupby("permno", sort=False):

        w_grp = wk_sub[wk_sub["permno"] == permno].sort_values("wkdt")

        if w_grp.empty:

            continue

        wk_dates = w_grp["wkdt"].to_numpy(dtype="datetime64[ns]")

        wkret = w_grp["wkret"].to_numpy(dtype=float)

        ewret = w_grp["ewret"].to_numpy(dtype=float)

        for date in m_grp["date"]:

            end = intnx_month(pd.Series([date]), -1, "end").iloc[0]

            start = intnx_month(pd.Series([date]), -36, "end").iloc[0]

            i0 = wk_dates.searchsorted(np.datetime64(start), side="left")

            i1 = wk_dates.searchsorted(np.datetime64(end), side="right")

            if i1 - i0 < 52:

                continue

            beta = _ols_beta(wkret[i0:i1], ewret[i0:i1])

            if np.isfinite(beta):

                rows.append({"permno": int(permno), "date": date, "beta": beta})

    return pd.DataFrame(rows)





def estimate_green_beta(

    panel_dates: pd.DataFrame, db, workers: int | None = None

) -> pd.DataFrame:

    """Green SAS beta: 36-month weekly stock return on equal-weight market."""

    permnos = panel_dates["permno"].dropna().astype(int).unique().tolist()

    if not permnos:

        return pd.DataFrame(columns=["permno", "date", "beta"])



    print(f"Loading weekly returns for {len(permnos):,} permnos...", flush=True)

    wk = _load_weekly_returns(db, permnos)

    panel_dates = panel_dates.drop_duplicates(["permno", "date"]).copy()

    panel_dates["date"] = pd.to_datetime(panel_dates["date"])



    frames = run_permno_parallel(

        permnos,

        _beta_chunk_worker,

        lambda chunk: (chunk, wk, panel_dates[panel_dates["permno"].isin(chunk)]),

        workers=workers,

        label="Green beta",

    )

    if not frames:

        return pd.DataFrame(columns=["permno", "date", "beta"])

    return pd.concat(frames, ignore_index=True)





def build_beta_character(db, output_dir=OUTPUT_DIR, workers: int | None = None):

    monthly = load_monthly_alignment_frame(output_dir, db=db)

    monthly["date"] = pd.to_datetime(monthly["date"])

    monthly["permno"] = pd.to_numeric(monthly["permno"], errors="coerce").astype("int64")

    beta = estimate_green_beta(monthly[["permno", "date"]], db, workers=workers)

    out = monthly.merge(beta, on=["permno", "date"], how="left")

    out = out[out["beta"].replace([np.inf, -np.inf], np.nan).notna()].copy()

    out = out[out["date"].dt.year >= 1980]

    return out[["permno", "permco", "date", "signal_yyyymm", "target_yyyymm", "sic", "exchcd", "shrcd", "beta"]]





def build_betasq_character(db, output_dir=OUTPUT_DIR, workers: int | None = None):
    beta_path = Path(output_dir) / "beta.csv"
    if beta_path.exists():
        print(f"betasq: reusing existing {beta_path}", flush=True)
        out = pd.read_csv(beta_path)
        out["betasq"] = out["beta"] ** 2
        return out.drop(columns=["beta"])
    out = build_beta_character(db, output_dir, workers=workers)
    out["betasq"] = out["beta"] ** 2
    return out.drop(columns=["beta"])





def run_beta_cli():

    parser = argparse.ArgumentParser(

        description="Build beta from Green SAS weekly rolling market regressions."

    )

    parser.add_argument("--wrds-user", default=None)

    parser.add_argument("--output", default=OUTPUT_DIR / "beta.csv")

    parser.add_argument(

        "--workers",

        type=int,

        default=None,

        help="Parallel worker count (default: STOCK_CHARACTERS_WORKERS or min(cpu, 8)).",

    )

    args = parser.parse_args()



    output = Path(args.output)

    if not output.is_absolute():

        output = PROJECT_ROOT / output

    output.parent.mkdir(parents=True, exist_ok=True)



    db = connect_wrds(args.wrds_user)

    try:

        result = build_beta_character(db, workers=args.workers)

    finally:

        db.close()



    result.to_csv(output, index=False)

    print(f"Saved beta to: {output.resolve()}")

    print(f"Rows: {len(result):,}")


