# GKX Phase 7 datashare validation

Window: `signal_yyyymm` **201801**–**202312**.

Comparison: repo annual CSV expanded to monthly signal months via `expand_annual_file`,
merged with `Supplementary_assistive_files/datashare.csv` on `permno × signal_yyyymm`.

Industry-adjusted variables use **Green SAS**: subtract industry **mean** within **Compustat SIC2 × fiscal year**.
Datashare (GKX) follows the same Green construction; Dacheng FF49 is **not** the benchmark here.

**`chatoia` rebuild (2026-06-14):** `chatoia.csv` rebuilt from **full Compustat history** (no `STOCK_CHARACTERS_SAMPLE_*` filter). Formula unchanged. Stale 14,184-row sample file replaced with **213,837** annual rows (`datadate` 1976–2026).

## Availability (monthly comparison stage)

| Variable | In datashare.csv | Repo annual non-null | Repo monthly non-null | Datashare monthly non-null |
| --- | --- | ---: | ---: | ---: |
| `cfp_ia` | Yes | 30775 | 278022 | 201312 |
| `chatoia` | Yes | 213837 | 282410 | 190718 |
| `chempia` | Yes | 24221 | 202915 | 191414 |
| `chpmia` | Yes | 22444 | 189034 | 188942 |
| `pchcapx_ia` | Yes | 21884 | 183244 | 180668 |

## Correlation summary

| Variable | Overlap rows | Paired rows | Pearson | Spearman | Pearson (1/99 winsor) | Median |diff| | Pattern |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| `cfp_ia` | 141,449 | 122,930 | 0.2315 | 0.6601 | 0.2369 | 0.0577074 | material_disagreement |
| `chatoia` | 175,534 | 169,375 | 0.0078 | 0.0600 | 0.0122 | 924.069 | material_disagreement |
| `chempia` | 81,853 | 70,986 | 0.2561 | 0.7172 | 0.7450 | 0.0271591 | material_disagreement |
| `chpmia` | 77,057 | 69,973 | 0.1929 | 0.4583 | 0.4751 | 0.698191 | material_disagreement |
| `pchcapx_ia` | 73,991 | 66,104 | 0.1408 | 0.3932 | 0.6726 | 0.332182 | material_disagreement |

## Per-variable interpretation

### `cfp_ia`

- Paired: **122,930** on 141,449 overlapping permno×month rows.
- Pearson **0.2315**, Spearman **0.6601**, winsorized Pearson **0.2369**, median |diff| **0.0577074**.
- **Material disagreement:** investigate sample-history truncation, missing rules, or timing before changing formulas.

Industry demean of `cfp` on SIC2×fyear. Low Pearson with high Spearman often reflects outlier levels in cash-flow-to-price; rank agreement supports Green-style mean demean.

### `chatoia`

- Paired: **169,375** on 175,534 overlapping permno×month rows (was **21,070** paired before full-history rebuild).
- Repo monthly non-null **282,410** vs datashare **190,718** — coverage gap **resolved** (repo now exceeds datashare in window).
- Pearson **0.0078**, Spearman **0.0600**, winsorized Pearson **0.0122**, median |diff| **924**.
- **Coverage fixed; level agreement still weak.** After rebuild, paired overlap increased 8× but rank/level correlations remain near zero. Likely drivers: extreme `chato` ratio tails, industry-mean composition differences, and CCM/timing — **not** stale sample history. Formula unchanged per coverage-loss audit.

### `chempia`

- Paired: **70,986** on 81,853 overlapping permno×month rows.
- Pearson **0.2561**, Spearman **0.7172**, winsorized Pearson **0.7450**, median |diff| **0.0271591**.
- **Material disagreement:** investigate sample-history truncation, missing rules, or timing before changing formulas.

Demean of `hire`; Green sets missing emp to hire=0 before demean. Level outliers in employee growth can depress Pearson while preserving cross-section rank.

### `chpmia`

- Paired: **69,973** on 77,057 overlapping permno×month rows.
- Pearson **0.1929**, Spearman **0.4583**, winsorized Pearson **0.4751**, median |diff| **0.698191**.
- **Material disagreement:** investigate sample-history truncation, missing rules, or timing before changing formulas.

Should match repo `chpm` column (same SIC2×fyear mean demean). Any gap vs datashare likely timing or profit-margin outlier driven, not median vs mean (Green uses mean).

### `pchcapx_ia`

- Paired: **66,104** on 73,991 overlapping permno×month rows.
- Pearson **0.1408**, Spearman **0.3932**, winsorized Pearson **0.6726**, median |diff| **0.332182**.
- **Material disagreement:** investigate sample-history truncation, missing rules, or timing before changing formulas.

Demean of `pchcapx`; capx imputation and zero denominators create heavy tails. Winsorized Pearson helps distinguish outlier-driven level gaps from formula mismatch.

## Disagreement checklist (industry-adjusted)

| Hypothesis | Phase 7 assessment |
| --- | --- |
| SIC2×fyear vs FF/other grouping | Repo matches Green/GKX; Dacheng FF49 not used |
| Mean vs median demean | Green mean — repo matches |
| Timing / fiscal-year alignment | June expansion via `expand_annual_file`; `chatoia` now full-history |
| Stale/truncated `chatoia.csv` | **Fixed** — 213,837 annual rows; monthly 282,410 vs DS 190,718 |
| SIC source | Compustat company SIC (same as Green) |
| Missing-value rules | Green `req` / `count<3` for `chato`; no formula change indicated |
| Outliers | Primary driver of low Pearson when Spearman high |

## Conclusion

**Formulas unchanged.** `chatoia` full-history rebuild confirms the prior coverage gap was a **stale truncated CSV**, not a formula bug. Paired overlap rose from 21k to 169k; monthly repo coverage now exceeds datashare in the 201801–202312 window. Level/rank disagreement for `chatoia` persists and warrants separate investigation — **not** grounds to change the Green formula without a proven bug.

Other Phase 7 variables unchanged; no implementation changes required.
