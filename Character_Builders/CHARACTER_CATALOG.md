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
| `abr` | Cumulative abnormal returns around earnings announcement dates | Quarterly/event | Scaffolded; needs specialized builder |
| `acc` | Operating accruals | Annual/quarterly accounting | Implemented through shared Green builder: `Green_ACC_Generalized` |
| `adm` | Advertising expense-to-market | Annual accounting | Implemented through shared Green builder: `Green_ADM_Generalized` |
| `agr` | Asset growth | Annual/quarterly accounting | Implemented through shared Green builder: `Green_AGR_Generalized` |
| `alm` | Asset liquidity | Annual/quarterly accounting | Implemented through shared Green builder: `Green_ALM_Generalized` |
| `ato` | Asset turnover | Annual/quarterly accounting | Implemented through shared Green builder: `Green_ATO_Generalized` |
| `baspread` | Bid-ask spread, rolling 3 months | Monthly/daily CRSP | Implemented through shared Green builder: `Green_BASPREAD_Generalized` |
| `beta` | Beta, rolling 3 months | Monthly/daily CRSP | Scaffolded; needs specialized builder |
| `bm` | Book-to-market equity | Annual accounting plus December CRSP ME | Implemented: `HXZ_BM_Generalized` |
| `bmj` | Book-to-June-end market equity | Annual accounting plus June CRSP price | Implemented: `HXZ_BMJ_Generalized` |
| `bm_ia` | Industry-adjusted book-to-market | Annual accounting plus industry adjustment | Implemented through shared Green builder: `Green_BM_IA_Generalized` |
| `cash` | Cash holdings | Annual/quarterly accounting | Implemented through shared Green builder: `Green_CASH_Generalized` |
| `cashdebt` | Cash to debt | Annual/quarterly accounting | Implemented through shared Green builder: `Green_CASHDEBT_Generalized` |
| `cfp` | Cash-flow-to-price | Annual accounting plus December CRSP ME | Implemented: `HXZ_CFP_Generalized` |
| `chcsho` | Change in shares outstanding | Annual/quarterly accounting | Implemented through shared Green builder: `Green_CHCSHO_Generalized` |
| `chpm` | Industry-adjusted change in profit margin | Annual/quarterly accounting plus industry adjustment | Implemented through shared Green builder: `Green_CHPM_Generalized` |
| `chtx` | Change in tax expense | Annual/quarterly accounting | Scaffolded; needs specialized builder |
| `cinvest` | Corporate investment | Quarterly accounting | Scaffolded; needs specialized builder |
| `depr` | Depreciation / PP&E | Annual/quarterly accounting | Implemented through shared Green builder: `Green_DEPR_Generalized` |
| `dolvol` | Dollar trading volume | Monthly CRSP | Implemented through shared Green builder: `Green_DOLVOL_Generalized` |
| `dy` | Dividend yield | Monthly CRSP | Scaffolded; needs specialized builder |
| `ep` | Earnings-to-price | Annual/quarterly accounting plus price | Implemented through shared Green builder: `Green_EP_Generalized` |
| `gma` | Gross profitability | Annual/quarterly accounting | Implemented through shared Green builder: `Green_GMA_Generalized` |
| `grltnoa` | Growth in long-term net operating assets | Annual/quarterly accounting | Implemented through shared Green builder: `Green_GRLTNOA_Generalized` |
| `herf` | Industry sales concentration | Annual accounting plus industry aggregation | Implemented through shared Green builder: `Green_HERF_Generalized` |
| `hire` | Employee growth rate | Annual accounting | Implemented through shared Green builder: `Green_HIRE_Generalized` |
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
| `ni` | Net stock issues | Annual/quarterly accounting | Scaffolded; needs specialized builder |
| `nincr` | Number of earnings increases | Quarterly accounting | Scaffolded; needs specialized builder |
| `noa` | Net operating assets | Annual/quarterly accounting | Implemented through shared Green builder: `Green_NOA_Generalized` |
| `op` | Operating profitability | Annual accounting | Implemented: `HXZ_OPE_Generalized` |
| `pctacc` | Percent operating accruals | Annual/quarterly accounting | Implemented through shared Green builder: `Green_PCTACC_Generalized` |
| `pm` | Profit margin | Annual/quarterly accounting | Implemented through shared Green builder: `Green_PM_Generalized` |
| `ps` | Performance score | Quarterly accounting | Implemented through shared Green builder: `Green_PS_Generalized` |
| `rd_sale` | R&D to sales | Annual/quarterly accounting | Implemented through shared Green builder: `Green_RD_SALE_Generalized` |
| `rdm` | R&D expense-to-market | Annual/quarterly accounting plus market equity | Implemented through shared Green builder: `Green_RDM_Generalized` |
| `re` | Revisions in analyst earnings forecasts | Monthly IBES/analyst | Scaffolded; needs specialized builder |
| `rna` | Return on net operating assets | Annual/quarterly accounting | Scaffolded; needs specialized builder |
| `Roa1` | Return on assets | Annual/quarterly accounting | Scaffolded; needs specialized builder |
| `roe` | Return on equity | Annual/quarterly accounting | Implemented through shared Green builder: `Green_ROE_Generalized` |
| `rsup` | Revenue surprise | Annual/quarterly accounting | Scaffolded; needs specialized builder |
| `rvar_capm` | Residual variance, CAPM rolling 3 months | Monthly/daily CRSP plus factor data | Scaffolded; needs specialized builder |
| `rvar_ff3` | Residual variance, FF3 rolling 3 months | Monthly/daily CRSP plus factor data | Scaffolded; needs specialized builder |
| `rvar_mean` | Daily return volatility from previous month; Green SAS column `retvol` | Monthly/daily CRSP | Implemented through shared Green builder: `Green_RVAR_MEAN_Generalized` |
| `seas1a` | Seasonality | Monthly CRSP returns | Scaffolded; needs specialized builder |
| `sgr` | Sales growth | Annual/quarterly accounting | Implemented through shared Green builder: `Green_SGR_Generalized` |
| `sp` | Sales-to-price | Annual/quarterly accounting plus price | Implemented through shared Green builder: `Green_SP_Generalized` |
| `std_dolvol` | Standard deviation of dollar trading volume, rolling 3 months | Monthly/daily CRSP | Implemented through shared Green builder: `Green_STD_DOLVOL_Generalized` |
| `std_turn` | Standard deviation of share turnover, rolling 3 months | Monthly/daily CRSP | Implemented through shared Green builder: `Green_STD_TURN_Generalized` |
| `sue` | Unexpected quarterly earnings | Quarterly accounting | Scaffolded; needs specialized builder |
| `turn` | Share turnover | Monthly CRSP | Implemented through shared Green builder: `Green_TURN_Generalized` |
| `zerotrade` | Number of zero-trading days, rolling 3 months | Monthly/daily CRSP | Implemented through shared Green builder: `Green_ZEROTRADE_Generalized` |
