# GKX `ms` predictor audit (Mohanram vs Piotroski)

Conducted before Phase 6 (Batch A + B) implementation. **`ms` was not implemented in this phase.**

---

## Summary recommendation

**Implement as a distinct GKX predictor in a future quarterly batch — do not alias to `ps`.**

| Question | Finding |
| --- | --- |
| Truly missing? | **Yes** — no `ms` column in repository panels |
| Mohanram Score? | **Yes** — GKX list #50: Mohanram (2005, RAS), Compustat **Quarterly** |
| Exists under another name? | **No** — not an alias of `ps`, `abr`, or any current column |
| Overlaps / duplicates `ps`? | **No** — different score (8 vs 9 signals), different frequency, different inputs |
| Green SAS implements? | **Yes** — multi-step Mohanram construction (`m1`–`m8` → `ms`; L219–285, L620–641, L796–799) |
| Dacheng/Xiu implements? | **Not found** in `accounting_100.py` annual output list |
| In `datashare.csv`? | **Yes** — non-null ~2.4M rows; integer values **0–8** |
| Distinct GKX predictor? | **Yes** — GKX lists both `ms` (#50) and `ps` (#67, Piotroski 2000) separately |

---

## Evidence

### GKX character list

- **`ms`**: Financial statement score — Mohanram 2005 — Compustat **Quarterly**
- **`ps`**: Financial statement score — Piotroski 2000 — Compustat **Annual**

### datashare.csv

| Column | Value range | Interpretation |
| --- | --- | --- |
| `ms` | 0–8 | Mohanram (8 binary signals) |
| `ps` | 0–9 | Piotroski F-score (9 binary signals) |

Repository **`ps`** matches Green SAS Piotroski (L207–208) and is already in panels.

### Green SAS

**Piotroski (`ps`)** — annual, L207–208: nine profitability/leverage/liquidity/operating signals summed.

**Mohanram (`ms`)** — quarterly pipeline:

1. Prep ratios: `roa`, `cfroa`, `xrdint`, `capxint`, `xadint` (L220–225)
2. Industry medians by `fyear` × `sic2` (L257–270)
3. Signals `m1`–`m6`: compare firm to industry medians + `oancf > ni` (L278–283)
4. Quarterly volatility signals `m7`, `m8` from `roavol`, `sgrvol` vs industry medians (L640–641)
5. **`ms = m1 + … + m8`** (L799)

Requires quarterly Compustat, industry medians, credit-rating merge (`comp.adsprate`), and earnings-month alignment — materially more complex than annual Batch B.

### Repository

- **`ps`**: implemented in `green_builders.py` (Piotroski F-score)
- **`ms`**: not implemented

---

## Decision

| Option | Verdict |
| --- | --- |
| Alias to `ps` | **Reject** — different economic construct and GKX column |
| Mark as already covered | **Reject** — `ps` ≠ `ms` |
| **Implement later** | **Accept** — defer to post–Batch B quarterly phase |

Phase 6 proceeds with Batch A + B only; `ms` remains on the missing list.
