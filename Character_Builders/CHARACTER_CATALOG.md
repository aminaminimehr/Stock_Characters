# Character Catalog

Authoritative inventory of what the repository builds and **where it is actually implemented on
disk**. The canonical engine is `_shared/` driven by `build_all_implemented_characters.py`; the
remaining `Green_*_Generalized/` folders are **optional single-character CLIs** for targeted
rebuilds and are **not** called by the main orchestrator. See `docs/methodology/` for formulas,
timing, linking, filters, industry, availability, imputation, and validation status.

## Datashare output (95 predictors)

The production target is the **95 GKX datashare signal predictors** (94 characteristics + `sic2`).
The allowlist lives in `pipeline_config.py` (`DATASHARE_PREDICTORS`, `datashare_output_columns()`).

When `--profile datashare` is active:

- `build_all_implemented_characters.py` **computes** the full Green baseline internally but **writes**
  only the 95 mapped output CSVs.
- `build_all_character_panel.py` merges only those 95 stems (ignores stale non-datashare CSVs).
- `run_full_pipeline.py` builds HXZ `book_to_market`, `operating_profitability`, and `bm_ia` only.

Green/research profiles write the full registry (Green baseline remains reproducible).

## Naming convention

| Family | Naming | Builder |
|---|---|---|
| Green (canonical) | short names (`bm`, `operprof`, `cfp`) | `_shared/` + `build_all_implemented_characters.py` |
| HXZ / FF June | descriptive (`book_to_market`, …) | `HXZ_*_Generalized/build_*.py` |
| Datashare IA | `bm_ia` | `Datashare_BM_IA_Generalized` (SIC2 × month demean) |

## Timing contract (final monthly panel)

- `signal_yyyymm`: month where the predictor is placed.
- `target_yyyymm`: next-month return month (`signal_yyyymm + 1`).
- `datadate`: the raw fiscal data date used to construct the signal.

**Green annual** characteristics expand via the Green rolling window
(`intnx('MONTH', datadate, 7) <= crsp.date < intnx('MONTH', datadate, 20)`, i.e. months **7–19**),
keeping the latest fiscal `datadate` per `permno × signal_yyyymm` (`Character_Panels/timing.py`,
`expand_annual_file_green`). **HXZ June** stems (`book_to_market`, `operating_profitability`) use
`expand_annual_file_june` (June `y+1` .. May `y+2`). **Quarterly** characteristics use the
reporting/availability lag in `_shared/quarterly_builders.py`. **Monthly / daily-rolled CRSP**
characteristics are placed at their explicit `signal_yyyymm` after the builder's lag.

---

## Green characters WITH a dedicated wrapper folder (optional CLIs)

Each remaining `Green_<ACRONYM>_Generalized/` delegates to `_shared/`. Output column in parentheses.

`Green_ABR_Generalized` (abr) · `Green_ACC_Generalized` (acc) · `Green_AGR_Generalized` (agr) ·
`Green_BASPREAD_Generalized` (baspread) · `Green_BETA_Generalized` (beta) ·
`Green_CASH_Generalized` (cash) · `Green_CASHDEBT_Generalized` (cashdebt) ·
`Green_CHCSHO_Generalized` (chcsho) · `Green_CHTX_Generalized` (chtx) ·
`Green_CINVEST_Generalized` (cinvest) · `Green_DEPR_Generalized` (depr) ·
`Green_DOLVOL_Generalized` (dolvol) · `Green_DY_Generalized` (dy) · `Green_EP_Generalized` (ep) ·
`Green_GMA_Generalized` (gma) · `Green_GRLTNOA_Generalized` (grltnoa) ·
`Green_HERF_Generalized` (herf) · `Green_HIRE_Generalized` (hire) · `Green_ILL_Generalized` (ill) ·
`Green_LGR_Generalized` (lgr) · `Green_LEV_Generalized` (lev) · `Green_MAXRET_Generalized` (maxret) ·
`Green_ME_IA_Generalized` (me_ia) · `Green_MOM1M_Generalized` (mom1m) ·
`Green_MOM6M_Generalized` (mom6m) · `Green_MOM12M_Generalized` (mom12m) ·
`Green_MOM36M_Generalized` (mom36m) · `Green_MVEL1_Generalized` (mvel1) ·
`Green_NINCR_Generalized` (nincr) · `Green_PCTACC_Generalized` (pctacc) ·
`Green_PS_Generalized` (ps) · `Green_RD_SALE_Generalized` (rd_sale) · `Green_RDM_Generalized` (rdm) ·
`Green_ROA1_Generalized` (roaq) · `Green_RSUP_Generalized` (rsup) ·
`Green_RVAR_MEAN_Generalized` (rvar_mean, Green SAS `retvol`) · `Green_SGR_Generalized` (sgr) ·
`Green_SP_Generalized` (sp) · `Green_STD_DOLVOL_Generalized` (std_dolvol) ·
`Green_STD_TURN_Generalized` (std_turn) · `Green_TURN_Generalized` (turn) ·
`Green_ZEROTRADE_Generalized` (zerotrade)

> Note: `Green_ABR_Generalized` builds `abr` (datashare `ear`). `Green_ROA1_Generalized` outputs
> quarterly `roaq`.

**Removed CLI folders** (not in datashare; pipeline uses `_shared/` only): `Green_ADM`, `Green_ALM`,
`Green_ATO`, `Green_CHPM`, `Green_ME`, `Green_MOM60M`, `Green_NI`, `Green_NOA`, `Green_PM`,
`Green_RE`, `Green_RNA`, `Green_ROE`, `Green_RVAR_CAPM`, `Green_RVAR_FF3`, `Green_SEAS1A`,
`Green_SUE`, `HXZ_BMJ`, `HXZ_CFP`.

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

## Datashare mapping (production)

| datashare | repo column | builder |
|---|---|---|
| `bm` | `book_to_market` | `HXZ_BM_Generalized` |
| `operprof` | `operating_profitability` | `HXZ_OPE_Generalized` |
| `cfp` | `cfp` | Green `_shared/green_builders.py` |
| `bm_ia` | `bm_ia` | `Datashare_BM_IA_Generalized` (SIC2 × month demean of `book_to_market`) |

Use `--profile datashare` in `run_full_pipeline.py`. See `docs/CONFIGURATION.md`.

---

## HXZ / Fama-French June layer (`HXZ_*_Generalized/`)

| Folder | Column | Description |
|---|---|---|
| `HXZ_BM_Generalized` | `book_to_market` | Book-to-market, December ME, June timing |
| `HXZ_OPE_Generalized` | `operating_profitability` | Operating profitability, June timing |
