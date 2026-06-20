# Datashare columns — Green SAS validation (primary)

Validation window: `198001`–`202412`. Monthly cross-sectional Spearman on `permno × YYYYMM`; months with < 50 paired observations skipped.

Repo panel: `outputs/panels/all_character_signal_panel.csv`
Green SAS: `Supplementary_assistive_files/Output_From_Greens_SAS_code.sas7bdat`

**Datashare values are not the primary benchmark** — they are omitted here except where noted for diagnostics in separate reports.

## Green-validated predictors

| Datashare | Green SAS | Repo source | Median ρ | Valid months | Median pairs/mo | Total pairs | Coverage | Status |
|-----------|-----------|-------------|---------:|-------------:|----------------:|------------:|---------:|--------|
| `convind` | `convind` | `convind` | 1.0000 | 540 | 4226 | 2245687 | 0.9879 | Green-validated >= 0.95 |
| `divo` | `divo` | `divo` | 1.0000 | 540 | 3957 | 2110251 | 0.9877 | Green-validated >= 0.95 |
| `divi` | `divi` | `divi` | 1.0000 | 540 | 3957 | 2110251 | 0.9877 | Green-validated >= 0.95 |
| `sin` | `sin` | `sin` | 1.0000 | 540 | 4226 | 2245687 | 0.9879 | Green-validated >= 0.95 |
| `rd` | `rd` | `rd` | 1.0000 | 540 | 1442 | 783837 | 0.3669 | Green-validated >= 0.95 |
| `securedind` | `securedind` | `securedind` | 1.0000 | 528 | 4226 | 2245687 | 0.9879 | Green-validated >= 0.95 |
| `age` | `age` | `age` | 1.0000 | 540 | 4226 | 2245687 | 0.9879 | Green-validated >= 0.95 |
| `nincr` | `nincr` | `nincr` | 1.0000 | 540 | 3668 | 2036616 | 0.9879 | Green-validated >= 0.95 |
| `depr` | `depr` | `depr` | 1.0000 | 540 | 4079 | 2157435 | 0.9899 | Green-validated >= 0.95 |
| `realestate` | `realestate` | `realestate` | 1.0000 | 480 | 1835 | 990534 | 0.9896 | Green-validated >= 0.95 |
| `sp` | `sp` | `sp` | 1.0000 | 540 | 4221 | 2240138 | 0.9879 | Green-validated >= 0.95 |
| `orgcap` | `orgcap` | `orgcap` | 1.0000 | 454 | 3273 | 1482759 | 0.9907 | Green-validated >= 0.95 |
| `tang` | `tang` | `tang` | 1.0000 | 540 | 4068 | 2160327 | 0.9893 | Green-validated >= 0.95 |
| `lev` | `lev` | `lev` | 1.0000 | 540 | 4210 | 2239557 | 0.9879 | Green-validated >= 0.95 |
| `salerec` | `salerec` | `salerec` | 1.0000 | 540 | 4098 | 2165957 | 0.9881 | Green-validated >= 0.95 |
| `pchsaleinv` | `pchsaleinv` | `pchsaleinv` | 1.0000 | 540 | 3146 | 1633644 | 0.9909 | Green-validated >= 0.95 |
| `saleinv` | `saleinv` | `saleinv` | 1.0000 | 540 | 3344 | 1755855 | 0.9909 | Green-validated >= 0.95 |
| `roavol` | `roavol` | `roavol` | 1.0000 | 540 | 3234 | 1757593 | 0.9874 | Green-validated >= 0.95 |
| `salecash` | `salecash` | `salecash` | 1.0000 | 540 | 4206 | 2229046 | 0.9879 | Green-validated >= 0.95 |
| `rd_mve` | `rd_mve` | `rdm` | 1.0000 | 540 | 2070 | 1100763 | 0.9881 | Green-validated >= 0.95 (alias) |
| `secured` | `secured` | `secured` | 1.0000 | 516 | 2597 | 1346255 | 0.9855 | Green-validated >= 0.95 |
| `rd_sale` | `rd_sale` | `rd_sale` | 1.0000 | 540 | 2042 | 1079406 | 0.9880 | Green-validated >= 0.95 |
| `cash` | `cash` | `cash` | 1.0000 | 540 | 3619 | 2025147 | 0.9879 | Green-validated >= 0.95 |
| `dy` | `dy` | `dy` | 1.0000 | 540 | 4218 | 2240161 | 0.9879 | Green-validated >= 0.95 |
| `std_turn` | `std_turn` | `std_turn` | 1.0000 | 540 | 4225 | 2185131 | 0.9877 | Green-validated >= 0.95 |
| `ill` | `ill` | `ill` | 1.0000 | 540 | 4221 | 2183365 | 0.9877 | Green-validated >= 0.95 |
| `std_dolvol` | `std_dolvol` | `std_dolvol` | 1.0000 | 540 | 4220 | 2180166 | 0.9877 | Green-validated >= 0.95 |
| `cashdebt` | `cashdebt` | `cashdebt` | 1.0000 | 540 | 3803 | 2042211 | 0.9295 | Green-validated >= 0.95 |
| `zerotrade` | `zerotrade` | `zerotrade` | 1.0000 | 540 | 4221 | 2183393 | 0.9877 | Green-validated >= 0.95 |
| `absacc` | `absacc` | `absacc` | 1.0000 | 540 | 3664 | 1971865 | 0.9875 | Green-validated >= 0.95 |
| `retvol` | `retvol` | `rvar_mean` | 1.0000 | 540 | 4226 | 2245628 | 0.9879 | Green-validated >= 0.95 (alias) |
| `baspread` | `baspread` | `baspread` | 1.0000 | 540 | 4226 | 2245641 | 0.9879 | Green-validated >= 0.95 |
| `currat` | `currat` | `currat` | 1.0000 | 540 | 4092 | 2175897 | 0.9881 | Green-validated >= 0.95 |
| `quick` | `quick` | `quick` | 1.0000 | 540 | 4074 | 2163228 | 0.9881 | Green-validated >= 0.95 |
| `pchquick` | `pchquick` | `pchquick` | 1.0000 | 540 | 3754 | 2024323 | 0.9879 | Green-validated >= 0.95 |
| `ep` | `ep` | `ep` | 1.0000 | 540 | 4226 | 2245687 | 0.9879 | Green-validated >= 0.95 |
| `sgr` | `sgr` | `sgr` | 1.0000 | 540 | 3910 | 2078502 | 0.9876 | Green-validated >= 0.95 |
| `bm` | `bm` | `bm` | 1.0000 | 540 | 4226 | 2245687 | 0.9879 | Green-validated >= 0.95 |
| `cfp` | `cfp` | `cfp` | 1.0000 | 540 | 3686 | 2053974 | 0.9715 | Green-validated >= 0.95 |
| `agr` | `agr` | `agr` | 1.0000 | 540 | 3957 | 2110218 | 0.9877 | Green-validated >= 0.95 |
| `grltnoa` | `grltnoa` | `grltnoa` | 1.0000 | 540 | 3058 | 1609145 | 0.9885 | Green-validated >= 0.95 |
| `pchdepr` | `pchdepr` | `pchdepr` | 1.0000 | 540 | 3766 | 2017871 | 0.9897 | Green-validated >= 0.95 |
| `pchsale_pchxsga` | `pchsale_pchxsga` | `pchsale_pchxsga` | 1.0000 | 540 | 3332 | 1755430 | 0.9888 | Green-validated >= 0.95 |
| `pchsale_pchrect` | `pchsale_pchrect` | `pchsale_pchrect` | 1.0000 | 540 | 3766 | 2022482 | 0.9878 | Green-validated >= 0.95 |
| `lgr` | `lgr` | `lgr` | 1.0000 | 540 | 3947 | 2103137 | 0.9876 | Green-validated >= 0.95 |
| `egr` | `egr` | `egr` | 1.0000 | 540 | 3957 | 2110065 | 0.9877 | Green-validated >= 0.95 |
| `chcsho` | `chcsho` | `chcsho` | 1.0000 | 540 | 3956 | 2109433 | 0.9877 | Green-validated >= 0.95 |
| `pchsale_pchinvt` | `pchsale_pchinvt` | `pchsale_pchinvt` | 1.0000 | 540 | 3178 | 1654964 | 0.9908 | Green-validated >= 0.95 |
| `chinv` | `chinv` | `chinv` | 1.0000 | 540 | 3861 | 2058483 | 0.9876 | Green-validated >= 0.95 |
| `roic` | `roic` | `roic` | 1.0000 | 540 | 4094 | 2161102 | 0.9878 | Green-validated >= 0.95 |
| `pchgm_pchsale` | `pchgm_pchsale` | `pchgm_pchsale` | 1.0000 | 540 | 3910 | 2078322 | 0.9876 | Green-validated >= 0.95 |
| `cashpr` | `cashpr` | `cashpr` | 1.0000 | 540 | 4196 | 2223859 | 0.9879 | Green-validated >= 0.95 |
| `gma` | `gma` | `gma` | 1.0000 | 540 | 3957 | 2105702 | 0.9876 | Green-validated >= 0.95 |
| `rsup` | `rsup` | `rsup` | 1.0000 | 540 | 3631 | 2017051 | 0.9853 | Green-validated >= 0.95 |
| `hire` | `hire` | `hire` | 1.0000 | 540 | 3950 | 2106009 | 0.9878 | Green-validated >= 0.95 |
| `roeq` | `roeq` | `roeq` | 1.0000 | 540 | 3658 | 2033230 | 0.9879 | Green-validated >= 0.95 |
| `roaq` | `roaq` | `roaq` | 1.0000 | 540 | 3659 | 2033470 | 0.9879 | Green-validated >= 0.95 |
| `chtx` | `chtx` | `chtx` | 1.0000 | 540 | 3604 | 2000654 | 0.9879 | Green-validated >= 0.95 |
| `acc` | `acc` | `acc` | 1.0000 | 540 | 3664 | 1971865 | 0.9875 | Green-validated >= 0.95 |
| `pctacc` | `pctacc` | `pctacc` | 1.0000 | 540 | 3664 | 1971853 | 0.9875 | Green-validated >= 0.95 |
| `pchcurrat` | `pchcurrat` | `pchcurrat` | 1.0000 | 540 | 3352 | 1762552 | 0.8543 | Green-validated >= 0.95 |
| `mom1m` | `mom1m` | `mom1m` | 1.0000 | 540 | 4226 | 2245687 | 0.9879 | Green-validated >= 0.95 |
| `maxret` | `maxret` | `maxret` | 1.0000 | 540 | 4226 | 2245671 | 0.9879 | Green-validated >= 0.95 |
| `mvel1` | `mve` | `mvel1` | 1.0000 | 540 | 4226 | 2245687 | 0.9879 | Green-validated >= 0.95 |
| `aeavol` | `aeavol` | `aeavol` | 0.9999 | 540 | 3665 | 2023393 | 0.9879 | Green-validated >= 0.95 |
| `ear` | `ear` | `abr` | 0.9998 | 540 | 3666 | 2035028 | 0.9879 | Green-validated >= 0.95 (alias) |
| `dolvol` | `dolvol` | `dolvol` | 0.9993 | 540 | 4210 | 2171184 | 0.9875 | Green-validated >= 0.95 |
| `invest` | `invest` | `invest` | 0.9992 | 540 | 3852 | 2043832 | 0.9890 | Green-validated >= 0.95 |
| `turn` | `turn` | `turn` | 0.9988 | 540 | 4191 | 2171654 | 0.9872 | Green-validated >= 0.95 |
| `chatoia` | `chatoia` | `chatoia` | 0.9986 | 540 | 3652 | 1959963 | 0.9875 | Green-validated >= 0.95 |
| `beta` | `beta` | `beta` | 0.9985 | 540 | 4186 | 2224781 | 0.9878 | Green-validated >= 0.95 |
| `stdcf` | `stdcf` | `stdcf` | 0.9984 | 540 | 2687 | 1460601 | 0.9894 | Green-validated >= 0.95 |
| `stdacc` | `stdacc` | `stdacc` | 0.9984 | 540 | 2687 | 1460601 | 0.9894 | Green-validated >= 0.95 |
| `betasq` | `betasq` | `betasq` | 0.9984 | 540 | 4186 | 2224781 | 0.9878 | Green-validated >= 0.95 |
| `idiovol` | `idiovol` | `idiovol` | 0.9980 | 540 | 4186 | 2224781 | 0.9878 | Green-validated >= 0.95 |
| `bm_ia` | `bm_ia` | `bm_ia` | 0.9976 | 540 | 4226 | 2245687 | 0.9879 | Green-validated >= 0.95 |
| `mve_ia` | `mve_ia` | `me_ia` | 0.9975 | 540 | 4226 | 2245687 | 0.9879 | Green-validated >= 0.95 (alias) |
| `sic2` | `sic2` | `sic2` | 0.9970 | 540 | 4226 | 2245687 | 0.9879 | Green-validated >= 0.95 |
| `herf` | `herf` | `herf` | 0.9967 | 540 | 4226 | 2245677 | 0.9879 | Green-validated >= 0.95 |
| `mom6m` | `mom6m` | `mom6m` | 0.9959 | 540 | 4104 | 2185914 | 0.9877 | Green-validated >= 0.95 |
| `grcapx` | `grcapx` | `grcapx` | 0.9959 | 540 | 3390 | 1800023 | 0.9312 | Green-validated >= 0.95 |
| `tb` | `tb` | `tb` | 0.9954 | 540 | 3578 | 1932375 | 0.9648 | Green-validated >= 0.95 |
| `chempia` | `chempia` | `chempia` | 0.9947 | 540 | 3950 | 2106009 | 0.9878 | Green-validated >= 0.95 |
| `mom12m` | `mom12m` | `mom12m` | 0.9946 | 540 | 3926 | 2098354 | 0.9875 | Green-validated >= 0.95 |
| `cfp_ia` | `cfp_ia` | `cfp_ia` | 0.9936 | 540 | 3686 | 2053974 | 0.9715 | Green-validated >= 0.95 |
| `chmom` | `chmom` | `chmom` | 0.9934 | 540 | 3926 | 2098354 | 0.9875 | Green-validated >= 0.95 |
| `chpmia` | `chpmia` | `chpmia` | 0.9927 | 540 | 3903 | 2073256 | 0.9877 | Green-validated >= 0.95 |
| `mom36m` | `mom36m` | `mom36m` | 0.9920 | 540 | 3313 | 1794364 | 0.9871 | Green-validated >= 0.95 |
| `cinvest` | `cinvest` | `cinvest` | 0.9897 | 540 | 3532 | 1956352 | 0.9709 | Green-validated >= 0.95 |
| `ps` | `ps` | `ps` | 0.9792 | 540 | 3957 | 2110251 | 0.9877 | Green-validated >= 0.95 |
| `pricedelay` | `pricedelay` | `pricedelay` | 0.9392 | 540 | 4186 | 2224752 | 0.9878 | Green-validated < 0.95 |
| `pchcapx_ia` | `pchcapx_ia` | `pchcapx_ia` | 0.7292 | 540 | 3688 | 1934184 | 0.9316 | Green-validated < 0.95 |
| `ms` | `ms` | `ms` | 0.5797 | 540 | 3668 | 2036616 | 0.9879 | Green-validated < 0.95 |
| `operprof` | `operprof` | `operprof` | 0.5726 | 540 | 3957 | 2105549 | 0.9876 | Green-validated < 0.95 |
| `indmom` | `indmom` | `indmom` | -0.0300 | 540 | 4200 | 2232013 | 0.9820 | Green-validated < 0.95 |

## Below 0.95 vs Green (fix priority)

| Rank | Datashare | Repo | Green | Median ρ | Valid months | Notes |
|-----:|-----------|------|-------|---------:|-------------:|-------|
| 1 | `indmom` | `indmom` | `indmom` | -0.0300 | 540 |  |
| 2 | `operprof` | `operprof` | `operprof` | 0.5726 | 540 | Repo `operating_profitability` mismatches; try `op` or rebuild from Green |
| 3 | `ms` | `ms` | `ms` | 0.5797 | 540 |  |
| 4 | `pchcapx_ia` | `pchcapx_ia` | `pchcapx_ia` | 0.7292 | 540 | Industry-adjusted cap-ex growth; audit formula/timing |
| 5 | `pricedelay` | `pricedelay` | `pricedelay` | 0.9392 | 540 |  |

## Not validated against Green

| Datashare | Repo | Green | Status | Reason |
|-----------|------|-------|--------|--------|

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
