# Timing Conventions

How Compustat fundamentals and CRSP observations are aligned to calendar months. Source:
`Character_Panels/timing.py`, `Character_Builders/_shared/green_builders.py`,
`_shared/quarterly_builders.py`, `Greens_code.sas`, Dacheng `accounting_60.py`.

## Summary of conventions used

| Convention | Rule | Used for |
|---|---|---|
| **Green annual rolling** | Fundamentals from fiscal-year-end `datadate` are available in calendar months **`datadate + 7` … `datadate + 19`** (SAS `intnx(datadate,7) <= date < intnx(datadate,20)`, offsets `range(7,20)`), inner-joined to the CRSP month index; latest fiscal `datadate` kept per `(permno, signal_yyyymm)` | All repo **Green annual** characteristics (`ANNUAL_CHARACTER_INFO`) |
| **Green quarterly** | Quarterly fundamentals lagged; expanded to monthly with Green quarterly availability | Repo **Green quarterly** characteristics (`chtx`, `roaq`, `roeq`, `cinvest`, `ni`, `nincr`, `rna`, `rsup`, `sue`, `cash`, `stdacc`, `stdcf`, `roavol`) |
| **HXZ / Fama-French June** | FY ending in calendar year `y` → available **June `y+1` … May `y+2`**; December `y` market equity for price ratios | Repo **HXZ June layer** (`book_to_market`, `cash_flow_to_price`, `operating_profitability`, `bmj`) |
| **Datashare (Dacheng)** | Annual `jdate = datadate + 4 months`; quarterly `jdate = datadate + 3 months`; forward-filled monthly until next report; annual/quarterly **blended** by most-recent `datadate` | Repo **Dacheng-exact layer** (`bm_dc`, `operprof_dc`, `cfp_dc`, `bm_ia_dc`) |
| **Monthly-native** | CRSP monthly variables already keyed by `(permno, signal_yyyymm, target_yyyymm)`; kept as-is | Momentum, turnover, dolvol, beta, idiovol, rvar_*, baspread, ill, maxret, std_*, zerotrade, me, mvel1, indmom |

## Green annual rolling (the repo's primary convention)

`Character_Panels/timing.py`:

```81:86:Character_Panels/timing.py
def green_signal_yyyymm_offsets() -> range:
    """Inclusive month offsets used in vectorized Green expansion (7..19)."""
    return range(
        GREEN_ANNUAL_WINDOW_START_LAG_MONTHS,
        GREEN_ANNUAL_WINDOW_END_LAG_MONTHS,
    )
```

```118:154:Character_Panels/timing.py
def expand_annual_file_green(df, character_columns, crsp_month_index=None):
    """Green rolling annual availability (Greens_code.sas L484, L505-L508)."""
    ...
    for month_lag in green_signal_yyyymm_offsets():
        signal_dates = (chunk["datadate"] + pd.DateOffset(months=month_lag))...
    ...
    # inner-join to the CRSP month index so only real trading months survive
```

- A fiscal row produces monthly signal rows over offsets 7–19. The latest fiscal year wins on
  duplicate `(permno, signal_yyyymm)` (`keep="last"`).
- `target_yyyymm = signal_yyyymm + 1` — the return month the signal predicts.

## HXZ / Fama-French June

```97:115:Character_Panels/timing.py
def expand_annual_file_june(df, character_columns):
    """HXZ / Fama-French June availability: FY ending calendar year y -> Jun y+1 .. May y+2."""
    availability_year = df["datadate"].dt.year + 1
    ...
```

Stems routed to June timing (`timing.py` L36-43): `book_to_market`, `book_to_june_market_equity`,
`cash_flow_to_price`, `operating_profitability`. All other annual stems route to Green rolling
(`timing_convention_for_stem`, L89-94).

## Datashare (Dacheng) timing

From `accounting_60.py`:
- Annual: `ccm1['jdate'] = ccm1['datadate'] + MonthEnd(4)` (L204).
- Quarterly: `ccm1['jdate'] = ccm1['datadate'] + MonthEnd(3)` (L633).
- After merging to monthly CRSP, accounting fields are forward-filled within `(permno, datadate)`
  (L1089-1091).
- The final blend (`impute_rank_output_bchmk_60.py` L59-81) picks, per characteristic, the annual or
  quarterly value with the **more recent `datadate`** (else whichever is available, annual preferred).
- Dacheng additionally shifts the saved `DATE` to the following month relative to the predictor
  `jdate` (`impute_rank_output_bchmk_60.py` L89-91). The repo Dacheng validator tests both alignments.

## How Compustat data become available (annual)

1. Pull `comp.funda` (consolidated/standardized/industrial/domestic). Green requires non-missing
   `at`, `prcc_f`, `ni` and `datadate >= 1975` in the SAS source (`Greens_code.sas` L69); the repo
   builds full history and applies screens at panel time.
2. Link to CRSP `permno` via CCM (see `03_linking.md`).
3. Expand the single fiscal row across the availability window (Green rolling, HXZ June, or
   datashare lag) and inner-join to the CRSP month index so only months with a real CRSP observation
   survive.

## How CRSP months are assigned

- CRSP monthly observations are stamped to month-end (`signal_yyyymm` = year*100+month).
- Monthly-native characteristics keep their own `(permno, signal_yyyymm)`.
- The annual/quarterly expansions are inner-joined to the CRSP month index (preferring `me.csv`, else
  the union of monthly-native panels) so the spine is the actual CRSP trading-month universe
  (`build_all_character_panel.py` L197-203).

## Per-variable timing convention

- **Green rolling (7–19):** every key in `ANNUAL_CHARACTER_INFO` (`green_builders.py` L34-108).
- **Green quarterly:** every key in `QUARTERLY_CHARACTER_INFO` (`quarterly_builders.py` L47-75).
- **June:** the four HXZ stems above.
- **Datashare lag (+4/+3, blended):** the four `_dc` characteristics.
- **Monthly-native:** `MONTHLY_CHARACTER_INFO` + `DAILY_MONTHLY_CHARACTER_INFO` + special (beta,
  betasq, idiovol, pricedelay, ear, abr, aeavol, ms, re, rvar_capm, rvar_ff3).
