# rvar_mean Character

Description: daily return volatility from the previous month

The Green SAS output column is `retvol` and is computed as the within-month
standard deviation of daily returns. The local output column remains
`rvar_mean` for compatibility with the repository's Green-style acronym list.

Construction follows the Green SAS reference where the formula is available, while the panel timing follows this repository's `signal_yyyymm` / `target_yyyymm` convention.

Status: Implemented through the shared Green SAS builder.

## Run

```powershell
python Character_Builders/Green_RVAR_MEAN_Generalized/build_rvar_mean.py --wrds-user YOUR_WRDS_USERNAME
```
