# GKX final reconciliation audit

Compared `Supplementary_assistive_files/datashare.csv` (94 predictors) against repository panels:
- `outputs\panels\all_character_signal_panel.csv`
- `outputs\panels\complete_all_character_prediction_panel.csv`

Characteristic columns exclude merge metadata (`permno`, `signal_yyyymm`, etc.) and CRSP return fields (`ret`, `rf`, `dlret`, …).

## Summary counts

| Metric | Count |
| --- | ---: |
| Total GKX/datashare predictors | 94 |
| Exact name matches (in both panels) | 76 |
| Implemented under different name (alias) | 7 |
| Partially matched (alias + parallel variant) | 2 |
| **GKX predictors covered** | **85** |
| **GKX predictors still missing** | **9** |
| Repository-only extras (signal panel) | 18 |
| Signal panel characteristic columns | 106 |
| Complete panel characteristic columns | 106 |
| Complete panel merged columns incl. return fields | 112 |
| Unique economic concepts in signal panel | 106 |

## Verdict

**Answer: B.** The complete prediction panel has **112 merged columns**, but only **106** are characteristics. **9 of 94 GKX predictors remain missing**. The panel also carries **18 repository-only extras** and **duplicate implementations** for three GKX concepts (`bm`, `cfp`, `operprof`). We do **not** yet have all GKX predictors implemented.

## GKX predictor reconciliation

| GKX/datashare name | Repository name(s) | Status | Builder location | Notes |
| --- | --- | --- | --- | --- |
| `absacc` | `absacc` | exact match | Character_Builders/_shared/green_builders.py (annual) | — |
| `acc` | `acc` | exact match | Character_Builders/_shared/green_builders.py (annual) | — |
| `aeavol` | `—` | missing | — | — |
| `age` | `age` | exact match | Character_Builders/_shared/green_builders.py (annual) | — |
| `agr` | `agr` | exact match | Character_Builders/_shared/green_builders.py (annual) | — |
| `baspread` | `baspread` | exact match | Character_Builders/_shared/green_builders.py (daily/monthly) | — |
| `beta` | `beta` | exact match | Character_Builders/_shared/beta_builder.py | — |
| `betasq` | `betasq` | exact match | Character_Builders/_shared/beta_builder.py | — |
| `bm` | `bm, book_to_market` | partially matched | Character_Builders/_shared/green_builders.py (annual); Character_Builders/HXZ_BM_Generalized | GKX/Green column plus HXZ parallel variant in panel |
| `bm_ia` | `bm_ia` | exact match | Character_Builders/_shared/green_builders.py (annual) | — |
| `cash` | `cash` | exact match | Character_Builders/_shared/green_builders.py (annual) | — |
| `cashdebt` | `cashdebt` | exact match | Character_Builders/_shared/green_builders.py (annual) | — |
| `cashpr` | `cashpr` | exact match | Character_Builders/_shared/green_builders.py (annual) | — |
| `cfp` | `cfp, cash_flow_to_price` | partially matched | Character_Builders/_shared/green_builders.py (annual); Character_Builders/HXZ_CFP_Generalized | GKX/Green column plus HXZ parallel variant in panel |
| `cfp_ia` | `cfp_ia` | exact match | Character_Builders/_shared/green_builders.py (annual) | — |
| `chatoia` | `chatoia` | exact match | Character_Builders/_shared/green_builders.py (annual) | — |
| `chcsho` | `chcsho` | exact match | Character_Builders/_shared/green_builders.py (annual) | — |
| `chempia` | `chempia` | exact match | Character_Builders/_shared/green_builders.py (annual) | — |
| `chinv` | `chinv` | exact match | Character_Builders/_shared/green_builders.py (annual) | — |
| `chmom` | `—` | missing | — | — |
| `chpmia` | `chpmia` | exact match | Character_Builders/_shared/green_builders.py (annual) | — |
| `chtx` | `chtx` | exact match | Character_Builders/_shared/quarterly_builders.py | — |
| `cinvest` | `cinvest` | exact match | Character_Builders/_shared/quarterly_builders.py | — |
| `convind` | `convind` | exact match | Character_Builders/_shared/green_builders.py (annual) | — |
| `currat` | `currat` | exact match | Character_Builders/_shared/green_builders.py (annual) | — |
| `depr` | `depr` | exact match | Character_Builders/_shared/green_builders.py (annual) | — |
| `divi` | `divi` | exact match | Character_Builders/_shared/green_builders.py (annual) | — |
| `divo` | `divo` | exact match | Character_Builders/_shared/green_builders.py (annual) | — |
| `dolvol` | `dolvol` | exact match | Character_Builders/_shared/green_builders.py (monthly) | — |
| `dy` | `dy` | exact match | Character_Builders/_shared/green_builders.py (annual) | — |
| `ear` | `abr` | implemented under different name | Character_Builders/_shared/event_builders.py | GKX column name not in panel |
| `egr` | `egr` | exact match | Character_Builders/_shared/green_builders.py (annual) | — |
| `ep` | `ep` | exact match | Character_Builders/_shared/green_builders.py (annual) | — |
| `gma` | `gma` | exact match | Character_Builders/_shared/green_builders.py (annual) | — |
| `grcapx` | `grcapx` | exact match | Character_Builders/_shared/green_builders.py (annual) | — |
| `grltnoa` | `grltnoa` | exact match | Character_Builders/_shared/green_builders.py (annual) | — |
| `herf` | `herf` | exact match | Character_Builders/_shared/green_builders.py (annual) | — |
| `hire` | `hire` | exact match | Character_Builders/_shared/green_builders.py (annual) | — |
| `idiovol` | `—` | missing | — | — |
| `ill` | `ill` | exact match | Character_Builders/_shared/green_builders.py (daily/monthly) | — |
| `indmom` | `—` | missing | — | — |
| `invest` | `invest` | exact match | Character_Builders/_shared/green_builders.py (annual) | — |
| `lev` | `lev` | exact match | Character_Builders/_shared/green_builders.py (annual) | — |
| `lgr` | `lgr` | exact match | Character_Builders/_shared/green_builders.py (annual) | — |
| `maxret` | `maxret` | exact match | Character_Builders/_shared/green_builders.py (daily/monthly) | — |
| `mom12m` | `mom12m` | exact match | Character_Builders/_shared/green_builders.py (monthly) | — |
| `mom1m` | `mom1m` | exact match | Character_Builders/_shared/green_builders.py (monthly) | — |
| `mom36m` | `mom36m` | exact match | Character_Builders/_shared/green_builders.py (monthly) | — |
| `mom6m` | `mom6m` | exact match | Character_Builders/_shared/green_builders.py (monthly) | — |
| `ms` | `—` | missing | — | — |
| `mve_ia` | `me_ia` | implemented under different name | Character_Builders/_shared/green_builders.py (annual) | GKX column name not in panel |
| `mvel1` | `mvel1` | exact match | Character_Builders/_shared/green_builders.py (monthly) | — |
| `nincr` | `nincr` | exact match | Character_Builders/_shared/quarterly_builders.py | — |
| `operprof` | `op, operating_profitability` | implemented under different name | Character_Builders/_shared/green_builders.py (annual); Character_Builders/HXZ_OPE_Generalized | GKX column name not in panel |
| `orgcap` | `orgcap` | exact match | Character_Builders/_shared/green_builders.py (annual) | — |
| `pchcapx_ia` | `pchcapx_ia` | exact match | Character_Builders/_shared/green_builders.py (annual) | — |
| `pchcurrat` | `pchcurrat` | exact match | Character_Builders/_shared/green_builders.py (annual) | — |
| `pchdepr` | `pchdepr` | exact match | Character_Builders/_shared/green_builders.py (annual) | — |
| `pchgm_pchsale` | `pchgm_pchsale` | exact match | Character_Builders/_shared/green_builders.py (annual) | — |
| `pchquick` | `pchquick` | exact match | Character_Builders/_shared/green_builders.py (annual) | — |
| `pchsale_pchinvt` | `pchsale_pchinvt` | exact match | Character_Builders/_shared/green_builders.py (annual) | — |
| `pchsale_pchrect` | `pchsale_pchrect` | exact match | Character_Builders/_shared/green_builders.py (annual) | — |
| `pchsale_pchxsga` | `pchsale_pchxsga` | exact match | Character_Builders/_shared/green_builders.py (annual) | — |
| `pchsaleinv` | `pchsaleinv` | exact match | Character_Builders/_shared/green_builders.py (annual) | — |
| `pctacc` | `pctacc` | exact match | Character_Builders/_shared/green_builders.py (annual) | — |
| `pricedelay` | `—` | missing | — | — |
| `ps` | `ps` | exact match | Character_Builders/_shared/green_builders.py (annual) | — |
| `quick` | `quick` | exact match | Character_Builders/_shared/green_builders.py (annual) | — |
| `rd` | `rd` | exact match | Character_Builders/_shared/green_builders.py (annual) | — |
| `rd_mve` | `rdm` | implemented under different name | Character_Builders/_shared/green_builders.py (annual) | GKX column name not in panel |
| `rd_sale` | `rd_sale` | exact match | Character_Builders/_shared/green_builders.py (annual) | — |
| `realestate` | `realestate` | exact match | Character_Builders/_shared/green_builders.py (annual) | — |
| `retvol` | `rvar_mean` | implemented under different name | Character_Builders/_shared/green_builders.py (daily/monthly) | GKX column name not in panel |
| `roaq` | `roa1` | implemented under different name | Character_Builders/_shared/quarterly_builders.py | GKX column name not in panel |
| `roavol` | `—` | missing | — | — |
| `roeq` | `roe` | implemented under different name | Character_Builders/_shared/green_builders.py (annual) | GKX column name not in panel |
| `roic` | `roic` | exact match | Character_Builders/_shared/green_builders.py (annual) | — |
| `rsup` | `rsup` | exact match | Character_Builders/_shared/quarterly_builders.py | — |
| `salecash` | `salecash` | exact match | Character_Builders/_shared/green_builders.py (annual) | — |
| `saleinv` | `saleinv` | exact match | Character_Builders/_shared/green_builders.py (annual) | — |
| `salerec` | `salerec` | exact match | Character_Builders/_shared/green_builders.py (annual) | — |
| `secured` | `secured` | exact match | Character_Builders/_shared/green_builders.py (annual) | — |
| `securedind` | `securedind` | exact match | Character_Builders/_shared/green_builders.py (annual) | — |
| `sgr` | `sgr` | exact match | Character_Builders/_shared/green_builders.py (annual) | — |
| `sin` | `sin` | exact match | Character_Builders/_shared/green_builders.py (annual) | — |
| `sp` | `sp` | exact match | Character_Builders/_shared/green_builders.py (annual) | — |
| `std_dolvol` | `std_dolvol` | exact match | Character_Builders/_shared/green_builders.py (daily/monthly) | — |
| `std_turn` | `std_turn` | exact match | Character_Builders/_shared/green_builders.py (daily/monthly) | — |
| `stdacc` | `—` | missing | — | — |
| `stdcf` | `—` | missing | — | — |
| `tang` | `tang` | exact match | Character_Builders/_shared/green_builders.py (annual) | — |
| `tb` | `tb` | exact match | Character_Builders/_shared/green_builders.py (annual) | — |
| `turn` | `turn` | exact match | Character_Builders/_shared/green_builders.py (monthly) | — |
| `zerotrade` | `zerotrade` | exact match | Character_Builders/_shared/green_builders.py (daily/monthly) | — |

## Repository-only extras (not in GKX datashare)

| Repository name | Builder location | Notes |
| --- | --- | --- |
| `adm` | Character_Builders/_shared/green_builders.py (annual) | Advertising/MKT; Green/chars60 |
| `alm` | Character_Builders/_shared/green_builders.py (annual) | Asset liquidity; Green/chars60 |
| `ato` | Character_Builders/_shared/green_builders.py (annual) | Asset turnover; Green/chars60 |
| `bmj` | Character_Builders/HXZ_BMJ_Generalized | HXZ June ME variant; not in GKX 94 |
| `chobklg` | Character_Builders/_shared/green_builders.py (annual) | Green/chars60 backlog |
| `chpm` | Character_Builders/_shared/green_builders.py (annual) | Industry-adj PM; GKX uses chpmia |
| `me` | Character_Builders/_shared/green_builders.py (monthly) | Raw ME; GKX uses mvel1 (log lag ME) |
| `mom60m` | Character_Builders/_shared/green_builders.py (monthly) | 60-month momentum extension |
| `ni` | Character_Builders/_shared/quarterly_builders.py | Net stock issues; quarterly Green |
| `noa` | Character_Builders/_shared/green_builders.py (annual) | Net operating assets; Green/chars60 |
| `obklg` | Character_Builders/_shared/green_builders.py (annual) | Green/chars60 backlog |
| `pchcapx` | Character_Builders/_shared/green_builders.py (annual) | Green pct change capx; GKX uses pchcapx_ia |
| `pm` | Character_Builders/_shared/green_builders.py (annual) | Profit margin; Green/chars60 |
| `rna` | Character_Builders/_shared/quarterly_builders.py | Quarterly RNA; Green/chars60 |
| `rvar_capm` | Character_Builders/_shared/rvar_factor_builders.py | CAPM residual var; GKX uses retvol |
| `rvar_ff3` | Character_Builders/_shared/rvar_factor_builders.py | FF3 residual var; not in GKX |
| `seas1a` | Character_Builders/_shared/green_builders.py (monthly) | Seasonality; Green/chars60 |
| `sue` | Character_Builders/_shared/quarterly_builders.py | SUE; quarterly Green, not in datashare |

## Missing predictors — suggested next batch (by difficulty)

### Batch A — trivial / one-liner transforms

Square existing `beta` panel column.

`betasq`

### Batch B — annual Compustat (Green/Dacheng)

Follow Green SAS / `accounting_100.py`; fiscal ratios and event indicators.

`rd`, `divi`, `divo`, `roic`, `tb`, `convind`, `secured`, `securedind`, `pchgm_pchsale`, `pchsale_pchinvt`, `pchsale_pchrect`, `pchsale_pchxsga`

### Batch C — industry-adjusted annual

Extend existing base variables with sic2 demeaning (pattern used for `bm_ia`, `me_ia`).

`cfp_ia`, `chatoia`, `chempia`, `chpmia`, `pchcapx_ia`

### Batch D — CRSP momentum / daily

Rolling momentum changes and industry aggregates on monthly CRSP.

`chmom`, `indmom`, `pricedelay`

### Batch E — volatility / event volume

Multi-month or multi-year windows; daily CRSP and possibly event dates.

`idiovol`, `aeavol`, `roavol`, `stdacc`, `stdcf`

### Batch F — ambiguous / verify first

GKX lists both `ms` and `ps`; confirm whether `ms` duplicates `ps` or needs a separate score.

`ms`
