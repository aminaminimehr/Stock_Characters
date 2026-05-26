# abr Character

Description: cumulative abnormal returns around earnings announcement dates

Primary reference in the Green-style summary: Chan, Jegadeesh, and Lakonishok (1996).

Construction follows the Green SAS reference where the formula is available, while the panel timing follows this repository's `signal_yyyymm` / `target_yyyymm` convention.

Status: Scaffolded; this character requires a specialized event, IBES, quarterly, or factor-estimation routine before it can be used.

## Run

```powershell
python Character_Builders/Green_ABR_Generalized/build_abr.py --wrds-user YOUR_WRDS_USERNAME
```
