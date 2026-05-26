# Bmj Book-to-June-End Market Equity

This folder contains the HXZ `Bmj` character, book-to-June-end market equity.

## Character Definition

Following the HXZ testing-portfolio documentation, for June of year `t`:

```text
Bmj = split-adjusted book equity per share / CRSP June-end price
```

where book equity comes from the fiscal year ending in calendar year `t - 1`.
Book equity is constructed using the Davis-Fama-French book-equity convention:
stockholders' equity plus `TXDITC`, minus preferred stock. Preferred stock uses
`PSTKRV`, then `PSTKL`, then `PSTK`.

Book equity per share is:

```text
book_equity / CSHO
```

The script adjusts book equity per share for stock splits between the fiscal
year-end and June using CRSP `CFACPR`:

```text
book_equity_per_share_june_basis =
    book_equity_per_share * CFACPR_june / CFACPR_fiscal_year_end
```

Then:

```text
bmj = book_equity_per_share_june_basis / abs(PRC_june)
```

Firms with nonpositive book equity are excluded.

## Timing

The raw output keeps the actual Compustat `datadate`. For a fiscal year ending
in calendar year `y`, this signal is formed at the end of June `y + 1` and is
used for July `y + 1` through June `y + 2` returns.

For the repository's monthly prediction panel, this corresponds to
`signal_yyyymm = June y+1` and `target_yyyymm = July y+1` for the first return
month.

## Output

The output contains:

- `permno`
- `permco`
- `gvkey`
- `datadate`
- `sic`
- `fyear`
- `june_date`
- `book_equity_per_share`
- `split_adjustment`
- `june_price`
- `bmj`

By default, output is written to `outputs/book_to_june_market_equity.csv`.

## Run

```powershell
python Character_Builders/HXZ_BMJ_Generalized/build_book_to_june_market_equity.py --wrds-user YOUR_WRDS_USERNAME
```
