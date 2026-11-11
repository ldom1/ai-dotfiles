# Vibe bootstrap (Local Brain)

Vibe has no session-start hook. If `~/.vibe/brain-context.md` is less than 12 h old, read it and skip the manual sync and load below. The `vibe-brain` launcher wrote it after `sync.sh start`. Otherwise, before your first substantive action on a codebase or on the vault:

```bash
bash ~/ai-dotfiles/skills/brain-sync/scripts/sync.sh start
bash ~/ai-dotfiles/skills/brain-load/scripts/load.sh
```

- If `sync.sh start` fails, warn the user and continue. Do not call a permission error a rebase conflict.
- If `load.sh` exits 2 with `PROJECT_NOTE_MISSING`, follow `skills/brain-load/SKILL.md`.
- At session end: `bash ~/ai-dotfiles/skills/brain-sync/scripts/sync.sh end`, unless `vibe-brain` launched you (it runs `sync.sh end` itself).
