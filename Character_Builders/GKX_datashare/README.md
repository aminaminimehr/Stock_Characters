# GKX_datashare — experimental (not production)

**Status: rejected for this `datashare.csv`.**

Reverse-engineering (`docs/gkx/datashare_reverse_engineering.md`) showed the local datashare file
matches:

- `book_to_market` (HXZ) for `bm`
- `operating_profitability` (HXZ) for `operprof`
- Green `cfp` for `cfp`

The GKX `accounting_60.py` port in this folder (`be/me`, `(ib+dp)/me`, FF49 `bm_ia`) does **not**
match (e.g. `cfp` ρ ≈ −0.02).

## Do not use in pipeline

Use `--profile datashare` and the existing HXZ/Green builders instead. See `docs/CONFIGURATION.md`.

Files kept for historical reference:

- `build_datashare_chars.py`
- `validate_against_datashare.py`
