# GKX Phase 1 methodology notes (Green primary)

Batch: `invest`, `egr`, `chinv`, `absacc`, `age`

Implementation reference priority: **Green SAS** (`Supplementary_assistive_files/SAS_codes/Greens_code.sas`) > **Dacheng `accounting_100.py`** > GKX character list > HXZ factor documentation.

HXZ `Technical_Document_Factors_HXZ.md` documents q-factor inputs (e.g. investment-to-assets **I/A**). It does **not** define these five GKX/Green annual signals directly.

---

## 1. `invest` — Capital expenditures and inventory (Chen & Zhang 2010)

| Item | Detail |
| --- | --- |
| **Green SAS** | L165–166: `invest = ((ppegt - lag(ppegt)) + (invt - lag(invt))) / lag(at)`; if `ppegt` missing, replace `ppegt` delta with `(ppent - lag(ppent))`. |
| **Dacheng** | `accounting_100.py` ~L390–396: uses `at_l1` denominator; when `ppegt` not null uses `(ppegt - ppent_l1)` (not `ppegt_l1`) — **differs from Green**. |
| **HXZ** | Related concept: I/A = ΔAT / lag(AT) for q-factors — **not identical** to Green `invest`. |
| **Compustat** | `ppegt`, `ppent`, `invt`, `at` (+ lags) |
| **CRSP** | No (annual Compustat only until CCM merge) |
| **CCM** | Yes — attach `permno`/`permco` at `datadate` |
| **Timing** | Raw annual `datadate`; monthly `signal_yyyymm` via June availability in panel merge |
| **Frequency** | Annual fiscal → 12 monthly signal months |
| **Ambiguity** | Follow **Green** delta definitions; Dacheng branch when `ppegt` present is not replicated. |

---

## 2. `egr` — Growth in common shareholder equity

| Item | Detail |
| --- | --- |
| **Green SAS** | L167: `egr = (ceq - lag(ceq)) / lag(ceq)` |
| **Dacheng** | `accounting_100.py` ~L398–400: same formula on `ceq` |
| **HXZ** | Not documented for this acronym |
| **Compustat** | `ceq` (+ lag) |
| **CRSP** | No |
| **CCM** | Yes |
| **Timing** | Annual → June-expanded monthly signals |
| **Frequency** | Annual |
| **Ambiguity** | Low — Green and Dacheng agree |

---

## 3. `chinv` — Change in inventory (Thomas & Zhang 2002)

| Item | Detail |
| --- | --- |
| **Green SAS** | L148: `chinv = (invt - lag(invt)) / ((at + lag(at)) / 2)` |
| **Dacheng** | `accounting_100.py` ~L426–427: `(invt - invt_l1) / ((at + at_l2) / 2)` — **denominator uses t and t-2**, not Green’s t and t-1 average |
| **HXZ** | Not documented |
| **Compustat** | `invt`, `at` (+ lags) |
| **CRSP** | No |
| **CCM** | Yes |
| **Timing** | Annual → June-expanded monthly |
| **Frequency** | Annual |
| **Ambiguity** | Follow **Green** `(at + lag(at))/2` denominator |

---

## 4. `absacc` — Absolute accruals (Bandyopadhyay, Huang & Wirjanto 2010)

| Item | Detail |
| --- | --- |
| **Green SAS** | L146 after `acc`: `absacc = abs(acc)`; `acc` defined L138–139 with `oancf` fallback |
| **Dacheng** | No explicit `absacc` in `accounting_100.py` (GKX uses Green-style `acc` elsewhere) |
| **HXZ** | Not documented |
| **Compustat** | Same as `acc`: `ib`, `oancf`, `act`, `che`, `lct`, `dlc`, `txp`, `dp`, `at` |
| **CRSP** | No |
| **CCM** | Yes |
| **Timing** | Annual → June-expanded monthly |
| **Frequency** | Annual |
| **Ambiguity** | Low — implement `abs(acc)` after existing Green `acc` logic |

---

## 5. `age` — Years since first Compustat coverage (Jiang, Lee & Zhang 2005)

| Item | Detail |
| --- | --- |
| **Green SAS** | L81–84, L147: `count` = observation index within `gvkey` (starts at 1); `age = count` |
| **Dacheng** | Not explicitly in `accounting_100.py` output list |
| **HXZ** | Not documented |
| **Compustat** | Observation count per `gvkey` after sort by `datadate` |
| **CRSP** | No |
| **CCM** | Yes |
| **Timing** | Annual → June-expanded monthly |
| **Frequency** | Annual (monotonic within firm; first year = 1) |
| **Ambiguity** | Low — use `groupby(gvkey).cumcount() + 1` on sorted annual panel |

---

## Shared implementation notes

- First fiscal year per `gvkey`: lag-based variables (`invest`, `egr`, `chinv`, `absacc`) set to missing (consistent with existing Green annual first-row rule).
- `age` is valid from first observation (= 1).
- Output columns in raw CSV: `permno`, `permco`, `gvkey`, `datadate`, `sic`, `fyear`, `{character}`.
- Panel merge adds `signal_yyyymm`, `target_yyyymm` via `expand_annual_file` in `build_all_character_panel.py`.
