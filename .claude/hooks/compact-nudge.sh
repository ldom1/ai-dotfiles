#!/usr/bin/env bash
# Stop: tell the user when the session context grows past COMPACT_NUDGE_START tokens
# (default 250k), then once per extra COMPACT_NUDGE_STEP (default 100k). Every request
# re-reads the whole context, so long sessions cost far more per request.
# Reads the last assistant usage from the transcript tail; never blocks.
set -uo pipefail

STATE_DIR="$HOME/.claude/cache/compact-nudge"
INPUT=$(cat)

python3 - "$STATE_DIR" "${COMPACT_NUDGE_START:-250000}" "${COMPACT_NUDGE_STEP:-100000}" "$INPUT" <<'EOF' 2>/dev/null || true
import json, os, sys

state_dir, start, step = sys.argv[1], int(sys.argv[2]), int(sys.argv[3])
event = json.loads(sys.argv[4] or "{}")
path, session = event.get("transcript_path") or "", event.get("session_id") or "unknown"
if not os.path.isfile(path):
    sys.exit(0)

with open(path, "rb") as f:  # the last usage is near the end: read 512 KB, not the whole file
    f.seek(max(0, os.path.getsize(path) - 512_000))
    tail = f.read().decode("utf-8", "ignore").splitlines()

context = 0
for line in reversed(tail):
    try:
        usage = json.loads(line).get("message", {}).get("usage")
    except (ValueError, AttributeError):
        continue
    if usage:
        context = sum(usage.get(k) or 0 for k in
                      ("input_tokens", "cache_creation_input_tokens", "cache_read_input_tokens"))
        break
if context < start:
    sys.exit(0)

level = (context - start) // step + 1
os.makedirs(state_dir, exist_ok=True)
state = os.path.join(state_dir, session)
try:
    seen = int(open(state).read().strip() or 0)
except (OSError, ValueError):
    seen = 0
if level <= seen:
    sys.exit(0)
open(state, "w").write(str(level))
print(json.dumps({"systemMessage":
    f"[compact-nudge] Context is {context // 1000}k tokens. Every request re-reads all of it: "
    f"run /compact (keep files, decisions, failing tests, next command) or /clear on a topic change."}))
EOF
