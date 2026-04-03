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

## Long runs — `/clear` on context switches

In long sessions, when you **change theme**, **topic**, or **implementation block** (new feature area, unrelated refactor, different goal), **`/rename`** first if you may `--resume` later, then **`/clear`**. Prior exploration and tool output should not carry into the next block.

## Compaction — earlier than default

1. **Manual:** Run **`/compact`** **before** the window feels tight — do not wait for automatic compaction near the limit. When compacting, keep: files changed or in scope, open decisions, commands to verify (tests/build), failing errors, explicit user constraints.
2. **Automatic (shell):** To compact **earlier** than the built‑in late threshold, set before starting Claude Code, e.g. `export CLAUDE_AUTOCOMPACT_PCT_OVERRIDE=70` (lower % ≈ trigger sooner; tune 55–80 — too low wastes compaction). Optional: `CLAUDE_CODE_AUTO_COMPACT_WINDOW` to cap effective window. See `$BRAIN_PATH/resources/knowledge/operational/claude-finops.md`.

## FinOps

Precise prompts. MCP hygiene. Reference: `$BRAIN_PATH/resources/knowledge/operational/claude-finops.md`.
