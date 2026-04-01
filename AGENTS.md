# Local Brain bootstrap (ai-dotfiles)

Mistral Vibe does **not** run shell commands automatically when a session opens (unlike Cursor always-on rules). Follow this **before your first substantive action** when the task involves this repo, the Local Brain vault, or a codebase whose context should be loaded from the vault.

## 1. Sync and load (bash)

From the **git root** of the codebase you are working in, run:

```bash
bash ~/ai-dotfiles/skills/brain-sync/sync.sh start
bash ~/ai-dotfiles/skills/brain-load/load.sh
```

If the clone is not at `~/ai-dotfiles`, use the real path to `skills/brain-sync/sync.sh` and `skills/brain-load/load.sh` inside that clone.

- If `sync.sh start` fails (permissions, network), warn the user and continue if appropriate; do not claim a rebase conflict when it was a permission error.
- If `load.sh` exits **2** and stderr contains `PROJECT_NOTE_MISSING`, follow **`skills/brain-load/SKILL.md`** (`para_missing` → ask CAP, `instantiate.sh`, re-run `load.sh`; `legacy_missing` → offer `templates/brief.md`).

## 2. Optional: load full skill text

For detailed procedures, use the **`skill`** tool with `brain-sync` and/or `brain-load` so the full `SKILL.md` is injected into context.

## 3. Session end

When the user’s last request in a brain-related session is done, run:

```bash
bash ~/ai-dotfiles/skills/brain-sync/sync.sh end
```

(Adjust the path if the clone is not `~/ai-dotfiles`.)
