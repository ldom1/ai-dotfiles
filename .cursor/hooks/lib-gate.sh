#!/usr/bin/env bash
# sourced by session-*.sh — do not execute alone
brain_hooks_log() {
  local log_dir="${BRAIN_HOOKS_LOG_DIR:-$HOME/.cursor/logs}"
  mkdir -p "$log_dir"
  printf 'ts=%s %s\n' "$(date -Iseconds)" "$*" >>"$log_dir/brain-hooks.log"
}

# decision=RUN|SKIP with action= alias; includes env correlation fields
brain_hooks_log_decision() {
  local decision="$1"
  shift
  local action
  case "$decision" in
    RUN) action=run ;;
    SKIP) action=skip ;;
    *) action="${decision,,}" ;;
  esac
  brain_hooks_log decision="$decision" action="$action" \
    BRAIN_AGENT_HOOKS="${BRAIN_AGENT_HOOKS:-unset}" \
    CURSOR_VERSION="${CURSOR_VERSION:-unset}" \
    "$@"
}

# Agent CLI packages as YYYY.MM.DD-…; desktop IDE uses X.Y.Z.
brain_hooks_looks_like_cli() {
  [[ "${CURSOR_VERSION:-}" =~ ^[0-9]{4}\.[0-9]{2}\.[0-9]{2} ]]
}

# IDE / remote editor surfaces (not authoritative alone — used when version ≠ CLI).
brain_hooks_looks_like_ide() {
  [[ "${CURSOR_CODE_REMOTE:-}" == "true" ]] && return 0
  [[ -n "${VSCODE_PID:-}" || -n "${VSCODE_IPC_HOOK:-}" ]] && return 0
  local v="${CURSOR_VERSION:-}"
  if [[ -n "$v" && "$v" =~ ^[0-9]+\.[0-9]+\.[0-9]+ && ! "$v" =~ ^[0-9]{4}\.[0-9]{2}\.[0-9]{2} ]]; then
    return 0
  fi
  case "${VSCODE_CWD:-}" in
    *[/\\]Programs[/\\][Cc]ursor*|*[/\\]Cursor.app*) return 0 ;;
  esac
  return 1
}

# stdout: reason string; exit 0 = RUN, 1 = SKIP
# Default: Agent CLI ON, IDE OFF. Override: BRAIN_AGENT_HOOKS=1 force RUN, =0 force SKIP.
# Never export BRAIN_AGENT_HOOKS=1 from shell profile (forces IDE RUN too).
brain_hooks_should_run() {
  case "${BRAIN_AGENT_HOOKS:-}" in
    0) echo explicit_disable; return 1 ;;
    1) echo explicit_enable; return 0 ;;
  esac
  if brain_hooks_looks_like_cli; then
    echo cli_default; return 0
  fi
  if brain_hooks_looks_like_ide; then
    echo ide_surface; return 1
  fi
  echo cli_default; return 0
}
