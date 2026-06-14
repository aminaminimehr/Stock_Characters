# GKX Phase 1 disagreement audit (`invest`, `egr`, `age`)

Sample window: `201801`–`202312` (`signal_yyyymm`).  
Comparison: repo annual builder + `expand_annual_file` vs local `datashare.csv` (GKX).  
**No formulas were changed for this audit.**

Reproduce diagnostics: `python scripts/audit_gkx_disagreement.py`

---

## Executive summary

| Character | Spearman | Pearson (raw) | Pearson (winsor 1/99) | Primary driver of disagreement |
|-----------|----------|---------------|------------------------|--------------------------------|
| **invest** | 0.86 | 0.19 | **0.78** | **Outliers / extreme levels**, not rank or timing |
| **egr** | 0.88 | 0.09 | **0.84** | **Outliers / extreme levels**, not rank or timing |
| **age** | 0.08 | 0.06 | 0.06 | **Sample-history truncation** (repo age 1–4 vs GKX 1–59) |

**Conclusion:** For `invest` and `egr`, the current Green-aligned implementation is **economically equivalent in rank/cross-section** to GKX/datashare; low Pearson is **not** evidence of a wholesale formula bug. For `age`, the near-zero correlation is **not** a formula mismatch—it reflects comparing a **truncated-history validation build** against GKX’s **full-history** firm age.

---

## 1. Line-by-line implementation comparison

### 1.1 `invest`

| Dimension | **Our repo** (`green_builders.py`) | **Green SAS** (`Greens_code.sas` L165–166) | **Dacheng/Xiu** (`accounting_100.py` L390–396) |
|-----------|-----------------------------------|---------------------------------------------|------------------------------------------------|
| **Numerator (ppegt present)** | `(ppegt − lag(ppegt)) + (invt − lag(invt))` | Same | `(ppegt − ppent_l1) + (invt − invt_l1)` **≠ Green** |
| **Numerator (ppegt missing)** | `(ppent − lag(ppent)) + (invt − lag(invt))` | Same | Same |
| **Denominator** | `lag(at)` | `lag(at)` | `at_l1` (= lag(at)) |
| **Lag key** | `gvkey` | `gvkey` (SAS `lag()` within `by gvkey`) | `permno` |
| **Zero denominator** | `safe_divide` → NaN | SAS `/` → missing | Direct division |
| **First observation** | Set NaN (`count=1` rule) | Set missing (`count=1`) | No explicit first-row mask |
| **Winsorization** | None at build | None at build | None at build |
| **CCM** | `attach_ccm_links` at `datadate` | CCM at `datadate` | CCM at `datadate`; dedup by `linkprim`, latest `datadate` per `(permno, yearend)` |
| **Monthly timing** | June of `(calendar_year(datadate)+1)` for 12 months | `datadate+7mo ≤ date < datadate+20mo`, dedupe latest | `jdate = datadate + 4 months`; merge CRSP; **forward-fill** to all months |
| **Sample floor** | `datadate ≥ 1975-01-01` (+ optional sample env) | `datadate ≥ 1975` | `datadate ≥ 1959` |

**Reference alignment:** We follow **Green**, not Dacheng’s `ppegt` branch. Dacheng uses `ppent_l1` instead of `ppegt_l1` when `ppegt` is non-null—a known deviation from Green documented in `docs/gkx/gkx_phase1_methodology.md`.

---

### 1.2 `egr`

| Dimension | **Our repo** | **Green SAS** (L167) | **Dacheng/Xiu** (L398–400) |
|-----------|-------------|----------------------|----------------------------|
| **Formula** | `(ceq − lag(ceq)) / lag(ceq)` | Same | Same |
| **Lag key** | `gvkey` | `gvkey` | `permno` |
| **Zero denominator** | `safe_divide` | SAS `/` | Direct division |
| **First observation** | NaN | Missing (`count=1`) | No explicit mask |
| **Winsorization** | None | None | None |
| **Monthly timing** | Same June expansion as above | Green 7–19 month window | Dacheng +4mo + ffill |

**Reference alignment:** Formula matches **both Green and Dacheng**. Main structural differences are **lag grouping** (`gvkey` vs `permno`) and **monthly availability mapping**.

---

### 1.3 `age`

| Dimension | **Our repo** | **Green SAS** (L81–84, L147) | **Dacheng/Xiu** (L230–231) |
|-----------|-------------|------------------------------|----------------------------|
| **Definition** | `groupby(gvkey).cumcount() + 1` | SAS `count` within `gvkey` (starts 1) | **`# data_rawa['count'] = ...` commented out** |
| **First observation** | 1 (valid) | 1 | Not computed in `accounting_100.py` |
| **Monthly timing** | June expansion | Green 7–19 month window | Not in Dacheng annual output list |
| **GKX datashare** | — | Consistent with Green full-history count | Age in datashare likely from **Green-style** pipeline, not Dacheng script |

**Reference alignment:** Our formula matches **Green SAS**. Dacheng’s public `accounting_100.py` does **not** export `age`; GKX `datashare.csv` age behaves like **Green full-history** counts (median ≈ 18 in 2018–2023).

---

## 2. Correlation diagnostics (201801–202312)

### 2.1 `invest`

| Metric | Value |
|--------|------:|
| Paired rows | 68,826 |
| Pearson (raw) | 0.192 |
| Spearman (raw) | **0.856** |
| Pearson (winsor 1/99) | **0.780** |
| Pearson (global percentile ranks) | **0.856** |
| Mean monthly cross-sectional Spearman | **0.860** |
| Median monthly cross-sectional Spearman | **0.884** |

**Outliers**

| Metric | Value |
|--------|------:|
| Pearson after trimming top 1% \|diff\| | **0.859** |
| Pearson on top 1% \|diff\| only | 0.129 |
| Median \|repo − GKX\| | **0.000** |
| Share with \|diff\| > 1 | 0.2% |

**Timing-shift sensitivity** (repo `signal_yyyymm` shifted):

| shift | paired | pearson | spearman |
| ---: | ---: | ---: | ---: |
| -6 | 91,417 | 0.122 | 0.589 |
| -3 | 80,147 | 0.158 | 0.724 |
| +0 | 68,826 | 0.192 | 0.856 |
| +1 | 65,084 | 0.204 | **0.906** |
| +3 | 57,510 | 0.172 | 0.798 |
| +6 | 46,293 | 0.124 | 0.604 |

**Interpretation:** Rank agreement is strong and stable month-to-month. Raw Pearson collapses because a **small tail** of observations has large level differences (median diff = 0). Winsorization and trimming restore Pearson to ~0.86. This pattern is **classic outlier-driven Pearson failure**, not rank-preserving scaling. Timing shifts of ±1–2 months change Spearman modestly (+1 month peaks at 0.91); timing is secondary to outliers.

**Likely sources of outlier pairs (invest):**

1. **Dacheng `ppegt` branch** `(ppegt − ppent_l1)` vs Green `(ppegt − ppegt_l1)` for firms with both series populated.
2. **`permno` vs `gvkey` lags** when identifier history splits/merges.
3. **CCM deduplication** differences at fiscal dates.
4. Minor **availability-window** differences (Green 7–19mo vs our June-start 12mo block vs Dacheng +4mo ffill).

---

### 2.2 `egr`

| Metric | Value |
|--------|------:|
| Paired rows | 72,883 |
| Pearson (raw) | 0.089 |
| Spearman (raw) | **0.877** |
| Pearson (winsor 1/99) | **0.843** |
| Pearson (global percentile ranks) | **0.877** |
| Mean monthly cross-sectional Spearman | **0.877** |
| Median monthly cross-sectional Spearman | **0.944** |

**Outliers**

| Metric | Value |
|--------|------:|
| Pearson after trimming top 1% \|diff\| | **0.875** |
| Pearson on top 1% \|diff\| only | 0.100 |
| Median \|repo − GKX\| | **0.000** |
| Share with \|diff\| > 1 | 3.3% |

**Timing-shift sensitivity:**

| shift | paired | pearson | spearman |
| ---: | ---: | ---: | ---: |
| +0 | 72,883 | 0.089 | 0.877 |
| +1 | 68,894 | 0.090 | **0.936** |

**Interpretation:** Same pattern as `invest`. Formula is identical across Green and Dacheng; **low Pearson is overwhelmingly outlier-driven**. `egr` has more large-diff pairs than `invest` (3.3% vs 0.2% with \|diff\|>1), consistent with **explosive ratios when `lag(ceq)` is small**—a few extreme equity-growth observations destroy Pearson while ranks stay aligned.

**Likely sources of outlier pairs (egr):**

1. **Small / near-zero `lag(ceq)`** denominators (division spikes).
2. **`permno` vs `gvkey` lag** after corporate actions.
3. Timing / ffill differences (secondary).

---

### 2.3 `age`

| Metric | Value |
|--------|------:|
| Paired rows | 123,215 |
| Pearson (raw) | 0.061 |
| Spearman (raw) | 0.080 |
| Pearson (winsor 1/99) | 0.061 |
| Mean monthly cross-sectional Spearman | **−0.025** |

**Level comparison**

| | Repo | GKX datashare |
|---|-----:|---:|
| Mean | 1.81 | 20.60 |
| Median | 2 | 18 |
| Max | 4 | 59 |
| Exact match rate | 0.8% | — |
| Within ±1 year | 6.2% | — |
| Within ±5 years | 26.1% | — |
| Mean absolute gap | **18.8 years** | — |
| Median \|diff\| | **16 years** | — |

**Timing-shift sensitivity:** Shifting ±6 months leaves Spearman near 0.08—**timing is not the issue**.

**Interpretation:** Near-zero correlation is explained entirely by **sample-history dependence**:

- Validation build used `STOCK_CHARACTERS_SAMPLE_START=2018-01-01`, so `cumcount()` runs only on 2018–2023 Compustat rows → repo age ∈ **[1, 6]**.
- GKX datashare age uses **full Compustat history from 1959/1975** → age ∈ **[1, 59]**, median ≈ 18 in the comparison window.
- This is a **level offset**, not a rank-preserving transform; winsorization and percentile ranking **cannot** fix it.
- Dacheng’s `accounting_100.py` does not implement age; datashare matches **Green SAS `count`**, not Dacheng Python.

**Recommended implementation (no change yet—documentation only):**

1. Compute `age` on the **full** annual Compustat panel (`datadate ≥ 1975`), then apply CCM and panel expansion.
2. Do **not** apply sample-date filters before the `cumcount()` step (sample bounds may filter outputs afterward).
3. Treat age validation against datashare as **invalid under truncated sample builds**; re-test only after a full-history WRDS run.

---

## 3. Answers to audit questions

### Is the low Pearson primarily outliers (`invest`, `egr`)?

**Yes.** Evidence:

- Median absolute difference = **0** for both.
- Pearson jumps from ~0.09–0.19 (raw) to **0.78–0.84** (winsor) and **0.86–0.88** (trim top 1% diff / percentile ranks).
- Top 1% diff pairs have Pearson ≈ 0.1—those pairs are **not** rank-aligned at all in levels.
- Monthly cross-sectional Spearman ≈ 0.86–0.94 (median even higher).

### Scaling vs timing vs implementation mismatch?

| Factor | invest | egr | age |
|--------|--------|-----|-----|
| Scaling (linear transform) | No — percentile-rank Pearson ≈ Spearman | No | No — level shift ~17 years |
| Timing | Minor (±1mo helps Spearman slightly) | Minor | Ruled out |
| Outliers | **Primary** | **Primary** | N/A |
| Sample truncation | Minor for ranks | Minor for ranks | **Primary** |
| Formula mismatch vs Dacheng | **Yes** for `ppegt` branch only | No | N/A (Dacheng lacks age) |
| Formula mismatch vs Green | **No** | **No** | **No** (full history required) |

### Economic equivalence to Dacheng?

| Character | Economically equivalent? | Notes |
|-----------|-------------------------|-------|
| **invest** | **Rank-equivalent** to GKX; **level-different** in tails | We intentionally follow Green, not Dacheng’s `ppegt−ppent_l1` branch |
| **egr** | **Rank-equivalent** to GKX | Same formula; differences are outliers and micro timing |
| **age** | **Not comparable** under sample build | Full-history Green count needed |

---

## 4. Recommended next steps (diagnostic only—no formula changes)

1. **invest / egr:** Optional follow-up—quantify share of `invest` diff attributable to Dacheng vs Green `ppegt` branch on overlapping Compustat rows (requires recompute, not done here).
2. **age:** Re-validate after full-history build; expect Spearman to rise sharply if implementation remains Green `count`.
3. **Do not** interpret raw Pearson alone for ratio variables with heavy tails; use Spearman, winsorized Pearson, or trimmed diffs for GKX reconciliation.

---

## Appendix: Source locations

| Source | Path |
|--------|------|
| Repo builder | `Character_Builders/_shared/green_builders.py` |
| Panel timing | `Character_Panels/build_all_character_panel.py` → `expand_annual_file` |
| Green SAS | `Supplementary_assistive_files/SAS_codes/Greens_code.sas` |
| Dacheng Python | `Supplementary_assistive_files/Python_codes/Dacheng_Xiu_or_Xin_he/accounting_100.py` |
| GKX reference | `Supplementary_assistive_files/datashare.csv` |
| Audit script | `scripts/audit_gkx_disagreement.py` |
