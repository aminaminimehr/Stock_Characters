# Definitions (shared logic)

SQL **templates** only — each builder executes its own query with its own column list.

| Module | Role |
|--------|------|
| `config.py` | Re-exports `pipeline_config` |
| `paths.py` | `03_outputs/` tree |
| `catalog.py` | 95 stems, families, `ANNUAL_FUNDA_ITEMS`, `BUILD_ORDER` |
| `sql_templates.py` | `green_funda_sql`, `crsp_msf_sql`, `fundq_sql`, CCM SQL |
| `wrds_io.py` | Connect, retry, per-stem parquet cache |
| `ccm.py` | Green vs HXZ link attach |
| `annual_runner.py` | Fetch funda/CCM, finalize, write annual CSV |
| `annual_formulas.py` | Green annual formulas (called from each annual builder) |
| `monthly_runner.py` | Per-stem msf + SIC + monthly feature |
| `daily_monthly_runner.py` | Per-stem dsf GROUP BY |
| `quarterly_runner.py` | Per-stem fundq + expand |
| `hxz_runner.py` | `bm`, `operprof` |
| `bm_ia_runner.py` | SIC2 demean from `bm.csv` |
| `beta_runner.py` | Weekly factor panel |
| `event_runner.py` | `ear`, `aeavol` |
| `ms_runner.py` | Mohanram score |
| `timing.py` | Annual rolling / HXZ June expansion |
| `panel.py` | Merge + winsor |
| `winsor.py` | Green hitrim/hilotrim |
