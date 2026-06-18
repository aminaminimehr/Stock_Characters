# Datashare / Green Gap Character Fix Guideline

This document is a handoff for the next agent. It focuses only on the subset of `datashare.csv` columns that were validated against Green SAS output and found to be either missing from the current repository or built but not matching Green sufficiently.

The goal is not to redesign the whole repository. The goal is to guide a focused correction pass:

1. Treat Green SAS output as the primary value and timing benchmark.
2. Treat GKX `datashare.csv` as the target column universe.
3. Fix or implement only the datashare columns listed here.
4. Validate each fix against Green before moving to GKX-specific modifications.

## Source Context

The last validation report identified two groups:

- Missing from the repo panel: 11 datashare columns.
- Built in the repo but wrong or below threshold against Green: 11 datashare columns.

Important note:

`ear` is not missing. It is currently represented in the repo panel as `abr`, but it does not match Green and must be fixed.

## Benchmark Policy

Use this policy while working on this list:

| Object | Role |
| --- | --- |
| `Supplementary_assistive_files/SAS_codes/Greens_code.sas` | Formula, timing, and construction source of truth |
| `Supplementary_assistive_files/Output_From_Greens_SAS_code.sas7bdat` | Primary validation benchmark |
| `Supplementary_assistive_files/datashare.csv` | Target column universe and final export naming reference |
| `Supplementary_assistive_files/Python_codes/Dacheng_Xiu_or_Xin_he/` | Useful implementation reference, especially for slow daily rolling / parallel-processing design |

Do not copy GKX/Dacheng formulas blindly before checking Green SAS. Some Dacheng implementations differ from Green. Use Dacheng code mainly to understand architecture and possible GKX modifications after Green is matched.

## Missing Characters

These 11 datashare columns are not currently built in the repo panel.

| Datashare column | Green SAS column | Priority notes |
| --- | --- | --- |
| `aeavol` | `aeavol` | Quarterly/event variable tied to abnormal earnings announcement volume. Likely needs quarterly CRSP/event-date logic. |
| `chmom` | `chmom` | Monthly momentum-change style variable. Check Green SAS monthly CRSP section. |
| `idiovol` | `idiovol` | Daily return residual volatility. Likely slow daily rolling/regression variable; should use shared parallel daily-window infrastructure. |
| `indmom` | `indmom` | Industry momentum. Likely monthly CRSP plus industry grouping. |
| `ms` | `ms` | Mohanram-style score or related accounting score in Green SAS. Check exact Green construction before implementing. |
| `pricedelay` | `pricedelay` | Daily/weekly return regression variable. Likely slow and should use parallel firm chunks. |
| `roavol` | `roavol` | Quarterly volatility of ROA. Likely from quarterly Compustat history. |
| `roeq` | `roeq` | Quarterly return on equity. Do not alias annual `roe`; implement quarterly definition. |
| `sic2` | `sic2` | Two-digit SIC. May already exist as metadata in some intermediate files but is missing as a datashare panel/export column. |
| `stdacc` | `stdacc` | Volatility/std of accruals. Likely quarterly or annual history-based accounting variable. |
| `stdcf` | `stdcf` | Volatility/std of cash flows. Likely quarterly or annual history-based accounting variable. |

## Built But Wrong / Below Threshold

These 11 variables exist in the repo panel but do not match Green well enough.

| Datashare column | Current repo column | Median rho vs Green | Issue summary |
| --- | --- | ---: | --- |
| `cinvest` | `cinvest` | -0.07 | Sign/ranking inverted. |
| `nincr` | `nincr` | 0.05 | Earnings-streak logic wrong. |
| `ear` | `abr` | 0.11 | Event-window EAR mismatch. Not missing, but wrong. |
| `chtx` | `chtx` | 0.16 | Tax-change formula and/or timing mismatch. |
| `rsup` | `rsup` | 0.48 | Revenue surprise mismatch. |
| `beta` | `beta` | 0.53 | Weekly 36-month beta method mismatch. |
| `betasq` | `betasq` | 0.53 | Derived from `beta`; fix follows beta. |
| `operprof` | `operating_profitability` | 0.57 | Operating profitability mismatch. May need Green `operprof` or repo `op`, not HXZ `operating_profitability`. |
| `pchcapx_ia` | `pchcapx_ia` | 0.65 | Industry-adjusted cap-ex mismatch. |
| `roaq` | `roa1` | 0.66 | Quarterly ROA mismatch. |
| `cash` | `cash` | 0.93 | Close but below threshold. Needs targeted audit, probably timing or quarterly/annual source issue. |

## Recommended Fix Order

The next agent should avoid trying to fix all 22 variables at once. Use this order.

### Batch 1: Export / Alias / Metadata Sanity

Start with low-risk structural fixes.

1. `sic2`
2. `betasq`

For `sic2`, determine whether the correct two-digit SIC is already present in the panel metadata. If yes, expose it as a datashare-style column. If no, trace Green's SIC source and add it consistently.

For `betasq`, do not implement separate logic. It should be:

```text
betasq = beta * beta
```

But only after `beta` itself is corrected.

### Batch 2: Quarterly Compustat Formula Corrections

These likely share code in `Character_Builders/_shared/quarterly_builders.py`:

1. `cinvest`
2. `nincr`
3. `chtx`
4. `rsup`
5. `roaq`
6. `roeq`
7. `roavol`
8. `cash`

The built-but-wrong quarterly variables should be fixed before adding missing quarterly variables because the same base quarterly panel, lag rules, and timing alignment are probably involved.

Important: validate whether each variable should be sourced from quarterly Compustat, annual Compustat, or Green's merged monthly panel after quarterly alignment. Do not assume from the current repo names.

### Batch 3: Annual / Industry-Adjusted Accounting Corrections

Focus on:

1. `operprof`
2. `pchcapx_ia`
3. `ms`
4. `stdacc`
5. `stdcf`

For `operprof`, do not assume the HXZ builder `operating_profitability` is the right source. Green's `operprof` may correspond more closely to a Green annual formula in `_shared/green_builders.py`, possibly `op`, or a separate formula. Check Green SAS directly.

For `pchcapx_ia`, audit all of:

- raw `pchcapx` formula,
- capital expenditure missing-value handling,
- denominator and lag rules,
- SIC2/fiscal-year grouping,
- industry mean calculation,
- timing expansion,
- winsorization status.

### Batch 4: Slow Daily / Event / Regression Variables

These are likely expensive and should use parallel firm-chunk processing:

1. `beta`
2. `idiovol`
3. `pricedelay`
4. `aeavol`
5. `ear`
6. `chmom`
7. `indmom`

Use the separate parallel-processing review:

```text
agents review/Dacheng_Xin_He_parallel_processing_review.MD
```

That file explains Dacheng/Xin He's firm-chunk multiprocessing design. Use the architecture, but validate formulas against Green SAS first.

## Variable-Specific Guidance

### `cinvest`

Status: built but wrong, median rho approximately -0.07.

Likely issue:

- sign inversion,
- wrong numerator,
- wrong denominator,
- wrong lag,
- or wrong quarterly-to-monthly alignment.

First checks:

1. Find Green SAS formula for `cinvest`.
2. Compare current repo formula in `quarterly_builders.py`.
3. Validate raw quarterly values before monthly expansion.
4. Check whether multiplying by `-1` improves agreement. If yes, still inspect formula rather than applying a blind sign flip.

### `nincr`

Status: built but wrong, median rho approximately 0.05.

Likely issue:

- earnings increase streak logic,
- number of quarters considered,
- reset behavior,
- treatment of missing quarterly earnings,
- current quarter vs previous quarter alignment.

Green SAS should be followed line by line. This variable is prone to off-by-one errors.

### `ear` / `abr`

Status: repo has `abr`, but datashare/Green column is `ear`; median rho approximately 0.11.

Do not classify as missing. It is implemented under the wrong or incomplete logic.

Likely issue:

- event window around earnings announcement date,
- abnormal return benchmark,
- use of CRSP daily returns,
- announcement-date source,
- missing or shifted event date,
- monthly assignment.

Action:

1. Find exact Green SAS `ear` event-window logic.
2. Compare to current `Character_Builders/_shared/event_builders.py`.
3. Validate event dates before validating returns.
4. Validate raw event-level `ear` before monthly panel alignment.

### `chtx`

Status: built but wrong, median rho approximately 0.16.

Likely issue:

- quarterly tax expense change formula,
- denominator,
- lag length,
- fiscal-quarter sorting,
- Compustat variable choice.

Action:

1. Re-read Green SAS formula.
2. Compare lag construction in `quarterly_builders.py`.
3. Validate on `gvkey x datadate` before monthly alignment.

### `rsup`

Status: built but wrong, median rho approximately 0.48.

Likely issue:

- revenue surprise lag window,
- scaling variable,
- standardization,
- quarterly alignment.

Action:

1. Confirm whether Green uses seasonal quarterly revenue differences.
2. Confirm denominator and minimum history requirement.
3. Validate raw quarterly values first.

### `beta`

Status: built but wrong, median rho approximately 0.53.

The current repo `beta_builder.py` says it implements Green weekly 36-month beta. The low validation indicates the method is still not matching Green.

Green SAS forensic notes indicate beta should use:

```text
intnx('MONTH', date, -36) <= wkdt <= intnx('MONTH', date, -1)
```

with weekly stock returns and equal-weight market return.

Action:

1. Do not replace with Dacheng's 3-month daily beta unless targeting GKX/Dacheng specifically.
2. Audit weekly return construction.
3. Audit week-date assignment.
4. Audit equal-weight market return construction.
5. Audit 36-month window boundaries.
6. Audit minimum observation rule.
7. Parallelize by `permno` only after formula is validated on a small sample.

### `betasq`

Status: built but wrong because `beta` is wrong.

Action:

1. Fix `beta`.
2. Recompute `betasq = beta ** 2`.
3. Validate `betasq`.

No independent formula work should be needed.

### `operprof`

Status: repo column `operating_profitability`, median rho approximately 0.57.

Likely issue:

- repo is using HXZ/Fama-French-style operating profitability,
- Green `operprof` may differ from HXZ `operating_profitability`,
- wrong denominator or expense treatment.

Action:

1. Check Green SAS `operprof` formula.
2. Compare against repo Green annual `op` as well as HXZ `operating_profitability`.
3. Do not alias HXZ `operating_profitability` to `operprof` unless validation supports it.
4. If Green `op` is the correct source, export it under datashare name `operprof`.

### `pchcapx_ia`

Status: built but wrong, median rho approximately 0.65.

Likely issue:

- raw `pchcapx`,
- missing `capx` imputation,
- denominator zero handling,
- industry adjustment,
- SIC2/fyear group composition,
- timing.

Action:

1. Validate raw `pchcapx` against Green if available.
2. Validate industry mean separately.
3. Validate `pchcapx_ia = pchcapx - industry_mean`.
4. Check whether the disagreement is formula, industry group, or timing.

### `roaq`

Status: current repo column `roa1`, median rho approximately 0.66.

Likely issue:

- Green `roaq` definition differs from repo `roa1`,
- denominator/lag mismatch,
- quarterly timing mismatch.

Action:

1. Do not assume `roa1` equals `roaq`.
2. Implement or correct a Green-style quarterly `roaq`.
3. Export under datashare name `roaq`.

### `cash`

Status: built but close, median rho approximately 0.93.

Likely issue:

- annual vs quarterly source conflict,
- timing mismatch,
- Compustat variable treatment,
- winsorization/post-merge effect.

Action:

1. Determine whether datashare/Green `cash` is annual or quarterly in the validation mapping.
2. Compare raw values by `permno/date` and by `gvkey/datadate`.
3. Because rho is close, avoid broad rewrites. This is likely a small convention mismatch.

### `aeavol`

Status: missing.

Likely an earnings-announcement abnormal volume variable.

Action:

1. Locate Green SAS lines for `aeavol`.
2. Identify required event date source.
3. Determine whether current repo has enough data without IBES.
4. Implement event-level value first, then monthly assignment.

### `chmom`

Status: missing.

Likely change in momentum.

Action:

1. Locate Green SAS monthly CRSP formula.
2. Check whether existing `mom6m`, `mom12m`, or other momentum columns can be reused.
3. Implement from existing monthly CRSP panel if possible.

### `idiovol`

Status: missing.

Likely daily idiosyncratic volatility from residuals.

Action:

1. Locate Green SAS regression specification.
2. Implement using shared parallel daily-window engine.
3. Validate on a small sample before full history.

### `indmom`

Status: missing.

Likely industry momentum.

Action:

1. Identify Green industry classification source.
2. Compute industry-level momentum excluding or including own firm exactly as Green does.
3. Validate monthly cross-sections.

### `ms`

Status: missing.

Likely an accounting score variable.

Action:

1. Locate Green SAS formula.
2. Determine whether it is annual or quarterly.
3. Implement after the underlying component variables are validated.

### `pricedelay`

Status: missing.

Likely regression-based price delay variable using daily or weekly returns.

Action:

1. Locate Green SAS formula and window.
2. Implement with parallel firm chunks.
3. Be careful with lagged market returns and regression R-squared logic.

### `roavol`

Status: missing.

Likely volatility of quarterly ROA.

Action:

1. Implement only after `roaq` is corrected.
2. Match Green's number of quarters and minimum-history rule.

### `roeq`

Status: missing.

Do not alias annual `roe`.

Action:

1. Implement quarterly return on equity from Green SAS.
2. Validate raw quarterly values.
3. Export as `roeq`.

### `stdacc`

Status: missing.

Likely standard deviation of accruals over a historical accounting window.

Action:

1. Locate exact Green variable source: annual or quarterly.
2. Match rolling history length and minimum observations.
3. Implement after base accrual variable is validated.

### `stdcf`

Status: missing.

Likely standard deviation of cash flow over a historical accounting window.

Action:

1. Locate exact Green variable source: annual or quarterly.
2. Match rolling history length and minimum observations.
3. Implement after base cash-flow variable is validated.

## Validation Procedure For Each Fix

Every variable should go through the same validation sequence.

1. Identify Green SAS lines and copy the relevant formula/timing notes into the commit or report.
2. Build a small sample first, such as 2010-2015 or 2018-2023.
3. Validate raw source-level values where possible:
   - `gvkey x datadate` for accounting variables,
   - `permno x event_date` for event variables,
   - `permno x source month` for daily/monthly variables.
4. Validate final monthly panel against Green SAS on:
   - `permno`
   - month-end `DATE` / `signal_yyyymm`
5. Report:
   - paired rows,
   - coverage ratio,
   - Pearson,
   - Spearman,
   - median monthly Spearman,
   - median absolute difference,
   - top disagreement examples.
6. Only accept a fix when it improves both formula-level and monthly-panel validation.

## Parallel Processing Guidance

Several missing or wrong variables are slow because they require rolling daily, weekly, or event-window calculations.

Use the separate handoff:

```text
agents review/Dacheng_Xin_He_parallel_processing_review.MD
```

The key implementation rule:

Use Dacheng/Xin He's firm-chunk architecture for speed, but keep the Green SAS formula unless intentionally switching to a GKX-specific formula after Green validation.

Variables likely needing parallel processing:

- `beta`
- `idiovol`
- `pricedelay`
- possibly `aeavol`
- possibly `ear`
- if rewritten to 3-month rolling daily windows: `baspread`, `ill`, `maxret`, `rvar_mean`, `std_dolvol`, `std_turn`, `zerotrade`

## Files The Next Agent Should Inspect First

Core implementation files:

- `Character_Builders/_shared/quarterly_builders.py`
- `Character_Builders/_shared/green_builders.py`
- `Character_Builders/_shared/beta_builder.py`
- `Character_Builders/_shared/event_builders.py`
- `Character_Builders/_shared/rvar_factor_builders.py`
- `Character_Builders/build_all_implemented_characters.py`
- `Character_Panels/build_all_character_panel.py`
- `Character_Panels/timing.py`

Validation and audit files:

- `docs/gkx/datashare_columns_green_validation.md`
- `docs/gkx/datashare_columns_green_benchmark_mapping.md`
- `docs/gkx/green_timing_validation_2010_2015.md`
- `scripts/build_datashare_green_mapping.py`
- `scripts/validate_green_timing_2010_2015.py`

Reference files:

- `Supplementary_assistive_files/SAS_codes/Greens_code.sas`
- `Supplementary_assistive_files/Output_From_Greens_SAS_code.sas7bdat`
- `Supplementary_assistive_files/datashare.csv`
- `Supplementary_assistive_files/Python_codes/Dacheng_Xiu_or_Xin_he/`

## Success Criteria

The correction pass should produce:

1. All 11 missing datashare columns present in the repo panel or explicitly documented as unavailable due to data access.
2. All 11 built-but-wrong columns revalidated against Green.
3. A clear alias/export mapping:
   - `ear` may be sourced from corrected event logic but exported as `ear`.
   - `roaq` should not remain a blind alias for `roa1` unless validated.
   - `operprof` should not remain a blind alias for HXZ `operating_profitability` unless validated.
4. A validation report showing before/after metrics.
5. No broad formula changes to already-good variables unless necessary.
6. No full-history slow rebuilds until small-window validation passes.

## Final Warning

Do not optimize speed before confirming the correct formula and timing. Parallelizing the wrong formula will only make incorrect output arrive faster.

For each variable, establish the Green SAS target first, then make it fast.
