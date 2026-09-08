#!/usr/bin/env bash
# Log Cursor Agent skill file loads to ~/.claude/skill-usage.log (heuristic).
# Wired as preToolUse matcher Read only (not beforeReadFile — same load would double-count).
# Counts paths ending in SKILL.md under skills trees. Not ground truth — see README.
set -euo pipefail
AI_DOTFILES="${AI_DOTFILES:-$HOME/ai-dotfiles}"
LOG_HELPER="$AI_DOTFILES/scripts/log-skill-usage.sh"

payload=$(cat)
path=""

if ! command -v jq >/dev/null 2>&1; then
  echo '{}'
  exit 0
fi

path=$(printf '%s' "$payload" | jq -r '
  .file_path
  // .tool_input.file_path
  // .tool_input.path
  // .tool_input.target_file
  // empty
' 2>/dev/null || true)

path="${path:-}"
case "$path" in
  */SKILL.md|*/SKILL.MD) ;;
  *)
    echo '{}'
    exit 0
    ;;
esac

# */skills/* covers .claude/.cursor/.vibe/skills via symlink targets or linked paths
case "$path" in
  */skills/*|*/skills-cursor/*) ;;
  *)
    echo '{}'
    exit 0
    ;;
esac

skill=$(basename "$(dirname "$path")")
[[ -n "$skill" && "$skill" != "." && "$skill" != "/" ]] || { echo '{}'; exit 0; }

if [[ -x "$LOG_HELPER" ]]; then
  bash "$LOG_HELPER" "$skill" "cursor:skill-read" 2>/dev/null || true
fi

echo '{}'
exit 0
