# maxret Character

Description: Maximum daily returns rolling 3m

Primary reference in the Green-style summary: Bali, Cakici and Whitelaw (2011).

Construction follows the Green SAS reference where the formula is available, while the panel timing follows this repository's `signal_yyyymm` / `target_yyyymm` convention.

Status: Implemented through the shared Green SAS builder.

## Run

```powershell
python Character_Builders/Green_MAXRET_Generalized/build_maxret.py --wrds-user YOUR_WRDS_USERNAME
```
