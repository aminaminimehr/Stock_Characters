# Character Builders

This folder contains individual character builders from HXZ and Green-style sources.

Each character folder contains:

- one Python builder,
- one README documenting the definition and timing,
- raw annual output logic that keeps the actual Compustat `datadate`.

Current character folders:

- `HXZ_BM_Generalized`: book-to-market.
- `HXZ_BMJ_Generalized`: book-to-June-end market equity.
- `HXZ_OPE_Generalized`: operating-profitability-to-equity.
- `HXZ_CFP_Generalized`: cash-flow-to-price.
- `Green_MVEL1_Generalized`: monthly size, log lagged market equity.

The full Green-style target set and implementation status are tracked in
`CHARACTER_CATALOG.md`.
