# GKX Phase 7 validation (Batch C — industry-adjusted)

Industry grouping: **Compustat SIC2 × fiscal year**, subtract industry **mean** (Green SAS).

- Flat outputs/*.csv count: **0** (no stray flat CSVs under `outputs/`)
- Signal panel characteristic columns: **106**
- Complete panel characteristic columns: **112**
- Panels rebuilt after `chatoia` full-history fix: `all_character_signal_panel.csv`, `complete_all_character_prediction_panel.csv`

## `chatoia` full-history rebuild

| Metric | Before (stale sample) | After (full Compustat) |
| --- | ---: | ---: |
| Annual rows | 14,184 | **213,837** |
| `datadate` range | 2019-06-30 .. 2023-12-31 | **1976-12-31 .. 2026-04-30** |
| Monthly non-null (201801–202312) | ~136,133 | **282,410** |
| Paired vs datashare | 21,070 | **169,375** |

Formula unchanged. Rebuild command: full-history WRDS pull with `STOCK_CHARACTERS_SAMPLE_*` unset, `build_character(db, 'chatoia')`.

## Raw CSV checks

- `cfp_ia`: rows=30,775, nonnull=30,775, coverage=100.0%, datadate=2018-01-31 00:00:00..2023-12-31 00:00:00, missing=[]
- `chatoia`: rows=213,837, nonnull=213,837, coverage=100.0%, datadate=1976-12-31 00:00:00..2026-04-30 00:00:00, missing=[]
- `chempia`: rows=24,221, nonnull=24,221, coverage=100.0%, datadate=2018-10-31 00:00:00..2023-12-31 00:00:00, missing=[]
- `chpmia`: rows=22,444, nonnull=22,444, coverage=100.0%, datadate=2018-10-31 00:00:00..2023-12-31 00:00:00, missing=[]
- `pchcapx_ia`: rows=21,884, nonnull=21,884, coverage=100.0%, datadate=2018-10-31 00:00:00..2023-12-31 00:00:00, missing=[]

## Panel merge checks

- `cfp_ia` in signal panel: True; in complete panel: True
- `chatoia` in signal panel: True; in complete panel: True
- `chempia` in signal panel: True; in complete panel: True
- `chpmia` in signal panel: True; in complete panel: True
- `pchcapx_ia` in signal panel: True; in complete panel: True

## Notes

- Industry adjustment follows Green SAS (`sic2` x `fyear`, mean demean), not Dacheng FF49.
- Phase 1-6 variables not modified except additive `chpmia` column.
- `chatoia` rebuilt from full Compustat history; panels refreshed.
- Datashare comparison: `scripts/validate_gkx_phase7_datashare.py` (see `gkx_phase7_datashare_validation.md`).
