#!/usr/bin/env bash
# SessionEnd: brain-sync end (commit + push vault). May exceed default 1.5s — see CLAUDE.md.
set -euo pipefail
AI_DOTFILES="${AI_DOTFILES:-$HOME/ai-dotfiles}"
LOG="$HOME/.claude/logs/brain-sync-end.log"
mkdir -p "$(dirname "$LOG")"
"$AI_DOTFILES/skills/brain-sync/scripts/sync.sh" end 2>&1 | tee -a "$LOG" >&2 || true
