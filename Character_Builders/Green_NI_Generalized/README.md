# ni Character

Description: Net Stock Issues

Primary reference in the Green-style summary: Pontiff and Woodgate (2008).

Construction follows the Green SAS reference where the formula is available, while the panel timing follows this repository's `signal_yyyymm` / `target_yyyymm` convention.

Status: Scaffolded; this character requires a specialized event, IBES, quarterly, or factor-estimation routine before it can be used.

## Run

```powershell
python Character_Builders/Green_NI_Generalized/build_ni.py --wrds-user YOUR_WRDS_USERNAME
```
