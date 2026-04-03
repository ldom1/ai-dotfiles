# Global

## Session

- **Start:** `bash ~/ai-dotfiles/skills/brain-sync/sync.sh start` then `bash ~/ai-dotfiles/skills/brain-load/load.sh`
- **End:** `bash ~/ai-dotfiles/skills/brain-sync/sync.sh end`

## Memory

Persistent memory lives in the **Local Brain** vault (path: `config/brain.env` → `BRAIN_PATH`). Short index: `LocalBrain.md`. Deep reference: `$BRAIN_PATH/resources/knowledge/`.

## Bash hooks

PreToolUse on **Bash** runs **RTK rewrite** (if installed) + **tail-cap** on noisy installs/builds. Details: `RTK.md`.

## Skills

- **`/create-pr`** — GitHub PR with branch + commit conventions.

## FinOps

`/clear` between unrelated tasks. Precise prompts. MCP hygiene. Reference: `$BRAIN_PATH/resources/knowledge/operational/claude-finops.md`.
