# Industry Definitions and Industry-Adjusted Variables

Source: `Greens_code.sas`, `Character_Builders/_shared/green_builders.py`,
`Imputation/industry_codes.py`, `Imputation/industry_mappings.py`,
Dacheng `functions.py` (`ffi49`).

## Industry classification schemes available

| Scheme | Definition | Where it lives | Where used |
|---|---|---|---|
| **SIC** | 4-digit Standard Industrial Classification (CRSP `siccd` / Compustat `sic`) | raw data | base for SIC2 and FF mappings |
| **SIC2** | first 2 digits of SIC | `green_builders.py` L292 (`sic_str.str[:2]`) | **all Green industry-adjusted variables** and `indmom`, `ms` |
| **FF12 / FF17 / FF30 / FF38 / FF48 / FF49** (and FF5/FF10) | Fama-French SIC-range groupings | `Imputation/industry_mappings.py` (embedded tables) via `Imputation/industry_codes.py` | research-panel imputation (FF49); Dacheng layer (FF49) |

The repo carries the full FF mapping family (5/10/12/17/30/38/48/49) in
`Imputation/industry_mappings.py`; only **FF49** is wired into the production research panel
(`build_research_panel_1957.py`, default `--industry-scheme 49`). Dacheng's `functions.py` provides
an equivalent `ffi49`.

## Industry-adjustment rules

### Green layer (repository) — SIC2 × fiscal-year, **mean**

```583:598:Character_Builders/_shared/green_builders.py
grouped = comp.groupby(["sic2", "fyear"], dropna=False)
...
comp["cfp_ia"]  = comp["cfp"]   - grouped["cfp"].transform("mean")
comp["chatoia"] = comp["chato"] - grouped["chato"].transform("mean")
comp["chempia"] = comp["hire"]  - grouped["hire"].transform("mean")
comp["pchcapx_ia"] = comp["pchcapx"] - grouped["pchcapx"].transform("mean")
comp["bm_ia"]   = comp["bm"]    - grouped["bm"].transform("mean")
comp["me_ia"]   = comp["mve_f"] - grouped["mve_f"].transform("mean")
comp["tb"]      = comp["tb_1"]  - grouped["tb_1"].transform("mean")
# herf: sum of squared within-industry sales shares (industry concentration)
```

| Variable | Grouping | Statistic | Missing handling |
|---|---|---|---|
| `bm_ia`, `cfp_ia`, `me_ia`, `chatoia`, `chempia`, `chpmia`, `pchcapx_ia`, `tb` | SIC2 × fiscal year | **mean** | `dropna=False` (NaN SIC2 forms its own group); members with missing inputs excluded from the mean |
| `herf` | SIC2 × fiscal year | sum of squared sales shares | — |
| `indmom` | SIC2 × calendar month | **mean** of `mom12m`, broadcast to all members | `green_builders.py` L909 |
| `ms` (Mohanram) industry medians | SIC2 × fiscal year | **median** | `green_builders.py` L647 |

### Dacheng layer — FF49 × `datadate`, **mean**

```1116:1119:Supplementary_assistive_files/Python_codes/Dacheng_Xiu_or_Xin_he/accounting_60.py
df['bm_ia'] = df['bm'] - df.groupby(['datadate','ffi49'])['bm'].transform('mean')
```

The repo Dacheng-exact `bm_ia_dc` reproduces this (FF49, mean). Green's SIC2 grouping vs Dacheng's
FF49 grouping is the primary structural difference for industry-adjusted variables.

### Research-panel imputation grouping — FF49 × month, **median**

```146:166:Character_Panels/build_research_panel_1957.py
panel = add_fama_french_industry_code(panel, scheme=49, sic_col="sic", output_col="ffi49")
panel = winsorize_by_month(...)
panel = impute_by_month_industry(panel, character_cols, time_col="signal_yyyymm", industry_col="ffi49")
panel = rank_by_month(panel, character_cols, time_col="signal_yyyymm")
```

Imputation uses **median** by `(month, FF49)` with a same-month cross-sectional median fallback (see
`07_imputation.md`).

## Mean vs median — quick reference

| Operation | Statistic | Industry scheme |
|---|---|---|
| Green industry-adjusted characteristics (`*_ia`, `indmom`) | mean | SIC2 |
| Green Mohanram (`ms`) industry signals | median | SIC2 |
| Dacheng industry-adjusted (`bm_ia_dc`) | mean | FF49 |
| Research-panel imputation | median | FF49 |

## Handling of missing observations

- Industry means/medians are computed over **non-missing** members of the group; a firm with a
  missing input gets a missing industry-adjusted value (not zero).
- A missing `sic2` forms its own `NaN` group (`dropna=False`) rather than being dropped.
- In the research panel, after imputation, any residual missing is filled by the monthly
  cross-sectional median, then ranks map remaining gaps to 0.
