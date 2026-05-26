# sgr Character

Description: Sales growth

Primary reference in the Green-style summary: Lakonishok, Shleifer and Vishny (1994).

Construction follows the Green SAS reference where the formula is available, while the panel timing follows this repository's `signal_yyyymm` / `target_yyyymm` convention.

Status: Implemented through the shared Green SAS builder.

## Run

```powershell
python Character_Builders/Green_SGR_Generalized/build_sgr.py --wrds-user YOUR_WRDS_USERNAME
```
