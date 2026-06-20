# Task 04 — Wire presets into `run_full_pipeline.py`

**Priority:** High  
**Run on:** Local  
**Depends on:** Task 03  

## Objective

Connect `pipeline_config.py` to the production entry points:

- `Character_Panels/run_full_pipeline.py`
- `run_full_pipeline.sh` / `run_full_pipeline.ps1`
- `Character_Builders/build_all_implemented_characters.py` (forward CCM + sample args)
- `Character_Panels/build_all_character_panel.py` (universe screen, timing flags)

## Behavior

```bash
python Character_Panels/run_full_pipeline.py --wrds-user USER --profile datashare
python Character_Panels/run_full_pipeline.py --wrds-user USER --profile green --green-universe
```

Environment variable optional: `STOCK_CHARACTERS_PROFILE=datashare`

When `--profile datashare`:
- Pass `--sample-start 1957-01-01` to builders if not overridden
- Do **not** pass `--green-universe` unless user also passes it
- Still build HXZ quartet needed for datashare mapping

When `--profile green`:
- Default CCM to Green linking in character builder
- `--green-universe` remains opt-in

## Do NOT

- Break existing invocations without `--profile` (default = `green` or document breaking change in README).

## Acceptance checks

```bash
python Character_Panels/run_full_pipeline.py --help
# Must show --profile green|datashare|research

python Character_Panels/run_full_pipeline.py --wrds-user test --skip-build --profile datashare --help
```

Dry-run: `--skip-build` should not error on config resolution.

## Codex prompt

```
Read codex/tasks/04_wire_presets_pipeline.md and implement pipeline_config integration.

Wire --profile into run_full_pipeline.py, shell scripts, build_all_implemented_characters.py,
and build_all_character_panel.py so profile datashare sets 1957+ sample, no green-universe,
and forwards CCM flags.

Default profile should preserve current behavior for existing users (green).
Update run_full_pipeline.sh and .ps1 to pass STOCK_CHARACTERS_PROFILE if set.

Do NOT change character formulas. Run --help acceptance checks.
```
