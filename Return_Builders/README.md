# Return Builders

This folder contains builders for return-side variables used as prediction
targets.

## Excess Returns

`build_excess_returns.py` creates monthly CRSP excess returns with one row per
`permno` and return month.

The return month is stored as:

```text
target_yyyymm
```

This key is intentionally named to match the character panels. Character rows
are dated by `signal_yyyymm`, and their next-month return is identified by
`target_yyyymm`. To align features and targets, merge on:

```text
permno, target_yyyymm
```

The builder:

- uses CRSP monthly returns for common shares on NYSE, AMEX, and NASDAQ,
- adds CRSP delisting returns,
- subtracts the monthly risk-free rate from WRDS Fama-French monthly factors,
- writes `outputs/excess_returns.csv` by default.

## Run

```powershell
python Return_Builders/build_excess_returns.py --wrds-user YOUR_WRDS_USERNAME
```
