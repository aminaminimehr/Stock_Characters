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

Current HXZ character folders:

- `HXZ_BM_Generalized`: book-to-market.
- `HXZ_BMJ_Generalized`: book-to-June-end market equity.
- `HXZ_OPE_Generalized`: operating-profitability-to-equity.
- `HXZ_CFP_Generalized`: cash-flow-to-price.

The full Green-style target set and implementation status are tracked in
`CHARACTER_CATALOG.md`.
