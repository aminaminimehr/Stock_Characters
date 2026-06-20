# Datashare columns — Green SAS validation (primary)

Validation window: `201001`–`201512`. Monthly cross-sectional Spearman on `permno × YYYYMM`; months with < 50 paired observations skipped.

Repo panel: `outputs/panels/all_character_signal_panel.csv`
Green SAS: `Supplementary_assistive_files/Output_From_Greens_SAS_code.sas7bdat`

**Datashare values are not the primary benchmark** — they are omitted here except where noted for diagnostics in separate reports.

## Green-validated predictors

| Datashare | Green SAS | Repo source | Median ρ | Valid months | Median pairs/mo | Total pairs | Coverage | Status |
|-----------|-----------|-------------|---------:|-------------:|----------------:|------------:|---------:|--------|
| `rd` | `rd` | `rd` | 1.0000 | 72 | 1333 | 97858 | 0.3957 | Green-validated >= 0.95 |
| `divo` | `divo` | `divo` | 1.0000 | 72 | 3298 | 241774 | 0.9775 | Green-validated >= 0.95 |
| `divi` | `divi` | `divi` | 1.0000 | 72 | 3298 | 241774 | 0.9775 | Green-validated >= 0.95 |
| `convind` | `convind` | `convind` | 1.0000 | 72 | 3431 | 248722 | 0.9776 | Green-validated >= 0.95 |
| `sin` | `sin` | `sin` | 1.0000 | 72 | 3431 | 248722 | 0.9776 | Green-validated >= 0.95 |
| `securedind` | `securedind` | `securedind` | 1.0000 | 72 | 3431 | 248722 | 0.9776 | Green-validated >= 0.95 |
| `age` | `age` | `age` | 1.0000 | 72 | 3431 | 248722 | 0.9776 | Green-validated >= 0.95 |
| `baspread` | `baspread` | `baspread` | 1.0000 | 72 | 3452 | 250316 | 0.9839 | Green-validated >= 0.95 |
| `retvol` | `retvol` | `rvar_mean` | 1.0000 | 72 | 3452 | 250315 | 0.9839 | Green-validated >= 0.95 (alias) |
| `std_turn` | `std_turn` | `std_turn` | 1.0000 | 72 | 3452 | 250315 | 0.9839 | Green-validated >= 0.95 |
| `lev` | `lev` | `lev` | 1.0000 | 72 | 3416 | 247886 | 0.9775 | Green-validated >= 0.95 |
| `realestate` | `realestate` | `realestate` | 1.0000 | 72 | 1874 | 135862 | 0.9811 | Green-validated >= 0.95 |
| `sp` | `sp` | `sp` | 1.0000 | 72 | 3431 | 248722 | 0.9776 | Green-validated >= 0.95 |
| `depr` | `depr` | `depr` | 1.0000 | 72 | 3356 | 243236 | 0.9813 | Green-validated >= 0.95 |
| `ill` | `ill` | `ill` | 1.0000 | 72 | 3452 | 250313 | 0.9839 | Green-validated >= 0.95 |
| `secured` | `secured` | `secured` | 1.0000 | 72 | 1986 | 144917 | 0.9711 | Green-validated >= 0.95 |
| `pchsaleinv` | `pchsaleinv` | `pchsaleinv` | 1.0000 | 72 | 2478 | 179647 | 0.9811 | Green-validated >= 0.95 |
| `salecash` | `salecash` | `salecash` | 1.0000 | 72 | 3422 | 248134 | 0.9776 | Green-validated >= 0.95 |
| `std_dolvol` | `std_dolvol` | `std_dolvol` | 1.0000 | 72 | 3452 | 250304 | 0.9839 | Green-validated >= 0.95 |
| `zerotrade` | `zerotrade` | `zerotrade` | 1.0000 | 72 | 3452 | 250314 | 0.9839 | Green-validated >= 0.95 |
| `tang` | `tang` | `tang` | 1.0000 | 72 | 3356 | 243425 | 0.9805 | Green-validated >= 0.95 |
| `dy` | `dy` | `dy` | 1.0000 | 72 | 3428 | 248560 | 0.9776 | Green-validated >= 0.95 |
| `orgcap` | `orgcap` | `orgcap` | 1.0000 | 72 | 2548 | 186627 | 0.9790 | Green-validated >= 0.95 |
| `saleinv` | `saleinv` | `saleinv` | 1.0000 | 72 | 2564 | 186870 | 0.9814 | Green-validated >= 0.95 |
| `cashdebt` | `cashdebt` | `cashdebt` | 1.0000 | 72 | 3242 | 237764 | 0.9527 | Green-validated >= 0.95 |
| `rd_mve` | `rd_mve` | `rdm` | 1.0000 | 72 | 1766 | 127550 | 0.9795 | Green-validated >= 0.95 (alias) |
| `salerec` | `salerec` | `salerec` | 1.0000 | 72 | 3317 | 241866 | 0.9774 | Green-validated >= 0.95 |
| `mvel1` | `mve` | `mvel1` | 1.0000 | 72 | 3452 | 250316 | 0.9839 | Green-validated >= 0.95 |
| `absacc` | `absacc` | `absacc` | 1.0000 | 72 | 3296 | 241697 | 0.9776 | Green-validated >= 0.95 |
| `rd_sale` | `rd_sale` | `rd_sale` | 1.0000 | 72 | 1720 | 124452 | 0.9791 | Green-validated >= 0.95 |
| `maxret` | `maxret` | `maxret` | 1.0000 | 72 | 3452 | 250316 | 0.9839 | Green-validated >= 0.95 |
| `quick` | `quick` | `quick` | 1.0000 | 72 | 3358 | 243624 | 0.9776 | Green-validated >= 0.95 |
| `currat` | `currat` | `currat` | 1.0000 | 72 | 3388 | 245605 | 0.9775 | Green-validated >= 0.95 |
| `pchquick` | `pchquick` | `pchquick` | 1.0000 | 72 | 3224 | 236145 | 0.9775 | Green-validated >= 0.95 |
| `pchsale_pchxsga` | `pchsale_pchxsga` | `pchsale_pchxsga` | 1.0000 | 72 | 2794 | 205047 | 0.9784 | Green-validated >= 0.95 |
| `ep` | `ep` | `ep` | 1.0000 | 72 | 3431 | 248722 | 0.9776 | Green-validated >= 0.95 |
| `bm` | `bm` | `bm` | 1.0000 | 72 | 3431 | 248722 | 0.9776 | Green-validated >= 0.95 |
| `cfp` | `cfp` | `cfp` | 1.0000 | 72 | 3431 | 248692 | 0.9777 | Green-validated >= 0.95 |
| `pchdepr` | `pchdepr` | `pchdepr` | 1.0000 | 72 | 3226 | 236065 | 0.9812 | Green-validated >= 0.95 |
| `pchsale_pchrect` | `pchsale_pchrect` | `pchsale_pchrect` | 1.0000 | 72 | 3194 | 233712 | 0.9772 | Green-validated >= 0.95 |
| `agr` | `agr` | `agr` | 1.0000 | 72 | 3298 | 241774 | 0.9775 | Green-validated >= 0.95 |
| `lgr` | `lgr` | `lgr` | 1.0000 | 72 | 3278 | 240618 | 0.9775 | Green-validated >= 0.95 |
| `grltnoa` | `grltnoa` | `grltnoa` | 1.0000 | 72 | 2732 | 199354 | 0.9784 | Green-validated >= 0.95 |
| `sgr` | `sgr` | `sgr` | 1.0000 | 72 | 3250 | 237934 | 0.9773 | Green-validated >= 0.95 |
| `pchgm_pchsale` | `pchgm_pchsale` | `pchgm_pchsale` | 1.0000 | 72 | 3250 | 237934 | 0.9773 | Green-validated >= 0.95 |
| `chinv` | `chinv` | `chinv` | 1.0000 | 72 | 3255 | 238502 | 0.9776 | Green-validated >= 0.95 |
| `mom1m` | `mom1m` | `mom1m` | 1.0000 | 72 | 3452 | 250316 | 0.9839 | Green-validated >= 0.95 |
| `chcsho` | `chcsho` | `chcsho` | 1.0000 | 72 | 3298 | 241695 | 0.9775 | Green-validated >= 0.95 |
| `egr` | `egr` | `egr` | 1.0000 | 72 | 3298 | 241762 | 0.9775 | Green-validated >= 0.95 |
| `hire` | `hire` | `hire` | 1.0000 | 72 | 3294 | 241368 | 0.9777 | Green-validated >= 0.95 |
| `pchsale_pchinvt` | `pchsale_pchinvt` | `pchsale_pchinvt` | 1.0000 | 72 | 2498 | 181310 | 0.9812 | Green-validated >= 0.95 |
| `cashpr` | `cashpr` | `cashpr` | 1.0000 | 72 | 3402 | 246892 | 0.9775 | Green-validated >= 0.95 |
| `roic` | `roic` | `roic` | 1.0000 | 72 | 3416 | 247760 | 0.9775 | Green-validated >= 0.95 |
| `pctacc` | `pctacc` | `pctacc` | 1.0000 | 72 | 3296 | 241697 | 0.9776 | Green-validated >= 0.95 |
| `gma` | `gma` | `gma` | 1.0000 | 72 | 3298 | 241774 | 0.9775 | Green-validated >= 0.95 |
| `acc` | `acc` | `acc` | 1.0000 | 72 | 3296 | 241697 | 0.9776 | Green-validated >= 0.95 |
| `pchcurrat` | `pchcurrat` | `pchcurrat` | 1.0000 | 72 | 2662 | 194745 | 0.7986 | Green-validated >= 0.95 |
| `dolvol` | `dolvol` | `dolvol` | 0.9996 | 72 | 3444 | 249732 | 0.9838 | Green-validated >= 0.95 |
| `invest` | `invest` | `invest` | 0.9992 | 72 | 3228 | 236602 | 0.9806 | Green-validated >= 0.95 |
| `turn` | `turn` | `turn` | 0.9992 | 72 | 3431 | 249270 | 0.9838 | Green-validated >= 0.95 |
| `mve_ia` | `mve_ia` | `me_ia` | 0.9988 | 72 | 3431 | 248722 | 0.9776 | Green-validated >= 0.95 (alias) |
| `chatoia` | `chatoia` | `chatoia` | 0.9988 | 72 | 3198 | 234660 | 0.9773 | Green-validated >= 0.95 |
| `bm_ia` | `bm_ia` | `bm_ia` | 0.9982 | 72 | 3431 | 248722 | 0.9776 | Green-validated >= 0.95 |
| `chempia` | `chempia` | `chempia` | 0.9978 | 72 | 3294 | 241368 | 0.9777 | Green-validated >= 0.95 |
| `cfp_ia` | `cfp_ia` | `cfp_ia` | 0.9973 | 72 | 3431 | 248692 | 0.9777 | Green-validated >= 0.95 |
| `herf` | `herf` | `herf` | 0.9973 | 72 | 3431 | 248722 | 0.9776 | Green-validated >= 0.95 |
| `mom6m` | `mom6m` | `mom6m` | 0.9971 | 72 | 3366 | 246186 | 0.9838 | Green-validated >= 0.95 |
| `grcapx` | `grcapx` | `grcapx` | 0.9963 | 72 | 3136 | 230073 | 0.9776 | Green-validated >= 0.95 |
| `tb` | `tb` | `tb` | 0.9952 | 72 | 2928 | 211743 | 0.9354 | Green-validated >= 0.95 |
| `mom12m` | `mom12m` | `mom12m` | 0.9952 | 72 | 3294 | 241069 | 0.9837 | Green-validated >= 0.95 |
| `mom36m` | `mom36m` | `mom36m` | 0.9934 | 72 | 3070 | 222403 | 0.9832 | Green-validated >= 0.95 |
| `chpmia` | `chpmia` | `chpmia` | 0.9886 | 72 | 3238 | 237283 | 0.9774 | Green-validated >= 0.95 |
| `ps` | `ps` | `ps` | 0.9797 | 72 | 3298 | 241774 | 0.9775 | Green-validated >= 0.95 |
| `cash` | `cash` | `cash` | 0.9319 | 72 | 3422 | 248294 | 0.9779 | Green-validated < 0.95 |
| `roaq` | `roaq` | `roa1` | 0.6628 | 72 | 3422 | 248360 | 0.9782 | Green-validated < 0.95 (alias) |
| `pchcapx_ia` | `pchcapx_ia` | `pchcapx_ia` | 0.6492 | 72 | 3236 | 237165 | 0.9780 | Green-validated < 0.95 |
| `operprof` | `operprof` | `operating_profitability` | 0.5687 | 72 | 3254 | 237011 | 0.9583 | Green-validated < 0.95 (alias) |
| `beta` | `beta` | `beta` | 0.5287 | 72 | 3413 | 248646 | 0.9838 | Green-validated < 0.95 |
| `betasq` | `betasq` | `betasq` | 0.5252 | 72 | 3413 | 248646 | 0.9838 | Green-validated < 0.95 |
| `rsup` | `rsup` | `rsup` | 0.4847 | 72 | 3422 | 248121 | 0.9779 | Green-validated < 0.95 |
| `chtx` | `chtx` | `chtx` | 0.1584 | 72 | 3391 | 246935 | 0.9781 | Green-validated < 0.95 |
| `ear` | `ear` | `abr` | 0.1094 | 72 | 3424 | 248390 | 0.9779 | Green-validated < 0.95 (alias) |
| `nincr` | `nincr` | `nincr` | 0.0530 | 72 | 3425 | 248485 | 0.9780 | Green-validated < 0.95 |
| `cinvest` | `cinvest` | `cinvest` | -0.0708 | 72 | 3302 | 240753 | 0.9673 | Green-validated < 0.95 |

## Below 0.95 vs Green (fix priority)

| Rank | Datashare | Repo | Green | Median ρ | Valid months | Notes |
|-----:|-----------|------|-------|---------:|-------------:|-------|
| 1 | `cinvest` | `cinvest` | `cinvest` | -0.0708 | 72 |  |
| 2 | `nincr` | `nincr` | `nincr` | 0.0530 | 72 | Close (0.92); quarterly earnings-streak logic |
| 3 | `ear` | `abr` | `ear` | 0.1094 | 72 | Event-window `abr` rewrite still mismatches Green `ear` |
| 4 | `chtx` | `chtx` | `chtx` | 0.1584 | 72 |  |
| 5 | `rsup` | `rsup` | `rsup` | 0.4847 | 72 |  |
| 6 | `betasq` | `betasq` | `betasq` | 0.5252 | 72 | Square of `beta`; fix follows beta |
| 7 | `beta` | `beta` | `beta` | 0.5287 | 72 | Green weekly 36m EW-market beta; rebuild pending |
| 8 | `operprof` | `operating_profitability` | `operprof` | 0.5687 | 72 | Repo `operating_profitability` mismatches; try `op` or rebuild from Green |
| 9 | `pchcapx_ia` | `pchcapx_ia` | `pchcapx_ia` | 0.6492 | 72 | Industry-adjusted cap-ex growth; audit formula/timing |
| 10 | `roaq` | `roa1` | `roaq` | 0.6628 | 72 |  |
| 11 | `cash` | `cash` | `cash` | 0.9319 | 72 |  |

## Not validated against Green

| Datashare | Repo | Green | Status | Reason |
|-----------|------|-------|--------|--------|
| `aeavol` | `—` | `aeavol` | missing from repo | No repo implementation / export column |
| `chmom` | `—` | `chmom` | missing from repo | No repo implementation / export column |
| `idiovol` | `—` | `idiovol` | missing from repo | No repo implementation / export column |
| `indmom` | `—` | `indmom` | missing from repo | No repo implementation / export column |
| `ms` | `—` | `ms` | missing from repo | No repo implementation / export column |
| `pricedelay` | `—` | `pricedelay` | missing from repo | No repo implementation / export column |
| `roavol` | `—` | `roavol` | missing from repo | No repo implementation / export column |
| `roeq` | `—` | `roeq` | missing from repo | No repo implementation / export column |
| `sic2` | `—` | `sic2` | missing from repo | No repo implementation / export column |
| `stdacc` | `—` | `stdacc` | missing from repo | No repo implementation / export column |
| `stdcf` | `—` | `stdcf` | missing from repo | No repo implementation / export column |

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
