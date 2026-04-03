# Global — ai-dotfiles

## Session

- **Start:** `bash ~/ai-dotfiles/skills/brain-sync/sync.sh start` then `bash ~/ai-dotfiles/skills/brain-load/load.sh`
- **End:** `bash ~/ai-dotfiles/skills/brain-sync/sync.sh end`

## Memory (Local Brain)

Vault path: `~/ai-dotfiles/config/brain.env` → `BRAIN_PATH`. Where to store what: `.claude/LocalBrain.md` (short index). Deep reference: `$BRAIN_PATH/resources/knowledge/`.

## Bash / tokens

PreToolUse hook on **Bash** runs **RTK rewrite** (if installed) and **tail-caps** noisy installs/builds. Debugging: `rtk --version`, `rtk gain`. RTK details: `.claude/RTK.md`.

## Skills (invoke explicitly)

- **`/create-pr`** — Open a PR (`gh`) with this repo’s branch + commit conventions (see skill).

Install **brain-sync** / **brain-load** from marketplace `ldom1/ai-dotfiles` when not bundled.

## FinOps habits

`/clear` between unrelated tasks; prefer precise prompts; MCP hygiene. Canonical note: `$BRAIN_PATH/resources/knowledge/operational/claude-finops.md` (also [sfeir.dev FinOps Claude Code](https://www.sfeir.dev/ia/finops-claude-code-comment-optimiser-sa-consommation-de-tokens/)).
