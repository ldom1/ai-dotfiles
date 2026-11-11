# Vibe bootstrap (Local Brain)

Vibe has no session-start hook. Read `~/.vibe/brain-context.md` only if it exists and its first line is `cwd: <your working directory>`. Then skip the manual sync and load below: the `vibe-brain` launcher ran `sync.sh start` and will run `sync.sh end`. Otherwise, before your first substantive action on a codebase or on the vault:

```bash
bash ~/ai-dotfiles/skills/brain-sync/scripts/sync.sh start
bash ~/ai-dotfiles/skills/brain-load/scripts/load.sh
```

- If `sync.sh start` fails, warn the user and continue. Do not call a permission error a rebase conflict.
- If `load.sh` exits 2 with `PROJECT_NOTE_MISSING`, follow `skills/brain-load/SKILL.md`.
- At session end, if you ran the sync and load yourself: `bash ~/ai-dotfiles/skills/brain-sync/scripts/sync.sh end`.
