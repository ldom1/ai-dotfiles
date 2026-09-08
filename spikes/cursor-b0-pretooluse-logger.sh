#!/usr/bin/env bash
# spikes/cursor-b0-pretooluse-logger.sh — B0 observation spike (unregister from hooks.json after capture).
# Appends one NDJSON line per preToolUse / beforeReadFile event. Fail-open allow.
set -euo pipefail
OUT="${CURSOR_B0_LOG:-$HOME/.claude/cursor-b0-pretooluse.ndjson}"
mkdir -p "$(dirname "$OUT")"
payload=$(cat)
ts=$(date -Iseconds)
# one line: timestamp + compact json (or raw if jq missing)
if command -v jq >/dev/null 2>&1; then
  printf '%s %s\n' "$ts" "$(printf '%s' "$payload" | jq -c '.')" >>"$OUT"
else
  printf '%s %s\n' "$ts" "$payload" >>"$OUT"
fi
# fail-open: empty object / allow
echo '{}'
