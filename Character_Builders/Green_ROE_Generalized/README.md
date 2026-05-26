# roe Character

Description: Return on Equity

Primary reference in the Green-style summary: Hou, Xue, and Zhang (2015).

Construction follows the Green SAS reference where the formula is available, while the panel timing follows this repository's `signal_yyyymm` / `target_yyyymm` convention.

Status: Implemented through the shared Green SAS builder.

## Run

```powershell
python Character_Builders/Green_ROE_Generalized/build_roe.py --wrds-user YOUR_WRDS_USERNAME
```
