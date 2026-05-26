# bm_ia Character

Description: Industry-adjusted book to market

Primary reference in the Green-style summary: Asness, Porter and Stevens (2000).

Construction follows the Green SAS reference where the formula is available, while the panel timing follows this repository's `signal_yyyymm` / `target_yyyymm` convention.

Status: Implemented through the shared Green SAS builder.

## Run

```powershell
python Character_Builders/Green_BM_IA_Generalized/build_bm_ia.py --wrds-user YOUR_WRDS_USERNAME
```
