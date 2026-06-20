# Task index (run in order)

Check off when done. **Do not skip dependencies.**

| # | Task | Depends on | Where to run | Risk |
|---|------|------------|--------------|------|
| 01 | [Archive historical docs](tasks/01_archive_docs.md) | — | Local | Low (moves only) |
| 02 | [Reorganize scripts/](tasks/02_reorganize_scripts.md) | 01 optional | Local | Medium (path fixes) |
| 03 | [Add pipeline presets module](tasks/03_pipeline_presets.md) | — | Local | Medium (new code) |
| 04 | [Wire presets into run_full_pipeline](tasks/04_wire_presets_pipeline.md) | 03 | Local | Medium |
| 05 | [Write CONFIGURATION.md + README flags](tasks/05_configuration_docs.md) | 03, 04 | Local | Low |
| 06 | [Datashare universe validation script](tasks/06_datashare_universe_validation.md) | 04 | Local + server | Medium |
| 07 | [Extend Green cfp history 1957+](tasks/07_extend_cfp_history.md) | — | Server (WRDS) | Low |
| 08 | [Demote experimental paths, update docs](tasks/08_cleanup_experimental_paths.md) | 01, 05 | Local | Low |
| 09 | [Server full run + validation report](tasks/09_server_run_and_report.md) | 04, 06, 07 | Server | High (time) |
| 10 | [Push to remote + release notes](tasks/10_push_and_release.md) | 09 | Local/git | Low |

## Out of scope (do not assign to Codex unless you change your mind)

- **`bm_ia` replication** — abandoned.
- **Rewriting Green formulas** for characters already at ρ ≥ 0.95 vs Green SAS.
- **Deleting** `Green_SAS_Replication/` (keep as reference).
- **Force-pushing** to `main`.

## Current decisions (locked)

- Datashare mapping: `bm` → `book_to_market`, `operprof` → `operating_profitability`, `cfp` → Green `cfp`.
- Universe: datashare is sparse, 1957+, no Green joint `mve&mom1m&bm` screen.
- Green permnos are a **subset** of datashare (see `docs/gkx/datashare_universe_comparison.md`).
