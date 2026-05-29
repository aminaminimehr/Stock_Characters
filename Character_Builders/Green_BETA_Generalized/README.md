# beta Character

Description: Beta rolling 3m

Primary reference in the Green-style summary: Fama and MacBeth (1973).

Construction follows the Green SAS reference where the formula is available, while the panel timing follows this repository's `signal_yyyymm` / `target_yyyymm` convention.

Status: Implemented via `_shared/beta_builder.py` (rolling 3-month daily CAPM beta).

## Run

```powershell
python Character_Builders/Green_BETA_Generalized/build_beta.py --wrds-user YOUR_WRDS_USERNAME
```
