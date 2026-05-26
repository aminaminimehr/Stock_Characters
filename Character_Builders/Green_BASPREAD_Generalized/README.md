# baspread Character

Description: Bid-ask spread rolling 3m

Primary reference in the Green-style summary: Amihud and Mendelson (1989).

Construction follows the Green SAS reference where the formula is available, while the panel timing follows this repository's `signal_yyyymm` / `target_yyyymm` convention.

Status: Implemented through the shared Green SAS builder.

## Run

```powershell
python Character_Builders/Green_BASPREAD_Generalized/build_baspread.py --wrds-user YOUR_WRDS_USERNAME
```
