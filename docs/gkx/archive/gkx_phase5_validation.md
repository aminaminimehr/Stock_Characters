# GKX Phase 5 validation

- Flat outputs/*.csv count: **0**
- Signal panel characteristic columns: **88** (was 85)
- Complete panel characteristic columns: **94** (was 91)

Sample build: `STOCK_CHARACTERS_SAMPLE_START=2018-01-01`, `END=2023-12-31`.

## Raw CSV checks

| Character | Rows | Coverage | datadate range |
|-----------|-----:|---------:|----------------|
| realestate | 18,714 | 100% | 2018-01-31 .. 2023-12-31 |
| obklg | 4,009 | 100% | 2019-01-31 .. 2023-12-31 |
| chobklg | 3,933 | 100% | 2019-01-31 .. 2023-12-31 |

`obklg` / `chobklg` start at 2019 because Green `req`-array rules require one prior fiscal year (`ob`, `lag(ob)`, `avg(at)`).

## Panel merge checks

All three characteristics present in signal and complete prediction panels.

## datashare.csv comparison (201801–202312)

| Character | Paired rows | Pearson | Spearman | Notes |
|-----------|------------:|--------:|---------:|-------|
| realestate | 66,629 | **0.95** | **0.96** | GKX datashare benchmark |
| obklg | — | — | — | Not in datashare.csv |
| chobklg | — | — | — | Not in datashare.csv |

## Notes

- `obklg` and `chobklg` are Green/chars60 only; sparse `ob` coverage is expected.
- Phase 1–4 variables were not modified in this batch.
