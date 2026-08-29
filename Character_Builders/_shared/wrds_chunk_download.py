"""Sequential WRDS downloads for permno-chunked crsp.dsf queries.

Deliberately single-connection and single-threaded: WRDS caps concurrent
sessions per role, and a failed connect inside a worker thread prompts on
stdin and hangs the run. CPU parallelism happens after download, in
parallel_daily_windows.py.
"""
from __future__ import annotations

import pickle
import re
import time
from pathlib import Path

import pandas as pd

from _shared.green_builders import raw_sql_with_retry
from output_paths import CACHE_DIR, get_sample_bounds, sql_date_filter

PERMNO_CHUNK_SIZE = 400


def _format_duration(seconds: float) -> str:
    seconds = max(0, int(seconds))
    minutes, secs = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)
    if hours:
        return f"{hours}h{minutes:02d}m"
    if minutes:
        return f"{minutes}m{secs:02d}s"
    return f"{secs}s"


def _cache_slug(label: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "_", label.strip().lower()).strip("_")
    return slug or "dsf"


def _chunk_cache_dir(label: str, select_cols: str) -> Path:
    start, end = get_sample_bounds()
    end_tag = end or "open"
    cols_tag = re.sub(r"[^a-z0-9]+", "_", select_cols.lower()).strip("_")
    return CACHE_DIR / "dsf_chunks" / f"{_cache_slug(label)}_{start}_{end_tag}_{cols_tag}"


def _chunk_cache_path(cache_dir: Path, chunk_idx: int) -> Path:
    return cache_dir / f"chunk_{chunk_idx:04d}.pkl"


def fetch_dsf_by_permno_batches(
    permnos: list[int],
    *,
    db,
    select_cols: str = "permno, date, ret",
    label: str = "dsf",
) -> pd.DataFrame:
    """Fetch crsp.dsf rows for many permnos using chunked IN lists on one connection."""
    if db is None:
        raise ValueError("fetch_dsf_by_permno_batches requires an open WRDS db connection.")
    if not permnos:
        return pd.DataFrame()

    batches = [permnos[i : i + PERMNO_CHUNK_SIZE] for i in range(0, len(permnos), PERMNO_CHUNK_SIZE)]
    n_chunks = len(batches)
    date_filter = sql_date_filter("date")
    cache_dir = _chunk_cache_dir(label, select_cols)
    cache_dir.mkdir(parents=True, exist_ok=True)

    print(
        f"{label}: {n_chunks} chunks x {PERMNO_CHUNK_SIZE} permnos max, "
        f"sequential on one WRDS connection",
        flush=True,
    )

    parts: list[pd.DataFrame] = []
    rows_so_far = 0
    t0 = time.monotonic()

    for idx, batch in enumerate(batches, start=1):
        cache_path = _chunk_cache_path(cache_dir, idx)
        if cache_path.exists():
            with cache_path.open("rb") as handle:
                part = pickle.load(handle)
            parts.append(part)
            rows_so_far += len(part)
            elapsed = time.monotonic() - t0
            avg = elapsed / idx
            remaining = avg * (n_chunks - idx)
            print(
                f"  chunk {idx}/{n_chunks} ({len(batch)} permnos) | "
                f"cached {len(part):,} rows | {rows_so_far:,} rows so far | "
                f"elapsed {_format_duration(elapsed)} | est remaining {_format_duration(remaining)}",
                flush=True,
            )
            continue

        ids = ",".join(str(p) for p in batch)
        part = raw_sql_with_retry(
            db,
            f"""
            SELECT {select_cols}
            FROM crsp.dsf
            WHERE permno IN ({ids})
              AND {date_filter}
            """,
        )
        with cache_path.open("wb") as handle:
            pickle.dump(part, handle, protocol=pickle.HIGHEST_PROTOCOL)

        parts.append(part)
        rows_so_far += len(part)
        elapsed = time.monotonic() - t0
        avg = elapsed / idx
        remaining = avg * (n_chunks - idx)
        print(
            f"  chunk {idx}/{n_chunks} ({len(batch)} permnos) | "
            f"{len(part):,} rows | {rows_so_far:,} rows so far | "
            f"elapsed {_format_duration(elapsed)} | est remaining {_format_duration(remaining)}",
            flush=True,
        )

    return pd.concat(parts, ignore_index=True) if parts else pd.DataFrame()
