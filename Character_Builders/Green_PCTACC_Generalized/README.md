# pctacc Character

Description: Percent operating accruals

Primary reference in the Green-style summary: Hafzalla, Lundholm, and Van Winkle (2011).

Construction follows the Green SAS reference where the formula is available, while the panel timing follows this repository's `signal_yyyymm` / `target_yyyymm` convention.

Status: Implemented through the shared Green SAS builder.

## Run

```powershell
python Character_Builders/Green_PCTACC_Generalized/build_pctacc.py --wrds-user YOUR_WRDS_USERNAME
```
