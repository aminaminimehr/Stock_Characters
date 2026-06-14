# GKX Phase 6 validation (Batch A + B)

- Flat outputs/*.csv count: **0**
- Signal panel characteristic columns: **101** (was 88)
- Complete panel characteristic columns: **101** (was 88; 107 merged incl. return fields)

Sample build: `STOCK_CHARACTERS_SAMPLE_START=2018-01-01`, `END=2023-12-31`.

## Raw CSV checks

| Character | Rows | Coverage | Notes |
|-----------|-----:|---------:|-------|
| betasq | 276,183 | 100% | Monthly; `beta²` |
| rd | 8,289 | 100% | Binary {0,1}; sparse R&D firms |
| divi | 24,221 | 100% | Binary initiation |
| divo | 24,221 | 100% | Binary omission |
| roic | 30,723 | 100% | Level ratio |
| tb | 27,299 | 100% | Industry-adjusted |
| convind | 30,851 | 100% | Binary |
| secured | 24,049 | 100% | Sparse `dm` |
| securedind | 30,851 | 100% | Binary |
| pchgm_pchsale | 22,601 | 100% | Requires lag fiscal year |
| pchsale_pchinvt | 14,908 | 100% | Requires lag fiscal year |
| pchsale_pchrect | 22,012 | 100% | Requires lag fiscal year |
| pchsale_pchxsga | 18,713 | 100% | Requires lag fiscal year |

## Panel merge checks

All 13 batch characteristics present in signal and complete prediction panels.

## Notes

- `ms` audited separately; deferred (Mohanram quarterly score).
- Phase 1–5 variables not modified.
- datashare comparisons omitted from public methodology.
