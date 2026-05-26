# Roa1 Character

Description: Return on Assets

Primary reference in the Green-style summary: Balakrishnan, Bartov, and Faurel (2010).

Construction follows the Green SAS reference where the formula is available, while the panel timing follows this repository's `signal_yyyymm` / `target_yyyymm` convention.

Status: Scaffolded; this character requires a specialized event, IBES, quarterly, or factor-estimation routine before it can be used.

## Run

```powershell
python Character_Builders/Green_ROA1_Generalized/build_roa1.py --wrds-user YOUR_WRDS_USERNAME
```
