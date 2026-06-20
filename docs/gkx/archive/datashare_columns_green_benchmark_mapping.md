# Datashare columns → Green SAS benchmark mapping

This table defines the **target production column universe** (`datashare.csv`) and how each predictor maps to the current repo panel and Green SAS output.

**Benchmark policy**

- Primary value/timing benchmark: `Supplementary_assistive_files/Output_From_Greens_SAS_code.sas7bdat`
- Column universe only: `Supplementary_assistive_files/datashare.csv`
- Final export names follow **datashare**; repo/Green aliases are documented below.
- Do not prioritize Green-only variables absent from datashare.

Window for validation stats: `201001`–`201512` (monthly `permno × YYYYMM`).

## Summary

- Datashare predictors: **95**
- Green-validated ≥ 0.95: **73**
- Green-validated < 0.95: **11**
- Missing from repo: **11**
- Green column unavailable: **0**
- Alias / audit needed: **0**

## Full mapping

| Datashare | Repo source | Green SAS | Impl. | Validated | Median ρ vs Green | Valid months | Coverage vs Green | Status |
|-----------|-------------|-----------|-------|-----------|------------------:|-------------:|------------------:|--------|
| `absacc` | `absacc` | `absacc` | yes | yes | 1.0000 | 72 | 0.9776 | Green-validated >= 0.95 |
| `acc` | `acc` | `acc` | yes | yes | 1.0000 | 72 | 0.9776 | Green-validated >= 0.95 |
| `aeavol` | `—` | `aeavol` | no | no | — | 0 | — | missing from repo |
| `age` | `age` | `age` | yes | yes | 1.0000 | 72 | 0.9776 | Green-validated >= 0.95 |
| `agr` | `agr` | `agr` | yes | yes | 1.0000 | 72 | 0.9775 | Green-validated >= 0.95 |
| `baspread` | `baspread` | `baspread` | yes | yes | 1.0000 | 72 | 0.9839 | Green-validated >= 0.95 |
| `beta` | `beta` | `beta` | yes | yes | 0.5287 | 72 | 0.9838 | Green-validated < 0.95 |
| `betasq` | `betasq` | `betasq` | yes | yes | 0.5252 | 72 | 0.9838 | Green-validated < 0.95 |
| `bm` | `bm` | `bm` | yes | yes | 1.0000 | 72 | 0.9776 | Green-validated >= 0.95 |
| `bm_ia` | `bm_ia` | `bm_ia` | yes | yes | 0.9982 | 72 | 0.9776 | Green-validated >= 0.95 |
| `cash` | `cash` | `cash` | yes | yes | 0.9319 | 72 | 0.9779 | Green-validated < 0.95 |
| `cashdebt` | `cashdebt` | `cashdebt` | yes | yes | 1.0000 | 72 | 0.9527 | Green-validated >= 0.95 |
| `cashpr` | `cashpr` | `cashpr` | yes | yes | 1.0000 | 72 | 0.9775 | Green-validated >= 0.95 |
| `cfp` | `cfp` | `cfp` | yes | yes | 1.0000 | 72 | 0.9777 | Green-validated >= 0.95 |
| `cfp_ia` | `cfp_ia` | `cfp_ia` | yes | yes | 0.9973 | 72 | 0.9777 | Green-validated >= 0.95 |
| `chatoia` | `chatoia` | `chatoia` | yes | yes | 0.9988 | 72 | 0.9773 | Green-validated >= 0.95 |
| `chcsho` | `chcsho` | `chcsho` | yes | yes | 1.0000 | 72 | 0.9775 | Green-validated >= 0.95 |
| `chempia` | `chempia` | `chempia` | yes | yes | 0.9978 | 72 | 0.9777 | Green-validated >= 0.95 |
| `chinv` | `chinv` | `chinv` | yes | yes | 1.0000 | 72 | 0.9776 | Green-validated >= 0.95 |
| `chmom` | `—` | `chmom` | no | no | — | 0 | — | missing from repo |
| `chpmia` | `chpmia` | `chpmia` | yes | yes | 0.9886 | 72 | 0.9774 | Green-validated >= 0.95 |
| `chtx` | `chtx` | `chtx` | yes | yes | 0.1584 | 72 | 0.9781 | Green-validated < 0.95 |
| `cinvest` | `cinvest` | `cinvest` | yes | yes | -0.0708 | 72 | 0.9673 | Green-validated < 0.95 |
| `convind` | `convind` | `convind` | yes | yes | 1.0000 | 72 | 0.9776 | Green-validated >= 0.95 |
| `currat` | `currat` | `currat` | yes | yes | 1.0000 | 72 | 0.9775 | Green-validated >= 0.95 |
| `depr` | `depr` | `depr` | yes | yes | 1.0000 | 72 | 0.9813 | Green-validated >= 0.95 |
| `divi` | `divi` | `divi` | yes | yes | 1.0000 | 72 | 0.9775 | Green-validated >= 0.95 |
| `divo` | `divo` | `divo` | yes | yes | 1.0000 | 72 | 0.9775 | Green-validated >= 0.95 |
| `dolvol` | `dolvol` | `dolvol` | yes | yes | 0.9996 | 72 | 0.9838 | Green-validated >= 0.95 |
| `dy` | `dy` | `dy` | yes | yes | 1.0000 | 72 | 0.9776 | Green-validated >= 0.95 |
| `ear` | `abr` | `ear` | yes | yes | 0.1094 | 72 | 0.9779 | Green-validated < 0.95 (alias) |
| `egr` | `egr` | `egr` | yes | yes | 1.0000 | 72 | 0.9775 | Green-validated >= 0.95 |
| `ep` | `ep` | `ep` | yes | yes | 1.0000 | 72 | 0.9776 | Green-validated >= 0.95 |
| `gma` | `gma` | `gma` | yes | yes | 1.0000 | 72 | 0.9775 | Green-validated >= 0.95 |
| `grcapx` | `grcapx` | `grcapx` | yes | yes | 0.9963 | 72 | 0.9776 | Green-validated >= 0.95 |
| `grltnoa` | `grltnoa` | `grltnoa` | yes | yes | 1.0000 | 72 | 0.9784 | Green-validated >= 0.95 |
| `herf` | `herf` | `herf` | yes | yes | 0.9973 | 72 | 0.9776 | Green-validated >= 0.95 |
| `hire` | `hire` | `hire` | yes | yes | 1.0000 | 72 | 0.9777 | Green-validated >= 0.95 |
| `idiovol` | `—` | `idiovol` | no | no | — | 0 | — | missing from repo |
| `ill` | `ill` | `ill` | yes | yes | 1.0000 | 72 | 0.9839 | Green-validated >= 0.95 |
| `indmom` | `—` | `indmom` | no | no | — | 0 | — | missing from repo |
| `invest` | `invest` | `invest` | yes | yes | 0.9992 | 72 | 0.9806 | Green-validated >= 0.95 |
| `lev` | `lev` | `lev` | yes | yes | 1.0000 | 72 | 0.9775 | Green-validated >= 0.95 |
| `lgr` | `lgr` | `lgr` | yes | yes | 1.0000 | 72 | 0.9775 | Green-validated >= 0.95 |
| `maxret` | `maxret` | `maxret` | yes | yes | 1.0000 | 72 | 0.9839 | Green-validated >= 0.95 |
| `mom12m` | `mom12m` | `mom12m` | yes | yes | 0.9952 | 72 | 0.9837 | Green-validated >= 0.95 |
| `mom1m` | `mom1m` | `mom1m` | yes | yes | 1.0000 | 72 | 0.9839 | Green-validated >= 0.95 |
| `mom36m` | `mom36m` | `mom36m` | yes | yes | 0.9934 | 72 | 0.9832 | Green-validated >= 0.95 |
| `mom6m` | `mom6m` | `mom6m` | yes | yes | 0.9971 | 72 | 0.9838 | Green-validated >= 0.95 |
| `ms` | `—` | `ms` | no | no | — | 0 | — | missing from repo |
| `mve_ia` | `me_ia` | `mve_ia` | yes | yes | 0.9988 | 72 | 0.9776 | Green-validated >= 0.95 (alias) |
| `mvel1` | `mvel1` | `mve` | yes | yes | 1.0000 | 72 | 0.9839 | Green-validated >= 0.95 |
| `nincr` | `nincr` | `nincr` | yes | yes | 0.0530 | 72 | 0.9780 | Green-validated < 0.95 |
| `operprof` | `operating_profitability` | `operprof` | yes | yes | 0.5687 | 72 | 0.9583 | Green-validated < 0.95 (alias) |
| `orgcap` | `orgcap` | `orgcap` | yes | yes | 1.0000 | 72 | 0.9790 | Green-validated >= 0.95 |
| `pchcapx_ia` | `pchcapx_ia` | `pchcapx_ia` | yes | yes | 0.6492 | 72 | 0.9780 | Green-validated < 0.95 |
| `pchcurrat` | `pchcurrat` | `pchcurrat` | yes | yes | 1.0000 | 72 | 0.7986 | Green-validated >= 0.95 |
| `pchdepr` | `pchdepr` | `pchdepr` | yes | yes | 1.0000 | 72 | 0.9812 | Green-validated >= 0.95 |
| `pchgm_pchsale` | `pchgm_pchsale` | `pchgm_pchsale` | yes | yes | 1.0000 | 72 | 0.9773 | Green-validated >= 0.95 |
| `pchquick` | `pchquick` | `pchquick` | yes | yes | 1.0000 | 72 | 0.9775 | Green-validated >= 0.95 |
| `pchsale_pchinvt` | `pchsale_pchinvt` | `pchsale_pchinvt` | yes | yes | 1.0000 | 72 | 0.9812 | Green-validated >= 0.95 |
| `pchsale_pchrect` | `pchsale_pchrect` | `pchsale_pchrect` | yes | yes | 1.0000 | 72 | 0.9772 | Green-validated >= 0.95 |
| `pchsale_pchxsga` | `pchsale_pchxsga` | `pchsale_pchxsga` | yes | yes | 1.0000 | 72 | 0.9784 | Green-validated >= 0.95 |
| `pchsaleinv` | `pchsaleinv` | `pchsaleinv` | yes | yes | 1.0000 | 72 | 0.9811 | Green-validated >= 0.95 |
| `pctacc` | `pctacc` | `pctacc` | yes | yes | 1.0000 | 72 | 0.9776 | Green-validated >= 0.95 |
| `pricedelay` | `—` | `pricedelay` | no | no | — | 0 | — | missing from repo |
| `ps` | `ps` | `ps` | yes | yes | 0.9797 | 72 | 0.9775 | Green-validated >= 0.95 |
| `quick` | `quick` | `quick` | yes | yes | 1.0000 | 72 | 0.9776 | Green-validated >= 0.95 |
| `rd` | `rd` | `rd` | yes | yes | 1.0000 | 72 | 0.3957 | Green-validated >= 0.95 |
| `rd_mve` | `rdm` | `rd_mve` | yes | yes | 1.0000 | 72 | 0.9795 | Green-validated >= 0.95 (alias) |
| `rd_sale` | `rd_sale` | `rd_sale` | yes | yes | 1.0000 | 72 | 0.9791 | Green-validated >= 0.95 |
| `realestate` | `realestate` | `realestate` | yes | yes | 1.0000 | 72 | 0.9811 | Green-validated >= 0.95 |
| `retvol` | `rvar_mean` | `retvol` | yes | yes | 1.0000 | 72 | 0.9839 | Green-validated >= 0.95 (alias) |
| `roaq` | `roa1` | `roaq` | yes | yes | 0.6628 | 72 | 0.9782 | Green-validated < 0.95 (alias) |
| `roavol` | `—` | `roavol` | no | no | — | 0 | — | missing from repo |
| `roeq` | `—` | `roeq` | no | no | — | 0 | — | missing from repo |
| `roic` | `roic` | `roic` | yes | yes | 1.0000 | 72 | 0.9775 | Green-validated >= 0.95 |
| `rsup` | `rsup` | `rsup` | yes | yes | 0.4847 | 72 | 0.9779 | Green-validated < 0.95 |
| `salecash` | `salecash` | `salecash` | yes | yes | 1.0000 | 72 | 0.9776 | Green-validated >= 0.95 |
| `saleinv` | `saleinv` | `saleinv` | yes | yes | 1.0000 | 72 | 0.9814 | Green-validated >= 0.95 |
| `salerec` | `salerec` | `salerec` | yes | yes | 1.0000 | 72 | 0.9774 | Green-validated >= 0.95 |
| `secured` | `secured` | `secured` | yes | yes | 1.0000 | 72 | 0.9711 | Green-validated >= 0.95 |
| `securedind` | `securedind` | `securedind` | yes | yes | 1.0000 | 72 | 0.9776 | Green-validated >= 0.95 |
| `sgr` | `sgr` | `sgr` | yes | yes | 1.0000 | 72 | 0.9773 | Green-validated >= 0.95 |
| `sic2` | `—` | `sic2` | no | no | — | 0 | — | missing from repo |
| `sin` | `sin` | `sin` | yes | yes | 1.0000 | 72 | 0.9776 | Green-validated >= 0.95 |
| `sp` | `sp` | `sp` | yes | yes | 1.0000 | 72 | 0.9776 | Green-validated >= 0.95 |
| `std_dolvol` | `std_dolvol` | `std_dolvol` | yes | yes | 1.0000 | 72 | 0.9839 | Green-validated >= 0.95 |
| `std_turn` | `std_turn` | `std_turn` | yes | yes | 1.0000 | 72 | 0.9839 | Green-validated >= 0.95 |
| `stdacc` | `—` | `stdacc` | no | no | — | 0 | — | missing from repo |
| `stdcf` | `—` | `stdcf` | no | no | — | 0 | — | missing from repo |
| `tang` | `tang` | `tang` | yes | yes | 1.0000 | 72 | 0.9805 | Green-validated >= 0.95 |
| `tb` | `tb` | `tb` | yes | yes | 0.9952 | 72 | 0.9354 | Green-validated >= 0.95 |
| `turn` | `turn` | `turn` | yes | yes | 0.9992 | 72 | 0.9838 | Green-validated >= 0.95 |
| `zerotrade` | `zerotrade` | `zerotrade` | yes | yes | 1.0000 | 72 | 0.9839 | Green-validated >= 0.95 |

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
