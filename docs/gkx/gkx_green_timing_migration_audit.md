# Green timing migration — classification and design audit

**Date:** 2026-05-29  
**Policy:** Green-derived annual characteristics use Green SAS rolling monthly timing at panel merge. HXZ/Fama-French standalone builders keep documented June timing. Formula source and timing source may differ.

**Implementation:** `Character_Panels/timing.py`, `Character_Panels/build_all_character_panel.py`

---

## Step 1 — Characteristic classification (summary)

| Timing family | Count | Intended convention | Migration |
|---------------|------:|-------------------|-----------|
| Green annual (`ANNUAL_CHARACTER_INFO`) | 72 | **Green rolling** (`datadate+7` … `datadate+19` mo) | **Yes** — migrated |
| HXZ annual CSVs | 4 | **June** (`expand_annual_file_june`) | No |
| Green quarterly (`quarterly_builders.py`) | 8 | **Monthly native** (builder `merge_asof`) | No — separate Green quarterly SAS window (future work) |
| Green monthly CRSP | 10 | **Monthly native** | No |
| Green daily-rolled | 7 | **Monthly native** (prior-month lag) | No |
| Special (`beta`, `abr`, `re`, `rvar_*`) | 6 | **Monthly native** / event / IBES | No |

### Green annual characteristics (72) — all migrate to Green rolling timing

`absacc`, `acc`, `adm`, `age`, `agr`, `alm`, `ato`, `bm`, `bm_ia`, `cash`, `cashdebt`, `cashpr`, `cfp`, `cfp_ia`, `chcsho`, `chobklg`, `chinv`, `chpm`, `chpmia`, `chatoia`, `chempia`, `convind`, `currat`, `depr`, `dy`, `divi`, `divo`, `egr`, `ep`, `gma`, `grcapx`, `grltnoa`, `herf`, `hire`, `invest`, `lev`, `lgr`, `me_ia`, `noa`, `obklg`, `op`, `orgcap`, `pctacc`, `pchcurrat`, `pchdepr`, `pchcapx`, `pchcapx_ia`, `pchgm_pchsale`, `pchquick`, `pchsale_pchinvt`, `pchsale_pchrect`, `pchsale_pchxsga`, `pchsaleinv`, `pm`, `ps`, `quick`, `rd`, `rd_sale`, `rdm`, `realestate`, `roe`, `roic`, `sgr`, `salecash`, `saleinv`, `salerec`, `secured`, `securedind`, `sin`, `sp`, `tb`, `tang`

**Builder:** `Character_Builders/_shared/green_builders.py` → annual CSV (`permno`, `datadate`, …)  
**Panel path (before):** `expand_annual_file` (June flat 12 months)  
**Panel path (after):** `expand_annual_file_green` in `timing.py`

### HXZ / Fama-French — keep June timing

| CSV stem | Column | Builder |
|----------|--------|---------|
| `book_to_market` | `book_to_market` | `HXZ_BM_Generalized` |
| `book_to_june_market_equity` | `bmj` | `HXZ_BMJ_Generalized` |
| `cash_flow_to_price` | `cash_flow_to_price` | `HXZ_CFP_Generalized` |
| `operating_profitability` | `operating_profitability` | `HXZ_OPE_Generalized` |

### Monthly-native (no annual expansion)

Quarterly: `chtx`, `cinvest`, `ni`, `nincr`, `rna`, `roa1`, `rsup`, `sue`  
Monthly CRSP: `dolvol`, `me`, `mvel1`, `mom1m`, `mom6m`, `mom12m`, `mom36m`, `mom60m`, `seas1a`, `turn`  
Daily-rolled: `baspread`, `ill`, `maxret`, `rvar_mean`, `std_dolvol`, `std_turn`, `zerotrade`  
Other: `beta`, `betasq`, `abr`, `re`, `rvar_capm`, `rvar_ff3`

---

## Step 2 — Green annual pipeline trace

For each of the 72 Green annual variables:

| Stage | Behavior |
|-------|----------|
| **Annual CSV** | One row per `permno × datadate` from `compute_annual_characters` + CCM link |
| **`expand_annual_file` (legacy)** | June of `year(datadate)+1` for 12 constant months |
| **`expand_annual_file_green` (new)** | Months where `intnx(MONTH,datadate,7) ≤ date < intnx(MONTH,datadate,20)`; latest `datadate` per `permno×month` |
| **Signal panel merge** | Outer merge on `permno`, `signal_yyyymm`, `target_yyyymm` |
| **Complete panel** | Join excess returns on `target_yyyymm` |

Annual CSVs are **unchanged**; only panel expansion timing changed.

---

## Step 3 — Green timing function (SAS reference)

**Source:** `Greens_code.sas` lines 475–508

```sas
on a.permno=b.permno and intnx('MONTH',datadate,7)<=b.date<intnx('MONTH',datadate,20);
...
by permno date descending datadate;
by permno date;  /* nodupkey */
```

**Python:** `Character_Panels/timing.py`

- `expand_annual_file_green()` — vectorized month lags 7…19, dedupe latest `datadate`
- Optional `crsp_month_index` — intersect with monthly-native CRSP months (from `me.csv`, etc.)
- `expand_annual_file_june()` — legacy HXZ June convention
- `expand_annual_file` — alias to June for backward-compatible validation scripts

**Legacy export:** `python Character_Panels/build_all_character_panel.py --legacy-june-annual`

---

## Step 4 — Book equity / B/M formula audit (deferred changes)

| Variable | Green SAS | Repo (`green_builders.py`) | HXZ/FF | Decision |
|----------|-----------|---------------------------|--------|----------|
| **`bm`** | `ceq / mve_f` (no `ceq` fallback) | Same | `book_to_market`: FF BE hierarchy / Dec ME | **Keep Green formula** for `bm`; use `book_to_market` for FF |
| **`bm_ia`** | `bm − mean(bm)` by `sic2,fyear` | Same | — | **Keep Green** |
| **`cfp`** | `oancf/mve_f` or WC-accrual fallback | Same | `cash_flow_to_price`: `(IB+DP)/Dec ME` | **Keep Green** for `cfp` |
| **`cfp_ia`** | `cfp − mean(cfp)` by `sic2,fyear` | Same | — | **Keep Green** |
| **`op`** | `(revt−cogs−xsga0−xint0)/lag(ceq)` | Same | HXZ OPE uses FF BE | **Keep Green** for `op` |

**No formula changes in this phase.** Green timing migration improves monthly alignment without altering definitions (see validation: `bm` Spearman 0.9996 vs 0.9748 June).

**Note:** Green SAS output applies monthly winsorization to `chatoia`, `bm_ia`, etc.; repo builders do not. Residual monthly differences on industry-adjusted variables may reflect winsorization, not timing.

---

## Step 8 — Legacy behavior

- `--legacy-june-annual` on `build_all_character_panel.py` restores June flat expansion for all annual CSVs.
- `expand_annual_file` / `expand_annual_file_june` remain available for validation scripts.
- HXZ CSVs always use June timing regardless of flag.

---

## Risks / open items

1. **Quarterly Green SAS timing** (`intnx(MONTH,date,-10)` … `-5`) differs from repo `merge_asof` + 12-month validity — not migrated in this phase.
2. **`orgcap`:** all missing in Green SAS output 201801–202312 — cannot validate monthly alignment in-window.
3. **Green winsorization:** saved SAS values are post-winsor; repo compares pre-winsor builders.
4. **`bmj`:** HXZ June logic embedded in builder; panel still applies June expansion — verify separately against HXZ docs.

---

See also: `docs/gkx/gkx_green_sas_timing_forensic_audit.md`, `docs/gkx/gkx_green_timing_migration_validation.md`, `docs/gkx/gkx_green_timing_migration_report.md`
