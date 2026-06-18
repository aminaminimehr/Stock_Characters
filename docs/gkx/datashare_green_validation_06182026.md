# Datashare columns — Green SAS validation (primary)

Validation window: `201001`–`201512`. Monthly cross-sectional Spearman on `permno × YYYYMM`; months with < 50 paired observations skipped.

Repo panel: `outputs/panels/all_character_signal_panel.csv`
Green SAS: `Supplementary_assistive_files/Output_From_Greens_SAS_code.sas7bdat`

**Datashare values are not the primary benchmark** — they are omitted here except where noted for diagnostics in separate reports.

## Green-validated predictors

| Datashare | Green SAS | Repo source | Median ρ | Valid months | Median pairs/mo | Total pairs | Coverage | Status |
|-----------|-----------|-------------|---------:|-------------:|----------------:|------------:|---------:|--------|
| `divo` | `divo` | `divo` | 1.0000 | 72 | 3320 | 243358 | 0.9839 | Green-validated >= 0.95 |
| `divi` | `divi` | `divi` | 1.0000 | 72 | 3320 | 243358 | 0.9839 | Green-validated >= 0.95 |
| `convind` | `convind` | `convind` | 1.0000 | 72 | 3452 | 250316 | 0.9839 | Green-validated >= 0.95 |
| `rd` | `rd` | `rd` | 1.0000 | 72 | 1338 | 98248 | 0.3972 | Green-validated >= 0.95 |
| `sin` | `sin` | `sin` | 1.0000 | 72 | 3452 | 250316 | 0.9839 | Green-validated >= 0.95 |
| `securedind` | `securedind` | `securedind` | 1.0000 | 72 | 3452 | 250316 | 0.9839 | Green-validated >= 0.95 |
| `age` | `age` | `age` | 1.0000 | 72 | 3452 | 250316 | 0.9839 | Green-validated >= 0.95 |
| `baspread` | `baspread` | `baspread` | 1.0000 | 72 | 3452 | 250316 | 0.9839 | Green-validated >= 0.95 |
| `retvol` | `retvol` | `rvar_mean` | 1.0000 | 72 | 3452 | 250315 | 0.9839 | Green-validated >= 0.95 (alias) |
| `std_turn` | `std_turn` | `std_turn` | 1.0000 | 72 | 3452 | 250315 | 0.9839 | Green-validated >= 0.95 |
| `realestate` | `realestate` | `realestate` | 1.0000 | 72 | 1888 | 136798 | 0.9879 | Green-validated >= 0.95 |
| `depr` | `depr` | `depr` | 1.0000 | 72 | 3378 | 244758 | 0.9875 | Green-validated >= 0.95 |
| `pchsaleinv` | `pchsaleinv` | `pchsaleinv` | 1.0000 | 72 | 2496 | 180949 | 0.9882 | Green-validated >= 0.95 |
| `ill` | `ill` | `ill` | 1.0000 | 72 | 3452 | 250313 | 0.9839 | Green-validated >= 0.95 |
| `tang` | `tang` | `tang` | 1.0000 | 72 | 3377 | 244996 | 0.9868 | Green-validated >= 0.95 |
| `orgcap` | `orgcap` | `orgcap` | 1.0000 | 72 | 2566 | 188004 | 0.9862 | Green-validated >= 0.95 |
| `sp` | `sp` | `sp` | 1.0000 | 72 | 3452 | 250316 | 0.9839 | Green-validated >= 0.95 |
| `lev` | `lev` | `lev` | 1.0000 | 72 | 3440 | 249480 | 0.9838 | Green-validated >= 0.95 |
| `saleinv` | `saleinv` | `saleinv` | 1.0000 | 72 | 2582 | 188189 | 0.9883 | Green-validated >= 0.95 |
| `cashdebt` | `cashdebt` | `cashdebt` | 1.0000 | 72 | 3264 | 239318 | 0.9589 | Green-validated >= 0.95 |
| `salecash` | `salecash` | `salecash` | 1.0000 | 72 | 3445 | 249728 | 0.9839 | Green-validated >= 0.95 |
| `std_dolvol` | `std_dolvol` | `std_dolvol` | 1.0000 | 72 | 3452 | 250304 | 0.9839 | Green-validated >= 0.95 |
| `zerotrade` | `zerotrade` | `zerotrade` | 1.0000 | 72 | 3452 | 250314 | 0.9839 | Green-validated >= 0.95 |
| `salerec` | `salerec` | `salerec` | 1.0000 | 72 | 3340 | 243460 | 0.9838 | Green-validated >= 0.95 |
| `roavol` | `roavol` | `roavol` | 1.0000 | 72 | 3252 | 236464 | 0.9844 | Green-validated >= 0.95 |
| `dy` | `dy` | `dy` | 1.0000 | 72 | 3450 | 250154 | 0.9839 | Green-validated >= 0.95 |
| `mvel1` | `mve` | `mvel1` | 1.0000 | 72 | 3452 | 250316 | 0.9839 | Green-validated >= 0.95 |
| `absacc` | `absacc` | `absacc` | 1.0000 | 72 | 3318 | 243281 | 0.9840 | Green-validated >= 0.95 |
| `rd_sale` | `rd_sale` | `rd_sale` | 1.0000 | 72 | 1727 | 125047 | 0.9838 | Green-validated >= 0.95 |
| `rd_mve` | `rd_mve` | `rdm` | 1.0000 | 72 | 1773 | 128145 | 0.9841 | Green-validated >= 0.95 (alias) |
| `secured` | `secured` | `secured` | 1.0000 | 72 | 2004 | 146196 | 0.9797 | Green-validated >= 0.95 |
| `maxret` | `maxret` | `maxret` | 1.0000 | 72 | 3452 | 250316 | 0.9839 | Green-validated >= 0.95 |
| `pchsale_pchxsga` | `pchsale_pchxsga` | `pchsale_pchxsga` | 1.0000 | 72 | 2813 | 206424 | 0.9850 | Green-validated >= 0.95 |
| `pchquick` | `pchquick` | `pchquick` | 1.0000 | 72 | 3246 | 237706 | 0.9840 | Green-validated >= 0.95 |
| `currat` | `currat` | `currat` | 1.0000 | 72 | 3411 | 247181 | 0.9838 | Green-validated >= 0.95 |
| `pchdepr` | `pchdepr` | `pchdepr` | 1.0000 | 72 | 3248 | 237577 | 0.9874 | Green-validated >= 0.95 |
| `quick` | `quick` | `quick` | 1.0000 | 72 | 3380 | 245195 | 0.9839 | Green-validated >= 0.95 |
| `pchsale_pchrect` | `pchsale_pchrect` | `pchsale_pchrect` | 1.0000 | 72 | 3216 | 235296 | 0.9838 | Green-validated >= 0.95 |
| `grltnoa` | `grltnoa` | `grltnoa` | 1.0000 | 72 | 2752 | 200844 | 0.9857 | Green-validated >= 0.95 |
| `agr` | `agr` | `agr` | 1.0000 | 72 | 3320 | 243358 | 0.9839 | Green-validated >= 0.95 |
| `lgr` | `lgr` | `lgr` | 1.0000 | 72 | 3300 | 242202 | 0.9839 | Green-validated >= 0.95 |
| `bm` | `bm` | `bm` | 1.0000 | 72 | 3452 | 250316 | 0.9839 | Green-validated >= 0.95 |
| `sgr` | `sgr` | `sgr` | 1.0000 | 72 | 3272 | 239518 | 0.9839 | Green-validated >= 0.95 |
| `cfp` | `cfp` | `cfp` | 1.0000 | 72 | 3452 | 250286 | 0.9839 | Green-validated >= 0.95 |
| `ep` | `ep` | `ep` | 1.0000 | 72 | 3452 | 250316 | 0.9839 | Green-validated >= 0.95 |
| `pchgm_pchsale` | `pchgm_pchsale` | `pchgm_pchsale` | 1.0000 | 72 | 3272 | 239518 | 0.9839 | Green-validated >= 0.95 |
| `chcsho` | `chcsho` | `chcsho` | 1.0000 | 72 | 3320 | 243279 | 0.9839 | Green-validated >= 0.95 |
| `mom1m` | `mom1m` | `mom1m` | 1.0000 | 72 | 3452 | 250316 | 0.9839 | Green-validated >= 0.95 |
| `egr` | `egr` | `egr` | 1.0000 | 72 | 3320 | 243346 | 0.9839 | Green-validated >= 0.95 |
| `hire` | `hire` | `hire` | 1.0000 | 72 | 3316 | 242952 | 0.9842 | Green-validated >= 0.95 |
| `chinv` | `chinv` | `chinv` | 1.0000 | 72 | 3277 | 240063 | 0.9840 | Green-validated >= 0.95 |
| `pchsale_pchinvt` | `pchsale_pchinvt` | `pchsale_pchinvt` | 1.0000 | 72 | 2516 | 182612 | 0.9882 | Green-validated >= 0.95 |
| `roic` | `roic` | `roic` | 1.0000 | 72 | 3440 | 249354 | 0.9838 | Green-validated >= 0.95 |
| `gma` | `gma` | `gma` | 1.0000 | 72 | 3320 | 243358 | 0.9839 | Green-validated >= 0.95 |
| `cashpr` | `cashpr` | `cashpr` | 1.0000 | 72 | 3425 | 248486 | 0.9838 | Green-validated >= 0.95 |
| `pctacc` | `pctacc` | `pctacc` | 1.0000 | 72 | 3318 | 243281 | 0.9840 | Green-validated >= 0.95 |
| `acc` | `acc` | `acc` | 1.0000 | 72 | 3318 | 243281 | 0.9840 | Green-validated >= 0.95 |
| `cash` | `cash` | `cash` | 1.0000 | 72 | 3444 | 249888 | 0.9841 | Green-validated >= 0.95 |
| `pchcurrat` | `pchcurrat` | `pchcurrat` | 1.0000 | 72 | 2680 | 196073 | 0.8041 | Green-validated >= 0.95 |
| `chtx` | `chtx` | `chtx` | 1.0000 | 72 | 3412 | 248494 | 0.9843 | Green-validated >= 0.95 |
| `rsup` | `rsup` | `rsup` | 1.0000 | 72 | 3441 | 249543 | 0.9835 | Green-validated >= 0.95 |
| `roaq` | `roaq` | `roaq` | 1.0000 | 72 | 3442 | 249921 | 0.9843 | Green-validated >= 0.95 |
| `ear` | `ear` | `abr` | 0.9999 | 72 | 3444 | 249968 | 0.9842 | Green-validated >= 0.95 (alias) |
| `aeavol` | `aeavol` | `aeavol` | 0.9999 | 72 | 3444 | 249965 | 0.9842 | Green-validated >= 0.95 |
| `stdacc` | `stdacc` | `stdacc` | 0.9997 | 72 | 2610 | 189286 | 0.9868 | Green-validated >= 0.95 |
| `nincr` | `nincr` | `nincr` | 0.9997 | 72 | 3446 | 250047 | 0.9841 | Green-validated >= 0.95 |
| `dolvol` | `dolvol` | `dolvol` | 0.9996 | 72 | 3444 | 249732 | 0.9838 | Green-validated >= 0.95 |
| `stdcf` | `stdcf` | `stdcf` | 0.9995 | 72 | 2610 | 189286 | 0.9868 | Green-validated >= 0.95 |
| `invest` | `invest` | `invest` | 0.9992 | 72 | 3250 | 238163 | 0.9871 | Green-validated >= 0.95 |
| `turn` | `turn` | `turn` | 0.9992 | 72 | 3431 | 249270 | 0.9838 | Green-validated >= 0.95 |
| `beta` | `beta` | `beta` | 0.9980 | 72 | 3413 | 248646 | 0.9838 | Green-validated >= 0.95 |
| `betasq` | `betasq` | `betasq` | 0.9980 | 72 | 3413 | 248646 | 0.9838 | Green-validated >= 0.95 |
| `idiovol` | `idiovol` | `idiovol` | 0.9979 | 72 | 3413 | 248646 | 0.9838 | Green-validated >= 0.95 |
| `chatoia` | `chatoia` | `chatoia` | 0.9978 | 72 | 3218 | 236226 | 0.9839 | Green-validated >= 0.95 |
| `mve_ia` | `mve_ia` | `me_ia` | 0.9973 | 72 | 3452 | 250316 | 0.9839 | Green-validated >= 0.95 (alias) |
| `mom6m` | `mom6m` | `mom6m` | 0.9971 | 72 | 3366 | 246186 | 0.9838 | Green-validated >= 0.95 |
| `sic2` | `sic2` | `sic2` | 0.9970 | 72 | 3452 | 250316 | 0.9839 | Green-validated >= 0.95 |
| `bm_ia` | `bm_ia` | `bm_ia` | 0.9969 | 72 | 3452 | 250316 | 0.9839 | Green-validated >= 0.95 |
| `herf` | `herf` | `herf` | 0.9965 | 72 | 3452 | 250316 | 0.9839 | Green-validated >= 0.95 |
| `grcapx` | `grcapx` | `grcapx` | 0.9964 | 72 | 3156 | 231567 | 0.9839 | Green-validated >= 0.95 |
| `mom12m` | `mom12m` | `mom12m` | 0.9952 | 72 | 3294 | 241069 | 0.9837 | Green-validated >= 0.95 |
| `tb` | `tb` | `tb` | 0.9944 | 72 | 2950 | 213252 | 0.9421 | Green-validated >= 0.95 |
| `cfp_ia` | `cfp_ia` | `cfp_ia` | 0.9944 | 72 | 3452 | 250286 | 0.9839 | Green-validated >= 0.95 |
| `chempia` | `chempia` | `chempia` | 0.9941 | 72 | 3316 | 242952 | 0.9842 | Green-validated >= 0.95 |
| `chmom` | `chmom` | `chmom` | 0.9939 | 72 | 3294 | 241069 | 0.9837 | Green-validated >= 0.95 |
| `mom36m` | `mom36m` | `mom36m` | 0.9934 | 72 | 3070 | 222403 | 0.9832 | Green-validated >= 0.95 |
| `cinvest` | `cinvest` | `cinvest` | 0.9868 | 72 | 3334 | 243464 | 0.9782 | Green-validated >= 0.95 |
| `chpmia` | `chpmia` | `chpmia` | 0.9828 | 72 | 3260 | 238867 | 0.9839 | Green-validated >= 0.95 |
| `ps` | `ps` | `ps` | 0.9797 | 72 | 3320 | 243358 | 0.9839 | Green-validated >= 0.95 |
| `pricedelay` | `pricedelay` | `pricedelay` | 0.9374 | 72 | 3413 | 248646 | 0.9838 | Green-validated < 0.95 |
| `pchcapx_ia` | `pchcapx_ia` | `pchcapx_ia` | 0.6472 | 72 | 3258 | 238677 | 0.9842 | Green-validated < 0.95 |
| `operprof` | `operprof` | `operprof` | 0.6192 | 72 | 3320 | 243346 | 0.9839 | Green-validated < 0.95 |
| `ms` | `ms` | `ms` | 0.5914 | 72 | 3446 | 250047 | 0.9841 | Green-validated < 0.95 |
| `indmom` | `indmom` | `indmom` | -0.0610 | 72 | 3429 | 249156 | 0.9793 | Green-validated < 0.95 |

## Below 0.95 vs Green (fix priority)

| Rank | Datashare | Repo | Green | Median ρ | Valid months | Notes |
|-----:|-----------|------|-------|---------:|-------------:|-------|
| 1 | `indmom` | `indmom` | `indmom` | -0.0610 | 72 |  |
| 2 | `ms` | `ms` | `ms` | 0.5914 | 72 |  |
| 3 | `operprof` | `operprof` | `operprof` | 0.6192 | 72 | Repo `operating_profitability` mismatches; try `op` or rebuild from Green |
| 4 | `pchcapx_ia` | `pchcapx_ia` | `pchcapx_ia` | 0.6472 | 72 | Industry-adjusted cap-ex growth; audit formula/timing |
| 5 | `pricedelay` | `pricedelay` | `pricedelay` | 0.9374 | 72 |  |

## Not validated against Green

| Datashare | Repo | Green | Status | Reason |
|-----------|------|-------|--------|--------|
| `roeq` | `roeq` | `roeq` | formula/timing audit needed | Implemented under different name or wrong economic definition |

## Recommended next fixes (ranked)

1. **`ear` (`abr`)** — largest gap (ρ ≈ 0.03). Audit event-window construction vs Green SAS `ear`.
2. **`beta` / `betasq`** — rebuild with Green weekly 36-month EW-market method (`beta_builder.py`).
3. **`pchcapx_ia`** — industry-adjusted cap-ex; audit formula and annual timing.
4. **`nincr`** — near threshold (ρ ≈ 0.92); audit quarterly streak definition.
5. **`sue`** — treat separately: IBES policy decision; secondary diagnostic only.
6. **`operprof`** — repo `operating_profitability` scores ρ ≈ 0.57 vs Green; audit `op` and Green formula.
7. **Missing datashare predictors** — implement in Green order: `aeavol`, `idiovol`, `pricedelay`, `stdacc`/`stdcf`/`roavol`, `chmom`/`indmom`, `sic2`, `ms`.
8. **`roeq`** — build quarterly `roeq` export; do not alias annual `roe`.
9. **Export alias layer** — rename `roa1→roaq`, `rdm→rd_mve`, `rvar_mean→retvol`, `me_ia→mve_ia`.

## `sue` (separate policy)

Green SAS uses IBES actuals when available. The repo currently implements a Compustat `che/mveq` proxy. Validate against Green only after an explicit IBES policy decision.
