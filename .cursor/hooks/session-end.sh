#!/usr/bin/env bash
set -uo pipefail

HOOKS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
AI_DOTFILES="${AI_DOTFILES:-$HOME/ai-dotfiles}"
LOG_DIR="${BRAIN_HOOKS_LOG_DIR:-$HOME/.cursor/logs}"
LOG_FILE="$LOG_DIR/brain-hooks-session.log"
mkdir -p "$LOG_DIR"

INPUT_FILE="$(mktemp)"
trap 'rm -f "$INPUT_FILE"' EXIT
cat >"$INPUT_FILE" || true

# shellcheck source=lib-gate.sh
source "$HOOKS_DIR/lib-gate.sh"
# shellcheck source=lib-session.sh
source "$HOOKS_DIR/lib-session.sh"

brain_hooks_prune_markers

reason="$(brain_hooks_should_run)" || {
  brain_hooks_log_decision SKIP reason="$reason" event=sessionEnd \
    VSCODE_PID="${VSCODE_PID:-unset}" \
    VSCODE_CWD="${VSCODE_CWD:-unset}" \
    VSCODE_IPC_HOOK="${VSCODE_IPC_HOOK:+set}${VSCODE_IPC_HOOK:-unset}" \
    CURSOR_CODE_REMOTE="${CURSOR_CODE_REMOTE:-unset}" \
    id_source=n/a
  echo '{}'
  exit 0
}

brain_hooks_raw_id_to_vars "$INPUT_FILE"
id_source="$BRAIN_HOOKS_ID_SOURCE"
key=""
if [[ -n "${BRAIN_HOOKS_RAW_ID:-}" ]]; then
  key="$(brain_hooks_marker_key "$BRAIN_HOOKS_RAW_ID")"
fi

brain_hooks_with_sync_lock bash "$AI_DOTFILES/skills/brain-sync/scripts/sync.sh" end \
  >>"$LOG_FILE" 2>&1 || true

if [[ -n "$key" ]]; then
  marker_dir="$(brain_hooks_marker_dir)"
  started="$marker_dir/cursor-${key}.started"
  ended="$marker_dir/cursor-${key}.ended"
  touch "$ended"
  [[ -f "$started" ]] && rm -f "$started"
  brain_hooks_log_decision RUN reason="$reason" event=sessionEnd \
    id_source="$id_source" key="$key"
fi

exit 0
