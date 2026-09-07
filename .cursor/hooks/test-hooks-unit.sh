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

unset BRAIN_AGENT_HOOKS || true
if r="$(brain_hooks_should_run)"; then e=0; else e=$?; fi
[[ "$e" -eq 1 && "$r" == no_opt_in ]] && ok "gate unset skips" || bad "gate unset skips"

export BRAIN_AGENT_HOOKS=1
if r="$(brain_hooks_should_run)"; then e=0; else e=$?; fi
[[ "$e" -eq 0 && "$r" == opt_in ]] && ok "gate 1 runs" || bad "gate 1 runs"

export BRAIN_AGENT_HOOKS=0
if r="$(brain_hooks_should_run)"; then e=0; else e=$?; fi
[[ "$e" -eq 1 && "$r" == explicit_disable ]] && ok "gate 0 skips" || bad "gate 0 skips"

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
