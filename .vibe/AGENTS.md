# Local Brain bootstrap

**Canonical copy:** this file lives in **`.vibe/AGENTS.md`**. A symlink **`AGENTS.md`** at the repo root ensures Vibe can discover it.

Vibe does **not** auto-run shell. Follow this **before your first substantive action** when the task involves the Local Brain vault or a codebase whose context should be loaded.

## 1. Sync and load

```bash
bash ~/ai-dotfiles/skills/brain-sync/sync.sh start
bash ~/ai-dotfiles/skills/brain-load/load.sh
```

- If `sync.sh start` fails (permissions, network), warn the user and continue; do not claim a rebase conflict when it was a permission error.
- If `load.sh` exits **2** with `PROJECT_NOTE_MISSING`, follow **`skills/brain-load/SKILL.md`** (`para_missing` → ask CAP, `instantiate.sh`, re-run; `legacy_missing` → offer brief template).

## 2. Optional: load full skill text

Use the **`skill`** tool (`name`: `brain-sync` / `brain-load`) or slash commands `/brain-sync` / `/brain-load`.

## 3. Session end

```bash
bash ~/ai-dotfiles/skills/brain-sync/sync.sh end
```
