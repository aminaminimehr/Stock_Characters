# GKX Phase 6 methodology (Batch A + B)

Batch A: `betasq`  
Batch B: `rd`, `divi`, `divo`, `roic`, `tb`, `convind`, `secured`, `securedind`, `pchgm_pchsale`, `pchsale_pchinvt`, `pchsale_pchrect`, `pchsale_pchxsga`

Reference priority: **Green SAS** > **Dacheng `accounting_100.py`** > GKX list.

**Deferred:** `ms` (see `gkx_ms_audit.md`), volatility/event/daily predictors per reconciliation audit.

Phase 1–5 variables are **not** modified.

---

## Batch A

### `betasq` — Beta squared

| Item | Detail |
| --- | --- |
| **Green SAS** | L1120: `betasq = beta * beta` (monthly merge from rolling CAPM beta) |
| **Dacheng** | Not in `accounting_100.py` |
| **Compustat** | None |
| **CRSP** | Daily returns + `mktrf` (same as `beta`) |
| **Timing** | Monthly; 3-month rolling daily CAPM beta, aligned to `signal_yyyymm` |
| **Lags** | None |
| **Missing rules** | Missing when beta missing |
| **Ambiguity** | **Low** — deterministic transform of existing `beta` |
| **Coverage** | Same as `beta` |

---

## Batch B — annual Compustat

Common timing: fiscal `datadate` → June-expanded monthly signals. Lags by **`gvkey`**.

### `rd` — R&D increase indicator

| Item | Detail |
| --- | --- |
| **Green SAS** | L203: `rd=1` if `((xrd/at) - lag(xrd/lag(at))) / lag(xrd/lag(at)) > 0.05`, else `0` |
| **Dacheng** | L405–410: equivalent structure |
| **Compustat** | `xrd`, `at`, lags |
| **CRSP** | None |
| **Missing rules** | Green `req` array — NaN when `count=1` |
| **Ambiguity** | **Low** |

### `divi` / `divo` — Dividend initiation / omission

| Item | Detail |
| --- | --- |
| **Green SAS** | L192–193 |
| **Dacheng** | Not explicit in annual block |
| **Compustat** | `dvt`, `lag(dvt)` |
| **Formulas** | `divi=1` if `dvt>0` and prior `dvt` missing/0; `divo=1` if `dvt` missing/0 and prior `dvt>0` |
| **Missing rules** | Green `req` array — NaN when `count=1` |
| **Ambiguity** | **Low** |

### `roic` — Return on invested capital

| Item | Detail |
| --- | --- |
| **Green SAS** | L131: `(ebit - nopi) / (ceq + lt - che)` |
| **Dacheng** | L423–424: same |
| **Compustat** | `ebit`, `nopi`, `ceq`, `lt`, `che` |
| **Missing rules** | Not in `req` array — valid from first row |
| **Ambiguity** | **Low** |

### `tb` — Tax income to book income (industry-adjusted)

| Item | Detail |
| --- | --- |
| **Green SAS** | L209–217 (`tb_1`), L246: `tb = tb_1 - mean(tb_1)` by `sic2` × `fyear` |
| **Dacheng** | Not found in annual output |
| **Compustat** | `txfo`, `txfed`, `txt`, `txdi`, `ib`, `fyear` |
| **Tax rate `tr`** | Green statutory schedule by `fyear` (L210–214) |
| **Missing rules** | Industry demeaning after firm-level `tb_1` |
| **Ambiguity** | **Low** — follow Green industry adjustment (same pattern as `bm_ia`) |

### `secured` / `securedind`

| Item | Detail |
| --- | --- |
| **Green SAS** | L196–197: `securedind=1` if `dm≠0`; `secured=dm/dltt` |
| **Dacheng** | Not in annual chars list |
| **Compustat** | `dm`, `dltt` |
| **Missing rules** | Not in `req` array |
| **Ambiguity** | **Low** — expect sparse `dm` |

### `convind` — Convertible debt indicator

| Item | Detail |
| --- | --- |
| **Green SAS** | L93–95 (`dc` imputation), L198: `convind=1` if `(dc≠0) OR (cshrc≠0)` |
| **Dacheng** | L112–117 (`dc` imputation); no `convind` export found |
| **Compustat** | `dcvt`, `dcpstk`, `pstk`, `cshrc` |
| **Missing rules** | Not in `req` array |
| **Ambiguity** | **Low** |

### `pchsale_pchinvt`, `pchsale_pchrect`, `pchgm_pchsale`, `pchsale_pchxsga`

| Item | Detail |
| --- | --- |
| **Green SAS** | L158–161 |
| **Dacheng** | L429–447: same structures |
| **Compustat** | `sale`, `invt`, `rect`, `cogs`, `xsga`, lags |
| **Missing rules** | Green `req` array — NaN when `count=1` |
| **Ambiguity** | **Low** |

---

## Ambiguity gate

**No predictor in Batch A + B has blocking ambiguity.** Proceed with implementation.
