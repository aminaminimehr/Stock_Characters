# rna Character

Description: Quarterly Return on Net Operating Assets, Quarterly Asset Turnover

Primary reference in the Green-style summary: Soliman (2008).

Construction follows the Green SAS reference where the formula is available, while the panel timing follows this repository's `signal_yyyymm` / `target_yyyymm` convention.

Status: Scaffolded; this character requires a specialized event, IBES, quarterly, or factor-estimation routine before it can be used.

## Run

```powershell
python Character_Builders/Green_RNA_Generalized/build_rna.py --wrds-user YOUR_WRDS_USERNAME
```
