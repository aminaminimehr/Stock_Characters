# rvar_ff3 Character

Description: Residual variance - ff3 rolling 3m

Primary reference in the Green-style summary: Daily Stock residual variance of Fama French 3 factors ().

Construction follows the Green SAS reference where the formula is available, while the panel timing follows this repository's `signal_yyyymm` / `target_yyyymm` convention.

Status: Scaffolded; this character requires a specialized event, IBES, quarterly, or factor-estimation routine before it can be used.

## Run

```powershell
python Character_Builders/Green_RVAR_FF3_Generalized/build_rvar_ff3.py --wrds-user YOUR_WRDS_USERNAME
```
