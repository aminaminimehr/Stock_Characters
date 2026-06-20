# GKX Phase 1 validation

- Flat outputs/*.csv count: **0**

## Raw CSV checks

- `invest`: rows=23,077, nonnull=23,077, coverage=100.0%, datadate=2019-01-31 00:00:00..2023-12-31 00:00:00, missing=[]
- `egr`: rows=24,166, nonnull=24,166, coverage=100.0%, datadate=2018-10-31 00:00:00..2023-12-31 00:00:00, missing=[]
- `chinv`: rows=23,872, nonnull=23,872, coverage=100.0%, datadate=2018-10-31 00:00:00..2023-12-31 00:00:00, missing=[]
- `absacc`: rows=24,177, nonnull=24,177, coverage=100.0%, datadate=2018-10-31 00:00:00..2023-12-31 00:00:00, missing=[]
- `age`: rows=30,851, nonnull=30,851, coverage=100.0%, datadate=2018-01-31 00:00:00..2023-12-31 00:00:00, missing=[]

## Panel merge checks

- `invest` in signal panel: True; in complete panel: True
- `egr` in signal panel: True; in complete panel: True
- `chinv` in signal panel: True; in complete panel: True
- `absacc` in signal panel: True; in complete panel: True
- `age` in signal panel: True; in complete panel: True

## datashare.csv comparison (sample window)

- `invest`: {'character': 'invest', 'overlap_rows': 77575, 'paired_rows': 68826, 'pearson': 0.19223612991394787, 'spearman': 0.8556436375027532}
- `egr`: {'character': 'egr', 'overlap_rows': 81637, 'paired_rows': 72883, 'pearson': 0.08859978482811852, 'spearman': 0.8767347763234605}
- `chinv`: {'character': 'chinv', 'overlap_rows': 80677, 'paired_rows': 72001, 'pearson': 0.7366422819818277, 'spearman': 0.8288940356574487}
- `absacc`: {'character': 'absacc', 'overlap_rows': 81720, 'paired_rows': 72942, 'pearson': 0.7841684123288694, 'spearman': 0.9249853640512546}
- `age`: {'character': 'age', 'overlap_rows': 141750, 'paired_rows': 123215, 'pearson': 0.06111452389800196, 'spearman': 0.08022090390648992}

## Notes

- Validation build used WRDS sample window `2018-01-01` to `2023-12-31` (Compustat filter via `STOCK_CHARACTERS_SAMPLE_*`).
- `age` is a cumulative gvkey count from first Compustat row; a truncated sample window resets counts, so low datashare agreement for `age` is expected under sample mode. Full-history builds should align better.
- `invest` and `egr` show high Spearman but low Pearson versus datashare, consistent with rank-preserving construction differences (e.g., `ppegt` vs `ppent` fallback for `invest`, scaling/outliers for `egr`).
- `chinv` and `absacc` show strong Pearson and Spearman agreement in the 2018–2023 window.
- datashare `DATE` is `YYYYMMDD`; comparisons map to `signal_yyyymm` via integer division by 100.
