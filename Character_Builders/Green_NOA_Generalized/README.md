# noa Character

Description: (Changes in) Net Operating Assets

Primary reference in the Green-style summary: Hirshleifer, Hou, Teoh, and Zhang (2004).

Construction follows the Green SAS reference where the formula is available, while the panel timing follows this repository's `signal_yyyymm` / `target_yyyymm` convention.

Status: Implemented through the shared Green SAS builder.

## Run

```powershell
python Character_Builders/Green_NOA_Generalized/build_noa.py --wrds-user YOUR_WRDS_USERNAME
```
