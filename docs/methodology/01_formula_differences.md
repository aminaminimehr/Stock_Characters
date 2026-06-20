# Formula Differences: Green vs Datashare vs Repository

**Empirical update (2026-06):** reverse-engineering against the local `datashare.csv` shows that
**this file follows Green/HXZ definitions**, not Dacheng's `accounting_60.py` port. See
`docs/gkx/datashare_reverse_engineering.md`.

| datashare column | Repository column | Status |
|---|---|---|
| `bm` | `book_to_market` (HXZ/FF-June) | ρ ≈ 0.96 pooled |
| `operprof` | `operating_profitability` (HXZ) | ρ ≈ 0.95 pooled |
| `cfp` | Green `cfp` (`oancf/mve_f`) | ρ ≈ 0.998 (1975+; extend to 1957) |
| `bm_ia` | — | **Out of scope** (not replicated) |

Use `--profile datashare` for universe/timing aimed at datashare; formulas come from the columns above.

---

## `bm` — book-to-market

| | Formula | Market equity | Timing |
|---|---|---|---|
| **Green** | `bm = ceq / mve_f` | Compustat FY-end `mve_f` | Green rolling months 7–19 |
| **Datashare (this file)** | HXZ `book_to_market`: `be/me_dec` with `be = seq+txditc−ps` (+ fallbacks) | December CRSP permco ME | FF-June |
| **Repo Green** | same as Green SAS code | `mve_f` | Green rolling |
| **Repo datashare** | `book_to_market` | December CRSP ME | FF-June via `timing.py` |

The pure Dacheng `be/current CRSP me` port in `Dacheng_datashare/` was **rejected** (ρ ≈ 0.82 vs datashare `bm`).

---

## `operprof` — operating profitability

| | Formula | Denominator |
|---|---|---|
| **Green (code)** | `(revt − cogs − xsga0 − xint0) / lag(ceq)` | lagged CEQ |
| **Datashare (this file)** | HXZ: `(revt − cogs − xsga0 − xint0) / be` | current book equity |
| **Repo Green** | follows Green **code** (includes `xsga0`) | lag CEQ |
| **Repo datashare** | `operating_profitability` | current BE |

Green **output** omits `xsga0` (known SAS typo); repo intentionally follows **code**.

---

## `cfp` — cash-flow-to-price

| | Formula |
|---|---|
| **Green / datashare (this file)** | `cfp = oancf / mve_f`, fallback `(ib − wc_accrual) / mve_f` |
| **HXZ `cash_flow_to_price`** | Different definition — **not** datashare match |
| **Dacheng `(ib+dp)/me`** | **Rejected** (ρ ≈ −0.02) |

Extend Compustat start to 1957 via `--profile datashare` or `scripts/rebuild/rebuild_green_cfp_full_history.py`.

---

## `bm_ia` — industry-adjusted book-to-market

**Out of scope.** No stable replication found; do not use repo `bm_ia` as a datashare substitute.

Green repo `bm_ia` uses SIC2 × fiscal-year mean demeaning (matches Green SAS intent). Datashare `bm_ia`
does not match simple demeaning of public `bm`.

---

## Intentional Green code-vs-output divergences

| Variable | Cause |
|---|---|
| `operprof` | Repo follows Green **code** (with `xsga0`), not buggy output |
| `pchcapx_ia` | Repo uses BY-group-correct lags; Green SAS output corrupted by global `lag()` |

See `docs/gkx/archive/green_universe_and_mismatch_audit.md` (if moved) or methodology `08_validation_status.md`.
