# HXZ Character Panels

This folder contains scripts that combine individual HXZ character builders into
larger panels.

These scripts do not connect to WRDS. They expect the individual character files
to already exist in `outputs/`.

Run the individual character builders first:

```powershell
python HXZ_Characters/HXZ_BM_Generalized/build_book_to_market.py --wrds-user YOUR_WRDS_USERNAME
python HXZ_Characters/HXZ_OPE_Generalized/build_operating_profitability.py --wrds-user YOUR_WRDS_USERNAME
python HXZ_Characters/HXZ_CFP_Generalized/build_cash_flow_to_price.py --wrds-user YOUR_WRDS_USERNAME --use-imputed-market-equity
```

Required local files:

```text
outputs/book_to_market.csv
outputs/operating_profitability.csv
outputs/cash_flow_to_price.csv
```

## Annual Panel

```powershell
python HXZ_Character_Panels/build_annual_character_panel.py
```

Output:

```text
outputs/annual_character_panel.csv
```

## Monthly Prediction Panel

```powershell
python HXZ_Character_Panels/build_monthly_character_panel.py
```

Output:

```text
outputs/monthly_character_panel.csv
```

The monthly panel repeats each annual characteristic from July of
`datadate.year + 1` through June of `datadate.year + 2`.
