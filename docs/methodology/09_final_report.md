# Final Report — Repository Restructuring

Updated: 2026-06-20 after implementation pass.

## Completed

| Item | Status |
|---|---|
| Pipeline profiles (`green`, `datashare`, `research`) | Done — `pipeline_config.py` + `run_full_pipeline.py` |
| Config documentation | Done — `docs/CONFIGURATION.md`, README Configuration section |
| Archive historical `docs/gkx/` audits | Done — `docs/gkx/archive/` |
| Archive `agents review/` | Done — `docs/archive/agents_review/` |
| Reorganize `scripts/` | Done — validation / rebuild / audits / archive |
| Datashare universe validation script | Done — `scripts/validation/validate_datashare_universe.py` |
| Compustat sample start configurable (1957 for datashare) | Done — `output_paths.get_sample_bounds()` |
| Formula docs updated for empirical datashare mapping | Done — `docs/methodology/01_formula_differences.md` |
| `bm_ia` | **Abandoned** — documented everywhere |
| Dacheng_datashare builder | Demoted to experimental / rejected for this datashare.csv |
| Release notes | Done — `docs/RELEASE_NOTES.md` |

## Datashare mapping (locked)

| datashare | repo column | Profile |
|---|---|---|
| `bm` | `book_to_market` | `datashare` |
| `operprof` | `operating_profitability` | `datashare` |
| `cfp` | `cfp` (Green) | `datashare` |

Validate with:

```bash
python scripts/validation/validate_datashare_universe.py
```

## Green validation (unchanged benchmark)

92/95 datashare columns at median monthly ρ ≥ 0.95 vs Green SAS output.
Details: `docs/methodology/08_validation_status.md`.

## Pending (requires WRDS server run)

1. Full `--profile datashare` pipeline rebuild on server.
2. Run `validate_datashare_universe.py` and record results in `docs/gkx/datashare_universe_validation_report.md`.
3. Optional: `scripts/rebuild/rebuild_green_cfp_full_history.py --annual-start 1957-01-01`.
4. Push committed changes to remote (`git push`).

## Open technical debt

- **`ms`** replication (ρ ≈ 0.58 vs Green).
- **Imputation unification** — research panel inline vs `Imputation/` module.
- **HXZ builders** do not use `sql_date_filter` (load full Compustat; not a practical issue for history).

## Push to remote

After server validation:

```bash
git add -A
git commit -m "Add pipeline profiles, reorganize docs/scripts, datashare validation tooling"
git push origin YOUR_BRANCH
```
