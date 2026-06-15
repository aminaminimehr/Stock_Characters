# GKX Phase 7 validation (Batch C — industry-adjusted)

Industry grouping: **Compustat SIC2 × fiscal year**, subtract industry **mean** (Green SAS).

**`chatoia` lookup-merge fix (2026-06-15):** commit `4a3fd82` moved `age`/`orgcap` lookups after industry demeaning. Rebuilt `chatoia.csv` (233,644 rows). Datashare Spearman **0.775** (was **0.060** on corrupted file). See `gkx_chatoia_lookup_fix_validation.md`.

- Flat outputs/*.csv count: **0**
- Signal panel characteristic columns: **106**
- Complete panel characteristic columns: **112**

## Raw CSV checks

- `cfp_ia`: rows=30,775, nonnull=30,775, coverage=100.0%, datadate=2018-01-31 00:00:00..2023-12-31 00:00:00, missing=[]
- `chatoia`: rows=233,644, nonnull=233,644, coverage=100.0%, datadate=1976-12-31 00:00:00..2026-04-30 00:00:00, missing=[]
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
- Datashare comparison: run `scripts/validate_gkx_phase7_datashare.py`.
