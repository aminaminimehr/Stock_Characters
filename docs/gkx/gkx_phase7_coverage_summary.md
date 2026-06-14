# GKX Phase 7 coverage summary (Batch C — industry-adjusted)

Industry grouping: **Compustat SIC2 × fiscal year**, subtract industry **mean** (Green SAS L244–249).

## Coverage before vs after

| Metric | Before Phase 7 | After Phase 7 | Change |
| --- | ---: | ---: | ---: |
| GKX predictors covered | 80 | **85** | +5 |
| GKX predictors missing | 14 | **9** | −5 |
| Signal panel characteristic columns | 101 | **106** | +5 |

## Remaining missing GKX predictors (9)

`aeavol`, `chmom`, `idiovol`, `indmom`, `ms`, `pricedelay`, `roavol`, `stdacc`, `stdcf`

## Suggested next batch

1. **Quarterly `ms`** (Mohanram) — see `gkx_ms_audit.md`
2. **CRSP daily/monthly deferred batch:** `chmom`, `indmom`, `pricedelay`
3. **Volatility/event batch:** `aeavol`, `idiovol`, `roavol`, `stdacc`, `stdcf`
