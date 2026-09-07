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
# shellcheck source=lib-pitfalls-excerpt.sh
source "$HOOKS_DIR/lib-pitfalls-excerpt.sh"

brain_hooks_prune_markers

brain_hooks_emit_additional_context() {
  local ctx="$1"
  if command -v jq >/dev/null 2>&1; then
    if jq -n --arg c "$ctx" '{additional_context:$c}'; then
      return 0
    fi
  fi
  if command -v python3 >/dev/null 2>&1; then
    if printf '%s' "$ctx" | python3 -c 'import json,sys; print(json.dumps({"additional_context": sys.stdin.read()}))'; then
      return 0
    fi
  fi
  echo '{}'
  return 1
}

reason="$(brain_hooks_should_run)" || {
  brain_hooks_log_decision SKIP reason="$reason" event=sessionStart \
    VSCODE_PID="${VSCODE_PID:-unset}" \
    VSCODE_CWD="${VSCODE_CWD:-unset}" \
    VSCODE_IPC_HOOK="${VSCODE_IPC_HOOK:+set}${VSCODE_IPC_HOOK:-unset}" \
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
    id_source="$id_source" key="$key"
  echo '{}'
  exit 0
fi

brain_hooks_with_sync_lock bash "$AI_DOTFILES/skills/brain-sync/scripts/sync.sh" start \
  >>"$LOG_FILE" 2>&1 || true

LOAD_OUT="$(bash "$AI_DOTFILES/skills/brain-load/scripts/load.sh" 2>>"$LOG_FILE" | head -30 || true)"

PITFALLS_FILE="${BRAIN_PATH:-}/resources/operational/ai-agents/pitfalls.md"
EXCERPT=""
INSTRUCTIONS=""
BRAIN_WARN=""
if [[ -n "${BRAIN_PATH:-}" && -f "$PITFALLS_FILE" ]]; then
  EXCERPT="$(brain_hooks_pitfalls_excerpt "$PITFALLS_FILE" || true)"
fi

if [[ -n "${BRAIN_PATH:-}" ]]; then
  read -r -d '' INSTRUCTIONS <<EOF || true
--- PITFALLS BEHAVIOR (CLI) ---
Canonical file: ${BRAIN_PATH:-}/resources/operational/ai-agents/pitfalls.md
Before substantive work (implementation, debugging, refactors, shell/git, config): skim headings; treat matching entries as hard constraints (Read full file for detail — excerpt is incomplete).
When the user corrects a mistake: prepend a Registry-style bullet to that file (context → wrong → instead), newest first.
Before claiming done/fixed/passing: re-check pitfalls for the changed surface.
--- END PITFALLS BEHAVIOR ---
EOF
else
  read -r -d '' BRAIN_WARN <<EOF || true
--- BRAIN_PATH WARNING ---
Local Brain not configured (BRAIN_PATH unset or empty). Set BRAIN_PATH in config/brain.env. Pitfalls excerpt skipped.
--- END BRAIN_PATH WARNING ---
EOF
fi

CTX="${LOAD_OUT:-}"
if [[ -n "$BRAIN_WARN" ]]; then
  CTX="${CTX}

${BRAIN_WARN}"
fi
if [[ -n "$EXCERPT" ]]; then
  CTX="${CTX}

${EXCERPT}"
fi
if [[ -n "$INSTRUCTIONS" ]]; then
  CTX="${CTX}

${INSTRUCTIONS}"
fi

if brain_hooks_emit_additional_context "$CTX"; then
  touch "$started"
  brain_hooks_log_decision RUN reason="$reason" event=sessionStart \
    id_source="$id_source" key="$key"
else
  touch "$started"
  brain_hooks_log_decision RUN reason=emit_failed_marked event=sessionStart \
    id_source="$id_source" key="$key"
fi

exit 0
