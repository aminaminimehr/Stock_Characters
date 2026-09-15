# dl_blt_Characters

Flat procedural rebuild of the 95-character GKX datashare signal panel. Each script pulls its own WRDS data (or reads cache), writes one category Parquet under `outputs/characters/`, and the panel step merges everything into `outputs/panel/final_panel.csv`.

There is **no** wrapper or orchestrator — run scripts manually in the order below.

## Layout

| Path | Purpose |
|------|---------|
| `config/` | Hardcoded conventions, winsor lists, FF49 ranges |
| `annual/` | Green annual + HXZ (`bm`, `operprof`, `bm_ia`) |
| `quarterly/` | Green quarterly Compustat characters |
| `monthly/` | Green monthly CRSP characters |
| `daily_monthly/` | CRSP daily → monthly aggregates |
| `daily_weekly_rolling/` | Beta family (`beta`, `betasq`, `idiovol`, `pricedelay`) |
| `event_daily/` | Event-study characters (`ear`, `aeavol`) |
| `annual_quarterly/` | `ms` (Mohanan–Shroff) |
| `excess_returns/` | CRSP excess returns keyed on `target_yyyymm` |
| `panel/` | Merge, winsorize, attach returns → `final_panel.csv` |
| `outputs/cache/` | WRDS pull caches (per script) |
| `outputs/characters/` | Category Parquet outputs |
| `outputs/panel/` | `excess_returns.parquet`, `final_panel.csv` |

## Manual run order

From `Stock_Characters/dl_blt_Characters/` (WRDS credentials required for builder scripts):

```bash
# 1. Category builders (each writes outputs/characters/{stem}.parquet)
python annual/build_annual.py
python quarterly/build_quarterly.py
python monthly/build_monthly.py
python daily_monthly/build_daily_monthly.py
python daily_weekly_rolling/build_beta_family.py
python event_daily/build_event.py
python annual_quarterly/build_ms.py

# 2. Excess returns (writes outputs/panel/excess_returns.parquet)
python excess_returns/build_excess_returns.py

# 3. Final panel (reads 7 character parquets + excess returns)
python panel/build_panel.py

# 4. Optional validation vs Readable_Pipeline
python panel/compare_to_readable.py
```

Steps 1–7 are independent of each other except they all need WRDS access. Step 8 can run in parallel with 1–7. Step 9 requires all seven character Parquets and `excess_returns.parquet`.

## Cache deletion

Scripts cache expensive WRDS pulls under `outputs/cache/`. To force a fresh download, delete the relevant cache file(s) before re-running that script:

```bash
# Refresh everything (full re-pull)
rm -rf outputs/cache/*

# Or delete individual caches, e.g.:
rm outputs/cache/annual_funda.parquet
rm outputs/cache/monthly_msf.parquet
rm outputs/cache/daily_monthly_dsf.parquet
```

Character and panel outputs are **not** cached skip-if-exists in the builders — re-running a builder overwrites its Parquet. Delete `outputs/characters/*.parquet` only if you want to confirm a downstream merge fails when inputs are missing.

To rebuild the final CSV only (no WRDS):

```bash
rm outputs/panel/final_panel.csv
python panel/build_panel.py
```

## Outputs

| File | Description |
|------|-------------|
| `outputs/characters/annual.parquet` | ~61 annual-derived predictors on monthly grid |
| `outputs/characters/quarterly.parquet` | 10 quarterly-derived predictors |
| `outputs/characters/monthly.parquet` | 9 monthly CRSP predictors |
| `outputs/characters/daily_monthly.parquet` | 7 daily-aggregated predictors |
| `outputs/characters/beta_family.parquet` | `beta`, `betasq`, `idiovol`, `pricedelay` |
| `outputs/characters/event.parquet` | `ear`, `aeavol` |
| `outputs/characters/ms.parquet` | `ms` |
| `outputs/panel/excess_returns.parquet` | `permno`, `target_yyyymm`, `excess_return` |
| `outputs/panel/final_panel.csv` | Merged 95-predictor panel + `sic`, `ffi49`, `excess_return` |

## Validation

`panel/compare_to_readable.py` inner-joins `final_panel.csv` to `Readable_Pipeline/03_outputs/panels/all_character_signal_panel.csv` on `(permno, signal_yyyymm)` and prints count, Spearman ρ, and max |Δ| for each shared predictor column.
