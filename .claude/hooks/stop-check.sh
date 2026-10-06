#!/usr/bin/env bash
# Stop: run the project's fast check before the agent can finish a turn.
# Opt-in per repo: .claude/stop-check holds one shell command (e.g. `ruff check . && pytest -x -q`).
# Runs only when the git tree has changes. On failure, blocks the stop and feeds the
# output tail back to the model. Never blocks twice in a row (stop_hook_active), so it
# cannot loop. A timeout warns without blocking.
# Trust gate: the command runs only if its normalized hash is approved for this repo in
# ~/.claude/stop-check-trust (see bin/stop-check-trust). An unapproved command is skipped, never
# blocks, and warns once per session.
set -uo pipefail

TIMEOUT_S="${STOP_CHECK_TIMEOUT:-120}"
TAIL_LINES=40
LOG="$HOME/.claude/logs/stop-check.log"
STORE="$HOME/.claude/stop-check-trust"
TRUST_BIN="$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")/../../bin/stop-check-trust"

# Hook JSON on stdin; parse with python3 (jq may be missing in hook PATH).
read -r ACTIVE SID CWD < <(python3 -c '
import json, re, sys
e = json.load(sys.stdin)
sid = re.sub(r"[^A-Za-z0-9_-]", "", str(e.get("session_id") or "")) or "none"
print("1" if e.get("stop_hook_active") else "0", sid, e.get("cwd") or ".")' 2>/dev/null) || exit 0

[[ "$ACTIVE" == "1" ]] && exit 0
ROOT=$(git -C "$CWD" rev-parse --show-toplevel 2>/dev/null) || exit 0
CHECK_FILE="$ROOT/.claude/stop-check"
[[ -f "$CHECK_FILE" ]] || exit 0
[[ -n "$(git -C "$ROOT" status --porcelain 2>/dev/null)" ]] || exit 0

CMD=$("$TRUST_BIN" --command "$ROOT" 2>/dev/null) || exit 0
KEY=$("$TRUST_BIN" --key "$ROOT" 2>/dev/null) || exit 0

if ! grep -qxF "$KEY" "$STORE" 2>/dev/null; then
  WARNED="${TMPDIR:-/tmp}/stop-check-warned-$SID"
  grep -qxF "$KEY" "$WARNED" 2>/dev/null && exit 0
  printf '%s\n' "$KEY" >>"$WARNED"
  python3 -c '
import json, sys
print(json.dumps({"systemMessage": f"[stop-check] skipped: command not approved: {sys.argv[1]}. To approve, the user runs: ! stop-check-trust"}))' \
    "$(head -n1 <<<"$CMD")"
  exit 0
fi

OUT=$(cd "$ROOT" && timeout "$TIMEOUT_S" bash -c "$CMD" 2>&1)
RC=$?

mkdir -p "$(dirname "$LOG")"
printf '%s repo=%s rc=%s\n' "$(date -Iseconds)" "$ROOT" "$RC" >>"$LOG"

(( RC == 0 )) && exit 0

python3 - "$RC" "$CMD" "$TIMEOUT_S" "$TAIL_LINES" "$OUT" <<'EOF'
import json, sys
rc, cmd, timeout_s, tail, out = int(sys.argv[1]), sys.argv[2], sys.argv[3], int(sys.argv[4]), sys.argv[5]
if rc == 124:
    print(json.dumps({"systemMessage": f"[stop-check] `{cmd}` timed out after {timeout_s}s; not blocking."}))
else:
    last = "\n".join(out.splitlines()[-tail:])
    print(json.dumps({"decision": "block",
                      "reason": f"[stop-check] `{cmd}` failed (exit {rc}). Fix this before finishing:\n{last}"}))
EOF
