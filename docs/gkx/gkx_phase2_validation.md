# GKX Phase 2 validation

- Flat outputs/*.csv count: **0**

## Raw CSV checks

- `grcapx`: rows=16,381, nonnull=16,381, coverage=100.0%, datadate=2019-06-30 00:00:00..2023-12-31 00:00:00, missing=[]
- `pchdepr`: rows=22,072, nonnull=22,072, coverage=100.0%, datadate=2018-10-31 00:00:00..2023-12-31 00:00:00, missing=[]
- `cashpr`: rows=30,712, nonnull=30,712, coverage=100.0%, datadate=2018-01-31 00:00:00..2023-12-31 00:00:00, missing=[]
- `orgcap`: rows=20,391, nonnull=20,391, coverage=100.0%, datadate=2018-10-31 00:00:00..2023-12-31 00:00:00, missing=[]
- `pchcurrat`: rows=19,504, nonnull=19,504, coverage=100.0%, datadate=2018-10-31 00:00:00..2023-12-31 00:00:00, missing=[]

## Panel merge checks

- `grcapx` in signal panel: True; in complete panel: True
- `pchdepr` in signal panel: True; in complete panel: True
- `cashpr` in signal panel: True; in complete panel: True
- `orgcap` in signal panel: True; in complete panel: True
- `pchcurrat` in signal panel: True; in complete panel: True

## datashare.csv comparison (201801–202312)

| Character | Paired rows | Pearson | Spearman |
|-----------|------------:|--------:|---------:|
| grcapx | 23,690 | 0.31 | **0.89** |
| pchdepr | 66,280 | 0.19 | **0.80** |
| cashpr | 122,546 | 0.12 | **0.98** |
| orgcap | 52,263 | **0.94** | **1.00** |
| pchcurrat | 56,681 | 0.42 | **0.80** |

## Notes

- Sample build: `STOCK_CHARACTERS_SAMPLE_START=2018-01-01`, `END=2023-12-31`.
- Signal panel now has **75** characteristic columns (was 70).
- Low Pearson / high Spearman for `grcapx`, `pchdepr`, `cashpr`, `pchcurrat` matches Phase 1 outlier pattern; ranks align well.
- `orgcap` uses full-history recursive accumulation (`load_annual_orgcap_lookup`), similar to the `age` fix.
- `cashpr` is Green-only (not in Dacheng `accounting_100.py`).
- Phase 1 variables (`invest`, `egr`, `chinv`, `absacc`, `age`) were not modified.
