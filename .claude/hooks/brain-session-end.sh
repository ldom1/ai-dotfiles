#!/usr/bin/env bash
# SessionEnd: brain-sync end (commit + push vault). May exceed default 1.5s — see CLAUDE.md.
set -euo pipefail
AI_DOTFILES="${AI_DOTFILES:-$HOME/ai-dotfiles}"
"$AI_DOTFILES/skills/brain-sync/scripts/sync.sh" end >&2 || true
