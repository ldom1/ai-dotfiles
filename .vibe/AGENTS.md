# Local Brain bootstrap (ai-dotfiles)

**Canonical copy:** this file lives in **`.vibe/AGENTS.md`**. A symlink **`AGENTS.md`** at the repository root points here so [Mistral Vibe](https://docs.mistral.ai/mistral-vibe/agents-skills) can load it: Vibe only collects `AGENTS.md` in the current working directory and its **parent** directories — it does **not** scan inside `.vibe/` automatically.

Mistral Vibe does **not** run shell commands when a session opens (unlike Cursor always-on rules). Follow this **before your first substantive action** when the task involves this repo, the Local Brain vault, or a codebase whose context should be loaded from the vault.

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

Use either the **`skill`** tool (`name`: `brain-sync` / `brain-load`) **or** Mistral Vibe slash commands **`/brain-sync`** and **`/brain-load`** — both only **inject** the `SKILL.md` text; they do not run the shell scripts.

## 3. Session end

When the user’s last request in a brain-related session is done, run:

```bash
bash ~/ai-dotfiles/skills/brain-sync/sync.sh end
```

(Adjust the path if the clone is not `~/ai-dotfiles`.)

## Development (tokens, simplicity)

- **Tokens and context:** Rationalize what you read, invoke, and output—keep only what you need to answer correctly (no dump walls or aimless exploration).
- **Occam’s razor (lex parsimoniae):** When several approaches are plausible, prefer the one with fewer assumptions and smaller surface area. Favor **structured, simple, human-readable** code; avoid spaghetti. Core principle for Claude Code, Cursor, and Mistral Vibe.
