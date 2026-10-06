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
| `end` | `sync-project.sh --all` → vault `git add -A` + commit `brain: session sync <ts>` + push → `qmd update` + `qmd embed` (logged to `~/.claude/logs/brain-sync.log`). ai-dotfiles is **not** committed — commit it yourself via `/git-commit`. |

The SessionEnd hook runs `sync.sh end` first, then warns if `inbox/daily/implementation/` has no note dated today. The warning goes to `~/.claude/logs/brain-sync-end.log` and the next SessionStart prints it as one `[last exit]` status line plus up to 5 warnings; the full log stays in `brain-sync-end.log.prev` — there is no systemMessage and no extra turn. A note written after that is committed at the next session's end. So write the session log with `/capture` *before* ending.

Failures never block the session: rebase conflict → `git rebase --abort`, stash restored, fix by hand in `$BRAIN_PATH`; push failure → commit stays local, `git push` later. Details: `reference/EDGE-CASES.md`.

**Config** — `BRAIN_PATH` (absolute path to the vault git repo) from the first of: `$BRAIN_ENV_FILE` · `brain.env` beside `sync.sh` · `~/ai-dotfiles/config/brain.env`. `QMD_INDEX_PATH` enables the reindex. Standalone use: copy `brain-sync/`, put `brain.env` (from `reference/brain.env.example`) beside the script.
