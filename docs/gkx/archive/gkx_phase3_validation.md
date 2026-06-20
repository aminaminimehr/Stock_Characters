# GKX Phase 3 validation

- Flat outputs/*.csv count: **0**

Sample build: `STOCK_CHARACTERS_SAMPLE_START=2018-01-01`, `END=2023-12-31`.

## Raw CSV checks

- `pchcapx`: rows=21,884, nonnull=21,884, coverage=100.0%, datadate=2018-10-31..2023-12-31
- `pchsaleinv`: rows=14,659, nonnull=14,659, coverage=100.0%, datadate=2018-10-31..2023-12-31
- `pchquick`: rows=23,452, nonnull=23,452, coverage=100.0%, datadate=2018-10-31..2023-12-31
- `salecash`: rows=30,806, nonnull=30,806, coverage=100.0%, datadate=2018-01-31..2023-12-31
- `currat`: rows=30,227, nonnull=30,227, coverage=100.0%, datadate=2018-01-31..2023-12-31

## Panel merge checks

- All five characteristics present in signal panel (**80** columns) and complete prediction panel.

## datashare.csv comparison (201801–202312)

| Character | Paired rows | Pearson | Spearman | Notes |
|-----------|------------:|--------:|---------:|-------|
| pchcapx | — | — | — | **Not in datashare.csv** |
| pchsaleinv | 47,535 | 0.24 | **0.83** | Outlier pattern |
| pchquick | 70,471 | 0.14 | **0.81** | Outlier pattern |
| salecash | 122,992 | 0.23 | **0.98** | Outlier pattern |
| currat | 120,116 | 0.17 | **0.98** | Outlier pattern |

## Notes

- Low Pearson / high Spearman matches Phase 1 disagreement audit (outlier-driven level differences; ranks align well).
- Phase 1 and Phase 2 variables were not modified.
- `pchcapx` cannot be cross-checked against local datashare (column absent); validation is internal consistency + panel merge only.
