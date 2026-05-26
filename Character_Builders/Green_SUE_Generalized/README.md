# sue Character

Description: Unexpected quarterly earnings

Primary reference in the Green-style summary: Rendelman, Jones and Latane (1982).

Construction follows the Green SAS reference where the formula is available, while the panel timing follows this repository's `signal_yyyymm` / `target_yyyymm` convention.

Status: Scaffolded; this character requires a specialized event, IBES, quarterly, or factor-estimation routine before it can be used.

## Run

```powershell
python Character_Builders/Green_SUE_Generalized/build_sue.py --wrds-user YOUR_WRDS_USERNAME
```
