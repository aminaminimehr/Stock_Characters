# Release notes — repository restructuring (2026-06)

## Summary

The repository is reorganized around two goals:

1. **Green replication** (primary benchmark vs Green SAS output).
2. **Configurable datashare alignment** for `bm`, `operprof`, `cfp` via `--profile datashare` — not hard-coded.

`bm_ia` replication is **abandoned**.

## What changed

### Pipeline configuration
- New `pipeline_config.py` with profiles: **`green`**, **`datashare`**, **`research`**.
- `run_full_pipeline.py` accepts `--profile` and forwards sample dates, CCM flags, universe screen.
- Shell scripts honor `STOCK_CHARACTERS_PROFILE`.

### Datashare profile (`--profile datashare`)
- Sample start **1957-01-01** (via `STOCK_CHARACTERS_SAMPLE_START`).
- **No** Green joint `mve & mom1m & bm` universe screen.
- Builds HXZ `book_to_market` and `operating_profitability` (+ full Green library for `cfp`).
- Skips research panel by default.

### Documentation
- **`docs/CONFIGURATION.md`** — full flags reference.
- **`docs/methodology/`** — authoritative methodology (updated formula doc for datashare mapping).
- **`docs/gkx/archive/`** — historical phase audits moved out of the way.
- **`docs/gkx/README.md`** — index of active datashare/Green reports.

### Scripts
- Reorganized into `scripts/validation/`, `scripts/rebuild/`, `scripts/audits/`, `scripts/archive/`.
- New **`scripts/validation/validate_datashare_universe.py`** — permno coverage + correlation for bm/operprof/cfp.

### Compustat sample window
- Removed hard-coded `1975` floor from `ANNUAL_COMPUSTAT_WHERE`; default start is **1975-01-01** via
  `output_paths.get_sample_bounds()`, overridable to **1957** for datashare.

### Experimental code
- `Character_Builders/Dacheng_datashare/` marked experimental (wrong model for this datashare.csv).
- `Green_SAS_Replication/` remains a reference cross-check, not the production path.

## What you should run on the server

```bash
git pull
export WRDS_USER=...
export PGPASSFILE=~/.pgpass
export STOCK_CHARACTERS_PROFILE=datashare
export STOCK_CHARACTERS_WORKERS=8
bash run_full_pipeline.sh

python scripts/validation/validate_datashare_universe.py
python scripts/validation/compare_panel_final_vs_green.py
```

Optional: extend `cfp` pre-1975 with `scripts/rebuild/rebuild_green_cfp_full_history.py --annual-start 1957-01-01`.

## Known open items

- **`ms`**: Green replication still at median monthly ρ ≈ 0.58.
- **Datashare universe gap**: datashare has ~32.8k permnos vs ~18.7k in Green output — profile datashare + validation script quantify residual gap.
- **Imputation**: research panel still uses inline imputation; unification with `Imputation/` module pending.
