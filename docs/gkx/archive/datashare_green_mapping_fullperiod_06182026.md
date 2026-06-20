# Datashare columns → Green SAS benchmark mapping

This table defines the **target production column universe** (`datashare.csv`) and how each predictor maps to the current repo panel and Green SAS output.

**Benchmark policy**

- Primary value/timing benchmark: `Supplementary_assistive_files/Output_From_Greens_SAS_code.sas7bdat`
- Column universe only: `Supplementary_assistive_files/datashare.csv`
- Final export names follow **datashare**; repo/Green aliases are documented below.
- Do not prioritize Green-only variables absent from datashare.

Window for validation stats: `198001`–`202412` (monthly `permno × YYYYMM`).

## Summary

- Datashare predictors: **95**
- Green-validated ≥ 0.95: **90**
- Green-validated < 0.95: **5**
- Missing from repo: **0**
- Green column unavailable: **0**
- Alias / audit needed: **0**

## Full mapping

| Datashare | Repo source | Green SAS | Impl. | Validated | Median ρ vs Green | Valid months | Coverage vs Green | Status |
|-----------|-------------|-----------|-------|-----------|------------------:|-------------:|------------------:|--------|
| `absacc` | `absacc` | `absacc` | yes | yes | 1.0000 | 540 | 0.9875 | Green-validated >= 0.95 |
| `acc` | `acc` | `acc` | yes | yes | 1.0000 | 540 | 0.9875 | Green-validated >= 0.95 |
| `aeavol` | `aeavol` | `aeavol` | yes | yes | 0.9999 | 540 | 0.9879 | Green-validated >= 0.95 |
| `age` | `age` | `age` | yes | yes | 1.0000 | 540 | 0.9879 | Green-validated >= 0.95 |
| `agr` | `agr` | `agr` | yes | yes | 1.0000 | 540 | 0.9877 | Green-validated >= 0.95 |
| `baspread` | `baspread` | `baspread` | yes | yes | 1.0000 | 540 | 0.9879 | Green-validated >= 0.95 |
| `beta` | `beta` | `beta` | yes | yes | 0.9985 | 540 | 0.9878 | Green-validated >= 0.95 |
| `betasq` | `betasq` | `betasq` | yes | yes | 0.9984 | 540 | 0.9878 | Green-validated >= 0.95 |
| `bm` | `bm` | `bm` | yes | yes | 1.0000 | 540 | 0.9879 | Green-validated >= 0.95 |
| `bm_ia` | `bm_ia` | `bm_ia` | yes | yes | 0.9976 | 540 | 0.9879 | Green-validated >= 0.95 |
| `cash` | `cash` | `cash` | yes | yes | 1.0000 | 540 | 0.9879 | Green-validated >= 0.95 |
| `cashdebt` | `cashdebt` | `cashdebt` | yes | yes | 1.0000 | 540 | 0.9295 | Green-validated >= 0.95 |
| `cashpr` | `cashpr` | `cashpr` | yes | yes | 1.0000 | 540 | 0.9879 | Green-validated >= 0.95 |
| `cfp` | `cfp` | `cfp` | yes | yes | 1.0000 | 540 | 0.9715 | Green-validated >= 0.95 |
| `cfp_ia` | `cfp_ia` | `cfp_ia` | yes | yes | 0.9936 | 540 | 0.9715 | Green-validated >= 0.95 |
| `chatoia` | `chatoia` | `chatoia` | yes | yes | 0.9986 | 540 | 0.9875 | Green-validated >= 0.95 |
| `chcsho` | `chcsho` | `chcsho` | yes | yes | 1.0000 | 540 | 0.9877 | Green-validated >= 0.95 |
| `chempia` | `chempia` | `chempia` | yes | yes | 0.9947 | 540 | 0.9878 | Green-validated >= 0.95 |
| `chinv` | `chinv` | `chinv` | yes | yes | 1.0000 | 540 | 0.9876 | Green-validated >= 0.95 |
| `chmom` | `chmom` | `chmom` | yes | yes | 0.9934 | 540 | 0.9875 | Green-validated >= 0.95 |
| `chpmia` | `chpmia` | `chpmia` | yes | yes | 0.9927 | 540 | 0.9877 | Green-validated >= 0.95 |
| `chtx` | `chtx` | `chtx` | yes | yes | 1.0000 | 540 | 0.9879 | Green-validated >= 0.95 |
| `cinvest` | `cinvest` | `cinvest` | yes | yes | 0.9897 | 540 | 0.9709 | Green-validated >= 0.95 |
| `convind` | `convind` | `convind` | yes | yes | 1.0000 | 540 | 0.9879 | Green-validated >= 0.95 |
| `currat` | `currat` | `currat` | yes | yes | 1.0000 | 540 | 0.9881 | Green-validated >= 0.95 |
| `depr` | `depr` | `depr` | yes | yes | 1.0000 | 540 | 0.9899 | Green-validated >= 0.95 |
| `divi` | `divi` | `divi` | yes | yes | 1.0000 | 540 | 0.9877 | Green-validated >= 0.95 |
| `divo` | `divo` | `divo` | yes | yes | 1.0000 | 540 | 0.9877 | Green-validated >= 0.95 |
| `dolvol` | `dolvol` | `dolvol` | yes | yes | 0.9993 | 540 | 0.9875 | Green-validated >= 0.95 |
| `dy` | `dy` | `dy` | yes | yes | 1.0000 | 540 | 0.9879 | Green-validated >= 0.95 |
| `ear` | `abr` | `ear` | yes | yes | 0.9998 | 540 | 0.9879 | Green-validated >= 0.95 (alias) |
| `egr` | `egr` | `egr` | yes | yes | 1.0000 | 540 | 0.9877 | Green-validated >= 0.95 |
| `ep` | `ep` | `ep` | yes | yes | 1.0000 | 540 | 0.9879 | Green-validated >= 0.95 |
| `gma` | `gma` | `gma` | yes | yes | 1.0000 | 540 | 0.9876 | Green-validated >= 0.95 |
| `grcapx` | `grcapx` | `grcapx` | yes | yes | 0.9959 | 540 | 0.9312 | Green-validated >= 0.95 |
| `grltnoa` | `grltnoa` | `grltnoa` | yes | yes | 1.0000 | 540 | 0.9885 | Green-validated >= 0.95 |
| `herf` | `herf` | `herf` | yes | yes | 0.9967 | 540 | 0.9879 | Green-validated >= 0.95 |
| `hire` | `hire` | `hire` | yes | yes | 1.0000 | 540 | 0.9878 | Green-validated >= 0.95 |
| `idiovol` | `idiovol` | `idiovol` | yes | yes | 0.9980 | 540 | 0.9878 | Green-validated >= 0.95 |
| `ill` | `ill` | `ill` | yes | yes | 1.0000 | 540 | 0.9877 | Green-validated >= 0.95 |
| `indmom` | `indmom` | `indmom` | yes | yes | -0.0300 | 540 | 0.9820 | Green-validated < 0.95 |
| `invest` | `invest` | `invest` | yes | yes | 0.9992 | 540 | 0.9890 | Green-validated >= 0.95 |
| `lev` | `lev` | `lev` | yes | yes | 1.0000 | 540 | 0.9879 | Green-validated >= 0.95 |
| `lgr` | `lgr` | `lgr` | yes | yes | 1.0000 | 540 | 0.9876 | Green-validated >= 0.95 |
| `maxret` | `maxret` | `maxret` | yes | yes | 1.0000 | 540 | 0.9879 | Green-validated >= 0.95 |
| `mom12m` | `mom12m` | `mom12m` | yes | yes | 0.9946 | 540 | 0.9875 | Green-validated >= 0.95 |
| `mom1m` | `mom1m` | `mom1m` | yes | yes | 1.0000 | 540 | 0.9879 | Green-validated >= 0.95 |
| `mom36m` | `mom36m` | `mom36m` | yes | yes | 0.9920 | 540 | 0.9871 | Green-validated >= 0.95 |
| `mom6m` | `mom6m` | `mom6m` | yes | yes | 0.9959 | 540 | 0.9877 | Green-validated >= 0.95 |
| `ms` | `ms` | `ms` | yes | yes | 0.5797 | 540 | 0.9879 | Green-validated < 0.95 |
| `mve_ia` | `me_ia` | `mve_ia` | yes | yes | 0.9975 | 540 | 0.9879 | Green-validated >= 0.95 (alias) |
| `mvel1` | `mvel1` | `mve` | yes | yes | 1.0000 | 540 | 0.9879 | Green-validated >= 0.95 |
| `nincr` | `nincr` | `nincr` | yes | yes | 1.0000 | 540 | 0.9879 | Green-validated >= 0.95 |
| `operprof` | `operprof` | `operprof` | yes | yes | 0.5726 | 540 | 0.9876 | Green-validated < 0.95 |
| `orgcap` | `orgcap` | `orgcap` | yes | yes | 1.0000 | 454 | 0.9907 | Green-validated >= 0.95 |
| `pchcapx_ia` | `pchcapx_ia` | `pchcapx_ia` | yes | yes | 0.7292 | 540 | 0.9316 | Green-validated < 0.95 |
| `pchcurrat` | `pchcurrat` | `pchcurrat` | yes | yes | 1.0000 | 540 | 0.8543 | Green-validated >= 0.95 |
| `pchdepr` | `pchdepr` | `pchdepr` | yes | yes | 1.0000 | 540 | 0.9897 | Green-validated >= 0.95 |
| `pchgm_pchsale` | `pchgm_pchsale` | `pchgm_pchsale` | yes | yes | 1.0000 | 540 | 0.9876 | Green-validated >= 0.95 |
| `pchquick` | `pchquick` | `pchquick` | yes | yes | 1.0000 | 540 | 0.9879 | Green-validated >= 0.95 |
| `pchsale_pchinvt` | `pchsale_pchinvt` | `pchsale_pchinvt` | yes | yes | 1.0000 | 540 | 0.9908 | Green-validated >= 0.95 |
| `pchsale_pchrect` | `pchsale_pchrect` | `pchsale_pchrect` | yes | yes | 1.0000 | 540 | 0.9878 | Green-validated >= 0.95 |
| `pchsale_pchxsga` | `pchsale_pchxsga` | `pchsale_pchxsga` | yes | yes | 1.0000 | 540 | 0.9888 | Green-validated >= 0.95 |
| `pchsaleinv` | `pchsaleinv` | `pchsaleinv` | yes | yes | 1.0000 | 540 | 0.9909 | Green-validated >= 0.95 |
| `pctacc` | `pctacc` | `pctacc` | yes | yes | 1.0000 | 540 | 0.9875 | Green-validated >= 0.95 |
| `pricedelay` | `pricedelay` | `pricedelay` | yes | yes | 0.9392 | 540 | 0.9878 | Green-validated < 0.95 |
| `ps` | `ps` | `ps` | yes | yes | 0.9792 | 540 | 0.9877 | Green-validated >= 0.95 |
| `quick` | `quick` | `quick` | yes | yes | 1.0000 | 540 | 0.9881 | Green-validated >= 0.95 |
| `rd` | `rd` | `rd` | yes | yes | 1.0000 | 540 | 0.3669 | Green-validated >= 0.95 |
| `rd_mve` | `rdm` | `rd_mve` | yes | yes | 1.0000 | 540 | 0.9881 | Green-validated >= 0.95 (alias) |
| `rd_sale` | `rd_sale` | `rd_sale` | yes | yes | 1.0000 | 540 | 0.9880 | Green-validated >= 0.95 |
| `realestate` | `realestate` | `realestate` | yes | yes | 1.0000 | 480 | 0.9896 | Green-validated >= 0.95 |
| `retvol` | `rvar_mean` | `retvol` | yes | yes | 1.0000 | 540 | 0.9879 | Green-validated >= 0.95 (alias) |
| `roaq` | `roaq` | `roaq` | yes | yes | 1.0000 | 540 | 0.9879 | Green-validated >= 0.95 |
| `roavol` | `roavol` | `roavol` | yes | yes | 1.0000 | 540 | 0.9874 | Green-validated >= 0.95 |
| `roeq` | `roeq` | `roeq` | yes | yes | 1.0000 | 540 | 0.9879 | Green-validated >= 0.95 |
| `roic` | `roic` | `roic` | yes | yes | 1.0000 | 540 | 0.9878 | Green-validated >= 0.95 |
| `rsup` | `rsup` | `rsup` | yes | yes | 1.0000 | 540 | 0.9853 | Green-validated >= 0.95 |
| `salecash` | `salecash` | `salecash` | yes | yes | 1.0000 | 540 | 0.9879 | Green-validated >= 0.95 |
| `saleinv` | `saleinv` | `saleinv` | yes | yes | 1.0000 | 540 | 0.9909 | Green-validated >= 0.95 |
| `salerec` | `salerec` | `salerec` | yes | yes | 1.0000 | 540 | 0.9881 | Green-validated >= 0.95 |
| `secured` | `secured` | `secured` | yes | yes | 1.0000 | 516 | 0.9855 | Green-validated >= 0.95 |
| `securedind` | `securedind` | `securedind` | yes | yes | 1.0000 | 528 | 0.9879 | Green-validated >= 0.95 |
| `sgr` | `sgr` | `sgr` | yes | yes | 1.0000 | 540 | 0.9876 | Green-validated >= 0.95 |
| `sic2` | `sic2` | `sic2` | yes | yes | 0.9970 | 540 | 0.9879 | Green-validated >= 0.95 |
| `sin` | `sin` | `sin` | yes | yes | 1.0000 | 540 | 0.9879 | Green-validated >= 0.95 |
| `sp` | `sp` | `sp` | yes | yes | 1.0000 | 540 | 0.9879 | Green-validated >= 0.95 |
| `std_dolvol` | `std_dolvol` | `std_dolvol` | yes | yes | 1.0000 | 540 | 0.9877 | Green-validated >= 0.95 |
| `std_turn` | `std_turn` | `std_turn` | yes | yes | 1.0000 | 540 | 0.9877 | Green-validated >= 0.95 |
| `stdacc` | `stdacc` | `stdacc` | yes | yes | 0.9984 | 540 | 0.9894 | Green-validated >= 0.95 |
| `stdcf` | `stdcf` | `stdcf` | yes | yes | 0.9984 | 540 | 0.9894 | Green-validated >= 0.95 |
| `tang` | `tang` | `tang` | yes | yes | 1.0000 | 540 | 0.9893 | Green-validated >= 0.95 |
| `tb` | `tb` | `tb` | yes | yes | 0.9954 | 540 | 0.9648 | Green-validated >= 0.95 |
| `turn` | `turn` | `turn` | yes | yes | 0.9988 | 540 | 0.9872 | Green-validated >= 0.95 |
| `zerotrade` | `zerotrade` | `zerotrade` | yes | yes | 1.0000 | 540 | 0.9877 | Green-validated >= 0.95 |

## Known name aliases (export layer)

| Datashare export | Repo source today | Green SAS column |
|------------------|-------------------|------------------|
| `ear` | `abr` | `ear` |
| `roaq` | `roa1` | `roaq` |
| `rd_mve` | `rdm` | `rd_mve` |
| `retvol` | `rvar_mean` | `retvol` |
| `mve_ia` | `me_ia` | `mve_ia` |
| `operprof` | `operating_profitability` (candidate) | `operprof` |
| `roeq` | *not built* (repo has annual `roe` only) | `roeq` |
| `mvel1` | `mvel1` | `mve` (Green name differs) |

## Repo variables outside datashare universe

These exist in the repo panel and/or Green SAS but are **not** datashare predictors (no production export required unless added to datashare later):

`sue` (Green uses IBES when available; repo proxy exists), `roe` (annual; datashare uses quarterly `roeq`), `ni`, `chpm`, `chobklg`, `obklg`, `rna`, `pchcapx`, `book_to_market`, `cash_flow_to_price`, `mom60m`, `rvar_capm`, `rvar_ff3`, `me`, and other repo-only diagnostics.

## Green-only variables excluded from production scope

Green SAS contains predictors and intermediates **not** in datashare. These are out of scope unless needed as build inputs:

`DATE`, `DLRET`, `DLSTCD`, `EXCHCD`, `IPO`, `MEANEST`, `MEANREC`, `RET`, `SHROUT`, `VOL`, `chato`, `grGW`, `sue`, `woGW`
