# GKX Phase 3 methodology notes (Green primary)

Batch: `pchcapx`, `pchsaleinv`, `pchquick`, `salecash`, `currat`

Implementation reference priority: **Green SAS** (`Supplementary_assistive_files/SAS_codes/Greens_code.sas`) > **Dacheng `accounting_100.py`** > GKX character list.

Phase 1 and Phase 2 variables are **not** modified in this batch unless a clear bug is found.

---

## 1. `pchcapx` — Change in capital expenditures

| Item | Detail |
| --- | --- |
| **Green formula** | If `capx` missing and `count≥2`: impute `capx = ppent − lag(ppent)`; then `pchcapx = (capx − lag(capx)) / lag(capx)`. |
| **Dacheng** | L459–461: `(capx − capx_l1) / capx_l1`; **no** Green `capx` imputation; lags by `permno`. |
| **Compustat** | `capx`, `ppent`, lags |
| **Full-history lookup** | No (uses same-sample `capx` imputation as `grcapx`) |
| **Denominator** | `lag(capx)` |
| **Missing rules** | Missing when `count=1` (Green `req` array); `safe_divide` → NaN when denominator 0 |
| **Timing** | Annual fiscal → June-expanded monthly signals via panel merge |
| **Ambiguity** | Follow **Green** capx imputation and `gvkey` lags |

---

## 2. `pchsaleinv` — Change in sales-to-inventory

| Item | Detail |
| --- | --- |
| **Green formula** | L188: `pchsaleinv = ((sale/invt) − (lag(sale)/lag(invt))) / (lag(sale)/lag(invt))` |
| **Dacheng** | L499–501: same formula; lags by `permno` |
| **Compustat** | `sale`, `invt`, lags |
| **Full-history lookup** | No |
| **Denominator** | `lag(sale)/lag(invt)` |
| **Missing rules** | Missing when `count=1`; NaN when lag inventory sales ratio is 0 |
| **Timing** | Annual → June-expanded monthly |
| **Ambiguity** | Low — formulas agree; lag key differs (`gvkey` vs `permno`) |

---

## 3. `pchquick` — Change in quick ratio

| Item | Detail |
| --- | --- |
| **Green formula** | L179–180 impute `act`, `lct` if missing; L183–184: `quick = (act−invt)/lct`; `pchquick = (quick − lag(quick)) / lag(quick)` where lag quick uses imputed lag act/lct. |
| **Dacheng** | L485–488: same structure; lags by `permno`; **no** explicit Green `act`/`lct` imputation |
| **Compustat** | `act`, `lct`, `che`, `rect`, `invt`, `ap`, lags |
| **Full-history lookup** | No |
| **Denominator** | Lagged quick ratio `(lag(act)−lag(invt))/lag(lct)` with Green imputation on lagged act/lct |
| **Missing rules** | Missing when `count=1` |
| **Timing** | Annual → June-expanded monthly |
| **Ambiguity** | Follow **Green** act/lct imputation for Phase 3 vars only (Phase 2 `pchcurrat` left unchanged) |

---

## 4. `salecash` — Sales-to-cash

| Item | Detail |
| --- | --- |
| **Green formula** | L185: `salecash = sale / che` |
| **Dacheng** | L490–491: same |
| **Compustat** | `sale`, `che` |
| **Full-history lookup** | No |
| **Denominator** | `che` |
| **Missing rules** | Valid from first row (`count=1` allowed); NaN when `che=0` |
| **Timing** | Annual → June-expanded monthly |
| **Ambiguity** | Low |

---

## 5. `currat` — Current ratio

| Item | Detail |
| --- | --- |
| **Green formula** | L179–181: impute missing `act = che+rect+invt`, `lct = ap`; `currat = act/lct` |
| **Dacheng** | L475–476: `act/lct` without imputation |
| **Compustat** | `act`, `lct`, `che`, `rect`, `invt`, `ap` |
| **Full-history lookup** | No |
| **Denominator** | `lct` (possibly imputed) |
| **Missing rules** | Valid from first row; NaN when imputed/raw `lct=0` |
| **Timing** | Annual → June-expanded monthly |
| **Ambiguity** | Follow **Green** act/lct imputation for `currat` |

---

## Shared notes

- Lag structure: `gvkey`-sorted annual panel (`lag` helper), consistent with existing Green builder.
- `age` / `orgcap` full-history lookups unchanged.
- Output: `outputs/characteristics/individual/{character}.csv` with standard ID columns.
