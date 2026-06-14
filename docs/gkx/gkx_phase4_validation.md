# GKX Phase 4 validation

- Flat outputs/*.csv count: **0**
- Signal panel characteristic columns: **85** (was 80)
- Complete panel characteristic columns: **91** (was 86)

Sample build: `STOCK_CHARACTERS_SAMPLE_START=2018-01-01`, `END=2023-12-31`.

## Raw CSV checks

| Character | Rows | Coverage | datadate range |
|-----------|-----:|---------:|----------------|
| saleinv | 18,841 | 100% | 2018-01-31 .. 2023-12-31 |
| salerec | 28,752 | 100% | 2018-01-31 .. 2023-12-31 |
| quick | 29,978 | 100% | 2018-01-31 .. 2023-12-31 |
| tang | 29,379 | 100% | 2018-01-31 .. 2023-12-31 |
| sin | 30,851 | 100% | 2018-01-31 .. 2023-12-31 |

## Panel merge checks

All five characteristics present in signal and complete prediction panels.

## datashare.csv comparison (201801–202312)

| Character | Paired rows | Pearson | Spearman | Notes |
|-----------|------------:|--------:|---------:|-------|
| saleinv | 80,985 | 0.53 | **0.99** | Outlier pattern |
| salerec | 117,485 | 0.52 | **0.98** | Outlier pattern |
| quick | 119,152 | 0.17 | **0.98** | Outlier pattern; Green act/lct imputation |
| tang | 116,204 | **0.99** | **0.98** | Strong level agreement |
| sin | 123,215 | **0.94** | **0.94** | Binary indicator; Pearson ≈ Spearman |

## Notes

- Low Pearson / high Spearman on ratio variables (`saleinv`, `salerec`, `quick`) matches Phase 1 disagreement audit (outlier-driven level differences).
- `tang` shows strong Pearson and Spearman — Green-only formula aligns well with datashare.
- `sin` is 0/1; high agreement suggests SIC/NAICS rules match GKX datashare.
- Phase 1–3 variables were not modified.
- `realestate`, `obklg`, `chobklg` deferred pending methodology audit.
