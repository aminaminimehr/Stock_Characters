# Codex Agent Task Pack — Stock Characters Repository

This folder is your **control center for delegating work to Codex** (or any coding agent).
Each file in `codex/tasks/` is a **self-contained job** with objective, constraints, acceptance
criteria, and the exact prompt to paste into Codex.

You do **not** need to understand “agentic programming” deeply. Think of it as:

1. Pick **one task** from `TASK_INDEX.md` (in order unless noted).
2. Open the task file (e.g. `tasks/03_pipeline_presets.md`).
3. Copy the **Codex prompt** block at the bottom into Codex.
4. Let Codex work; review the diff; run acceptance checks; commit.
5. Move to the next task.

---

## What is “agentic” here?

An **agent** (Codex, Cursor Agent, etc.) is an AI that can:

- read many files in your repo,
- run terminal commands,
- edit code,
- iterate until a goal is met.

**Agentic programming** means you give a **written specification** (the task file) instead of typing
every edit yourself. The agent explores the codebase and implements the spec.

**Skills** (in Cursor) are reusable instruction files the agent reads automatically. **This repo does
not require Cursor skills** — the task files here *are* the skills for Codex. If you later use Cursor
Agent on the same repo, you can point it at `codex/tasks/NN_*.md` the same way.

---

## Codex vs Cursor vs you

| Who | Role |
|---|---|
| **You** | Choose task, paste prompt, approve changes, run WRDS jobs on server, `git push` |
| **Codex (local or cloud)** | Implement one task file: code, docs, moves, tests |
| **Server (WRDS machine)** | Long pipeline runs (`run_full_pipeline.sh`), 8+ GB RAM, hours of runtime |

**Rule:** Codex should do **one task at a time**. Do not paste the whole index into one prompt — tasks
have dependencies and you need to review between steps.

---

## Where to run Codex

- **Local Windows machine:** good for cleanup, docs, config code, small scripts. **No WRDS** unless
  you have credentials in `pytorch_env` / `aa_env`.
- **Linux server (`ycq-ThinkStation`):** required for full pipeline rebuilds and datashare universe
  validation against WRDS.

For server tasks, either:

- SSH in and run Codex there, **or**
- Implement on Windows, `git push`, `git pull` on server, then run the **Acceptance commands** from
  the task file manually.

---

## Standard workflow (every task)

```
1. Read codex/TASK_INDEX.md → pick next OPEN task
2. Open codex/tasks/NN_....md
3. Copy "Codex prompt" → paste into Codex
4. Review diff (git diff). Reject unrelated changes.
5. Run "Acceptance checks" from the task file
6. git add … && git commit -m "…"   (you or Codex, if you asked)
7. Mark task done in TASK_INDEX.md (optional checkbox)
8. Next task
```

---

## Repository goals (context for every agent)

1. **Primary:** replicate Green's SAS character library (`Output_From_Greens_SAS_code.sas7bdat`).
2. **Secondary:** match `datashare.csv` for **`bm`, `operprof`, `cfp`** (universe + formula), using
   existing builders — **not** a separate GKX `accounting_60` port.
3. **`bm_ia`:** **out of scope** (explicitly abandoned).
4. **Configuration:** datashare-like behavior must be a **preset/flag**, not hard-coded. Users who
   want Green-only or research panels change flags, not formulas.
5. **Do not rewrite** working Green character formulas unless the task explicitly says so.

Authoritative docs: `docs/methodology/`. Historical audits: `docs/gkx/` (to be archived in task 01).

---

## Folder layout

```
codex/
  README.md                 ← you are here
  TASK_INDEX.md             ← ordered checklist + dependencies
  PROMPT_TIPS.md            ← how to write good prompts, fix bad runs
  tasks/
    01_archive_docs.md
    02_reorganize_scripts.md
    03_pipeline_presets.md
    04_wire_presets_pipeline.md
    05_configuration_docs.md
    06_datashare_universe_validation.md
    07_extend_cfp_history.md
    08_cleanup_experimental_paths.md
    09_server_run_and_report.md
    10_push_and_release.md
```

---

## Quick start (if you only do three things)

1. **Task 03 + 04** — add `--profile green|datashare|research` so behavior is configurable.
2. **Task 06** — prove permno/universe match for `bm` / `operprof` / `cfp` vs datashare.
3. **Task 01 + 02** — archive clutter so the repo is readable.

Then task 09 on the server and task 10 to update the remote repo.
