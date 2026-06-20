# GKX Batch C industry-adjustment methodology audit

Batch: `cfp_ia`, `chatoia`, `chempia`, `chpmia`, `pchcapx_ia`

Reference priority: **Green SAS** (`Greens_code.sas`) > GKX `accounting_100.py` > GKX list.

Phase 1–6 variables are **not** modified unless a clear bug is found.

---

## Executive summary

| Question | Answer |
| --- | --- |
| Industry operation | **Subtract industry mean** (not median, rank, or ratio) |
| Green industry group | **`sic2` × `fyear`** — two-digit Compustat SIC |
| SIC source | Compustat `comp.company.sic` → `substr(sic,1,2)` |
| GKX for these five | **Not implemented** in `accounting_100.py` annual output |
| GKX `bm_ia` / `me_ia` | **FF49 × datadate** — differs from Green |
| Repo existing `bm_ia`, `me_ia`, `chpm`, `tb` | **Green-aligned** (`sic2` × `fyear`, mean demean) |
| Imputation module (`Imputation/`) | **Separate** — FF schemes for missing-value median fill, not used in characteristic construction |
| Ambiguity blocking implementation? | **No** — implement per Green |

---

## Two distinct uses of industry classification

### 1. Industry median imputation (NOT this batch)

| Item | Detail |
| --- | --- |
| Location | `Imputation/industry_median_imputation.py`, `Imputation/industry_codes.py` |
| Purpose | Fill **missing** characteristic values |
| Industry | User-selected Fama-French scheme (FF5–FF49) from Compustat SIC |
| Time key | User-provided (`signal_yyyymm`, etc.) |
| Statistic | **Median** within time × industry |
| Used in Green builders? | **No** |

### 2. Industry-adjusted characteristic construction (THIS batch)

| Item | Detail |
| --- | --- |
| Location | Green SAS L241–249; repo `green_builders.py` grouped demean block |
| Purpose | Define the **predictor** as firm value minus industry average |
| Industry | **`sic2` × `fyear`** |
| SIC source | Compustat company SIC at fiscal `datadate` |
| Statistic | **Arithmetic mean** within group |
| Minimum n | None explicit in Green SAS |

---

## Source comparison: industry definition

| Use case | Green SAS | GKX/Xiu | Repo (current) |
| --- | --- | --- | --- |
| `bm_ia`, `mve_ia` / `me_ia` | `sic2` × `fyear`, mean demean | **`ffi49` × `datadate`**, mean demean | Green (`sic2` × `fyear`) |
| `cfp_ia`, `chatoia`, `chempia`, `chpmia`, `pchcapx_ia` | `sic2` × `fyear`, mean demean | Not in annual char list | **To implement** |
| Missing-value imputation | N/A in Green SAS chars | N/A | FF schemes in `Imputation/` only |
| `herf` | `sic2` × `fyear` sales sum | `ffi49` × `datadate` for some steps | Green `sic2` × `fyear` |

**GKX datashare** follows Green-style construction. Implementation uses **Green `sic2` × `fyear`**.

MarkItDown outputs: no additional industry-adjustment detail found beyond standard GKX/Green references.

---

## Per-variable audit

### 1. `cfp_ia`

| Item | Detail |
| --- | --- |
| Base (`cfp`) | Green L144–145: `oancf/mve_f` or WC-accrual cash flow / `mve_f` |
| Adjustment | `cfp_ia = cfp - mean(cfp)` by `sic2`, `fyear` (L247) |
| Operation | Subtract industry **mean** |
| Grouping | SIC2 × fiscal year |
| Timing | Annual fiscal → June-expanded monthly |
| Missing | Base `cfp` missing rules; no extra Green `req` flag for `cfp` at count=1 |
| GKX | `cfp` yes; **`cfp_ia` no** |

### 2. `chatoia`

| Item | Detail |
| --- | --- |
| Base (`chato`) | Green L157: `sale/avg(at) - lag(sale)/avg(lag(at), lag2(at))` |
| Adjustment | `chatoia = chato - mean(chato)` (L244) |
| Operation | Subtract industry **mean** |
| Grouping | SIC2 × fiscal year |
| Missing | Green L236–238: **`chato` missing when `count < 3`** (first two fiscal rows) |
| GKX | `chato` yes (permno lags); **`chatoia` no** |

### 3. `chempia`

| Item | Detail |
| --- | --- |
| Base (`hire`) | Green L153–154: `(emp - lag(emp))/lag(emp)`; missing emp → `hire=0` |
| Adjustment | `chempia = hire - mean(hire)` (L245) |
| Operation | Subtract industry **mean** |
| Grouping | SIC2 × fiscal year |
| Missing | Green `req` array — NaN when `count=1` |
| GKX | `hire` yes; **`chempia` no** |

### 4. `chpmia`

| Item | Detail |
| --- | --- |
| Base (`chpm`) | Green L156: `(ib/sale) - (lag(ib)/lag(sale))` |
| Adjustment | `chpmia = chpm - mean(chpm)` (L244) |
| Operation | Subtract industry **mean** |
| Grouping | SIC2 × fiscal year |
| Missing | Green `req` array — NaN when `count=1` |
| Repo note | Existing column **`chpm` is already demeaned** (= Green `chpmia`); new **`chpmia`** column added without changing `chpm` |
| GKX | `chpm` yes; **`chpmia` no** |

### 5. `pchcapx_ia`

| Item | Detail |
| --- | --- |
| Base (`pchcapx`) | Green L169: `(capx - lag(capx))/lag(capx)` with capx imputation |
| Adjustment | `pchcapx_ia = pchcapx - mean(pchcapx)` (L246) |
| Operation | Subtract industry **mean** |
| Grouping | SIC2 × fiscal year |
| Missing | Green `req` array — NaN when `count=1` |
| GKX | `pchcapx` yes; **`pchcapx_ia` no** |

---

## Implementation decision

Proceed with Green SAS:

```python
sic2 = Compustat sic // 100
group = (fyear, sic2)
char_ia = char - group_mean(char)
```

No Fama-French mapping for these five variables.
