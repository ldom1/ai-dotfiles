#!/usr/bin/env bash
# Print the Local Brain context (project note, then pitfalls) within 9,500 B, for agents that have no
# SessionStart hook: Cursor CLI (brain-hooks-prewarm.sh) and Vibe (bin/vibe-brain). Run it from the project.
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
AI_DOTFILES="${AI_DOTFILES:-$(cd "$HERE/.." && pwd)}"
# shellcheck source=brain-context-lib.sh
source "$HERE/brain-context-lib.sh"

ENV_FILE="${BRAIN_ENV_FILE:-$AI_DOTFILES/config/brain.env}"
# shellcheck source=/dev/null
[[ -f "$ENV_FILE" ]] && source "$ENV_FILE"
PITFALLS="${BRAIN_PATH:-}/resources/operational/ai-agents/pitfalls.md"

NOTE_MAX_BYTES=$(brain_note_max_bytes "$BRAIN_CONTEXT_MAX_BYTES" "$PITFALLS" 0)
if (( NOTE_MAX_BYTES > 0 )); then
  # BRAIN_LOAD_SKIP_MEMORY: the note is capped, the project memory files are not.
  NOTE="$(BRAIN_LOAD_SKIP_MEMORY=1 bash "$AI_DOTFILES/skills/brain-load/scripts/load.sh" --max-bytes "$NOTE_MAX_BYTES" || true)"
else
  NOTE="[brain-load] note skipped: no room left for it after pitfalls"
fi
[[ -z "$NOTE" ]] || printf '%s\n' "$NOTE"
brain_print_pitfalls "$PITFALLS" "$BRAIN_CONTEXT_MAX_BYTES" "$(printf '%s\n' "$NOTE" | wc -c)"
