"""Parallel WRDS downloads for permno-chunked crsp.dsf queries.

``--workers`` controls CPU compute (ProcessPoolExecutor). WRDS pulls are I/O-bound
and use a separate thread pool (``STOCK_CHARACTERS_WRDS_DOWNLOAD_WORKERS``).
"""
from __future__ import annotations

import os
from concurrent.futures import ThreadPoolExecutor, as_completed

import pandas as pd

from _shared.green_builders import connect_wrds, raw_sql_with_retry
from output_paths import sql_date_filter


def resolve_wrds_download_workers() -> int:
    raw = os.environ.get("STOCK_CHARACTERS_WRDS_DOWNLOAD_WORKERS", "4")
    return max(1, min(16, int(raw)))


def resolve_wrds_user(db=None, wrds_user: str | None = None) -> str | None:
    if wrds_user:
        return wrds_user
    if db is not None:
        for attr in ("username", "_username"):
            val = getattr(db, attr, None)
            if val:
                return str(val)
    return os.environ.get("WRDS_USERNAME") or os.environ.get("WRDS_USER")


def _permno_chunk_size() -> int:
    return max(50, int(os.environ.get("STOCK_CHARACTERS_WRDS_PERMNO_CHUNK", "400")))


def _fetch_dsf_batch_task(args: tuple) -> tuple[int, pd.DataFrame]:
    wrds_user, batch, chunk_idx, n_chunks, date_filter, select_cols = args
    db = connect_wrds(wrds_user)
    try:
        ids = ",".join(str(p) for p in batch)
        print(
            f"  {select_cols} WRDS chunk {chunk_idx}/{n_chunks} ({len(batch)} permnos)...",
            flush=True,
        )
        part = raw_sql_with_retry(
            db,
            f"""
            SELECT {select_cols}
            FROM crsp.dsf
            WHERE permno IN ({ids})
              AND {date_filter}
            """,
        )
        return chunk_idx - 1, part
    finally:
        db.close()


def fetch_dsf_by_permno_batches(
    permnos: list[int],
    *,
    db=None,
    wrds_user: str | None = None,
    select_cols: str = "permno, date, ret",
    label: str = "dsf",
) -> pd.DataFrame:
    """Fetch crsp.dsf rows for many permnos using chunked IN lists."""
    if not permnos:
        return pd.DataFrame()

    chunk_size = _permno_chunk_size()
    batches = [permnos[i : i + chunk_size] for i in range(0, len(permnos), chunk_size)]
    n_chunks = len(batches)
    date_filter = sql_date_filter("date")
    user = resolve_wrds_user(db, wrds_user)
    download_workers = resolve_wrds_download_workers()

    if download_workers <= 1 or not user:
        parts: list[pd.DataFrame] = []
        for idx, batch in enumerate(batches, start=1):
            if user:
                _, part = _fetch_dsf_batch_task(
                    (user, batch, idx, n_chunks, date_filter, select_cols)
                )
            else:
                ids = ",".join(str(p) for p in batch)
                print(
                    f"  {select_cols} WRDS chunk {idx}/{n_chunks} ({len(batch)} permnos)...",
                    flush=True,
                )
                part = raw_sql_with_retry(
                    db,
                    f"""
                    SELECT {select_cols}
                    FROM crsp.dsf
                    WHERE permno IN ({ids})
                      AND {date_filter}
                    """,
                )
            parts.append(part)
        return pd.concat(parts, ignore_index=True) if parts else pd.DataFrame()

    print(
        f"{label}: downloading {n_chunks} WRDS chunks with {download_workers} parallel connections "
        f"(compute --workers is used only after this step)...",
        flush=True,
    )
    tasks = [
        (user, batch, idx, n_chunks, date_filter, select_cols)
        for idx, batch in enumerate(batches, start=1)
    ]
    parts: list[pd.DataFrame | None] = [None] * n_chunks
    with ThreadPoolExecutor(max_workers=download_workers) as pool:
        futures = {pool.submit(_fetch_dsf_batch_task, task): task[2] - 1 for task in tasks}
        for future in as_completed(futures):
            slot, part = future.result()
            parts[slot] = part
    return pd.concat([p for p in parts if p is not None], ignore_index=True)
