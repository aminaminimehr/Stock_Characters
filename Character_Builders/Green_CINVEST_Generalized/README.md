# cinvest Character

Description: Corporate investment

Primary reference in the Green-style summary: Titman, Wei and Xie (2004).

Construction follows the Green SAS reference where the formula is available, while the panel timing follows this repository's `signal_yyyymm` / `target_yyyymm` convention.

Status: Scaffolded; this character requires a specialized event, IBES, quarterly, or factor-estimation routine before it can be used.

## Run

```powershell
python Character_Builders/Green_CINVEST_Generalized/build_cinvest.py --wrds-user YOUR_WRDS_USERNAME
```
