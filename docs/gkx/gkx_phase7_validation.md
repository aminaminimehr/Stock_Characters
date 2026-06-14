# GKX Phase 7 validation (Batch C — industry-adjusted)

Industry grouping: **Compustat SIC2 × fiscal year**, subtract industry **mean** (Green SAS).

- Flat outputs/*.csv count: **0**
- Signal panel characteristic columns: **106** (was 101)
- Complete panel characteristic columns: **106** (was 101)

Sample build: `STOCK_CHARACTERS_SAMPLE_START=2018-01-01`, `END=2023-12-31`.

## Raw CSV checks

| Character | Rows | Coverage | datadate range |
|-----------|-----:|---------:|----------------|
| cfp_ia | 30,775 | 100% | 2018-01-31 .. 2023-12-31 |
| chatoia | 14,184 | 100% | 2019-06-30 .. 2023-12-31 |
| chempia | 24,221 | 100% | 2018-10-31 .. 2023-12-31 |
| chpmia | 22,444 | 100% | 2018-10-31 .. 2023-12-31 |
| pchcapx_ia | 21,884 | 100% | 2018-10-31 .. 2023-12-31 |

`chatoia` starts later due to Green `count < 3` rule for `chato`.

## Panel merge checks

All five characteristics present in signal and complete prediction panels.

## Notes

- Industry adjustment follows Green SAS (`sic2` × `fyear`, mean demean), not Dacheng FF49.
- Existing `chpm` column unchanged; additive `chpmia` GKX column added.
- Phase 1–6 variables not otherwise modified.

## datashare.csv comparison

See [`gkx_phase7_datashare_validation.md`](gkx_phase7_datashare_validation.md).

All five variables exist in datashare. Under the 2018–2023 sample build, level Pearson correlations are moderate to weak; winsorized Pearson and Spearman are stronger for several variables. Gaps are attributed to **truncated-sample industry means** and **truncated firm history** (especially `chatoia`), not formula bugs. **Formulas unchanged.**
