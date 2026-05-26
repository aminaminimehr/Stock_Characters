# seas1a Character

Description: Seasonality

Primary reference in the Green-style summary: Heston and Sadka (2008).

Construction follows the Green SAS reference where the formula is available, while the panel timing follows this repository's `signal_yyyymm` / `target_yyyymm` convention.

Status: Scaffolded; this character requires a specialized event, IBES, quarterly, or factor-estimation routine before it can be used.

## Run

```powershell
python Character_Builders/Green_SEAS1A_Generalized/build_seas1a.py --wrds-user YOUR_WRDS_USERNAME
```
