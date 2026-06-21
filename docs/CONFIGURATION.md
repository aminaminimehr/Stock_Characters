# Configuration reference

All pipeline behavior is controlled by **profiles** (presets) plus **CLI flags** and **environment variables**.
Nothing is hard-coded for datashare replication — use `--profile datashare` or set
`STOCK_CHARACTERS_PROFILE=datashare`.

Implementation: `pipeline_config.py`, wired through `Character_Panels/run_full_pipeline.py`.

---

## Profiles

| Profile | Purpose | Sample start | Green universe screen | Research panel | HXZ builders |
|---|---|---|---|---|---|
| **`green`** (default) | Replicate Green SAS library | 1975-01-01 (default) | Off unless `--green-universe` | Yes | All 4 |
| **`datashare`** | Match `datashare.csv` for bm/operprof/cfp | **1957-01-01** | **Off** (sparse panel) | **No** | `book_to_market`, `operating_profitability` only |
| | | | | **Skips** beta/rvar/ear/daily-CRSP chars | |
| **`research`** | Ranked 1957+ ML panel | 1975-01-01 (default) | Off | Yes | All 4 |

### Datashare column mapping (bm_ia out of scope)

| `datashare.csv` | Repository column | Builder |
|---|---|---|
| `bm` | `book_to_market` | `HXZ_BM_Generalized` (FF-June timing) |
| `operprof` | `operating_profitability` | `HXZ_OPE_Generalized` |
| `cfp` | `cfp` | Green `_shared/green_builders.py` |
| `bm_ia` | — | **Not replicated** |

---

## Quick commands

### Green replication (benchmark vs Green SAS output)

```bash
export WRDS_USER=your_user
export PGPASSFILE=~/.pgpass
python Character_Panels/run_full_pipeline.py --wrds-user "$WRDS_USER" --profile green
# Optional exact Green final sample:
python Character_Panels/run_full_pipeline.py --wrds-user "$WRDS_USER" --profile green --green-universe
```

### Datashare-like build (1957+, sparse universe)

```bash
export STOCK_CHARACTERS_PROFILE=datashare
bash run_full_pipeline.sh
# or:
python Character_Panels/run_full_pipeline.py --wrds-user "$WRDS_USER" --profile datashare
```

### Validate datashare universe + correlation

```bash
python scripts/validation/validate_datashare_universe.py \
  --datashare Supplementary_assistive_files/datashare.csv \
  --panel outputs/panels/all_character_signal_panel.csv
```

### Green benchmark validation

```bash
python scripts/validation/compare_panel_final_vs_green.py
```

### Extend Green `cfp` history (server / WRDS)

```bash
python scripts/rebuild/rebuild_green_cfp_full_history.py \
  --wrds-user "$WRDS_USER" \
  --annual-start 1957-01-01
```

---

## CLI flags (`run_full_pipeline.py`)

| Flag | Default | Description |
|---|---|---|
| `--wrds-user` | (required) | WRDS PostgreSQL username |
| `--profile` | `green` | `green`, `datashare`, or `research` |
| `--skip-build` | off | Rebuild panels only from existing CSVs |
| `--skip-ibes` | on | Skip IBES-dependent `re` |
| `--resume` | off | `--skip-existing` + `--skip-annual-monthly` on Green bulk build |
| `--sample-start` | profile default | Override WRDS lower date (`YYYY-MM-DD`) |
| `--sample-end` | none | Override WRDS upper date |
| `--workers` | env or CPU | Parallel workers for beta/rvar/event builders |
| `--green-universe` | off | Drop rows missing Green `bm`, `mom1m`, `mve`/`mvel1`/`me` |
| `--no-green-universe` | — | Force screen off |
| `--ccm-linktypes` | profile default | Override CCM link types |
| `--ccm-linkprim` | profile default | Override CCM link primaries (HXZ; Green uses broad links) |

### Character builder flags (`build_all_implemented_characters.py`)

| Flag | Default | Description |
|---|---|---|
| `--ccm-linktypes` | `LU,LC` in argparse; Green path uses Green SAS set internally | Passed for API compatibility |
| `--ccm-linkprim` | `P,C` | Passed for quarterly/special builders |
| `--skip-existing` | off | Skip CSVs that already exist |
| `--skip-annual-monthly` | off | Skip monthly/daily character blocks |
| `--skip-ibes` | off | Skip IBES |
| `--sample-start` / `--sample-end` | env / 1975 default | WRDS date window via `sql_date_filter` |

### Panel flags (`build_all_character_panel.py`)

| Flag | Description |
|---|---|
| `--green-universe` | Green SAS final screen on merged panel |
| `--legacy-june-annual` | Force June expansion for all annual CSVs (legacy) |

---

## Environment variables

| Variable | Used by | Description |
|---|---|---|
| `WRDS_USER` / `WRDS_USERNAME` | WRDS connection | PostgreSQL username |
| `PGPASSFILE` | WRDS connection | Path to `.pgpass` |
| `STOCK_CHARACTERS_PROFILE` | `run_full_pipeline` | Default profile if `--profile` omitted |
| `STOCK_CHARACTERS_SAMPLE_START` | SQL filters | Set automatically by profile / `--sample-start` |
| `STOCK_CHARACTERS_SAMPLE_END` | SQL filters | Optional upper bound |
| `STOCK_CHARACTERS_DEFAULT_ANNUAL_START` | `output_paths.py` | Default `1975-01-01` when no sample start set |
| `STOCK_CHARACTERS_WORKERS` | Parallel builders | Worker count |
| `STOCK_CHARACTERS_WRDS_PERMNO_CHUNK` | WRDS `dsf` IN-clause size | Default `400` (smaller = fewer timeouts) |
| `RESUME=1` | `run_full_pipeline.sh` | Adds `--resume` |
| `SKIP_IBES=1` | shell scripts | Adds `--skip-ibes` |
| `GREEN_UNIVERSE=1` | shell scripts | Adds `--green-universe` |
| `SAMPLE_START` / `SAMPLE_END` | shell scripts | Forwarded to pipeline |

---

## CCM linking

| Context | Link types | Link primaries |
|---|---|---|
| Green annual/quarterly (production) | `LU,LC,LD,LF,LN,LO,LS,LX` | none (Green SAS) |
| HXZ / datashare bm & operprof | `LU,LC` (default) | `P,C` |
| Override | `--ccm-linktypes` / `--ccm-linkprim` | CLI |

See `docs/methodology/03_linking.md`.

---

## Timing conventions

| Character family | Convention | Configurable? |
|---|---|---|
| Green annual (bulk) | Rolling months 7–19 after `datadate` | Per-stem in `timing.py`; `--legacy-june-annual` forces June for all |
| HXZ (`book_to_market`, etc.) | FF-June: Jun y+1 .. May y+2 | Fixed per stem in `timing.py` |
| Green quarterly | Lag in `quarterly_builders.py` | Not yet a CLI flag |
| Monthly CRSP | Native monthly keys | — |

See `docs/methodology/02_timing.md`.

---

## Universe / permno filters

| Filter | Green profile | Datashare profile |
|---|---|---|
| Exchange | `exchcd 1–3` (in builders) | same |
| Share code | `shrcd 10,11` | same |
| Price floor | none | none |
| Financial exclusion | none | none |
| Joint screen `mve & mom1m & bm` | optional `--green-universe` | **never** |
| Panel style | wide merge; optional screen | **sparse** (keep rows with partial missingness) |

See `docs/gkx/datashare_universe_comparison.md`.

---

## Imputation (research panel only)

FF49 industry median imputation + rank to `[-1,1]` in `build_research_panel_1957.py`.
See `docs/methodology/07_imputation.md`.

---

## Scripts layout

| Folder | Purpose |
|---|---|
| `scripts/validation/` | Run regularly (Green + datashare checks) |
| `scripts/rebuild/` | Maintenance rebuilds (e.g. full-history `cfp`) |
| `scripts/audits/` | Historical investigative audits |
| `scripts/archive/` | Superseded phase validators and scratch tools |
