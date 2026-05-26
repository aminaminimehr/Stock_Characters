# chcsho Character

Description: Change in shares outstanding

Primary reference in the Green-style summary: Pontiff and Woodgate (2008).

Construction follows the Green SAS reference where the formula is available, while the panel timing follows this repository's `signal_yyyymm` / `target_yyyymm` convention.

Status: Implemented through the shared Green SAS builder.

## Run

```powershell
python Character_Builders/Green_CHCSHO_Generalized/build_chcsho.py --wrds-user YOUR_WRDS_USERNAME
```
