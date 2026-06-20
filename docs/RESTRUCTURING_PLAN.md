# Repository Restructuring Plan

Status: **IMPLEMENTED** (2026-06-20). See `docs/RELEASE_NOTES.md` and `docs/methodology/09_final_report.md`.

Original plan items:

| Item | Status |
|---|---|
| Archive `docs/gkx/` historical files | Done |
| Reorganize `scripts/` | Done |
| `pipeline_config.py` + profiles | Done |
| Wire `run_full_pipeline.py` | Done |
| `docs/CONFIGURATION.md` | Done |
| `validate_datashare_universe.py` | Done |
| Compustat sample start 1957 for datashare | Done |
| Demote `Dacheng_datashare/` | Done |
| Server full run + push | **Pending** (user/server) |

Pending after push:

- Run `--profile datashare` on WRDS server and record validation report.
- Optional imputation unification.
- Resolve `ms` Green replication gap.
