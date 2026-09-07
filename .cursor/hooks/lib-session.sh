#!/usr/bin/env bash
# sourced by session-*.sh — do not execute alone
_HOOKS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib-gate.sh
source "$_HOOKS_DIR/lib-gate.sh"

brain_hooks_read_stdin_to() {
  local file="$1"
  cat >"$file" || true
}

brain_hooks_marker_dir() {
  printf '%s/brain-hooks-%s' "${XDG_RUNTIME_DIR:-/tmp}" "$(id -u)"
}

# Preferred for callers that need both raw id and id_source in the current shell.
# Task 3 session hooks should use this instead of raw=$(brain_hooks_raw_id …).
# Sets BRAIN_HOOKS_RAW_ID and BRAIN_HOOKS_ID_SOURCE (no stdout capture required).
brain_hooks_raw_id_to_vars() {
  local file="$1"
  local raw=""

  if command -v jq >/dev/null 2>&1; then
    raw="$(jq -r '.conversation_id // empty' "$file" 2>/dev/null || true)"
    if [[ -n "$raw" ]]; then
      BRAIN_HOOKS_ID_SOURCE=conversation_id
      BRAIN_HOOKS_RAW_ID="$raw"
      export BRAIN_HOOKS_RAW_ID BRAIN_HOOKS_ID_SOURCE
      return 0
    fi
    raw="$(jq -r '.session_id // empty' "$file" 2>/dev/null || true)"
    if [[ -n "$raw" ]]; then
      BRAIN_HOOKS_ID_SOURCE=session_id
      BRAIN_HOOKS_RAW_ID="$raw"
      export BRAIN_HOOKS_RAW_ID BRAIN_HOOKS_ID_SOURCE
      return 0
    fi
  fi

  if [[ -n "${CURSOR_TRACE_ID:-}" ]]; then
    BRAIN_HOOKS_ID_SOURCE=CURSOR_TRACE_ID
    BRAIN_HOOKS_RAW_ID="$CURSOR_TRACE_ID"
    export BRAIN_HOOKS_RAW_ID BRAIN_HOOKS_ID_SOURCE
    return 0
  fi

  BRAIN_HOOKS_ID_SOURCE=synthetic
  local stdin_bytes transcript project time
  stdin_bytes="$(cat "$file")"
  transcript="${CURSOR_TRANSCRIPT_PATH:-}"
  project="${CURSOR_PROJECT_DIR:-}"
  time="${EPOCHREALTIME:-$(date +%s.%N)}"
  BRAIN_HOOKS_RAW_ID="$(printf '%s' "${stdin_bytes}${transcript}${project}${time}" | sha256sum | awk '{print $1}')"
  # Exported for callers / shellcheck (vars are intentional API of this helper)
  export BRAIN_HOOKS_RAW_ID BRAIN_HOOKS_ID_SOURCE
}

# Prints raw id to stdout; sets BRAIN_HOOKS_ID_SOURCE in the current shell only
# (lost if invoked via $() subshell). Tests may call this directly; Task 3 should
# use brain_hooks_raw_id_to_vars and read BRAIN_HOOKS_RAW_ID / BRAIN_HOOKS_ID_SOURCE.
brain_hooks_raw_id() {
  brain_hooks_raw_id_to_vars "$1"
  printf '%s' "$BRAIN_HOOKS_RAW_ID"
}

brain_hooks_marker_key() {
  local raw="$1"
  printf '%s' "$raw" | sha256sum | awk '{print $1}'
}

brain_hooks_prune_markers() {
  local dir
  dir="$(brain_hooks_marker_dir)"
  [[ -d "$dir" ]] || return 0
  find "$dir" -maxdepth 1 -type f \( -name 'cursor-*.started' -o -name 'cursor-*.ended' \) -mmin +1440 -delete 2>/dev/null || true
}

brain_hooks_with_sync_lock() {
  local dir lock lock_mtime lock_age
  dir="$(brain_hooks_marker_dir)"
  mkdir -p "$dir"
  lock="$dir/sync.lock"

  _brain_hooks_acquire_lock() {
    if mkdir "$lock" 2>/dev/null; then
      trap 'rmdir "$lock" 2>/dev/null || true' RETURN
      "$@"
      local rc=$?
      rmdir "$lock" 2>/dev/null || true
      trap - RETURN
      return "$rc"
    fi
    return 1
  }

  if _brain_hooks_acquire_lock "$@"; then
    return 0
  fi

  lock_mtime="$(stat -c %Y "$lock" 2>/dev/null || echo 0)"
  lock_age=$(( $(date +%s) - lock_mtime ))

  if (( lock_age < 600 )); then
    brain_hooks_log reason=lock_busy lock_age="$lock_age"
    return 1
  fi

  brain_hooks_log reason=lock_stale_reclaimed lock_age="$lock_age"
  rmdir "$lock" 2>/dev/null || rm -rf "$lock"

  if _brain_hooks_acquire_lock "$@"; then
    return 0
  fi

  brain_hooks_log reason=lock_busy lock_age="$lock_age"
  return 1
}
