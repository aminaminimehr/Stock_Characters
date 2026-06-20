# GKX / Xin He Parallel Processing Review

## Addendum: GKX / Xin He Parallel Daily-Character Pattern

This addendum was added after reviewing the GKX / Xin He reference scripts under:

```text
Supplementary_assistive_files/Python_codes/GKX_Xiu_or_Xin_he/
```

The user specifically asked about:

- `rvar_capm.py`
- `rvar_ff3.py`
- `std_dolvol.py`

The same parallel-processing design also appears in:

- `beta.py`
- `bid_ask_spread.py`
- `ill.py`
- `maxret_d.py`
- `rvar_mean.py`
- `std_turn.py`
- `zerotrade.py`

### Core Design In GKX / Xin He Code

The parallel design is the same across these scripts. Only the statistic computed inside the rolling window changes.

The common structure is:

1. Pull a large daily CRSP dataframe from WRDS.
2. Sort by `permno, date`.
3. Convert `permno` to integer and `date` to datetime.
4. Create a monthly identifier for each firm by finding the trading day closest to calendar month-end.
5. Assign a firm-level `month_count`:
   - only month-end rows get a new integer count,
   - then `month_count` is backfilled to all daily rows in that month.
6. Build `df_firm`, one row per `permno`, with:
   - `permno`
   - `count`: a simple 0-based row number used only for chunk splitting
   - `month_num`: the final available month count for that firm
7. Split `df_firm` into quantile chunks using `count.quantile(...)`.
8. For each chunk:
   - subset the daily dataframe to firms in that chunk,
   - run a worker function on only those firms,
   - return the modified chunk dataframe.
9. Use `multiprocessing.Pool().apply_async(...)` to run one worker per chunk.
10. Wait with `pool.close()` and `pool.join()`.
11. Collect each async result with `.get()`.
12. Concatenate chunk outputs.
13. Drop rows where the target characteristic is missing.
14. Keep only `permno`, `date`, and the characteristic column.
15. Write to a feather file.

The key code idea is:

```python
df = sub_df(0, 1, 0.05)  # 20 chunks
pool = mp.Pool()
p_dict = {}
for i in range(20):
    p_dict[f"p{i}"] = pool.apply_async(worker, (df[f"crsp{i}"], df[f"firm{i}"]))
pool.close()
pool.join()

result = pd.DataFrame()
for i in range(20):
    result = pd.concat([result, p_dict[f"p{i}"].get()])
```

The important insight is that the split is by firm, not by date. That is correct because every rolling window is firm-local. No worker needs another worker's firms.

### Rolling Window Definition

Inside each worker, the code loops:

```python
for firm, count in zip(firm_list["permno"], firm_list["month_num"]):
    for i in range(count + 1):
        temp = df[
            (df["permno"] == firm)
            & (i - 2 <= df["month_count"])
            & (df["month_count"] <= i)
        ]
```

This is a 3-calendar-month rolling daily window, based on `month_count`.

For each firm-month `i`, the window includes:

- current source month `i`
- previous source month `i - 1`
- two-months-prior source month `i - 2`

Rows are skipped if the 3-month daily window has fewer than 21 observations:

```python
if temp["permno"].count() < 21:
    pass
```

The result is written to the final row of the rolling window:

```python
index = temp.tail(1).index
df.loc[index, character] = value
```

Because `temp.tail(1)` is the last trading day closest to that month end, the resulting `date` is effectively the month-end trading date for the source month.

### Character-Specific Calculations In The Reference Scripts

These are the formulas inside the same parallel template.

#### `rvar_capm.py`

Inputs:

- `crsp.dsf`: `permno`, `date`, `ret`
- `ff.factors_daily`: `rf`, `mktrf`
- `crsp.dsedelist`: `dlret`, `dlstdt`

Processing:

```python
retadj = (1 + ret.fillna(0)) * (1 + dlret.fillna(0)) - 1
exret = retadj - rf
```

Rolling window:

```python
Y = exret
X = intercept + mktrf
residuals = (I - X (X'X)^-1 X') Y
rvar_capm = var(residuals, ddof=1)
```

#### `rvar_ff3.py`

Same as `rvar_capm`, but:

```python
X = intercept + mktrf + smb + hml
rvar_ff3 = var(residuals, ddof=1)
```

#### `std_dolvol.py`

Inputs:

- `permno`, `date`, `vol`, `prc`

Rolling window:

```python
std_dolvol = std(log(abs(vol * prc)))
```

#### `beta.py`

Inputs:

- `ret`, `rf`, `mktrf`
- delisting returns

Processing:

```python
retadj = (1 + ret.fillna(0)) * (1 + dlret.fillna(0)) - 1
exret = retadj - rf
```

Rolling window:

```python
Y = exret
X = mktrf
beta = (X' M X)^-1 X' M Y
```

where `M` demeans the observations. This is equivalent to an intercept regression of excess return on market excess return.

Important: the current repo's `beta_builder.py` says it is implementing Green SAS weekly 36-month beta, not GKX's 3-month daily beta. Do not blindly replace it unless the target profile is GKX rather than Green-exact.

#### `bid_ask_spread.py`

Inputs:

- `askhi`, `bidlo`

Rolling window:

```python
baspread = (askhi - bidlo) / mean((askhi + bidlo) / 2)
```

Note: the script assigns a Series-like object to a single row. A careful rewrite should verify whether the intended statistic is the mean of the daily proportional spread:

```python
mean((askhi - bidlo) / ((askhi + bidlo) / 2))
```

Do not assume; validate against Green and/or datashare.

#### `ill.py`

Inputs:

- `ret`, `vol`, `prc`
- delisting returns

Processing:

```python
retadj = (1 + ret.fillna(0)) * (1 + dlret.fillna(0)) - 1
```

Rolling window as written:

```python
ill = mean(abs(retadj) / abs(prc) * vol)
```

Warning: standard Amihud illiquidity is often `abs(ret) / dollar_volume`, so the missing parentheses matter. The reference script uses the expression above. Validate before changing formulas.

#### `maxret_d.py`

Inputs:

- `ret`

Rolling window:

```python
maxret = max(ret)
```

#### `rvar_mean.py`

Inputs:

- `ret`
- delisting returns are merged and `retadj` is created, but the script computes variance of raw `ret`, not `retadj`.

Rolling window:

```python
rvar_mean = var(ret)
```

#### `std_turn.py`

Inputs:

- `vol`, `shrout`

Rolling window:

```python
std_turn = std(vol / shrout)
```

#### `zerotrade.py`

Inputs:

- `vol`, `shrout`

Rolling window:

```python
countzero = 1 if vol == 0 else 0
turn = vol / shrout
turn = inf if turn == 0 else turn
zerotrade = (countzero + ((1 / turn) / 480000)) * 21 / number_of_daily_rows
```

Warning: the script again assigns a vector-like expression into a single final row. A careful rewrite should verify whether the intended output is the sum of the daily zero-trade expression across the rolling window, which is the more natural reading of the Liu-style zero trading measure. Validate against benchmark output.

### Which Current Repo Builders Should Be Modified Or Reviewed

The current repo has two relevant implementation locations:

- `Character_Builders/_shared/green_builders.py`
- `Character_Builders/_shared/rvar_factor_builders.py`
- `Character_Builders/_shared/beta_builder.py`

The following existing repo characters should be reviewed for this parallel/chunked daily-processing approach:

| Character | Current repo location | Reason to modify/review |
| --- | --- | --- |
| `baspread` | `green_builders.py` daily block | Currently computed by SQL monthly grouping; GKX pattern uses 3-month rolling firm windows. |
| `ill` | `green_builders.py` daily block | Same daily 3-month rolling pattern in GKX. Also verify formula parentheses. |
| `maxret` | `green_builders.py` daily block | Same daily 3-month rolling pattern in GKX. |
| `rvar_mean` | `green_builders.py` daily block | Same daily 3-month rolling pattern in GKX; current SQL grouping appears one-month. |
| `std_dolvol` | `green_builders.py` daily block | Same daily 3-month rolling pattern in GKX; user specifically asked about this. |
| `std_turn` | `green_builders.py` daily block | Same daily 3-month rolling pattern in GKX. |
| `zerotrade` | `green_builders.py` daily block | Same daily 3-month rolling pattern in GKX; verify intended aggregation. |
| `rvar_capm` | `rvar_factor_builders.py` | Currently loops serially by `permno`; should be parallelized by firm chunks. |
| `rvar_ff3` | `rvar_factor_builders.py` | Same as `rvar_capm`; should share one generic parallel residual-variance engine. |
| `beta` | `beta_builder.py` | Current implementation loops serially by `permno` and month. Parallelize if keeping Green weekly beta; do not confuse with GKX 3-month daily beta. |
| `betasq` | `beta_builder.py` | Depends on `beta`; no separate parallel work needed if generated from beta. |

### Characters In GKX Folder That Use This Exact Multiprocessing Pattern

These are the scripts in `GKX_Xiu_or_Xin_he` that use `multiprocessing.Pool`, firm chunks, and rolling daily windows:

```text
beta.py                 -> beta
bid_ask_spread.py       -> baspread
ill.py                  -> ill
maxret_d.py             -> maxret
rvar_mean.py            -> rvar_mean / retvol-style raw return variance
rvar_capm.py            -> rvar_capm
rvar_ff3.py             -> rvar_ff3
std_dolvol.py           -> std_dolvol
std_turn.py             -> std_turn
zerotrade.py            -> zerotrade
```

Other files in that folder may be slow or important, but they do not use this same multiprocessing design.

### Recommended Repo Design For The Next Agent

Do not copy the GKX scripts verbatim. Instead, build a reusable engine.

Recommended module:

```text
Character_Builders/_shared/parallel_daily_windows.py
```

Recommended responsibilities:

1. Load daily data once per relevant family.
2. Add month-end trading-day labels and `month_count`.
3. Build the firm inventory with `permno`, chunk id, and `month_num`.
4. Split by `permno` into balanced chunks.
5. Run a top-level worker function per chunk.
6. Concatenate only compact result rows, not full modified daily chunks.
7. Return a dataframe keyed by:

```text
permno, source_yyyymm, source_date, character
```

Then existing panel alignment can merge this to monthly signal rows using `source_yyyymm`.

### Important Improvement Over GKX's Original Code

GKX's workers return the entire daily chunk with one value filled into a row. That is memory-heavy.

For this repo, workers should return only result rows:

```text
permno, source_yyyymm, source_date, value
```

This will reduce inter-process pickle traffic and memory pressure.

### Windows-Safe Multiprocessing Guidance

This repo is used on Windows. The next agent must keep multiprocessing Windows-safe.

Rules:

- Worker functions must be defined at module top level.
- Do not define worker functions inside another function.
- Protect script entry points with `if __name__ == "__main__":`.
- For library functions called by the pipeline, use `concurrent.futures.ProcessPoolExecutor` or `multiprocessing.get_context("spawn").Pool`.
- Pass only the chunk dataframe and a small spec object to each worker.
- Avoid relying on Unix fork semantics or global mutable data.
- Add a `--workers` CLI flag and an environment fallback such as `STOCK_CHARACTERS_WORKERS`.
- Default to something conservative like `min(os.cpu_count() or 1, 8)`, not always all cores.
- Allow `--workers 1` for debugging and reproducibility.

### Proposed Generic Worker Contract

Use one generic worker for simple rolling statistics and one for rolling regressions.

Simple rolling-stat worker:

```text
worker_daily_stat(chunk, firm_list, spec)
```

Where `spec` defines:

- `character`
- `window_months`, usually 3
- `min_obs`, usually 21
- required input columns
- calculation function

Regression worker:

```text
worker_residual_or_beta(chunk, firm_list, spec)
```

Where `spec` defines:

- dependent variable column
- factor columns
- whether to compute beta or residual variance
- `window_months`
- `min_obs`

### Suggested Implementation Steps

1. Create the shared daily rolling-window engine.
2. First port `std_dolvol` because it is simple and was explicitly requested.
3. Validate `std_dolvol` over a small sample against the current output and, if possible, against Green/GKX.
4. Port `rvar_capm` and `rvar_ff3` to the same chunking engine.
5. Port `rvar_mean`, `std_turn`, `maxret`, `baspread`, `ill`, and `zerotrade`.
6. Parallelize current Green `beta_builder.py` separately, because its current intended method is Green weekly 36-month beta, not GKX 3-month daily beta.
7. Add `--workers` to relevant CLIs and pass it from `build_all_implemented_characters.py`.
8. Add a small deterministic sample test with `workers=1` and `workers=2` and assert identical sorted outputs.

### Formula And Benchmark Caution

The user wants exact Green first. GKX's multiprocessing pattern is useful for speed, but the formulas may not always be the Green formulas.

So the next agent should separate:

- processing architecture: adopt from GKX
- formula definitions: validate against Green SAS first
- GKX modifications: only after Green baseline is trusted

In other words: use GKX's firm-chunk parallel design, but do not automatically use GKX's formulas unless the target profile is explicitly GKX.
