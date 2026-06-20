# GKX Phase 4 methodology notes (Green primary)

Batch: `saleinv`, `salerec`, `quick`, `tang`, `sin`

Implementation reference priority: **Green SAS** (`Supplementary_assistive_files/SAS_codes/Greens_code.sas`) > **Dacheng `accounting_100.py`** > GKX character list.

Phase 1–3 variables are **not** modified unless a clear bug is found.

**Deferred:** `realestate`, `obklg`, `chobklg` — pending separate methodology audit (require `fatb`, `fatl`, `ob`, etc.).

---

## 1. `saleinv` — Sales-to-inventory

| Item | Detail |
| --- | --- |
| **Green formula** | L187: `saleinv = sale / invt` |
| **Dacheng** | L496–497: same |
| **Compustat** | `sale`, `invt` |
| **Full-history lookup** | No |
| **Denominator** | `invt` |
| **Missing rules** | Valid from first fiscal row; NaN when `invt=0` |
| **Timing** | Annual fiscal → June-expanded monthly signals |
| **Ambiguity** | Low |

---

## 2. `salerec` — Sales-to-receivables

| Item | Detail |
| --- | --- |
| **Green formula** | L186: `salerec = sale / rect` |
| **Dacheng** | L493–494: same |
| **Compustat** | `sale`, `rect` |
| **Full-history lookup** | No |
| **Denominator** | `rect` |
| **Missing rules** | Valid from first row; NaN when `rect=0` |
| **Timing** | Annual → June-expanded monthly |
| **Ambiguity** | Low |

---

## 3. `quick` — Quick ratio

| Item | Detail |
| --- | --- |
| **Green formula** | L179–180 impute missing `act`, `lct`; L183: `quick = (act − invt) / lct` |
| **Dacheng** | L482–483: `(act − invt) / lct` without Green imputation |
| **Compustat** | `act`, `lct`, `che`, `rect`, `invt`, `ap` |
| **Full-history lookup** | No |
| **Denominator** | `lct` (possibly imputed as `ap`) |
| **Missing rules** | Valid from first row; NaN when imputed/raw `lct=0` |
| **Timing** | Annual → June-expanded monthly |
| **Ambiguity** | Follow **Green** act/lct imputation (same helper as Phase 3 `currat`/`pchquick`) |

---

## 4. `tang` — Tangibility (Almeida & Campello 2007)

| Item | Detail |
| --- | --- |
| **Green formula** | L176: `tang = (che + rect×0.715 + invt×0.547 + ppent×0.535) / at` |
| **Dacheng** | Not in `accounting_100.py` output list |
| **Compustat** | `che`, `rect`, `invt`, `ppent`, `at` |
| **Full-history lookup** | No |
| **Denominator** | `at` |
| **Missing rules** | Valid from first row; NaN when `at=0` |
| **Timing** | Annual → June-expanded monthly |
| **Ambiguity** | Low — Green-only coefficients |

---

## 5. `sin` — Sin stocks indicator (Hong & Kacperczyk 2009)

| Item | Detail |
| --- | --- |
| **Green formula** | L177–178: `sin=1` if `(2100≤sic≤2199)` OR `(2080≤sic≤2085)` OR `naics` in (`7132`, `71312`, `713210`, `71329`, `713290`, `72112`, `721120`); else `sin=0` |
| **Dacheng** | Not in `accounting_100.py` |
| **Compustat** | `sic` (from `comp.company`), `naics` (from `comp.company`) |
| **Full-history lookup** | No |
| **Industry/SIC** | Tobacco (21xx), wine (2080–2085), selected NAICS for gaming/hospitality |
| **Missing rules** | Always 0 or 1; missing SIC/NAICS treated as non-sin (0) unless SIC range matches |
| **Timing** | Annual → June-expanded monthly (time-invariant within fiscal year) |
| **Ambiguity** | NAICS stored as numeric in Compustat — compare as zero-padded strings; Green uses character NAICS codes |

---

## Shared notes

- Lag structure unchanged (`gvkey` panel).
- `age` / `orgcap` full-history lookups unchanged.
- Output: `outputs/characteristics/individual/{character}.csv` with standard ID columns.
