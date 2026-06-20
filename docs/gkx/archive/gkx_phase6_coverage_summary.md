# GKX Phase 6 coverage summary

Phase 6 implemented Batch A (`betasq`) + Batch B (12 annual Compustat predictors).  
`ms` audited and deferred (see `gkx_ms_audit.md`).

## Coverage before vs after

| Metric | Before Phase 6 | After Phase 6 | Change |
| --- | ---: | ---: | ---: |
| GKX predictors covered | 67 | **80** | +13 |
| GKX predictors missing | 27 | **14** | −13 |
| Exact name matches | 58 | 71 | +13 |
| Aliases | 7 | 7 | — |
| Partial (HXZ parallel) | 2 | 2 | — |
| Repository-only extras | 18 | 18 | — |
| Signal panel characteristic columns | 88 | **101** | +13 |

## Remaining missing GKX predictors (14)

| Predictor | Difficulty | Notes |
| --- | --- | --- |
| `cfp_ia`, `chatoia`, `chempia`, `chpmia`, `pchcapx_ia` | Medium | Industry-adjusted annual (Batch C) |
| `chmom`, `indmom`, `pricedelay` | Medium–high | CRSP momentum / daily (deferred) |
| `aeavol`, `idiovol`, `roavol`, `stdacc`, `stdcf` | High | Volatility / event windows (deferred) |
| `ms` | High | Mohanram quarterly score (deferred) |

## Suggested next batch

**Batch C — industry-adjusted annual (5 predictors):** lowest-risk path from 80 → 85 GKX coverage.

Then **Batch D/E** for deferred daily/event/volatility predictors and **quarterly `ms`**.
