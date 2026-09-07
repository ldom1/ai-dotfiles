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

# stdout: reason string; exit 0 = RUN, 1 = SKIP
brain_hooks_should_run() {
  case "${BRAIN_AGENT_HOOKS:-}" in
    0) echo explicit_disable; return 1 ;;
    1) echo opt_in; return 0 ;;
    *) echo no_opt_in; return 1 ;;
  esac
}
