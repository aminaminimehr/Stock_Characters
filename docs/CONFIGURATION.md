# Configuration reference

All pipeline conventions are **hardcoded** in `pipeline_config.py`. There are no profiles, no
convention CLI flags, and no `STOCK_CHARACTERS_*` environment overrides for universe/link/sample
settings.

The single entry point is:

```bash
python Character_Panels/run_full_pipeline.py --wrds-user <user>
```

Optional flags: `--workers N` (parallel daily-CRSP builders), `--skip-build` (merge panel only).

---

## Hardcoded conventions

| Constant | Value | Notes |
|---|---|---|
| `SAMPLE_START` | `1950-01-01` | WRDS download lower bound |
| `SAMPLE_END` | `None` | Open-ended (latest available) |
| `CCM_LINKTYPES` | `L*` | Dacheng prefix rule (LC, LU, LD, …) |
| `CCM_LINKPRIM` | `P,C` | Primary CRSP links only |
| `CRSP_SHRCD` | `ALL` | No share-code filter (critical for `bm_ia`) |
| `CRSP_EXCHCD` | `1,2,3` | NYSE, AMEX, NASDAQ |
| `INDUSTRY_AGG` | `post_ccm` | Industry means after CCM merge |
| `SIC_SOURCE` | `comp_company` | `comp.company.sic` on monthly rows |
| `SKIP_IBES` | `True` | No IBES tables |

Winsorization is **always on** during panel merge (`apply_green_winsorization` in
`build_all_character_panel.py`).

---

## Output

| Artifact | Path |
|---|---|
| Per-character CSVs | `outputs/characteristics/individual/*.csv` |
| Signal panel (95 predictors) | `outputs/panels/all_character_signal_panel.csv` |

Column names match GKX `datashare.csv` directly (`bm`, `operprof`, `mve_ia`, `rd_mve`, `retvol`, `ear`, …).

---

## Build order

1. `build_all_implemented_characters.py` — bulk Green/shared builders (92 of 95; excludes `bm`, `operprof`, `bm_ia`)
2. HXZ subprocess: `bm.csv`, `operprof.csv` (June timing)
3. `bm_ia.csv` — SIC2 × month demean of `bm.csv` (WRDS-free)
4. `build_all_character_panel.py` — merge, winsorize, write signal panel

---

## Performance environment variables (optional)

These tune CPU compute only; they do **not** change conventions or WRDS connections.
WRDS `crsp.dsf` downloads are always **sequential on one connection** (see
`Character_Builders/_shared/wrds_chunk_download.py`). Completed chunks are cached under
`outputs/diagnostics/cache/dsf_chunks/` so restarts resume.

| Variable | Purpose |
|---|---|
| `STOCK_CHARACTERS_WORKERS` | CPU workers for beta/ear/aeavol factor estimation (used if `--workers` omitted) |

---

## Validation

```bash
python scripts/validation/compare_panel_vs_gkx_datashare.py
```

Report Spearman **and** sample N **and** unique permnos for every comparison.

---

## Obsolete scripts

Scripts under `scripts/rebuild/` that referenced `--profile research` or trim/research panel builders
are no longer functional after the datashare-only refactor. Use `run_full_pipeline.py` instead.

Historical profile documentation in older `docs/gkx/` reports remains for audit trail but does not
describe the current pipeline interface.
