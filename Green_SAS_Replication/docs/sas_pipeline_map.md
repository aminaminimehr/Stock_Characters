# SAS Pipeline Map — Greens_code.sas

Source: `Supplementary_assistive_files/SAS_codes/Greens_code.sas`

Benchmark: `Supplementary_assistive_files/Output_From_Greens_SAS_code.sas7bdat`

Python module mapping:

| Stage | SAS lines | WRDS inputs | Intermediate | Python module |
|-------|-----------|-------------|--------------|---------------|
| Annual extract | 39–72 | `comp.company`, `comp.funda` | `data` | `annual_compustat.py` |
| Annual cleanup | 79–101 | — | `data` | `annual_compustat.py` |
| Annual characteristics | 122–240 | — | `data2` | `annual_compustat.py` |
| Industry adjustments | 242–256 | — | `data2` | `annual_compustat.py` |
| Mohanram m1–m6 | 258–285 | — | `data2` | `annual_compustat.py` |
| Credit ratings | 287–296 | `comp.adsprate` | `data2` | `annual_compustat.py` |
| CPI / orgcap | 299–398 | embedded CPI | `data` | `annual_compustat.py` |
| CCM link | 410–417 | `crsp.ccmxpf_linktable` | `temp` | `ccm_linking.py` |
| Exchange screen | 428–448 | `crsp.mseall` | `temp` | `ccm_linking.py` |
| Annual keep | 459–471 | — | `temp` | `annual_compustat.py` |
| Annual→monthly | 480–523 | `crsp.msf`, `crsp.mseall` | `temp2` | `annual_to_monthly_timing.py` |
| Quarterly extract | 532–549 | `comp.fundq` | `data` | `quarterly_compustat.py` |
| Quarterly chars | 558–642 | — | `data3`/`data6` | `quarterly_compustat.py` |
| IBES→SUE | 644–687 | `ibes.statsum_epsus` | `data4` | **Excluded** (`sue=che/mveq`) |
| Quarterly CCM | 688–700 | `ccmxpf_linktable` | `data5` | `quarterly_compustat.py` |
| Daily around rdq | 709–741 | `crsp.dsf` | `data6` | `quarterly_compustat.py` |
| Quarterly→monthly | 760–776 | — | `temp3` | `quarterly_compustat.py` |
| eamonth | 777–795 | — | `temp3` | `quarterly_compustat.py` |
| Mohanram ms | 796–801 | — | `temp3` | `quarterly_compustat.py` |
| IBES monthly | 810–924 | `ibes.*` | `temp4` | `ibes_stubs.py` (NaN) |
| CRSP monthly | 931–997 | — | `temp6` | `crsp_monthly.py` |
| Daily monthly agg | 1005–1033 | `crsp.dsf` | `temp6` | `crsp_daily.py` |
| Beta / idiovol / delay | 1034–1135 | `crsp.dsf` | `temp7` | `crsp_daily.py` |
| Final filters | 1137–1152 | — | `temp7` | `green_replication_pipeline.py` |
| Winsorization | 1160–1240 | — | `temp2` | `winsorization.py` |

## Key filters

### Annual Compustat (L68–72)

- `not missing(at, prcc_f, ni)`
- `datadate >= 01JAN1975`
- `indfmt='INDL'`, `datafmt='STD'`, `popsrc='D'`, `consol='C'`
- `nodupkey by gvkey datadate`

### CCM (L411–412)

- `LINKTYPE in (LU, LC, LD, LF, LN, LO, LS, LX)`
- `(2015 >= year(LINKDT) or LINKDT = .B)`
- `(1950 <= year(LINKENDDT) or LINKENDDT = .E)`

### Exchange / share (L443)

- `exchcd in (1,2,3)` and `shrcd in (10,11)`

### Green annual timing (L484)

```sas
intnx('MONTH', datadate, 7) <= b.date < intnx('MONTH', datadate, 20)
```

Sort: `permno date descending datadate` → `nodupkey permno date`.

### Quarterly timing (L768)

```sas
intnx('MONTH', a.date, -10) <= b.datadate <= intnx('MONTH', a.date, -5, 'beg')
```

### Final sample (L1149)

- `not missing(mve, mom1m, bm)`
- `year(date) >= 1980` (before final keep in SAS L1137)

## Winsorization variable lists

See `config.HITRIM_VARS`, `config.HILOTRIM_VARS`, `config.WINSOR_DUMMY_EXCLUDE`.

Dummies excluded from winsorization: `rd`, `eamonth`, `IPO`, `divi`, `divo`, `securedind`, `convind`, `ltg`, `credrat_dwn`, `woGW`, `sin`, `retcons_pos`, `retcons_neg`.

## IBES variables (excluded)

| Variable | SAS lines | Table | Python treatment |
|----------|-----------|-------|------------------|
| sue (IBES path) | 684–686 | `ibes.statsum_epsus` | Use `che/mveq` only |
| disp, chfeps, fgr5yr, meanest, nanalyst, sfe | 810–923 | `ibes.statsum_epsus` | NaN (+ SAS year rules) |
| meanrec, chrec | 858–879 | `ibes.recdsum` | NaN |
| ltg, chnanalyst | 914–960 | derived | Rule-based on stubs |
