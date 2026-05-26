# rvar_mean Character

Description: return variance rolling 3m

Primary reference in the Green-style summary: Daily Stock return variance ().

Construction follows the Green SAS reference where the formula is available, while the panel timing follows this repository's `signal_yyyymm` / `target_yyyymm` convention.

Status: Implemented through the shared Green SAS builder.

## Run

```powershell
python Character_Builders/Green_RVAR_MEAN_Generalized/build_rvar_mean.py --wrds-user YOUR_WRDS_USERNAME
```
