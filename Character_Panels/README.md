# Character Panels

This folder contains scripts that combine individual character builders into
larger panels.

These scripts do not connect to WRDS. They expect the individual character files
to already exist in `outputs/`.

For the annual accounting panel, run:

```powershell
python Character_Builders/HXZ_BM_Generalized/build_book_to_market.py --wrds-user YOUR_WRDS_USERNAME
python Character_Builders/HXZ_BMJ_Generalized/build_book_to_june_market_equity.py --wrds-user YOUR_WRDS_USERNAME
python Character_Builders/HXZ_OPE_Generalized/build_operating_profitability.py --wrds-user YOUR_WRDS_USERNAME
python Character_Builders/HXZ_CFP_Generalized/build_cash_flow_to_price.py --wrds-user YOUR_WRDS_USERNAME --use-imputed-market-equity
```

For the monthly prediction panel, also run:

```powershell
python Character_Builders/Green_MVEL1_Generalized/build_mvel1.py --wrds-user YOUR_WRDS_USERNAME
```

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
files directly on `permno`, `signal_yyyymm`, and `target_yyyymm`.

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
