# nincr Character

Description: Number of earnings increases

Primary reference in the Green-style summary: Barth, Elliott and Finn (1999).

Construction follows the Green SAS reference where the formula is available, while the panel timing follows this repository's `signal_yyyymm` / `target_yyyymm` convention.

Status: Scaffolded; this character requires a specialized event, IBES, quarterly, or factor-estimation routine before it can be used.

## Run

```powershell
python Character_Builders/Green_NINCR_Generalized/build_nincr.py --wrds-user YOUR_WRDS_USERNAME
```
