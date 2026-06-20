# Prompt tips for Codex (beginner-friendly)

## The golden rule

**One task file = one Codex session.** Finish, review, commit, then start the next.

Bad:

> "Clean up the repo, add presets, validate datashare, and push to GitHub."

Good:

> Open `codex/tasks/03_pipeline_presets.md`, copy the prompt block, paste into Codex.

---

## What to attach in Codex

When Codex asks for context or you start a new chat, attach or @-mention:

| Always | Sometimes |
|--------|-----------|
| The task file (`codex/tasks/NN_....md`) | Output of acceptance command if debugging |
| `README.md` | One failing log from server |
| `docs/methodology/00_overview.md` | `docs/gkx/datashare_universe_comparison.md` for universe tasks |

Do **not** attach all of `docs/gkx/` (50 files) — use the task file + methodology docs only.

---

## If Codex goes off track

Say explicitly:

```
Stop. Re-read codex/tasks/03_pipeline_presets.md.
Do NOT change Green builder formulas.
Only implement what the task file lists under "Scope".
Revert any unrelated file changes.
```

---

## If Codex cannot run WRDS

Tasks 07 and 09 need the server. Codex on Windows should:

1. Implement the **script/code** locally.
2. Document exact server commands in the task's acceptance section.
3. You SSH to the server, `git pull`, run commands, paste log back if something fails.

---

## Review checklist before you commit

- [ ] Diff is limited to files listed in the task **Scope**
- [ ] No credentials in committed files
- [ ] No changes to Green formulas (unless task 07 cfp **start date** only)
- [ ] Acceptance commands pass (or server steps documented)
- [ ] README / CONFIGURATION updated if flags changed

---

## Git (you stay in control)

Codex may offer to commit. **You** decide when to push to the remote.

Typical sequence after task 09:

```bash
git status
git add -A
git commit -m "Add pipeline profiles and archive audit docs"
git push origin YOUR_BRANCH
```

Use a branch + PR if others review; push to `main` only if that is your team norm.
