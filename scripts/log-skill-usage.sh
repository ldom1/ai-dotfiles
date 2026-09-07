#!/usr/bin/env bash
# Append one skill-usage line. Usage: log-skill-usage.sh <skill> [source]
# Examples: log-skill-usage.sh brain-sync cursor:sessionStart
set -euo pipefail
skill="${1:?skill name required}"
source="${2:-}"
log="${SKILL_USAGE_LOG:-$HOME/.claude/skill-usage.log}"
mkdir -p "$(dirname "$log")"
if [[ -n "$source" ]]; then
  printf '%s %s %s\n' "$(date -Iseconds)" "$skill" "$source" >>"$log"
else
  printf '%s %s\n' "$(date -Iseconds)" "$skill" >>"$log"
fi
