#!/usr/bin/env bash
# rtk-hook-version: 3
# PreToolUse (Bash): RTK rewrite when available + FinOps tail cap on noisy output.
# Requires: jq. rtk >= 0.23.0 optional (warns if missing/old; tail cap still runs).

finops_tail_wrap() {
  local c="$1"
  if [[ "$c" == *"|"*tail* ]] || [[ "$c" == *"|"*head* ]]; then
    echo "$c"
    return
  fi
  local t="${c#"${c%%[![:space:]]*}"}"
  while [[ "$t" == sudo\ * ]]; do
    t="${t#sudo }"
    t="${t#"${t%%[![:space:]]*}"}"
  done
  case "$t" in
    npm\ install*|npm\ ci*|pnpm\ install*|yarn\ install*|bun\ install*|\
    cargo\ build*|docker\ build*|docker\ compose\ build*|brew\ install*)
      echo "( $c ) 2>&1 | tail -n 120"
      ;;
    *)
      echo "$c"
      ;;
  esac
}

if ! command -v jq &>/dev/null; then
  echo "[rtk] WARNING: jq is not installed. Hook cannot run. Install jq: https://jqlang.github.io/jq/download/" >&2
  exit 0
fi

RTK_OK=0
if command -v rtk &>/dev/null; then
  RTK_VERSION=$(rtk --version 2>/dev/null | grep -oE '[0-9]+\.[0-9]+\.[0-9]+' | head -1)
  if [ -n "$RTK_VERSION" ]; then
    MAJOR=$(echo "$RTK_VERSION" | cut -d. -f1)
    MINOR=$(echo "$RTK_VERSION" | cut -d. -f2)
    if [ "$MAJOR" -eq 0 ] && [ "$MINOR" -lt 23 ]; then
      echo "[rtk] WARNING: rtk $RTK_VERSION is too old (need >= 0.23.0). Upgrade: cargo install rtk" >&2
    else
      RTK_OK=1
    fi
  fi
else
  echo "[rtk] WARNING: rtk is not installed or not in PATH. Install: https://github.com/rtk-ai/rtk#installation" >&2
fi

INPUT=$(cat)
CMD=$(echo "$INPUT" | jq -r '.tool_input.command // empty')

if [ -z "$CMD" ]; then
  exit 0
fi

AFTER_RTK="$CMD"
if [ "$RTK_OK" = 1 ]; then
  R=$(rtk rewrite "$CMD" 2>/dev/null) && [ -n "$R" ] && AFTER_RTK="$R"
fi

FINAL=$(finops_tail_wrap "$AFTER_RTK")

if [ "$FINAL" = "$CMD" ]; then
  exit 0
fi

ORIGINAL_INPUT=$(echo "$INPUT" | jq -c '.tool_input')
UPDATED_INPUT=$(echo "$ORIGINAL_INPUT" | jq --arg cmd "$FINAL" '.command = $cmd')

REASON="FinOps tail-capped bash output"
[ "$AFTER_RTK" != "$CMD" ] && REASON="RTK rewrite + FinOps tail cap"

jq -n \
  --argjson updated "$UPDATED_INPUT" \
  --arg reason "$REASON" \
  '{
    "hookSpecificOutput": {
      "hookEventName": "PreToolUse",
      "permissionDecision": "allow",
      "permissionDecisionReason": $reason,
      "updatedInput": $updated
    }
  }'
