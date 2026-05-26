# chpm Character

Description: Industry-adjusted change in profit margin

Primary reference in the Green-style summary: Soliman (2008).

Construction follows the Green SAS reference where the formula is available, while the panel timing follows this repository's `signal_yyyymm` / `target_yyyymm` convention.

Status: Implemented through the shared Green SAS builder.

## Run

```powershell
python Character_Builders/Green_CHPM_Generalized/build_chpm.py --wrds-user YOUR_WRDS_USERNAME
```
