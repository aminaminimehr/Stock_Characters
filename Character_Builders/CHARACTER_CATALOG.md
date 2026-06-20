# Character Catalog

Authoritative inventory of what the repository builds and **where it is actually implemented on
disk**. The canonical engine is `_shared/` driven by `build_all_implemented_characters.py`; the
`Green_*_Generalized/` folders are **optional single-character CLIs** for targeted rebuilds and do
**not** all exist for every character. See `docs/methodology/` for formulas, timing, linking,
filters, industry, availability, imputation, and validation status.

## Naming convention

| Family | Naming | Builder |
|---|---|---|
| Green (canonical) | short names (`bm`, `operprof`, `cfp`, `bm_ia`) | `_shared/` + `build_all_implemented_characters.py` |
| Dacheng-exact | `_dc` suffix (`bm_dc`, …) | `Dacheng_datashare/build_datashare_chars.py` |
| HXZ / FF June | descriptive (`book_to_market`, …) | `HXZ_*_Generalized/build_*.py` |

## Timing contract (final monthly panel)

- `signal_yyyymm`: month where the predictor is placed.
- `target_yyyymm`: next-month return month (`signal_yyyymm + 1`).
- `datadate`: the raw fiscal data date used to construct the signal.

**Green annual** characteristics expand via the Green rolling window
(`intnx('MONTH', datadate, 7) <= crsp.date < intnx('MONTH', datadate, 20)`, i.e. months **7–19**),
keeping the latest fiscal `datadate` per `permno × signal_yyyymm` (`Character_Panels/timing.py`,
`expand_annual_file_green`). **HXZ June** stems (`book_to_market`, `cash_flow_to_price`,
`operating_profitability`, `book_to_june_market_equity`) use `expand_annual_file_june` (June `y+1` ..
May `y+2`). **Quarterly** characteristics use the reporting/availability lag in
`_shared/quarterly_builders.py`. **Monthly / daily-rolled CRSP** characteristics are placed at their
explicit `signal_yyyymm` after the builder's lag.

---

## Green characters WITH a dedicated wrapper folder (optional CLIs, 59)

Each `Green_<ACRONYM>_Generalized/` delegates to `_shared/`. Output column in parentheses.

`Green_ABR_Generalized` (abr) · `Green_ACC_Generalized` (acc) · `Green_ADM_Generalized` (adm) ·
`Green_AGR_Generalized` (agr) · `Green_ALM_Generalized` (alm) · `Green_ATO_Generalized` (ato) ·
`Green_BASPREAD_Generalized` (baspread) · `Green_BETA_Generalized` (beta) ·
`Green_BM_IA_Generalized` (bm_ia) · `Green_CASH_Generalized` (cash) ·
`Green_CASHDEBT_Generalized` (cashdebt) · `Green_CHCSHO_Generalized` (chcsho) ·
`Green_CHTX_Generalized` (chtx) · `Green_CHPM_Generalized` (chpm) ·
`Green_CINVEST_Generalized` (cinvest) · `Green_DEPR_Generalized` (depr) ·
`Green_DOLVOL_Generalized` (dolvol) · `Green_DY_Generalized` (dy) · `Green_EP_Generalized` (ep) ·
`Green_GMA_Generalized` (gma) · `Green_GRLTNOA_Generalized` (grltnoa) ·
`Green_HERF_Generalized` (herf) · `Green_HIRE_Generalized` (hire) · `Green_ILL_Generalized` (ill) ·
`Green_LGR_Generalized` (lgr) · `Green_LEV_Generalized` (lev) · `Green_MAXRET_Generalized` (maxret) ·
`Green_ME_Generalized` (me) · `Green_ME_IA_Generalized` (me_ia) · `Green_MOM1M_Generalized` (mom1m) ·
`Green_MOM6M_Generalized` (mom6m) · `Green_MOM12M_Generalized` (mom12m) ·
`Green_MOM36M_Generalized` (mom36m) · `Green_MOM60M_Generalized` (mom60m) ·
`Green_MVEL1_Generalized` (mvel1) · `Green_NI_Generalized` (ni) · `Green_NINCR_Generalized` (nincr) ·
`Green_NOA_Generalized` (noa) · `Green_PCTACC_Generalized` (pctacc) · `Green_PM_Generalized` (pm) ·
`Green_PS_Generalized` (ps) · `Green_RD_SALE_Generalized` (rd_sale) · `Green_RDM_Generalized` (rdm) ·
`Green_RE_Generalized` (re) · `Green_RNA_Generalized` (rna) · `Green_ROA1_Generalized` (roaq) ·
`Green_ROE_Generalized` (roe) · `Green_RSUP_Generalized` (rsup) ·
`Green_RVAR_CAPM_Generalized` (rvar_capm) · `Green_RVAR_FF3_Generalized` (rvar_ff3) ·
`Green_RVAR_MEAN_Generalized` (rvar_mean, Green SAS `retvol`) · `Green_SEAS1A_Generalized` (seas1a) ·
`Green_SGR_Generalized` (sgr) · `Green_SP_Generalized` (sp) ·
`Green_STD_DOLVOL_Generalized` (std_dolvol) · `Green_STD_TURN_Generalized` (std_turn) ·
`Green_SUE_Generalized` (sue) · `Green_TURN_Generalized` (turn) ·
`Green_ZEROTRADE_Generalized` (zerotrade)

> Note: `Green_ABR_Generalized` and `Green_BETA_Generalized` build only `abr`/`beta`; `abr` is a
> legacy alias of `ear` (`_shared/event_builders.py`). `Green_ROA1_Generalized` outputs the quarterly
> `roaq` column.

---

## Green characters built via the shared engine ONLY (no dedicated folder)

These exist in the `_shared/` registries and are produced by `build_all_implemented_characters.py`,
but have **no** `Green_*_Generalized/` folder.

**Annual** (`_shared/green_builders.py` `ANNUAL_CHARACTER_INFO`):
`absacc, age, bm, cashpr, cfp, cfp_ia, chobklg, chinv, chpmia, chatoia, chempia, convind, currat,
divi, divo, egr, grcapx, invest, obklg, op, operprof, orgcap, pchcurrat, pchdepr, pchcapx,
pchcapx_ia, pchgm_pchsale, pchquick, pchsale_pchinvt, pchsale_pchrect, pchsale_pchxsga, pchsaleinv,
quick, rd, realestate, roic, salecash, saleinv, salerec, secured, securedind, sic2, sin, tb, tang`

**Monthly** (`MONTHLY_CHARACTER_INFO`): `chmom, indmom`

**Quarterly** (`_shared/quarterly_builders.py` `QUARTERLY_CHARACTER_INFO`):
`roeq, stdacc, stdcf, roavol`

**Special** (`build_all_implemented_characters.py`):
`betasq, idiovol, pricedelay, ear, aeavol, ms`

---

## Dacheng-exact `_dc` layer (`Dacheng_datashare/`) — **experimental / not used**

Empirical tests show this datashare.csv matches **HXZ + Green `cfp`**, not Dacheng `accounting_60.py`.
The `_dc` builder is retained for reference only. **Do not wire into the production panel.**

## Datashare mapping (production)

| datashare | repo column | builder |
|---|---|---|
| `bm` | `book_to_market` | `HXZ_BM_Generalized` |
| `operprof` | `operating_profitability` | `HXZ_OPE_Generalized` |
| `cfp` | `cfp` | Green `_shared/green_builders.py` |
| `bm_ia` | — | not replicated |

Use `--profile datashare` in `run_full_pipeline.py`. See `docs/CONFIGURATION.md`.

---

## HXZ / Fama-French June layer (`HXZ_*_Generalized/`)

| Folder | Column | Description |
|---|---|---|
| `HXZ_BM_Generalized` | `book_to_market` | Book-to-market, December ME, June timing |
| `HXZ_BMJ_Generalized` | `bmj` | Book-to-June-end market equity |
| `HXZ_CFP_Generalized` | `cash_flow_to_price` | Cash-flow-to-price, June timing |
| `HXZ_OPE_Generalized` | `operating_profitability` | Operating profitability, June timing |
