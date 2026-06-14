# GKX `age` fix validation (201801–202312 sample build)

Sample window: `STOCK_CHARACTERS_SAMPLE_START=2018-01-01`, `END=2023-12-31`.  
`invest` and `egr` formulas were **not** changed.

## Bug

`age` was computed as `groupby(gvkey).cumcount() + 1` on the **sample-filtered** annual Compustat panel returned by `load_annual_compustat()`. Because `sql_date_filter()` applies `STOCK_CHARACTERS_SAMPLE_*` at the SQL layer, each firm's count restarted near 1 in sample-mode builds.

## Fix

Added `load_annual_age_lookup()`: a lightweight WRDS pull of `(gvkey, datadate)` only, using the standard annual Compustat screens from 1975 onward **without** the sample window. Green `count` is computed on that full panel and merged onto the sample-filtered annual panel by `(gvkey, datadate)`.

## Age distribution (201801–202312 expanded panel)

| Metric | Before fix | After fix | GKX datashare |
|--------|----------:|----------:|--------------:|
| Median | 2 | **15** | 18 |
| Max | 6 | **49** | 59 |
| Mean (paired overlap) | 1.81 | **20.40** | 20.60 |

## datashare.csv agreement (after fix)

| Metric | Value |
|--------|------:|
| Paired rows | 123,215 |
| Pearson | **0.972** |
| Spearman | **0.980** |
| Mean monthly cross-sectional Spearman | **0.981** |
| Exact match rate | **61.4%** |
| Mean absolute gap | **1.66 years** |

## Other checks

- Flat `outputs/*.csv` count: **0**
- `age` present in rebuilt signal and complete prediction panels
- `invest` / `egr` construction unchanged (Green-aligned)
