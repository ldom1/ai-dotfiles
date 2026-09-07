#!/usr/bin/env bash
# Unit checks for Cursor brain hooks libs (no agent required).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
HOOKS="$ROOT/.cursor/hooks"
# shellcheck source=/dev/null
source "$HOOKS/lib-gate.sh"
# shellcheck source=/dev/null
source "$HOOKS/lib-session.sh"
# shellcheck source=/dev/null
source "$HOOKS/lib-pitfalls-excerpt.sh"

fail=0
ok() { echo "PASS $1"; }
bad() { echo "FAIL $1"; fail=1; }

unset BRAIN_AGENT_HOOKS CURSOR_VERSION VSCODE_PID VSCODE_IPC_HOOK VSCODE_CWD CURSOR_CODE_REMOTE || true
if r="$(brain_hooks_should_run)"; then e=0; else e=$?; fi
[[ "$e" -eq 0 && "$r" == cli_default ]] && ok "gate unset cli_default runs" || bad "gate unset cli_default runs"

export CURSOR_VERSION=2026.09.02-c22c1a3
if r="$(brain_hooks_should_run)"; then e=0; else e=$?; fi
[[ "$e" -eq 0 && "$r" == cli_default ]] && ok "gate CLI version runs" || bad "gate CLI version runs"

# CLI version wins even if VSCODE_* inherited (integrated terminal)
export VSCODE_PID=12345
if r="$(brain_hooks_should_run)"; then e=0; else e=$?; fi
[[ "$e" -eq 0 && "$r" == cli_default ]] && ok "gate CLI version beats VSCODE" || bad "gate CLI version beats VSCODE"
unset VSCODE_PID CURSOR_VERSION

export CURSOR_VERSION=3.19.13
if r="$(brain_hooks_should_run)"; then e=0; else e=$?; fi
[[ "$e" -eq 1 && "$r" == ide_surface ]] && ok "gate IDE version skips" || bad "gate IDE version skips"
unset CURSOR_VERSION

export CURSOR_CODE_REMOTE=true
if r="$(brain_hooks_should_run)"; then e=0; else e=$?; fi
[[ "$e" -eq 1 && "$r" == ide_surface ]] && ok "gate remote skips" || bad "gate remote skips"
unset CURSOR_CODE_REMOTE

export BRAIN_AGENT_HOOKS=1 CURSOR_VERSION=3.19.13
if r="$(brain_hooks_should_run)"; then e=0; else e=$?; fi
[[ "$e" -eq 0 && "$r" == explicit_enable ]] && ok "gate 1 force runs" || bad "gate 1 force runs"

export BRAIN_AGENT_HOOKS=0 CURSOR_VERSION=2026.09.02-c22c1a3
if r="$(brain_hooks_should_run)"; then e=0; else e=$?; fi
[[ "$e" -eq 1 && "$r" == explicit_disable ]] && ok "gate 0 skips" || bad "gate 0 skips"
unset BRAIN_AGENT_HOOKS CURSOR_VERSION

# shellcheck source=/dev/null
source "$ROOT/config/brain.env"
P="${BRAIN_PATH}/resources/operational/ai-agents/pitfalls.md"
if [[ -f "$P" ]]; then
  out="$(brain_hooks_pitfalls_excerpt "$P")"
  bytes="$(printf '%s' "$out" | wc -c)"
  [[ "$bytes" -le 12288 ]] && ok "excerpt <= 12288" || bad "excerpt <= 12288 ($bytes)"
  [[ "$out" == *'RECENT ENTRIES'* ]] && ok "excerpt has recent header" || bad "excerpt has recent header"
  first="$(grep -m1 '^## ' "$P" || true)"
  if [[ -n "$first" ]]; then
    [[ "$out" == *"${first:0:40}"* ]] && ok "excerpt includes newest heading" || bad "excerpt includes newest heading"
  fi
else
  echo "SKIP excerpt (no pitfalls file)"
fi

dir="$(brain_hooks_marker_dir)"
mkdir -p "$dir"
rm -rf "$dir/sync.lock"
mkdir "$dir/sync.lock"
if brain_hooks_with_sync_lock true 2>/dev/null; then
  bad "lock_busy skips"
else
  ok "lock_busy skips"
fi
rmdir "$dir/sync.lock" 2>/dev/null || rm -rf "$dir/sync.lock"
out="$(brain_hooks_with_sync_lock echo ran_ok)"
[[ "$out" == ran_ok ]] && ok "lock clear runs" || bad "lock clear runs"

exit "$fail"
