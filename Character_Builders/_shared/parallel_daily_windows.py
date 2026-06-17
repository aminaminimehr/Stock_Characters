"""Firm-chunk parallel processing for daily-window characteristics.

Pattern adapted from Dacheng / Xin He reference scripts: split work by permno,
not by date, because rolling windows are firm-local. Workers return compact
result rows only (permno, source_yyyymm, value) to limit pickle/memory cost.
"""
from __future__ import annotations

import os
from concurrent.futures import ProcessPoolExecutor, as_completed
from typing import Callable, Iterable, Sequence, TypeVar

import numpy as np
import pandas as pd

DEFAULT_MAX_WORKERS = 8

T = TypeVar("T")


def resolve_worker_count(workers: int | None = None) -> int:
    if workers is not None:
        return max(1, int(workers))
    env = os.environ.get("STOCK_CHARACTERS_WORKERS")
    if env:
        return max(1, int(env))
    return max(1, min(os.cpu_count() or 1, DEFAULT_MAX_WORKERS))


def split_permno_chunks(permnos: Sequence[int], n_workers: int) -> list[list[int]]:
    """Quantile-balanced permno chunks (Dacheng-style firm splitting)."""
    unique = sorted({int(p) for p in permnos})
    if not unique:
        return []
    n_workers = min(max(1, n_workers), len(unique))
    firm = pd.DataFrame({"permno": unique, "count": np.arange(len(unique))})
    cuts = firm["count"].quantile(np.linspace(0, 1, n_workers + 1)).tolist()
    chunks: list[list[int]] = []
    for idx in range(n_workers):
        lo, hi = cuts[idx], cuts[idx + 1]
        if idx < n_workers - 1:
            part = firm[(firm["count"] >= lo) & (firm["count"] < hi)]["permno"].tolist()
        else:
            part = firm[firm["count"] >= lo]["permno"].tolist()
        if part:
            chunks.append(part)
    return chunks


def add_source_month_labels(daily: pd.DataFrame, date_col: str = "date") -> pd.DataFrame:
    """Add calendar source month and sequential month_count for rolling windows."""
    out = daily.sort_values(["permno", date_col]).copy()
    out["source_yyyymm"] = (
        pd.to_datetime(out[date_col]).dt.year * 100 + pd.to_datetime(out[date_col]).dt.month
    ).astype(int)
    month_end = out.groupby(["permno", "source_yyyymm"], sort=False)[date_col].transform("max")
    out["is_month_end"] = out[date_col] == month_end
    out["month_count"] = np.nan
    out.loc[out["is_month_end"], "month_count"] = out.loc[out["is_month_end"]].groupby(
        "permno", sort=False
    ).cumcount()
    out["month_count"] = out.groupby("permno", sort=False)["month_count"].ffill()
    return out


def run_permno_parallel(
    permnos: Sequence[int],
    worker_fn: Callable[..., T],
    build_args: Callable[[list[int]], object],
    workers: int | None = None,
    label: str = "parallel task",
) -> list[T]:
    """Run a top-level worker function over permno chunks."""
    worker_n = resolve_worker_count(workers)
    chunks = split_permno_chunks(permnos, worker_n)
    if not chunks:
        return []

    args_list = [build_args(chunk) for chunk in chunks]
    if worker_n == 1 or len(args_list) == 1:
        print(f"{label}: workers=1 ({len(args_list)} chunk(s))", flush=True)
        return [worker_fn(args) for args in args_list]

    import multiprocessing

    ctx = multiprocessing.get_context("spawn")
    print(f"{label}: workers={worker_n} ({len(args_list)} chunks)", flush=True)
    results: list[T] = []
    with ProcessPoolExecutor(max_workers=worker_n, mp_context=ctx) as pool:
        futures = {pool.submit(worker_fn, args): idx for idx, args in enumerate(args_list)}
        for future in as_completed(futures):
            results.append((futures[future], future.result()))
    results.sort(key=lambda pair: pair[0])
    return [value for _, value in results]
