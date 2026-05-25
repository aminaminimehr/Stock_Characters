# Book-to-Market Character

This folder contains the book-to-market character construction following the
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

So when merging with returns, the clean approach is to create an availability
date, such as June 30 of `datadate.year + 1`, and merge future returns after that
date. Conceptually, this moves the character forward to the date when it is
tradable. Avoid treating the raw `datadate` as directly predictive of returns in
the same calendar year.

## Character Definition

For each firm-year:

- Book equity comes from Compustat.
- Market equity comes from CRSP December market equity in the same calendar year
  as the Compustat `datadate`.
- If a firm has multiple Compustat records in the same calendar year because of a
  fiscal year-end change, the script keeps the most recent `datadate`.

The final file contains only:

- `permno`
- `permco`
- `gvkey`
- `datadate`
- `sic`
- `fyear`
- `book_to_market`

## CRSP Market Equity Imputation

By default, the script uses the exact CRSP monthly `prc` and `shrout` values.

To allow older monthly values to fill missing price or shares outstanding within
the same `permno`, run:

```powershell
python build_book_to_market.py --use-imputed-market-equity
```

The script prints whether this imputation option was used.

## Run

```powershell
python build_book_to_market.py
```

Optional output name:

```powershell
python build_book_to_market.py --output bm.csv
```

By default, output is written to `outputs/book_to_market.csv` in the
`Stock_Characters` folder.
