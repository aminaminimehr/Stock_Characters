# std_turn Character

Description: Std. of Share turnover rolling 3m

Primary reference in the Green-style summary: Chordia, Subrahmanyam, andAnshuman (2001).

Construction follows the Green SAS reference where the formula is available, while the panel timing follows this repository's `signal_yyyymm` / `target_yyyymm` convention.

Status: Implemented through the shared Green SAS builder.

## Run

```powershell
python Character_Builders/Green_STD_TURN_Generalized/build_std_turn.py --wrds-user YOUR_WRDS_USERNAME
```
