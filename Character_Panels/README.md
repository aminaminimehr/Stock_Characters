# Character Panels

This folder contains scripts that combine individual character builders into
larger panels.

**Full repository panel:** see the root [README](../README.md#recommended-full-pipeline-from-scratch).
Run `Character_Panels/run_full_pipeline.py` (or `run_full_pipeline.sh` /
`run_full_pipeline.ps1`) from the repository root. That builds all characters
via WRDS, then creates `all_character_signal_panel.csv` and
`research_panel_1957_ranked.csv`.

The panel scripts below do **not** connect to WRDS. They expect individual
character CSV files to already exist in `outputs/`.

The following HXZ-only commands build a **small subset** (about five files) and
are **not** sufficient for the full all-character panel:

```powershell
python Character_Builders/HXZ_BM_Generalized/build_book_to_market.py --wrds-user YOUR_WRDS_USERNAME
python Character_Builders/HXZ_BMJ_Generalized/build_book_to_june_market_equity.py --wrds-user YOUR_WRDS_USERNAME
python Character_Builders/HXZ_OPE_Generalized/build_operating_profitability.py --wrds-user YOUR_WRDS_USERNAME
python Character_Builders/HXZ_CFP_Generalized/build_cash_flow_to_price.py --wrds-user YOUR_WRDS_USERNAME --use-imputed-market-equity
```

For the legacy narrow annual panel workflow, those four files are required. For
the full panel, run `build_all_implemented_characters.py` first (includes
`mvel1` and all Green-style characters).

Required local files for the annual panel:

```text
outputs/book_to_market.csv
outputs/book_to_june_market_equity.csv
outputs/operating_profitability.csv
outputs/cash_flow_to_price.csv
```

Additional required local file for the monthly panel:

```text
outputs/mvel1.csv
```

## Annual Panel

```powershell
python Character_Panels/build_annual_character_panel.py
```

Output:

```text
outputs/annual_character_panel.csv
```

## Monthly Prediction Panel

```powershell
python Character_Panels/build_monthly_character_panel.py
```

Output:

```text
outputs/monthly_character_panel.csv
```

The monthly panel keeps two timing columns:

- `signal_yyyymm`: the predictor month where the characteristic is observable.
- `target_yyyymm`: the next-month return month.

Annual accounting characteristics are repeated from June of `datadate.year + 1`
through May of `datadate.year + 2`. This is equivalent to the usual July-through-
June testing return window, but the predictor month is kept explicit so returns
can be aligned later with a single one-month lead.

## All-Character Signal Panel

After running any individual character builders, combine all compatible local
CSV outputs with:

```powershell
python Character_Panels/build_all_character_panel.py
```

Output:

```text
outputs/all_character_signal_panel.csv
```

This script does not connect to WRDS. It reads existing files in `outputs/`,
expands annual files onto the shared signal-month calendar, and merges monthly
files directly on `permno`, `signal_yyyymm`, and `target_yyyymm`. It also
preserves SIC when available so later industry imputation can be performed.

## Complete Prediction Panel

After building monthly characters and excess returns, create the feature-target
panel with:

```powershell
python Character_Panels/build_complete_prediction_panel.py
```

Required inputs:

```text
outputs/monthly_character_panel.csv
outputs/excess_returns.csv
```

Output:

```text
outputs/complete_prediction_panel.csv
```

The merge keys are `permno` and `target_yyyymm`. The character month remains
`signal_yyyymm`; no additional shifting is applied to the character columns.

## 1957+ Research Panel

To create the project-ready broad panel used for prediction work, first build
the broad all-character signal panel and merge it to returns:

```powershell
python Character_Panels/build_all_character_panel.py
python Character_Panels/build_complete_prediction_panel.py --characters outputs/all_character_signal_panel.csv --returns outputs/excess_returns.csv --output outputs/complete_all_character_prediction_panel.csv
```

Then run:

```powershell
python Character_Panels/build_research_panel_1957.py
```

Output:

```text
outputs/research_panel_1957_ranked.csv
```

This final step keeps target return months from `195701` onward, winsorizes
each characteristic by signal month at the 1st and 99th percentiles, imputes
missing values using signal-month by Fama-French 49-industry medians, and then
cross-sectionally maps each characteristic's monthly ranks into `[-1, 1]`.
Remaining unavailable cells, which occur when an entire characteristic does not
exist in an early month, are assigned the neutral rank value `0`.
