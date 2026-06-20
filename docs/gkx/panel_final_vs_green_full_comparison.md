# Server panel vs Green SAS — full-period similarity (datashare columns)

- Panel: `all_character_signal_panel_final.csv`
- Green SAS: `Output_From_Greens_SAS_code.sas7bdat`
- Column universe: `datashare.csv` (95 predictors incl. `sic2`)
- Comparison: raw overlapping `permno × YYYYMM` cells, **no universe screen**.
- Alignment: panel `signal_yyyymm` == Green `DATE` month.
- `operprof` diverges **by design** (Green output drops `xsga0`; repo follows the SAS code).

## Dataset-level

| Dataset | Rows | Unique permnos | Month range |
|---------|-----:|---------------:|-------------|
| Panel | 4,605,028 | 31,111 | 192602–202805 |
| Green | 2,273,186 | 18,702 | 198001–202412 |

- Overlapping `permno × month` cells: **2,271,037** (= 99.9% of Green's rows).
- Permnos in both: **18,677**; panel-only: **12,409**; green-only: **0**.
- Green's permno set is essentially a **subset** of the panel's (panel is a superset; the extra ~12.4k permnos are CRSP names with no linked Compustat / outside Green's screen).

## Per-column similarity (sorted by median monthly Spearman)

`exact%` = share of paired cells with |Δ| ≤ 1e-4; `rel%` = |Δ| ≤ 1e-3·(1+|green|). High ρ with low exact% means ranks agree but levels differ by a monotone transform (scaling / log base / winsor / offset).

| datashare | panel col | green col | median ρ | pooled ρ | exact% | rel% | paired | panel N | green N |
|-----------|-----------|-----------|---------:|---------:|-------:|-----:|-------:|--------:|--------:|
| `convind` | `convind` | `convind` | 1.000 | 1.000 | 100.0 | 100.0 | 2,245,687 | 2,467,856 | 2,273,186 |
| `divo` | `divo` | `divo` | 1.000 | 1.000 | 100.0 | 100.0 | 2,110,251 | 2,263,814 | 2,136,629 |
| `securedind` | `securedind` | `securedind` | 1.000 | 1.000 | 100.0 | 100.0 | 2,245,687 | 2,467,856 | 2,273,186 |
| `sin` | `sin` | `sin` | 1.000 | 1.000 | 100.0 | 100.0 | 2,245,687 | 2,467,856 | 2,273,186 |
| `rd` | `rd` | `rd` | 1.000 | 0.999 | 100.0 | 100.0 | 783,837 | 819,447 | 2,136,629 |
| `divi` | `divi` | `divi` | 1.000 | 1.000 | 100.0 | 100.0 | 2,110,251 | 2,263,814 | 2,136,629 |
| `age` | `age` | `age` | 1.000 | 1.000 | 99.9 | 99.9 | 2,245,687 | 2,467,856 | 2,273,186 |
| `nincr` | `nincr` | `nincr` | 1.000 | 1.000 | 100.0 | 100.0 | 2,036,616 | 2,278,481 | 2,061,573 |
| `depr` | `depr` | `depr` | 1.000 | 1.000 | 99.0 | 99.0 | 2,157,435 | 2,366,310 | 2,179,378 |
| `realestate` | `realestate` | `realestate` | 1.000 | 1.000 | 99.0 | 99.1 | 990,534 | 1,022,123 | 1,000,927 |
| `sp` | `sp` | `sp` | 1.000 | 1.000 | 99.0 | 99.0 | 2,240,138 | 2,460,768 | 2,267,603 |
| `orgcap` | `orgcap` | `orgcap` | 1.000 | 1.000 | 99.0 | 99.1 | 1,482,759 | 1,924,227 | 1,496,656 |
| `tang` | `tang` | `tang` | 1.000 | 1.000 | 99.0 | 99.1 | 2,160,327 | 2,370,047 | 2,183,729 |
| `lev` | `lev` | `lev` | 1.000 | 1.000 | 99.0 | 99.0 | 2,239,557 | 2,460,339 | 2,266,992 |
| `salerec` | `salerec` | `salerec` | 1.000 | 1.000 | 99.0 | 99.0 | 2,165,957 | 2,380,443 | 2,192,153 |
| `pchsaleinv` | `pchsaleinv` | `pchsaleinv` | 1.000 | 1.000 | 99.0 | 99.0 | 1,633,644 | 1,764,529 | 1,648,697 |
| `saleinv` | `saleinv` | `saleinv` | 1.000 | 1.000 | 99.0 | 99.0 | 1,755,855 | 1,945,594 | 1,771,920 |
| `roavol` | `roavol` | `roavol` | 1.000 | 1.000 | 99.0 | 99.0 | 1,757,593 | 1,819,161 | 1,780,060 |
| `salecash` | `salecash` | `salecash` | 1.000 | 1.000 | 99.0 | 99.0 | 2,229,046 | 2,450,670 | 2,256,366 |
| `rd_mve` | `rdm` | `rd_mve` | 1.000 | 1.000 | 99.0 | 99.0 | 1,100,763 | 1,204,306 | 1,114,005 |
| `secured` | `secured` | `secured` | 1.000 | 1.000 | 99.0 | 99.0 | 1,346,255 | 1,400,440 | 1,366,114 |
| `rd_sale` | `rd_sale` | `rd_sale` | 1.000 | 1.000 | 99.0 | 99.0 | 1,079,406 | 1,182,465 | 1,092,463 |
| `cash` | `cash` | `cash` | 1.000 | 1.000 | 99.0 | 99.0 | 2,025,147 | 2,254,098 | 2,050,002 |
| `dy` | `dy` | `dy` | 1.000 | 1.000 | 99.0 | 99.1 | 2,240,161 | 2,461,292 | 2,267,579 |
| `std_turn` | `std_turn` | `std_turn` | 1.000 | 1.000 | 99.0 | 99.0 | 2,185,131 | 3,430,754 | 2,212,360 |
| `ill` | `ill` | `ill` | 1.000 | 1.000 | 99.6 | 99.9 | 2,183,365 | 3,425,334 | 2,210,529 |
| `std_dolvol` | `std_dolvol` | `std_dolvol` | 1.000 | 1.000 | 0.0 | 0.0 | 2,180,166 | 3,417,587 | 2,207,212 |
| `cashdebt` | `cashdebt` | `cashdebt` | 1.000 | 1.000 | 99.0 | 99.0 | 2,042,211 | 2,188,573 | 2,197,005 |
| `absacc` | `absacc` | `absacc` | 1.000 | 1.000 | 99.0 | 99.0 | 1,971,865 | 2,114,025 | 1,996,902 |
| `retvol` | `rvar_mean` | `retvol` | 1.000 | 1.000 | 99.0 | 99.1 | 2,245,628 | 3,706,721 | 2,273,127 |
| `baspread` | `baspread` | `baspread` | 1.000 | 1.000 | 99.1 | 99.1 | 2,245,641 | 3,706,740 | 2,273,141 |
| `zerotrade` | `zerotrade` | `zerotrade` | 1.000 | 1.000 | 99.2 | 99.2 | 2,183,393 | 3,425,366 | 2,210,557 |
| `currat` | `currat` | `currat` | 1.000 | 1.000 | 98.1 | 98.1 | 2,175,897 | 2,385,855 | 2,202,126 |
| `quick` | `quick` | `quick` | 1.000 | 1.000 | 98.1 | 98.1 | 2,163,228 | 2,372,926 | 2,189,245 |
| `pchquick` | `pchquick` | `pchquick` | 1.000 | 1.000 | 98.1 | 98.1 | 2,024,323 | 2,167,859 | 2,049,056 |
| `ep` | `ep` | `ep` | 1.000 | 1.000 | 98.1 | 98.1 | 2,245,687 | 2,466,926 | 2,273,186 |
| `sgr` | `sgr` | `sgr` | 1.000 | 1.000 | 98.0 | 98.0 | 2,078,502 | 2,231,574 | 2,104,524 |
| `hire` | `hire` | `hire` | 1.000 | 1.000 | 98.0 | 98.1 | 2,106,009 | 2,263,814 | 2,131,933 |
| `bm` | `bm` | `bm` | 1.000 | 1.000 | 98.0 | 98.0 | 2,245,687 | 2,466,662 | 2,273,186 |
| `cfp` | `cfp` | `cfp` | 1.000 | 1.000 | 98.3 | 98.3 | 2,053,974 | 2,208,655 | 2,114,247 |
| `agr` | `agr` | `agr` | 1.000 | 1.000 | 98.0 | 98.1 | 2,110,218 | 2,263,774 | 2,136,596 |
| `grltnoa` | `grltnoa` | `grltnoa` | 1.000 | 1.000 | 98.1 | 98.1 | 1,609,145 | 1,738,676 | 1,627,913 |
| `pchdepr` | `pchdepr` | `pchdepr` | 1.000 | 1.000 | 98.0 | 98.0 | 2,017,871 | 2,161,352 | 2,038,780 |
| `pchsale_pchxsga` | `pchsale_pchxsga` | `pchsale_pchxsga` | 1.000 | 1.000 | 98.0 | 98.0 | 1,755,430 | 1,885,261 | 1,775,344 |
| `pchsale_pchrect` | `pchsale_pchrect` | `pchsale_pchrect` | 1.000 | 1.000 | 98.0 | 98.0 | 2,022,482 | 2,170,404 | 2,047,407 |
| `lgr` | `lgr` | `lgr` | 1.000 | 1.000 | 98.0 | 98.0 | 2,103,137 | 2,256,409 | 2,129,443 |
| `egr` | `egr` | `egr` | 1.000 | 1.000 | 98.0 | 98.0 | 2,110,065 | 2,263,340 | 2,136,441 |
| `chcsho` | `chcsho` | `chcsho` | 1.000 | 1.000 | 98.0 | 98.0 | 2,109,433 | 2,262,313 | 2,135,807 |
| `pchsale_pchinvt` | `pchsale_pchinvt` | `pchsale_pchinvt` | 1.000 | 1.000 | 98.0 | 98.0 | 1,654,964 | 1,786,841 | 1,670,375 |
| `chinv` | `chinv` | `chinv` | 1.000 | 1.000 | 98.0 | 98.1 | 2,058,483 | 2,206,844 | 2,084,280 |
| `roic` | `roic` | `roic` | 1.000 | 1.000 | 98.0 | 98.0 | 2,161,102 | 2,373,567 | 2,187,758 |
| `pchgm_pchsale` | `pchgm_pchsale` | `pchgm_pchsale` | 1.000 | 1.000 | 98.0 | 98.0 | 2,078,322 | 2,231,389 | 2,104,343 |
| `cashpr` | `cashpr` | `cashpr` | 1.000 | 1.000 | 98.0 | 98.0 | 2,223,859 | 2,444,654 | 2,251,135 |
| `gma` | `gma` | `gma` | 1.000 | 1.000 | 98.0 | 98.0 | 2,105,702 | 2,258,912 | 2,132,047 |
| `rsup` | `rsup` | `rsup` | 1.000 | 1.000 | 98.1 | 98.1 | 2,017,051 | 2,223,470 | 2,047,183 |
| `roeq` | `roeq` | `roeq` | 1.000 | 1.000 | 98.0 | 98.0 | 2,033,230 | 2,265,151 | 2,058,036 |
| `roaq` | `roaq` | `roaq` | 1.000 | 1.000 | 98.0 | 98.1 | 2,033,470 | 2,257,570 | 2,058,293 |
| `chtx` | `chtx` | `chtx` | 1.000 | 1.000 | 98.0 | 98.1 | 2,000,654 | 2,178,144 | 2,025,142 |
| `acc` | `acc` | `acc` | 1.000 | 1.000 | 98.0 | 98.0 | 1,971,865 | 2,114,025 | 1,996,902 |
| `pctacc` | `pctacc` | `pctacc` | 1.000 | 1.000 | 98.0 | 98.0 | 1,971,853 | 2,114,025 | 1,996,890 |
| `pchcurrat` | `pchcurrat` | `pchcurrat` | 1.000 | 1.000 | 98.0 | 98.0 | 1,762,552 | 1,896,190 | 2,063,098 |
| `mom1m` | `mom1m` | `mom1m` | 1.000 | 0.999 | 98.0 | 98.1 | 2,245,687 | 3,733,527 | 2,273,186 |
| `maxret` | `maxret` | `maxret` | 1.000 | 1.000 | 98.5 | 98.6 | 2,245,671 | 3,706,758 | 2,273,185 |
| `mvel1` | `mvel1` | `mve` | 1.000 | 1.000 | 98.9 | 99.0 | 2,245,687 | 3,733,450 | 2,273,186 |
| `aeavol` | `aeavol` | `aeavol` | 1.000 | 1.000 | 98.2 | 98.2 | 2,023,393 | 2,251,184 | 2,048,225 |
| `ear` | `ear` | `ear` | 1.000 | 1.000 | 97.9 | 97.9 | 2,035,028 | 2,278,404 | 2,059,921 |
| `dolvol` | `dolvol` | `dolvol` | 0.999 | 0.998 | 98.7 | 98.8 | 2,171,184 | 3,420,894 | 2,198,640 |
| `invest` | `invest` | `invest` | 0.999 | 0.999 | 98.0 | 98.0 | 2,043,832 | 2,191,784 | 2,066,602 |
| `turn` | `turn` | `turn` | 0.999 | 0.996 | 98.3 | 98.3 | 2,171,654 | 3,453,076 | 2,199,923 |
| `chatoia` | `chatoia` | `chatoia` | 0.999 | 0.998 | 62.9 | 78.8 | 1,959,963 | 2,069,111 | 1,984,830 |
| `beta` | `beta` | `beta` | 0.998 | 0.993 | 0.1 | 0.0 | 2,224,781 | 2,494,716 | 2,252,178 |
| `stdcf` | `stdcf` | `stdcf` | 0.998 | 0.998 | 97.3 | 97.3 | 1,460,601 | 1,511,302 | 1,476,287 |
| `stdacc` | `stdacc` | `stdacc` | 0.998 | 0.998 | 97.3 | 97.3 | 1,460,601 | 1,511,302 | 1,476,287 |
| `betasq` | `betasq` | `betasq` | 0.998 | 0.993 | 0.4 | 2.7 | 2,224,781 | 2,494,716 | 2,252,178 |
| `idiovol` | `idiovol` | `idiovol` | 0.998 | 0.998 | 7.3 | 55.9 | 2,224,781 | 2,494,716 | 2,252,178 |
| `bm_ia` | `bm_ia` | `bm_ia` | 0.998 | 0.996 | 57.9 | 71.2 | 2,245,687 | 2,466,662 | 2,273,186 |
| `mve_ia` | `me_ia` | `mve_ia` | 0.997 | 0.998 | 57.4 | 62.7 | 2,245,687 | 2,466,954 | 2,273,186 |
| `sic2` | `sic2` | `sic2` | 0.997 | 0.997 | 99.6 | 99.6 | 2,245,687 | 2,467,856 | 2,273,186 |
| `herf` | `herf` | `herf` | 0.997 | 0.997 | 0.0 | 97.1 | 2,245,677 | 2,467,856 | 2,273,176 |
| `mom6m` | `mom6m` | `mom6m` | 0.996 | 0.995 | 97.1 | 97.2 | 2,185,914 | 3,601,108 | 2,213,029 |
| `grcapx` | `grcapx` | `grcapx` | 0.996 | 0.995 | 98.6 | 98.6 | 1,800,023 | 1,900,595 | 1,933,062 |
| `tb` | `tb` | `tb` | 0.995 | 0.995 | 13.4 | 25.3 | 1,932,375 | 2,132,806 | 2,002,917 |
| `chempia` | `chempia` | `chempia` | 0.995 | 0.993 | 3.7 | 12.2 | 2,106,009 | 2,263,814 | 2,131,933 |
| `mom12m` | `mom12m` | `mom12m` | 0.995 | 0.994 | 96.8 | 96.8 | 2,098,354 | 3,445,790 | 2,124,826 |
| `cfp_ia` | `cfp_ia` | `cfp_ia` | 0.994 | 0.859 | 34.4 | 51.3 | 2,053,974 | 2,208,655 | 2,114,247 |
| `chmom` | `chmom` | `chmom` | 0.993 | 0.993 | 96.7 | 96.7 | 2,098,354 | 3,445,790 | 2,124,826 |
| `chpmia` | `chpmia` | `chpmia` | 0.993 | 0.989 | 61.7 | 70.7 | 2,073,256 | 2,226,152 | 2,099,148 |
| `mom36m` | `mom36m` | `mom36m` | 0.992 | 0.992 | 95.5 | 95.6 | 1,794,364 | 2,893,435 | 1,817,881 |
| `cinvest` | `cinvest` | `cinvest` | 0.990 | 0.989 | 98.1 | 98.1 | 1,956,352 | 2,112,866 | 2,014,967 |
| `ps` | `ps` | `ps` | 0.979 | 0.982 | 11.0 | 11.0 | 2,110,251 | 2,263,814 | 2,136,629 |
| `indmom` | `indmom` | `indmom` | 0.960 | 0.988 | 2.8 | 8.4 | 2,245,531 | 3,751,979 | 2,273,029 |
| `pricedelay` | `pricedelay` | `pricedelay` | 0.939 | 0.925 | 0.5 | 5.5 | 2,224,752 | 2,493,953 | 2,252,149 |
| `pchcapx_ia` | `pchcapx_ia` | `pchcapx_ia` | 0.729 | 0.717 | 17.1 | 20.0 | 1,934,184 | 2,076,098 | 2,076,188 |
| `ms` | `ms` | `ms` | 0.580 | 0.570 | 27.8 | 27.8 | 2,036,616 | 2,199,552 | 2,061,573 |
| `operprof` | `operprof` | `operprof` | 0.573 | 0.571 | 14.6 | 14.6 | 2,105,549 | 2,258,560 | 2,131,892 |

## Summary buckets (median monthly Spearman vs Green)

- ρ ≥ 0.99 (essentially identical ranks): **88**
- 0.95 ≤ ρ < 0.99: **3**
- 0.90 ≤ ρ < 0.95: **1**
- ρ < 0.90 (investigate): **3**

### Below 0.95 vs Green (review)

| datashare | median ρ | pooled ρ | exact% | likely cause |
|-----------|---------:|---------:|-------:|--------------|
| `operprof` | 0.573 | 0.571 | 14.6 | by design — Green output drops `xsga0` (typo); repo follows SAS code |
| `ms` | 0.580 | 0.570 | 27.8 | still low after fillna(0) fix — quarterly m7/m8 alignment / m-component disagreement on overlap |
| `pchcapx_ia` | 0.729 | 0.717 | 17.1 | Green industry mean corrupted by SAS non-BY `lag()` in capx fallback; repo within-firm correct |
| `pricedelay` | 0.939 | 0.925 | 0.5 | adj-R² / lag construction edge effects |

### High rank agreement but low exact-match (level/units differences only)

These have median ρ ≥ 0.95 yet exact% < 50%, i.e. ranks match but stored values differ by a monotone transform — not an economic mismatch, but worth noting for any level-based use.

| datashare | median ρ | exact% | rel% |
|-----------|---------:|-------:|-----:|
| `std_dolvol` | 1.000 | 0.0 | 0.0 |
| `beta` | 0.998 | 0.1 | 0.0 |
| `betasq` | 0.998 | 0.4 | 2.7 |
| `idiovol` | 0.998 | 7.3 | 55.9 |
| `herf` | 0.997 | 0.0 | 97.1 |
| `tb` | 0.995 | 13.4 | 25.3 |
| `chempia` | 0.995 | 3.7 | 12.2 |
| `cfp_ia` | 0.994 | 34.4 | 51.3 |
| `ps` | 0.979 | 11.0 | 11.0 |
| `indmom` | 0.960 | 2.8 | 8.4 |
