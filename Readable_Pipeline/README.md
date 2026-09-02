# Readable Pipeline

Human-readable reconstruction of the 95-character GKX datashare signal panel.
Production code under `Character_Builders/` and `Character_Panels/` is **unchanged**.

## Layout

| Folder | Purpose |
|--------|---------|
| `01_definitions/` | Shared SQL templates, CCM, timing, winsor, catalog (not shared WRDS downloads) |
| `02_builders/` | One module per datashare stem (`ep.py`, `bm.py`, …); each runs **its own** WRDS queries on the **full** eligible universe |
| `03_outputs/` | Generated outputs: `single_characters/*.parquet`, `panels/*.csv`, `cache/`, `logs/`, `diagnostics/` |

## Reading order

1. This README
2. `01_definitions/config.py` — hardcoded conventions (from `pipeline_config.py`)
3. `01_definitions/catalog.py` — stem → family, funda items, build order
4. `01_definitions/sql_templates.py` — WHERE/JOIN templates (SELECT lists live in each builder)
5. The character of interest in `02_builders/{stem}.py`
6. `01_definitions/panel.py` — merge + winsor (panel-only)

## Run

```bash
cd Stock_Characters/Readable_Pipeline

# One character (own WRDS round-trips; full cross-section)
python run.py --wrds-user YOUR_USER --character ep

# All 95 (sequential; each stem queries WRDS independently)
python run.py --wrds-user YOUR_USER --all

# Merge existing Parquet files → 95-column panel CSV
python run.py --panel

# Build all then panel
python run.py --wrds-user YOUR_USER --all --panel
```

Per-stem disk cache: `03_outputs/cache/{stem}_funda.parquet` (use `--skip-cache` to force refresh).

Per-stem character outputs: `03_outputs/single_characters/{stem}.parquet`. Final panel: `03_outputs/panels/all_character_signal_panel.csv`.

## Independence

- **Independent** = one stem, one (or few) WRDS jobs, minimal column list — **not** one permno or one industry.
- Industry-adjusted chars (`cfp_ia`, `indmom`, `herf`, `ms`, `bm_ia`) still use the full post-CCM cross-section for benchmarks.
- Formulas match production (`green_builders`, HXZ scripts, `quarterly_builders`, etc.).

## Validation

Compare to production:

```bash
python 01_definitions/compare_to_production.py  # stem-level when prod CSVs exist
python ../scripts/validation/compare_panel_vs_gkx_datashare.py \
  --panel 03_outputs/panels/all_character_signal_panel.csv \
  --datashare ../Supplementary_assistive_files/datashare.csv
```
