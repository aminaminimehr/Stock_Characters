# depr Character

Description: Depreciation / PPandE

Primary reference in the Green-style summary: Holthausen and Larcker (1992).

Construction follows the Green SAS reference where the formula is available, while the panel timing follows this repository's `signal_yyyymm` / `target_yyyymm` convention.

Status: Implemented through the shared Green SAS builder.

## Run

```powershell
python Character_Builders/Green_DEPR_Generalized/build_depr.py --wrds-user YOUR_WRDS_USERNAME
```
