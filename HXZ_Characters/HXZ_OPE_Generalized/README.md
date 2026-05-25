# Operating Profitability Character

This folder contains the operating profitability to equity character construction
following the Hou-Xue-Zhang testing-portfolio documentation.

The output keeps the actual Compustat `datadate`. It does not shift the date for
return prediction. Any lagging or matching to future returns should be done later
when the return file is created.

## Timing for Prediction

The raw file is dated by the actual Compustat `datadate`. For HXZ
portfolio timing, a character from fiscal year ending in calendar year `y` is
used at the end of June in year `y + 1`.

Example:

- Compustat `datadate` in 2004.
- Character becomes available for June 2005 portfolio formation.
- It can predict returns from July 2005 through June 2006.

So when merging with returns, create an availability date such as June 30 of
`datadate.year + 1`, and merge future returns after that date.

## Character Definition

Operating profitability to equity is:

```text
(REVT - COGS - XSGA - XINT) / book_equity
```

where missing `COGS`, `XSGA`, and `XINT` are treated as zero, but at least one of
those three expense items must be nonmissing. The denominator is current
book equity, not lagged book equity.

Book equity is constructed as stockholders' equity plus `TXDITC`, minus preferred
stock. Preferred stock uses `PSTKRV`, then `PSTKL`, then `PSTK`.

If a firm has multiple Compustat records in the same calendar year because of a
fiscal year-end change, the script keeps the most recent `datadate`.

The final file contains only:

- `permno`
- `permco`
- `gvkey`
- `datadate`
- `sic`
- `fyear`
- `operating_profitability`

## Run

```powershell
python build_operating_profitability.py
```

Optional output name:

```powershell
python build_operating_profitability.py --output ope.csv
```

By default, output is written to `outputs/operating_profitability.csv` in the
`Stock_Characters` folder.
