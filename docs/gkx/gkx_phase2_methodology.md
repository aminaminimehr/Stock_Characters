# GKX Phase 2 methodology notes (Green primary)

Batch: `grcapx`, `pchdepr`, `cashpr`, `orgcap`, `pchcurrat`

Implementation reference priority: **Green SAS** (`Supplementary_assistive_files/SAS_codes/Greens_code.sas`) > **Dacheng `accounting_100.py`** > GKX character list.

Phase 1 variables (`invest`, `egr`, `chinv`, `absacc`, `age`) are **not** modified in this batch.

---

## 1. `grcapx` — Growth in capital expenditures

| Item | Detail |
| --- | --- |
| **Green SAS** | L168–170: if `capx` missing and `count≥2`, impute `capx = ppent − lag(ppent)`; `grcapx = (capx − lag2(capx)) / lag2(capx)`; set missing when `count<3`. |
| **Dacheng** | L463–465: same growth formula; **no** `capx` imputation from `ppent`; lags by `permno`. |
| **Compustat** | `capx`, `ppent`, lags |
| **CRSP / CCM** | CCM only |
| **Timing** | Annual fiscal → June-expanded monthly signals |
| **Ambiguity** | Follow **Green** capx imputation and `gvkey` lags; Dacheng omits imputation. |

---

## 2. `pchdepr` — Change in depreciation rate

| Item | Detail |
| --- | --- |
| **Green SAS** | L163: `pchdepr = ((dp/ppent) − (lag(dp)/lag(ppent))) / (lag(dp)/lag(ppent))` |
| **Dacheng** | L451–453: numerator uses `dp_l1/ppent_l1`; denominator uses `dp_l1/ppent` (**current** `ppent`, not lagged) — **differs from Green**. |
| **Compustat** | `dp`, `ppent`, lags |
| **CRSP / CCM** | CCM only |
| **Timing** | Annual → June-expanded monthly |
| **First row** | Missing when `count=1` (Green `req` array) |
| **Ambiguity** | Follow **Green** denominator `lag(dp)/lag(ppent)`. |

---

## 3. `cashpr` — Cash productivity (Palazzo 2012)

| Item | Detail |
| --- | --- |
| **Green SAS** | L127: `cashpr = (mve_f + dltt − at) / che` |
| **Dacheng** | Not in `accounting_100.py` output list |
| **Compustat** | `mve_f` (= `prcc_f × csho`), `dltt`, `at`, `che` |
| **CRSP / CCM** | CCM only |
| **Timing** | Annual → June-expanded monthly |
| **Ambiguity** | Low — Green-only definition |

---

## 4. `orgcap` — Organizational capital (Eisfeldt & Papanikolaou 2013)

| Item | Detail |
| --- | --- |
| **Green SAS** | L297–397: merge BLS CPI by `fyear`; retain `orgcap_1`; if `first.gvkey` then `orgcap_1 = (xsga/cpi)/(0.1+0.15)` else `orgcap_1 = orgcap_1*(1−0.15)+xsga/cpi`; `orgcap = orgcap_1 / ((at+lag(at))/2)`; missing when `count=1`. |
| **Dacheng** | Not in `accounting_100.py` |
| **Compustat** | `xsga`, `at`, `fyear`, CPI lookup |
| **CRSP / CCM** | CCM only |
| **Timing** | Annual → June-expanded monthly |
| **CPI table** | Green embedded CPI 1974–2015; repo extends through 2023 using BLS CPI-U annual averages for post-2015 fiscal years (documented in builder). |
| **Ambiguity** | CPI extension beyond Green table is required for recent samples; follow Green recursion otherwise. |

---

## 5. `pchcurrat` — Change in current ratio

| Item | Detail |
| --- | --- |
| **Green SAS** | L182: `pchcurrat = ((act/lct) − (lag(act)/lag(lct))) / (lag(act)/lag(lct))` |
| **Dacheng** | L479–480: same formula; lags by `permno` |
| **Compustat** | `act`, `lct`, lags |
| **CRSP / CCM** | CCM only |
| **Timing** | Annual → June-expanded monthly |
| **First row** | Missing when `count=1` (Green `req` array) |
| **Ambiguity** | Low — follow Green `gvkey` lags |

---

## Shared notes

- Lag structure: `gvkey`-sorted annual panel (`lag`, `lag2` helpers), consistent with existing Green builder.
- `age` continues to use full-history lookup (`load_annual_age_lookup`); unchanged in Phase 2.
- `orgcap` uses full-history recursive accumulation via `load_annual_orgcap_lookup` (same sample-window rule as `age`).
- Output: `outputs/characteristics/individual/{character}.csv` with standard ID columns.
