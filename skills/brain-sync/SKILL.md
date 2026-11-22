---
name: brain-sync
description: Sync the Local Brain Obsidian vault (git repo). Claude Code SessionStart/End and Cursor Agent CLI (default) run this automatically; Cursor IDE Agent must not auto-run it — only on explicit user request or /brain-sync.
user-invocable: true
---

# brain-sync

Git sync for the vault. Claude Code hooks (`.claude/hooks/brain-session-{start,end}.sh`) and Cursor Agent CLI hooks run it automatically (`BRAIN_AGENT_HOOKS=0` turns the CLI hooks off), so don't re-run it in a hooked session unless the user asks or a hook failed. Cursor IDE Agent: only on explicit request or `/brain-sync`, since its hooks are off by design. Mistral Vibe: `/brain-sync` loads this skill; the script still needs a bash step.

```bash
bash ~/ai-dotfiles/skills/brain-sync/scripts/sync.sh start   # pull
bash ~/ai-dotfiles/skills/brain-sync/scripts/sync.sh end     # commit + push vault
```

| Command | Does |
|---|---|
| `start` | Vault and ai-dotfiles: stash tracked changes → `git pull --rebase origin <branch>` (3 tries) → pop. Then `scripts/sync-project.sh --all` (rsync `.claude/memory/` ↔ `projects/<slug>/` for repos in `config/brain-projects.tsv`). |
| `end` | `sync-project.sh --all` → vault `git add -A` + commit `brain: session sync <ts>` + push → `qmd update` + `qmd embed`, detached and locked by `flock` on `${XDG_CACHE_HOME:-~/.cache}/qmd-brain.lock` (a second session end logs `qmd embed already running` and skips; logged to `~/.claude/logs/brain-sync.log`). Without `flock` (stock macOS) it logs `no flock` and runs unlocked: `brew install util-linux`. The commit is skipped with a warning during a rebase or on a detached HEAD. ai-dotfiles is **not** committed — commit it yourself via `/git-commit`. |

The SessionEnd hook runs `harness-metrics` first, then `sync.sh end`, then warns if `inbox/daily/implementation/` has no note dated today. The warning goes to `~/.claude/logs/brain-sync-end.log` and the next SessionStart prints it as one `[last exit]` status line plus up to 5 warnings; the full log stays in `brain-sync-end.log.prev` — there is no systemMessage and no extra turn. A note written after that is committed at the next session's end. So write the session log with `/capture` *before* ending.

Failures never block the session: rebase conflict → `git rebase --abort`, stash restored, fix by hand in `$BRAIN_PATH`; push failure → commit stays local, `git push` later. Details: `reference/EDGE-CASES.md`.

**Config** — `BRAIN_PATH` (absolute path to the vault git repo) from the first of: `$BRAIN_ENV_FILE` · `brain.env` beside `sync.sh` · `~/ai-dotfiles/config/brain.env`. `QMD_INDEX_PATH` enables the reindex. Standalone use: copy `brain-sync/`, put `brain.env` (from `reference/brain.env.example`) beside the script.

## Dev-project targets (Notion)

The notion-pilot Telegram bot can offer a dev project as a target after a capture ("à tester pour ai-dotfiles"). It reads the targets from a Notion database. Two scripts here keep that database in line with the vault. They need `NOTION_TOKEN` from the notion-pilot Infisical project (env `prod`).

| Script | Does |
|---|---|
| `scripts/setup_capture_targets.py` | One-off, idempotent. Creates the targets database `Projets dev` (`Nom`, `Slug`, `Résumé`, `Actif`), the capture relation `Cible` (reverse `Captures`), the checkbox `Veille cible faite`, the relation Laboratoire `Projet` → Projects (reverse `Idée d'origine`) and two rollups on Projects. Without `--apply` it prints the missing pieces only. |
| `scripts/sync_dev_projects.py` | Upserts one row per `$BRAIN_PATH/projects/*.md`, keyed by `Slug` (the filename). `Actif` follows `status: active`. It never deletes a row. It unchecks `Actif` for an absent project only after a scan that read every file. It logs and skips a malformed note. `--dry-run` prints the counts only. |

Run the sync by hand after you create a project during the day:

```bash
cd ~/lab/notion-pilot && infisical run --env=prod --silent -- \
  ~/ai-dotfiles/skills/brain-sync/scripts/sync_dev_projects.py
```

Daily run: link and start the timer once.

```bash
ln -s ~/ai-dotfiles/skills/brain-sync/systemd/sync-dev-projects.{service,timer} ~/.config/systemd/user/
systemctl --user daemon-reload && systemctl --user enable --now sync-dev-projects.timer
```

A renamed note is a new project: the old row is unchecked and keeps its links. `veille-technique` on the new slug does not see captures targeted before the rename.
