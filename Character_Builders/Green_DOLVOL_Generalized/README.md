# dolvol Character

Description: Dollar trading volume

Primary reference in the Green-style summary: Chordia, Subrahmanyam and Anshuman (2001).

Construction follows the Green SAS reference where the formula is available, while the panel timing follows this repository's `signal_yyyymm` / `target_yyyymm` convention.

Status: Implemented through the shared Green SAS builder.

## Run

```powershell
python Character_Builders/Green_DOLVOL_Generalized/build_dolvol.py --wrds-user YOUR_WRDS_USERNAME
```
