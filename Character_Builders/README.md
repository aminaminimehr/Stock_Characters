# Character Builders

This folder contains individual character builders from HXZ and Green-style sources.

Each character folder contains:

- one Python builder,
- one README documenting the definition and timing,
- raw annual output logic that keeps the actual Compustat `datadate`.

To build every currently implemented Green-style character in one run:

```powershell
python Character_Builders/build_all_implemented_characters.py --wrds-user YOUR_WRDS_USERNAME
```

Use `--only-daily` to rebuild only the daily-CRSP based monthly characters, or
`--skip-daily` to skip that slower block.

Accounting builders use the repository CCM default:

```text
linktype in ('LU', 'LC')
linkprim in ('P', 'C')
```

Override it with `--ccm-linktypes` and `--ccm-linkprim` when a replication
requires a different CRSP/Compustat linking convention.

Current HXZ character folders (datashare production):

- `HXZ_BM_Generalized`: book-to-market (`datashare.bm`).
- `HXZ_OPE_Generalized`: operating profitability (`datashare.operprof`).

Datashare profile (`--profile datashare`) writes only the 95 mapped predictors; see
`pipeline_config.datashare_output_columns()` and `CHARACTER_CATALOG.md`.
