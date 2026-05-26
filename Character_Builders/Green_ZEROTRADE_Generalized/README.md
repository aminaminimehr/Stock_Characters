# zerotrade Character

Description: Number of zero-trading days rolling 3m

Primary reference in the Green-style summary: Liu (2006).

Construction follows the Green SAS reference where the formula is available, while the panel timing follows this repository's `signal_yyyymm` / `target_yyyymm` convention.

Status: Implemented through the shared Green SAS builder.

## Run

```powershell
python Character_Builders/Green_ZEROTRADE_Generalized/build_zerotrade.py --wrds-user YOUR_WRDS_USERNAME
```
