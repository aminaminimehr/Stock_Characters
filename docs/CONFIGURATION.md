# Configuration reference

All pipeline behavior is controlled by **profiles** (recipes) plus **CLI flags** and **environment variables**.
The universe/link/window filters have **no silent defaults** — five flags are required, supplied either
explicitly or via a profile. Use `--profile green|datashare|research` or set `STOCK_CHARACTERS_PROFILE`.

Implementation: `pipeline_config.py`, wired through `Character_Panels/run_full_pipeline.py`.

---

## Required flags & recipes

`run_full_pipeline.py` requires five global flags. A profile fills all five; explicit flags override the
profile. If neither flags nor a profile are supplied, the pipeline errors and lists the missing flags, then
prints the resolved values at startup.

| Flag | Meaning | Green recipe | datashare recipe |
|---|---|---|---|
| `--ccm-linktypes` | CCM linktype filter (all builders) | `LU,LC,LD,LF,LN,LO,LS,LX` | `LU,LC` |
| `--ccm-linkprim` | CCM linkprim filter; `ALL` = no filter | `ALL` | `P,C` |
| `--crsp-shrcd` | CRSP share-code filter | `10,11` | `10,11` |
| `--crsp-exchcd` | CRSP exchange-code filter | `1,2,3` | `1,2,3` |
| `--sample-start` | WRDS download window start | `1975-01-01` | `1957-01-01` |

`--sample-end` is optional (open-ended = latest available).

**Flags are global — one set applies to every builder (Green and HXZ).** A single global `--ccm-linkprim`
forces a trade-off: `ALL` (Green recipe) changes HXZ `bm`/`operprof`/`cfp` vs a primary-link build; `P,C`
(datashare recipe) changes Green characters vs a broad-link Green SAS build. The legacy Green SAS 2015
link-date cap has been removed, so links from any start year are kept — re-baseline against `datashare.csv`
after upgrading (the old `PREV.md` benchmark no longer applies).

The CRSP share/exchange filters and CCM link filters are read from environment variables by every builder
(see Environment variables below), so standalone builder scripts also honor them when the env is set.

---

## Profiles

| Profile | Purpose | Sample start | CCM linktypes | CCM linkprim | Green universe | Research panel |
|---|---|---|---|---|---|---|
| **`green`** | Replicate Green SAS library | 1975-01-01 | broad (`LU,LC,LD,LF,LN,LO,LS,LX`) | `ALL` | Off unless `--green-universe` | Yes |
| **`datashare`** | Full library + datashare alignment | **1957-01-01** | `LU,LC` | `P,C` | **Off** (sparse panel) | **No** |
| **`research`** | Ranked 1957+ ML panel | 1975-01-01 | broad | `ALL` | Off | Yes |

All profiles set `--crsp-shrcd 10,11 --crsp-exchcd 1,2,3`. HXZ builders run under the same global flags as Green.

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

### Datashare build (full library, 1957+, sparse universe)

Builds **all** Green + HXZ characters. Differs from `green` only in sample window (1957+),
no Green joint universe screen, and no ranked research panel.

```bash
python Character_Panels/run_full_pipeline.py \
  --wrds-user "$WRDS_USER" \
  --profile datashare \
  --sample-start 1957-01-01 \
  --sample-end 2021-12-31 \
  --no-green-universe \
  --skip-ibes \
  --workers 8
```

Use `--skip-special` / `--skip-daily` only for quick debugging — not for production builds.

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
| `--profile` | none | `green`, `datashare`, or `research` (fills the 5 required flags) |
| `--ccm-linktypes` | (required¹) | CCM linktype filter for all builders |
| `--ccm-linkprim` | (required¹) | CCM linkprim filter for all builders; `ALL` = no filter |
| `--crsp-shrcd` | (required¹) | CRSP share codes, e.g. `10,11` |
| `--crsp-exchcd` | (required¹) | CRSP exchange codes, e.g. `1,2,3` |
| `--sample-start` | (required¹) | WRDS lower date (`YYYY-MM-DD`) |
| `--sample-end` | none | Optional WRDS upper date |
| `--skip-build` | off | Rebuild panels only from existing CSVs |
| `--skip-ibes` | on | Skip IBES-dependent `re` |
| `--resume` | off | `--skip-existing` + `--skip-annual-monthly` on Green bulk build |
| `--workers` | env or CPU | Parallel workers for beta/rvar/event builders |
| `--green-universe` | off | Drop rows missing Green `bm`, `mom1m`, `mve`/`mvel1`/`me` |
| `--no-green-universe` | — | Force screen off |
| `--skip-special` | off | Debug only: skip beta/rvar/ear/ms |
| `--skip-daily` | off | Debug only: skip daily-CRSP monthly chars |

¹ Required unless a `--profile` (or `STOCK_CHARACTERS_PROFILE`) supplies them. Enforced by
`validate_required()`; resolved values are printed at startup.

### Character builder flags (`build_all_implemented_characters.py`)

These mirror the pipeline flags for standalone runs; `run_full_pipeline.py` forwards them and sets the
matching env vars. The Green path no longer hard-codes its CCM set — it honors `--ccm-linktypes`/
`--ccm-linkprim` like every other builder.

| Flag | Default | Description |
|---|---|---|
| `--ccm-linktypes` | `LU,LC` (argparse) | CCM linktypes; also sets `STOCK_CHARACTERS_CCM_LINKTYPES` |
| `--ccm-linkprim` | `P,C` (argparse) | CCM linkprim; `ALL` = no filter; sets `STOCK_CHARACTERS_CCM_LINKPRIM` |
| `--crsp-shrcd` | `10,11` (env) | CRSP share codes; sets `STOCK_CHARACTERS_CRSP_SHRCD` |
| `--crsp-exchcd` | `1,2,3` (env) | CRSP exchange codes; sets `STOCK_CHARACTERS_CRSP_EXCHCD` |
| `--skip-existing` | off | Skip CSVs that already exist |
| `--skip-annual-monthly` | off | Skip monthly/daily character blocks |
| `--skip-ibes` | off | Skip IBES |
| `--sample-start` / `--sample-end` | env / 1975 fallback | WRDS date window via `sql_date_filter` |

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
| `STOCK_CHARACTERS_CCM_LINKTYPES` | CCM linkers | CCM linktype filter (set by profile / `--ccm-linktypes`) |
| `STOCK_CHARACTERS_CCM_LINKPRIM` | CCM linkers | CCM linkprim filter; `ALL`/unset = no filter |
| `STOCK_CHARACTERS_CRSP_SHRCD` | CRSP SQL filters | CRSP share codes (set by profile / `--crsp-shrcd`); fallback `10,11` |
| `STOCK_CHARACTERS_CRSP_EXCHCD` | CRSP SQL filters | CRSP exchange codes (set by profile / `--crsp-exchcd`); fallback `1,2,3` |
| `STOCK_CHARACTERS_DEFAULT_ANNUAL_START` | `output_paths.py` | Default `1975-01-01` when no sample start set |
| `STOCK_CHARACTERS_WORKERS` | Parallel **compute** (beta regressions, rvar, ear) | Default `min(cpu, 8)` |
| `STOCK_CHARACTERS_WRDS_DOWNLOAD_WORKERS` | Parallel **WRDS** dsf chunk downloads | Default `4` (separate from compute) |
| `STOCK_CHARACTERS_WRDS_PERMNO_CHUNK` | WRDS `dsf` IN-clause size | Default `400` (smaller = fewer timeouts) |
| `RESUME=1` | `run_full_pipeline.sh` | Adds `--resume` |
| `SKIP_IBES=1` | shell scripts | Adds `--skip-ibes` |
| `GREEN_UNIVERSE=1` | shell scripts | Adds `--green-universe` |
| `SAMPLE_START` / `SAMPLE_END` | shell scripts | Forwarded to pipeline |

---

## CCM linking

| Context | Link types | Link primaries |
|---|---|---|
| Green recipe (`--profile green`) | `LU,LC,LD,LF,LN,LO,LS,LX` | `ALL` (no filter) |
| datashare recipe (`--profile datashare`) | `LU,LC` | `P,C` |
| Override | `--ccm-linktypes` / `--ccm-linkprim` | CLI (global, all builders) |

Both Green and HXZ linkers honor the global `--ccm-linktypes` / `--ccm-linkprim` (read from
`STOCK_CHARACTERS_CCM_LINKTYPES` / `_LINKPRIM` by `load_ccm_links_green`). The Green SAS 2015/1950 link-date
cap has been removed. HXZ `attach_ccm_links` dedups to one primary permno per `(gvkey, datadate)`, so it stays
well-defined when `linkprim=ALL`.

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
| Exchange | `--crsp-exchcd 1,2,3` | same |
| Share code | `--crsp-shrcd 10,11` | same |
| Price floor | none | none |
| Financial exclusion | none | none |
| Joint screen `mve & mom1m & bm` | optional `--green-universe` | **never** |
| Panel style | wide merge; optional screen | **sparse** (keep rows with partial missingness) |

Exchange and share-code filters are now the required `--crsp-exchcd` / `--crsp-shrcd` flags (read from
`STOCK_CHARACTERS_CRSP_EXCHCD` / `_SHRCD` by every CRSP query), no longer hard-coded per builder.

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
