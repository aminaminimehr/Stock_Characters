# Mvel1 Size Character

This folder contains the monthly `mvel1` size character.

## Character Definition

`mvel1` is the natural log of lagged CRSP market equity:

```text
mvel1_t = log(abs(PRC_{t-1}) * SHROUT_{t-1})
```

where `PRC` and `SHROUT` are from CRSP monthly data. The construction keeps
common shares only (`SHRCD` 10 and 11) on NYSE, AMEX, and NASDAQ (`EXCHCD` 1, 2,
and 3).

This follows the size-character convention used in the empirical
asset-pricing predictor literature and is related to Banz's market-value size
effect.

## Timing

This is a monthly CRSP characteristic, not an annual accounting characteristic.
The value for month `t` uses market equity from month `t - 1`, so it is already
lagged by one month.

The output keeps timing explicit:

- `source_yyyymm`: month used to measure market equity.
- `signal_yyyymm`: predictor month where the characteristic is placed.
- `target_yyyymm`: next-month return month, equal to `signal_yyyymm + 1`.

For prediction, align characteristics on `signal_yyyymm` and align the dependent
return with `target_yyyymm`, or create a one-month-ahead return from the return
file.

## Output

The final file contains:

- `permno`
- `permco`
- `source_date`
- `source_yyyymm`
- `date`
- `signal_yyyymm`
- `target_yyyymm`
- `sic`
- `exchcd`
- `shrcd`
- `lagged_market_equity`
- `mvel1`

By default, output is written to `outputs/mvel1.csv` in the `Stock_Characters`
folder.

## Run

```powershell
python Character_Builders/Green_MVEL1_Generalized/build_mvel1.py --wrds-user YOUR_WRDS_USERNAME
```

Optional market-equity imputation:

```powershell
python Character_Builders/Green_MVEL1_Generalized/build_mvel1.py --wrds-user YOUR_WRDS_USERNAME --use-imputed-market-equity
```
