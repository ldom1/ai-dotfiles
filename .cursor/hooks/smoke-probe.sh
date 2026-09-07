#!/usr/bin/env bash
set -euo pipefail
LOG_DIR="$(cd "$(dirname "$0")/.." && pwd)/logs"
mkdir -p "$LOG_DIR"
STAMP="$(date -Iseconds)"
RAW="$LOG_DIR/phase0-raw-$$.json"
REPORT="$LOG_DIR/phase0-smoke-$(date +%Y%m%d).md"
cat >"$RAW" || true
{
  echo "# Phase 0 smoke $STAMP"
  echo
  echo "## env"
  echo "- CURSOR_VERSION=${CURSOR_VERSION:-unset}"
  echo "- CURSOR_PROJECT_DIR=${CURSOR_PROJECT_DIR:-unset}"
  echo "- CURSOR_TRANSCRIPT_PATH=${CURSOR_TRANSCRIPT_PATH:-unset}"
  echo "- BRAIN_AGENT_HOOKS=${BRAIN_AGENT_HOOKS:-unset}"
  echo "- VSCODE_PID=${VSCODE_PID:+set}${VSCODE_PID:-unset}"
  echo "- VSCODE_CWD=${VSCODE_CWD:+set}${VSCODE_CWD:-unset}"
  echo "- VSCODE_IPC_HOOK=${VSCODE_IPC_HOOK:+set}${VSCODE_IPC_HOOK:-unset}"
  echo
  echo "## stdin"
  echo '```json'
  cat "$RAW"
  echo '```'
  echo
  if command -v jq >/dev/null; then
    echo "## id fields"
    echo "- conversation_id=$(jq -r '.conversation_id // empty' "$RAW")"
    echo "- session_id=$(jq -r '.session_id // empty' "$RAW")"
  fi
} >>"$REPORT"
# Prove additional_context path: inject a unique token
TOKEN="PHASE0_CONTEXT_TOKEN_$$"
printf '{"additional_context":"PHASE0_HOOK_OK %s — if you see this token in context, injection works."}\n' "$TOKEN"
exit 0
