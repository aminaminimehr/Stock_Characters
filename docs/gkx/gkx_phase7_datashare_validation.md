# GKX Phase 7 datashare validation

Window: `signal_yyyymm` **201801**–**202312** (lightweight sample build 2018–2023).

Comparison: repo annual CSV expanded via `expand_annual_file` vs `Supplementary_assistive_files/datashare.csv`.

Industry-adjusted variables use **Green SAS**: subtract industry **mean** within **Compustat SIC2 × fiscal year**.
Datashare (GKX) follows the same Green construction; Dacheng FF49 is **not** the benchmark here.

**Important context:** This validation run uses a **truncated WRDS sample** (2018–2023). Industry means are computed over the **sample cross-section only**, and firm-level lags (`chato`, `chpm`, etc.) lack full pre-2018 history. GKX datashare is built from **full Compustat history**. Level correlations are therefore expected to be weaker than rank correlations even when formulas match Green.

---

## Availability

| Variable | In datashare.csv | Repo raw non-null | Datashare non-null (window) |
| --- | --- | ---: | ---: |
| `cfp_ia` | Yes | 30,775 | 201,312 |
| `chatoia` | Yes | 14,184 | 190,718 |
| `chempia` | Yes | 24,221 | 191,414 |
| `chpmia` | Yes | 22,444 | 188,942 |
| `pchcapx_ia` | Yes | 21,884 | 180,668 |

All five Phase 7 variables are present in datashare.csv.

---

## Correlation summary

| Variable | Overlap rows | Paired rows | Pearson | Spearman | Pearson (1/99 winsor) | Median \|diff\| | Pattern |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| `cfp_ia` | 141,449 | 122,930 | 0.23 | 0.66 | 0.24 | 0.058 | Moderate rank, weak level |
| `chatoia` | 23,121 | 21,070 | -0.01 | 0.01 | 0.01 | 398 | Near-zero (truncated history) |
| `chempia` | 81,853 | 70,986 | 0.26 | 0.72 | **0.75** | 0.027 | Outlier-driven levels |
| `chpmia` | 77,057 | 69,973 | 0.19 | 0.46 | 0.48 | 0.70 | Sample + outlier levels |
| `pchcapx_ia` | 73,991 | 66,104 | 0.14 | 0.39 | **0.67** | 0.33 | Outlier-driven levels |

---

## Per-variable interpretation

### `cfp_ia`

- **122,930** paired rows on 141,449 overlapping permno×month keys.
- Moderate Spearman (0.66) with low Pearson (0.23); median |diff| is small (0.058).
- **Likely drivers:** truncated-sample industry means shift demeaned levels; cash-flow-to-price heavy tails.
- **Not a grouping bug:** Green/GKX both use SIC2×fyear mean demean.

### `chatoia`

- **21,070** paired rows; Pearson and Spearman near zero; median |diff| very large.
- **Primary driver:** `chato` requires **two prior fiscal years** (Green `count < 3` rule). A 2018–2023 sample build resets firm history, so `chato` and industry demeaning diverge from full-history GKX.
- Secondary: extreme ratio levels inflate |diff| even when ranks are unstable in thin overlap.
- **Not evidence to switch to FF49 or median demean.**

### `chempia`

- **70,986** paired rows; Spearman **0.72**, winsorized Pearson **0.75** vs raw Pearson 0.26.
- Classic **low Pearson / higher winsorized Pearson** pattern: rank-preserving with level outliers in employee growth.
- Median |diff| **0.027** — economically small for most pairs.

### `chpmia`

- **69,973** paired rows; moderate winsorized Pearson (0.48), Spearman 0.46.
- Repo `chpmia` uses the same demean as Green `chpmia`; existing `chpm.csv` was **not rebuilt** in the sample run (249k full-history rows vs 22k `chpmia` sample rows).
- Disagreement driven by **sample industry means** and profit-margin tails, not median-vs-mean or FF grouping.

### `pchcapx_ia`

- **66,104** paired rows; winsorized Pearson **0.67** vs raw Pearson 0.14.
- Cap-ex change ratios have heavy tails; winsorization raises level correlation substantially.
- Industry demean on truncated sample shifts levels vs full-history GKX.

---

## Disagreement checklist (industry-adjusted)

| Hypothesis | Phase 7 assessment |
| --- | --- |
| SIC2×fyear vs FF/other grouping | Repo matches Green/GKX; Dacheng FF49 not used |
| Mean vs median demean | Green mean — repo matches |
| Timing / fiscal-year alignment | June expansion consistent; **sample window** differs from full GKX history |
| SIC source | Compustat company SIC (same as Green) |
| Missing-value rules | Green `req` / `count<3` for `chato`; exacerbated under truncated sample |
| Outliers | Major driver for `chempia`, `pchcapx_ia`; winsorized Pearson much higher |
| Truncated industry means | **Key sample-build artifact** for all five `_ia` variables |

---

## Conclusion

**Formulas unchanged.** Correlation gaps are consistent with:

1. **Truncated-sample industry means** (not full cross-section like GKX datashare).
2. **Truncated firm history** (especially `chatoia`).
3. **Level outliers** (winsorized Pearson often much higher than raw Pearson).

Re-validation after a **full-history WRDS build** is recommended before treating low Pearson as a formula defect.

Re-run: `python scripts/validate_gkx_phase7_datashare.py`
