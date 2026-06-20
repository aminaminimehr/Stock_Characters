# Getting started with Codex (5 minutes)

You said you are new to agentic programming. This is the shortest path.

---

## Step 0 — What you are doing

You will **not** code everything yourself. You will **assign jobs** to Codex using ready-made job
descriptions in `codex/tasks/`.

Each job description includes a gray box at the bottom: **"Codex prompt"**. Copy that box into Codex.

---

## Step 1 — Open Codex

Use whichever Codex interface you have (ChatGPT Codex, OpenAI Codex CLI, GitHub Copilot workspace,
etc.). The exact UI differs, but all support:

- pasting a long instruction,
- attaching a folder or repo,
- letting the agent edit files and run commands.

**Point Codex at this repository folder** on your machine:

`D:\Asset Pricing Researh Project With Dr. Guo and Dr. Yichen\Creating_the_non_matching_characters_Amin\Stock_Characters`

---

## Step 2 — Start with Task 01 (safest)

1. Open `codex/TASK_INDEX.md` — see the numbered list.
2. Open `codex/tasks/01_archive_docs.md`.
3. Scroll to **Codex prompt**.
4. Select all text inside the prompt block (from "You are working..." to the end).
5. Paste into Codex.
6. Press Enter / Run.

Codex will move docs and show you a diff. **You review** before saving or committing.

---

## Step 3 — Review like a manager

Ask yourself:

- Did it only touch files listed in the task?
- Did it avoid changing `green_builders.py` formulas?

If Codex changed too much, say:

> Revert unrelated changes. Follow codex/tasks/01_archive_docs.md scope only.

---

## Step 4 — Run acceptance checks

Each task file has an **Acceptance checks** section with terminal commands.

On Windows PowerShell, from repo root:

```powershell
cd "D:\Asset Pricing Researh Project With Dr. Guo and Dr. Yichen\Creating_the_non_matching_characters_Amin\Stock_Characters"
# paste commands from the task file
```

If checks pass, commit:

```powershell
git add -A
git commit -m "Archive historical GKX docs (codex task 01)"
```

---

## Step 5 — Repeat for the next task

Order matters. After 01, do **03 and 04** (profiles) before **09** (server run).

| If you want… | Do tasks… |
|--------------|-----------|
| Less clutter | 01, 02, 08 |
| Configurable datashare vs Green | 03, 04, 05 |
| Prove permno universe matches | 06, then 09 on server |
| Update GitHub | 10 |

---

## Step 6 — Server tasks (07, 09)

Your WRDS server cannot be driven from Windows Codex unless Codex runs **on that machine**.

**Pattern:**

1. Codex on Windows implements scripts + docs (tasks 03–06).
2. You `git push` from Windows.
3. SSH to server, `git pull`.
4. Run commands from `codex/tasks/09_server_run_and_report.md`.
5. If something fails, paste the log back into Codex with: "Task 09 failed; here is the log."

---

## Step 7 — What NOT to do

- Do not paste all 10 tasks into one Codex message.
- Do not ask Codex to "rewrite the whole repo."
- Do not skip reviewing diffs.
- Do not push secrets (WRDS passwords).

---

## Where to read more

- `codex/README.md` — full overview
- `codex/PROMPT_TIPS.md` — fixing bad runs
- `docs/CONFIGURATION.md` — created in task 05 (flags reference)

---

## Example: your first Codex message (Task 03)

If you want to jump to the important config work after task 01:

```
Read codex/tasks/03_pipeline_presets.md and docs/methodology/00_overview.md.

Implement pipeline_config.py with profiles green, datashare, and research.
Datashare profile: 1957+ sample, no green-universe screen, sparse panel behavior,
maps bm/operprof/cfp to existing HXZ/Green columns. bm_ia out of scope.
Do NOT change character formulas.
```

That is the entire "agentic" workflow: **spec file → paste → review → commit → next spec file.**
