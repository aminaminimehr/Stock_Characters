# GKX deferred-character methodology audit

Batch under review: `realestate`, `obklg`, `chobklg`

Phase 1–4 variables are **not** modified by this audit or subsequent Phase 5 work.

---

## Executive recommendation

| Character | Methodology clarity | In GKX datashare | Recommendation |
|-----------|--------------------:|------------------:|----------------|
| **realestate** | Clear | Yes | **Implement now** (GKX predictor) |
| **obklg** | Clear | No | **Implement now** (Green/chars60; not GKX) |
| **chobklg** | Clear | No | **Implement now** (Green/chars60; not GKX) |

All three formulas match between Green SAS and GKX `accounting_100.py`. No formula ambiguity blocks implementation. The main caveat is **Compustat sparsity** for `fatb`/`fatl` (`realestate`) and especially `ob` (`obklg`, `chobklg`).

---

## 1. `realestate` — Real-estate holdings (Tuzel 2010)

| Item | Detail |
| --- | --- |
| **Green SAS** | L190–191: `realestate = (fatb + fatl) / ppegt`; if `ppegt` missing, `(fatb + fatl) / ppent` |
| **GKX** | L503–506: identical |
| **Compustat** | `fatb`, `fatl`, `ppegt`, `ppent` |
| **Lag / timing** | None; level ratio at fiscal `datadate` |
| **Missing rules** | Not in Green `req` array — valid from first row when inputs exist; NaN if numerator/denominator missing or zero denominator |
| **Full-history lookup** | No |
| **datashare.csv** | **Yes** (`realestate`) |
| **GKX** | Listed in GKX gap audit missing set |
| **Data availability** | ~66% of 2018–2023 annual rows have `fatb` or `fatl` populated (WRDS spot check) |
| **Ambiguity** | Low — Green/GKX agree on ppegt vs ppent fallback |

---

## 2. `obklg` — Order backlog scaled by assets (O'Brien & Tan 2015)

| Item | Detail |
| --- | --- |
| **Green SAS** | L194: `obklg = ob / ((at + lag(at)) / 2)` |
| **GKX** | L508–509: identical; lags by `permno` |
| **Compustat** | `ob`, `at`, `lag(at)` |
| **Lag / timing** | `gvkey` lag on `at`; average assets denominator |
| **Missing rules** | Green `req` array (L228–230) — **missing when `count=1`** |
| **Full-history lookup** | No |
| **datashare.csv** | **No** |
| **GKX** | Not a GKX datashare predictor; Green/chars60 + GKX annual output |
| **Data availability** | `ob` populated in ~13% of 2018–2023 annual rows — expect **low coverage** |
| **Ambiguity** | Low — follow Green `gvkey` lags |

---

## 3. `chobklg` — Change in order backlog scaled by assets

| Item | Detail |
| --- | --- |
| **Green SAS** | L195: `chobklg = (ob − lag(ob)) / ((at + lag(at)) / 2)` |
| **GKX** | L511–513: identical structure; `permno` lags |
| **Compustat** | `ob`, `at`, lags |
| **Lag / timing** | One-year change in `ob`; same `avg(at)` denominator as `obklg` |
| **Missing rules** | Green `req` array — **missing when `count=1`** |
| **Full-history lookup** | No |
| **datashare.csv** | **No** |
| **GKX** | Not a GKX datashare predictor; Green/chars60 + GKX annual output |
| **Data availability** | Same sparse `ob` as `obklg` |
| **Ambiguity** | Low |

---

## GKX-focused build scope

- **Include in GKX pipeline:** `realestate` only (datashare + gap audit).
- **Include in Green/chars60 expansion:** `obklg`, `chobklg` — implement for catalog completeness; do not expect datashare validation.

Phase 5 proceeds with all three because methodology is unambiguous; coverage limits are documented, not blocking.
