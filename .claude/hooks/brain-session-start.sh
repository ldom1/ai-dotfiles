#!/usr/bin/env bash
# SessionStart: brain-sync start (startup/resume only) + brain-load; export BRAIN_PATH for Bash tools.
set -euo pipefail

AI_DOTFILES="${AI_DOTFILES:-$HOME/ai-dotfiles}"
SYNC="$AI_DOTFILES/skills/brain-sync/scripts/sync.sh"
LOAD="$AI_DOTFILES/skills/brain-load/scripts/load.sh"

ENV_FILE="${BRAIN_ENV_FILE:-}"
if [[ -z "$ENV_FILE" || ! -f "$ENV_FILE" ]]; then
  ENV_FILE="$AI_DOTFILES/config/brain.env"
fi
if [[ -f "$ENV_FILE" ]]; then
  # shellcheck source=/dev/null
  source "$ENV_FILE"
fi
if [[ -n "${CLAUDE_ENV_FILE:-}" && -n "${BRAIN_PATH:-}" ]]; then
  printf 'export BRAIN_PATH=%q\n' "$BRAIN_PATH" >> "$CLAUDE_ENV_FILE"
fi

# Hook JSON is on stdin; do not rely on jq (may be missing in hook PATH).
INPUT=$(cat || true)
SOURCE="startup"
if [[ "$INPUT" =~ \"source\"[[:space:]]*:[[:space:]]*\"([^\"]+)\" ]]; then
  SOURCE="${BASH_REMATCH[1]}"
fi

if [[ "$SOURCE" == "startup" || "$SOURCE" == "resume" ]]; then
  "$SYNC" start >&2 || true
fi

"$LOAD" || true
