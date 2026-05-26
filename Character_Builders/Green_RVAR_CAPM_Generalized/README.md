# rvar_capm Character

Description: Residual variance - CAPM rolling 3m

Primary reference in the Green-style summary: Daily Stock residual variance of CAPM ().

Construction follows the Green SAS reference where the formula is available, while the panel timing follows this repository's `signal_yyyymm` / `target_yyyymm` convention.

Status: Scaffolded; this character requires a specialized event, IBES, quarterly, or factor-estimation routine before it can be used.

## Run

```powershell
python Character_Builders/Green_RVAR_CAPM_Generalized/build_rvar_capm.py --wrds-user YOUR_WRDS_USERNAME
```
