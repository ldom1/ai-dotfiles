#!/usr/bin/env bash
# Claude Code PreToolUse/Skill — append to skill-usage.log with source tag.
# stdin: Claude hook JSON with .tool_input.skill
set -euo pipefail
AI_DOTFILES="${AI_DOTFILES:-$HOME/ai-dotfiles}"
LOG_HELPER="$AI_DOTFILES/scripts/log-skill-usage.sh"
payload=$(cat)
skill=""
if command -v jq >/dev/null 2>&1; then
  skill=$(printf '%s' "$payload" | jq -r '.tool_input.skill // empty' 2>/dev/null || true)
fi
[[ -n "$skill" ]] || exit 0
if [[ -x "$LOG_HELPER" ]]; then
  bash "$LOG_HELPER" "$skill" "claude:Skill" 2>/dev/null || true
fi
exit 0
