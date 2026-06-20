# GKX Phase 5 methodology notes (Green primary)

Batch: `realestate`, `obklg`, `chobklg`

Implementation reference priority: **Green SAS** (`Supplementary_assistive_files/SAS_codes/Greens_code.sas`) > **GKX `accounting_100.py`** > GKX character list.

Phase 1–4 variables are **not** modified.

See also: `docs/gkx/gkx_deferred_audit_realestate_obklg_chobklg.md`.

---

## 1. `realestate` — Real-estate holdings (Tuzel 2010)

| Item | Detail |
| --- | --- |
| **Green formula** | L190–191: `(fatb + fatl) / ppegt`; if `ppegt` missing, `(fatb + fatl) / ppent` |
| **GKX** | L503–506: same |
| **Compustat** | `fatb`, `fatl`, `ppegt`, `ppent` |
| **Full-history lookup** | No |
| **Missing rules** | Not in Green `req` array — valid from first row |
| **Timing** | Annual fiscal → June-expanded monthly signals |
| **GKX / datashare** | In GKX gap audit and `datashare.csv` |
| **Ambiguity** | Low |

---

## 2. `obklg` — Order backlog scaled by assets

| Item | Detail |
| --- | --- |
| **Green formula** | L194: `ob / ((at + lag(at)) / 2)` |
| **GKX** | L508–509: same |
| **Compustat** | `ob`, `at`, `lag(at)` |
| **Full-history lookup** | No |
| **Missing rules** | Green `req` array — missing when `count=1` |
| **Timing** | Annual → June-expanded monthly |
| **GKX / datashare** | Green/chars60 only; not in GKX datashare |
| **Data note** | `ob` is sparse in Compustat (~13% of recent annual rows) |
| **Ambiguity** | Low |

---

## 3. `chobklg` — Change in order backlog scaled by assets

| Item | Detail |
| --- | --- |
| **Green formula** | L195: `(ob − lag(ob)) / ((at + lag(at)) / 2)` |
| **GKX** | L511–513: same |
| **Compustat** | `ob`, `at`, lags |
| **Full-history lookup** | No |
| **Missing rules** | Green `req` array — missing when `count=1` |
| **Timing** | Annual → June-expanded monthly |
| **GKX / datashare** | Green/chars60 only; not in GKX datashare |
| **Ambiguity** | Low |
