# Character Catalog

This catalog tracks the Green-style target set used by the repository.
Each implemented character should live in its own source-labeled folder with a
builder and a README. HXZ-specific builders use `HXZ_<ACRONYM>_Generalized`.
Green SAS-derived builders use `Green_<ACRONYM>_Generalized`.

## Timing Contract

The final monthly panel should use:

- `signal_yyyymm`: the month where the predictor is placed.
- `target_yyyymm`: the next-month return month.
- `source_date` or `datadate`: the raw data date used to construct the signal.

For prediction work, keep characteristics aligned on `signal_yyyymm`; create or
merge the dependent excess return using `target_yyyymm`.

Annual accounting characteristics use the June availability convention. A fiscal
year ending in calendar year `y` is placed from June `y+1` through May `y+2`.
If fiscal-year-end changes create overlapping annual observations for the same
`permno` and signal month, panel construction keeps the observation with the
latest Compustat `datadate`.
Quarterly characteristics should use the documented reporting/availability lag.
Monthly and daily-rolled CRSP characteristics should be placed at their explicit
monthly `signal_yyyymm` after the required lag is applied inside the builder.

## Status Table

| Acronym | Description | Timing family | Status |
| --- | --- | --- | --- |
| `abr` | Cumulative abnormal returns around earnings announcement dates | Quarterly/event | Implemented: `Green_ABR_Generalized` / `_shared/event_builders.py` |
| `acc` | Operating accruals | Annual/quarterly accounting | Implemented through shared Green builder: `Green_ACC_Generalized` |
| `absacc` | Absolute accruals | Annual accounting | Implemented through shared Green builder: `Green_ABSACC_Generalized` |
| `adm` | Advertising expense-to-market | Annual accounting | Implemented through shared Green builder: `Green_ADM_Generalized` |
| `age` | Years since first Compustat coverage | Annual accounting | Implemented through shared Green builder: `Green_AGE_Generalized` |
| `agr` | Asset growth | Annual/quarterly accounting | Implemented through shared Green builder: `Green_AGR_Generalized` |
| `alm` | Asset liquidity | Annual/quarterly accounting | Implemented through shared Green builder: `Green_ALM_Generalized` |
| `ato` | Asset turnover | Annual/quarterly accounting | Implemented through shared Green builder: `Green_ATO_Generalized` |
| `baspread` | Bid-ask spread, rolling 3 months | Monthly/daily CRSP | Implemented through shared Green builder: `Green_BASPREAD_Generalized` |
| `beta` | Beta, rolling 3 months | Monthly/daily CRSP | Implemented: `Green_BETA_Generalized` / `_shared/beta_builder.py` |
| `betasq` | Beta squared | Monthly/daily CRSP | Implemented: `Green_BETASQ_Generalized` / `_shared/beta_builder.py` |
| `bm` | Book-to-market equity | Annual accounting plus December CRSP ME | Implemented: `HXZ_BM_Generalized` |
| `bmj` | Book-to-June-end market equity | Annual accounting plus June CRSP price | Implemented: `HXZ_BMJ_Generalized` |
| `bm_ia` | Industry-adjusted book-to-market | Annual accounting plus industry adjustment | Implemented through shared Green builder: `Green_BM_IA_Generalized` |
| `cash` | Cash holdings | Annual/quarterly accounting | Implemented through shared Green builder: `Green_CASH_Generalized` |
| `cashpr` | Cash productivity | Annual accounting | Implemented through shared Green builder: `Green_CASHPR_Generalized` |
| `convind` | Convertible debt indicator | Annual accounting | Implemented through shared Green builder: `Green_CONVIND_Generalized` |
| `currat` | Current ratio | Annual accounting | Implemented through shared Green builder: `Green_CURRAT_Generalized` |
| `cashdebt` | Cash to debt | Annual/quarterly accounting | Implemented through shared Green builder: `Green_CASHDEBT_Generalized` |
| `cfp` | Cash-flow-to-price | Annual accounting plus December CRSP ME | Implemented: `HXZ_CFP_Generalized` |
| `cfp_ia` | Industry-adjusted cash-flow-to-price | Annual accounting | Implemented through shared Green builder: `Green_CFP_IA_Generalized` |
| `chcsho` | Change in shares outstanding | Annual/quarterly accounting | Implemented through shared Green builder: `Green_CHCSHO_Generalized` |
| `chinv` | Change in inventory | Annual accounting | Implemented through shared Green builder: `Green_CHINV_Generalized` |
| `chobklg` | Change in order backlog scaled by assets | Annual accounting | Implemented through shared Green builder: `Green_CHOBKLG_Generalized` |
| `chpm` | Industry-adjusted change in profit margin | Annual/quarterly accounting plus industry adjustment | Implemented through shared Green builder: `Green_CHPM_Generalized` |
| `chpmia` | Industry-adjusted change in profit margin (GKX) | Annual accounting | Implemented through shared Green builder: `Green_CHPMIA_Generalized` |
| `chatoia` | Industry-adjusted change in asset turnover | Annual accounting | Implemented through shared Green builder: `Green_CHATOIA_Generalized` |
| `chempia` | Industry-adjusted employee growth | Annual accounting | Implemented through shared Green builder: `Green_CHEMPIA_Generalized` |
| `chtx` | Change in tax expense | Quarterly accounting | Implemented: `Green_CHTX_Generalized` / `_shared/quarterly_builders.py` |
| `cinvest` | Corporate investment | Quarterly accounting | Implemented: `Green_CINVEST_Generalized` / `_shared/quarterly_builders.py` |
| `depr` | Depreciation / PP&E | Annual/quarterly accounting | Implemented through shared Green builder: `Green_DEPR_Generalized` |
| `dolvol` | Dollar trading volume | Monthly CRSP | Implemented through shared Green builder: `Green_DOLVOL_Generalized` |
| `dy` | Dividend yield | Annual accounting | Implemented through shared Green annual builder: `Green_DY_Generalized` |
| `divi` | Dividend initiation | Annual accounting | Implemented through shared Green builder: `Green_DIVI_Generalized` |
| `divo` | Dividend omission | Annual accounting | Implemented through shared Green builder: `Green_DIVO_Generalized` |
| `egr` | Growth in common shareholder equity | Annual accounting | Implemented through shared Green builder: `Green_EGR_Generalized` |
| `ep` | Earnings-to-price | Annual/quarterly accounting plus price | Implemented through shared Green builder: `Green_EP_Generalized` |
| `gma` | Gross profitability | Annual/quarterly accounting | Implemented through shared Green builder: `Green_GMA_Generalized` |
| `grcapx` | Growth in capital expenditures | Annual accounting | Implemented through shared Green builder: `Green_GRCAPX_Generalized` |
| `grltnoa` | Growth in long-term net operating assets | Annual/quarterly accounting | Implemented through shared Green builder: `Green_GRLTNOA_Generalized` |
| `herf` | Industry sales concentration | Annual accounting plus industry aggregation | Implemented through shared Green builder: `Green_HERF_Generalized` |
| `hire` | Employee growth rate | Annual accounting | Implemented through shared Green builder: `Green_HIRE_Generalized` |
| `invest` | Capital expenditures and inventory | Annual accounting | Implemented through shared Green builder: `Green_INVEST_Generalized` |
| `ill` | Illiquidity, rolling 3 months | Monthly/daily CRSP | Implemented through shared Green builder: `Green_ILL_Generalized` |
| `lev` | Leverage | Annual/quarterly accounting | Implemented through shared Green builder: `Green_LEV_Generalized` |
| `lgr` | Growth in long-term debt | Annual/quarterly accounting | Implemented through shared Green builder: `Green_LGR_Generalized` |
| `maxret` | Maximum daily return, rolling 3 months | Monthly/daily CRSP | Implemented through shared Green builder: `Green_MAXRET_Generalized` |
| `me` | Market equity | Monthly CRSP | Implemented through shared Green builder: `Green_ME_Generalized` |
| `me_ia` | Industry-adjusted size | Monthly CRSP plus industry adjustment | Implemented through shared Green builder: `Green_ME_IA_Generalized` |
| `mom12m` | Momentum, rolling 12 months | Monthly CRSP returns | Implemented through shared Green builder: `Green_MOM12M_Generalized` |
| `mom1m` | Momentum, 1 month | Monthly CRSP returns | Implemented through shared Green builder: `Green_MOM1M_Generalized` |
| `mom36m` | Momentum, rolling 36 months | Monthly CRSP returns | Implemented through shared Green builder: `Green_MOM36M_Generalized` |
| `mom60m` | Momentum, rolling 60 months | Monthly CRSP returns | Implemented through shared Green builder: `Green_MOM60M_Generalized` |
| `mom6m` | Momentum, rolling 6 months | Monthly CRSP returns | Implemented through shared Green builder: `Green_MOM6M_Generalized` |
| `ni` | Net stock issues | Quarterly accounting | Implemented: `Green_NI_Generalized` / `_shared/quarterly_builders.py` |
| `nincr` | Number of earnings increases | Quarterly accounting | Implemented: `Green_NINCR_Generalized` / `_shared/quarterly_builders.py` |
| `noa` | Net operating assets | Annual/quarterly accounting | Implemented through shared Green builder: `Green_NOA_Generalized` |
| `obklg` | Order backlog scaled by assets | Annual accounting | Implemented through shared Green builder: `Green_OBKLG_Generalized` |
| `op` | Operating profitability | Annual accounting | Implemented: `HXZ_OPE_Generalized` |
| `orgcap` | Organizational capital | Annual accounting | Implemented through shared Green builder: `Green_ORGCAP_Generalized` |
| `pchcurrat` | Change in current ratio | Annual accounting | Implemented through shared Green builder: `Green_PCHCURRAT_Generalized` |
| `pchcapx` | Change in capital expenditures | Annual accounting | Implemented through shared Green builder: `Green_PCHCAPX_Generalized` |
| `pchcapx_ia` | Industry-adjusted change in capital expenditures | Annual accounting | Implemented through shared Green builder: `Green_PCHCAPX_IA_Generalized` |
| `pchgm_pchsale` | Change in gross margin minus change in sales | Annual accounting | Implemented through shared Green builder: `Green_PCHGM_PCHSALE_Generalized` |
| `pchsale_pchinvt` | Change in sales minus change in inventory | Annual accounting | Implemented through shared Green builder: `Green_PCHSALE_PCHINVT_Generalized` |
| `pchsale_pchrect` | Change in sales minus change in receivables | Annual accounting | Implemented through shared Green builder: `Green_PCHSALE_PCHRECT_Generalized` |
| `pchsale_pchxsga` | Change in sales minus change in SG&A | Annual accounting | Implemented through shared Green builder: `Green_PCHSALE_PCHXSGA_Generalized` |
| `pchdepr` | Change in depreciation rate | Annual accounting | Implemented through shared Green builder: `Green_PCHDEPR_Generalized` |
| `pchquick` | Change in quick ratio | Annual accounting | Implemented through shared Green builder: `Green_PCHQUICK_Generalized` |
| `pchsaleinv` | Change in sales-to-inventory | Annual accounting | Implemented through shared Green builder: `Green_PCHSALEINV_Generalized` |
| `pctacc` | Percent operating accruals | Annual/quarterly accounting | Implemented through shared Green builder: `Green_PCTACC_Generalized` |
| `pm` | Profit margin | Annual/quarterly accounting | Implemented through shared Green builder: `Green_PM_Generalized` |
| `quick` | Quick ratio | Annual accounting | Implemented through shared Green builder: `Green_QUICK_Generalized` |
| `ps` | Performance score | Quarterly accounting | Implemented through shared Green builder: `Green_PS_Generalized` |
| `rd_sale` | R&D to sales | Annual/quarterly accounting | Implemented through shared Green builder: `Green_RD_SALE_Generalized` |
| `rd` | R&D increase indicator | Annual accounting | Implemented through shared Green builder: `Green_RD_Generalized` |
| `rdm` | R&D expense-to-market | Annual/quarterly accounting plus market equity | Implemented through shared Green builder: `Green_RDM_Generalized` |
| `realestate` | Real-estate holdings | Annual accounting | Implemented through shared Green builder: `Green_REALESTATE_Generalized` |
| `re` | Revisions in analyst earnings forecasts | Monthly IBES/analyst | Implemented: `Green_RE_Generalized` / `_shared/ibes_builders.py` |
| `rna` | Return on net operating assets | Quarterly accounting | Implemented: `Green_RNA_Generalized` / `_shared/quarterly_builders.py` |
| `roa1` | Return on assets | Quarterly accounting | Implemented: `Green_ROA1_Generalized` / `_shared/quarterly_builders.py` |
| `roe` | Return on equity | Annual/quarterly accounting | Implemented through shared Green builder: `Green_ROE_Generalized` |
| `roic` | Return on invested capital | Annual accounting | Implemented through shared Green builder: `Green_ROIC_Generalized` |
| `rsup` | Revenue surprise | Quarterly accounting | Implemented: `Green_RSUP_Generalized` / `_shared/quarterly_builders.py` |
| `rvar_capm` | Residual variance, CAPM rolling 3 months | Monthly/daily CRSP plus factor data | Implemented: `Green_RVAR_CAPM_Generalized` / `_shared/rvar_factor_builders.py` |
| `rvar_ff3` | Residual variance, FF3 rolling 3 months | Monthly/daily CRSP plus factor data | Implemented: `Green_RVAR_FF3_Generalized` / `_shared/rvar_factor_builders.py` |
| `rvar_mean` | Daily return volatility from previous month; Green SAS column `retvol` | Monthly/daily CRSP | Implemented through shared Green builder: `Green_RVAR_MEAN_Generalized` |
| `seas1a` | Seasonality | Monthly CRSP returns | Implemented through shared Green monthly builder: `Green_SEAS1A_Generalized` |
| `sgr` | Sales growth | Annual/quarterly accounting | Implemented through shared Green builder: `Green_SGR_Generalized` |
| `salecash` | Sales-to-cash | Annual accounting | Implemented through shared Green builder: `Green_SALECASH_Generalized` |
| `saleinv` | Sales-to-inventory | Annual accounting | Implemented through shared Green builder: `Green_SALEINV_Generalized` |
| `salerec` | Sales-to-receivables | Annual accounting | Implemented through shared Green builder: `Green_SALEREC_Generalized` |
| `secured` | Secured debt | Annual accounting | Implemented through shared Green builder: `Green_SECURED_Generalized` |
| `securedind` | Secured debt indicator | Annual accounting | Implemented through shared Green builder: `Green_SECUREDIND_Generalized` |
| `sin` | Sin stocks indicator | Annual accounting | Implemented through shared Green builder: `Green_SIN_Generalized` |
| `sp` | Sales-to-price | Annual/quarterly accounting plus price | Implemented through shared Green builder: `Green_SP_Generalized` |
| `tb` | Industry-adjusted tax income to book income | Annual accounting | Implemented through shared Green builder: `Green_TB_Generalized` |
| `tang` | Tangibility | Annual accounting | Implemented through shared Green builder: `Green_TANG_Generalized` |
| `std_dolvol` | Standard deviation of dollar trading volume, rolling 3 months | Monthly/daily CRSP | Implemented through shared Green builder: `Green_STD_DOLVOL_Generalized` |
| `std_turn` | Standard deviation of share turnover, rolling 3 months | Monthly/daily CRSP | Implemented through shared Green builder: `Green_STD_TURN_Generalized` |
| `sue` | Unexpected quarterly earnings | Quarterly accounting | Implemented: `Green_SUE_Generalized` / `_shared/quarterly_builders.py` |
| `turn` | Share turnover | Monthly CRSP | Implemented through shared Green builder: `Green_TURN_Generalized` |
| `zerotrade` | Number of zero-trading days, rolling 3 months | Monthly/daily CRSP | Implemented through shared Green builder: `Green_ZEROTRADE_Generalized` |
