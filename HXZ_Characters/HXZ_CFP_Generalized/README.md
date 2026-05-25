# Cash-Flow-to-Price Character

This folder contains the cash-flow-to-price character construction following the
Hou-Xue-Zhang testing-portfolio documentation.

The output keeps the actual Compustat `datadate`. It does not shift the date for
return prediction. Any lagging or matching to future returns should be done later
when the return file is created.

## Timing for Prediction

The raw file is dated by the actual Compustat `datadate`. For HXZ
portfolio timing, a character from fiscal year ending in calendar year `y` is
used at the end of June in year `y + 1`.

Example:

- Compustat `datadate` in 2004.
- CRSP market equity from December 2004.
- Character becomes available for June 2005 portfolio formation.
- It can predict returns from July 2005 through June 2006.

So when merging with returns, create an availability date such as June 30 of
`datadate.year + 1`, and merge future returns after that date.

## Character Definition

Cash-flow-to-price is:

```text
(IB + DP) / December market equity
```

where:

- `IB` is income before extraordinary items.
- `DP` is depreciation.
- December market equity is from CRSP at the end of the same calendar year as
  the Compustat `datadate`.
- For firms with multiple share classes, market equity is summed across share
  classes at the `permco` level before computing the ratio.
- Firms with nonpositive cash flows are excluded.

If a firm has multiple Compustat records in the same calendar year because of a
fiscal year-end change, the script keeps the most recent `datadate`.

The final file contains only:

- `permno`
- `permco`
- `gvkey`
- `datadate`
- `sic`
- `fyear`
- `cash_flow_to_price`

## CRSP Market Equity Imputation

By default, the script uses the exact CRSP monthly `prc` and `shrout` values.

To allow older monthly values to fill missing price or shares outstanding within
the same `permno`, run:

```powershell
python build_cash_flow_to_price.py --use-imputed-market-equity
```

## Run

```powershell
python build_cash_flow_to_price.py
```

Optional output name:

```powershell
python build_cash_flow_to_price.py --output cfp.csv
```

By default, output is written to `outputs/cash_flow_to_price.csv` in the
`Stock_Characters` folder.
