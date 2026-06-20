# Task 05 — CONFIGURATION.md + README flags section

**Priority:** High  
**Run on:** Local  
**Depends on:** Tasks 03, 04  

## Objective

Document every flag and profile for users. README stays short; full reference lives in
`docs/CONFIGURATION.md`.

## Create / update

### `docs/CONFIGURATION.md`

Sections:

1. **Profiles** (`green`, `datashare`, `research`) — table of what each sets
2. **CLI flags** — `run_full_pipeline.py`, `build_all_implemented_characters.py`, panel scripts
3. **Environment variables** — `WRDS_USER`, `PGPASSFILE`, `STOCK_CHARACTERS_WORKERS`, `RESUME`,
   `GREEN_UNIVERSE`, `STOCK_CHARACTERS_PROFILE`
4. **CCM linking** — `--ccm-linktypes`, `--ccm-linkprim`, Green vs HXZ defaults
5. **Timing** — Green rolling vs FF-June (which stems); quarterly note
6. **Universe** — Green joint screen vs datashare sparse panel
7. **Datashare column mapping** — bm, operprof, cfp only; bm_ia not replicated
8. **Examples** — three copy-paste command blocks

### `README.md`

Add section **Configuration** with:

- Link to `docs/CONFIGURATION.md`
- Quick profile examples (3 commands)
- Note: flags in README are summaries; full list in CONFIGURATION.md

## Do NOT

- Remove existing README mission/pipeline sections.

## Acceptance checks

Manual: a new user can find how to run `--profile datashare` from README alone.

## Codex prompt

```
Read codex/tasks/05_configuration_docs.md and pipeline_config.py (from task 03/04).

Write docs/CONFIGURATION.md with full profile and flag reference.
Update README.md with a Configuration section linking to it and three example commands
(green replication, datashare-like build, research panel).

Mention bm_ia is out of scope. Do not change builder code.
```
