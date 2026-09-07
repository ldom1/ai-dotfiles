#!/usr/bin/env bash
# sessionStart: refresh user-rule inject + sidecar, background brain-sync.
set -uo pipefail

HOOKS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
AI_DOTFILES="${AI_DOTFILES:-$HOME/ai-dotfiles}"
LOG_DIR="${BRAIN_HOOKS_LOG_DIR:-$HOME/.cursor/logs}"
LOG_FILE="$LOG_DIR/brain-hooks-session.log"
SIDECAR="$LOG_DIR/brain-hooks-last-context.md"
mkdir -p "$LOG_DIR"

INPUT_FILE="$(mktemp)"
trap 'rm -f "$INPUT_FILE"' EXIT
cat >"$INPUT_FILE" || true

# shellcheck source=lib-gate.sh
source "$HOOKS_DIR/lib-gate.sh"
# shellcheck source=lib-session.sh
source "$HOOKS_DIR/lib-session.sh"
# shellcheck source=lib-inject-rule.sh
source "$HOOKS_DIR/lib-inject-rule.sh"

brain_hooks_prune_markers

reason="$(brain_hooks_should_run)" || {
  brain_hooks_clear_inject_rule
  brain_hooks_log_decision SKIP reason="$reason" event=sessionStart \
    VSCODE_PID="${VSCODE_PID:-unset}" \
    VSCODE_CWD="${VSCODE_CWD:-unset}" \
    VSCODE_IPC_HOOK="${VSCODE_IPC_HOOK:+set}${VSCODE_IPC_HOOK:-unset}" \
    CURSOR_CODE_REMOTE="${CURSOR_CODE_REMOTE:-unset}" \
    id_source=n/a
  echo '{}'
  exit 0
}

ENV_FILE="${BRAIN_ENV_FILE:-$AI_DOTFILES/config/brain.env}"
if [[ -f "$ENV_FILE" ]]; then
  # shellcheck source=/dev/null
  source "$ENV_FILE"
fi
BRAIN_PATH="${BRAIN_PATH:-}"

brain_hooks_raw_id_to_vars "$INPUT_FILE"
raw="$BRAIN_HOOKS_RAW_ID"
id_source="$BRAIN_HOOKS_ID_SOURCE"
key="$(brain_hooks_marker_key "$raw")"

marker_dir="$(brain_hooks_marker_dir)"
started="$marker_dir/cursor-${key}.started"

if [[ -f "$started" ]]; then
  brain_hooks_log_decision SKIP reason=already_ran event=sessionStart \
    id_source="$id_source" key="$key" \
    VSCODE_PID="${VSCODE_PID:-unset}" \
    VSCODE_CWD="${VSCODE_CWD:-unset}" \
    VSCODE_IPC_HOOK="${VSCODE_IPC_HOOK:+set}${VSCODE_IPC_HOOK:-unset}" \
    CURSOR_CODE_REMOTE="${CURSOR_CODE_REMOTE:-unset}"
  echo '{}'
  exit 0
fi

LOAD_OUT="$(bash "$AI_DOTFILES/skills/brain-load/scripts/load.sh" 2>>"$LOG_FILE" | head -30 || true)"
bash "$AI_DOTFILES/scripts/log-skill-usage.sh" brain-load "cursor:sessionStart" 2>/dev/null || true

CANARY="[brain-hooks] sessionStart OK reason=${reason} — Local Brain context injected (CLI)."
CTX="${CANARY}

${LOAD_OUT:-}

--- PITFALLS BEHAVIOR (CLI) ---
Canonical: ${BRAIN_PATH:-unset}/resources/operational/ai-agents/pitfalls.md
Before substantive work: Read that file; treat matches as hard constraints.
--- END PITFALLS BEHAVIOR ---"

printf '%s\n' "$CTX" >"$SIDECAR"
brain_hooks_write_inject_rule "$CTX"
touch "$started"
brain_hooks_log_decision RUN reason="$reason" event=sessionStart \
  id_source="$id_source" key="$key" \
  inject=user_rule sync=background \
  VSCODE_PID="${VSCODE_PID:-unset}" \
  VSCODE_CWD="${VSCODE_CWD:-unset}" \
  VSCODE_IPC_HOOK="${VSCODE_IPC_HOOK:+set}${VSCODE_IPC_HOOK:-unset}" \
  CURSOR_CODE_REMOTE="${CURSOR_CODE_REMOTE:-unset}"
echo "[brain-hooks] sessionStart RUN reason=${reason} (user rule inject + bg sync)" >&2

(
  brain_hooks_with_sync_lock bash "$AI_DOTFILES/skills/brain-sync/scripts/sync.sh" start \
    >>"$LOG_FILE" 2>&1 || true
  bash "$AI_DOTFILES/scripts/log-skill-usage.sh" brain-sync "cursor:sessionStart" 2>/dev/null || true
) >/dev/null 2>&1 &
disown 2>/dev/null || true

echo '{}'
exit 0
