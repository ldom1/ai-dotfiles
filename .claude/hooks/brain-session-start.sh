#!/usr/bin/env bash
# SessionStart: brain-sync start (startup/resume only) + brain-load; export BRAIN_PATH for Bash tools.
# BRAIN_LOAD_SLIM=1 — skip project note for fast/throwaway sessions.
set -euo pipefail

AI_DOTFILES="${AI_DOTFILES:-$HOME/ai-dotfiles}"
SYNC="$AI_DOTFILES/skills/brain-sync/scripts/sync.sh"
LOAD="$AI_DOTFILES/skills/brain-load/scripts/load.sh"
LOG_DIR="$AI_DOTFILES/.claude/logs"
LOG_FILE="$LOG_DIR/brain-load.log"

mkdir -p "$LOG_DIR"

ENV_FILE="${BRAIN_ENV_FILE:-}"
if [[ -z "$ENV_FILE" || ! -f "$ENV_FILE" ]]; then
  ENV_FILE="$AI_DOTFILES/config/brain.env"
fi
if [[ -f "$ENV_FILE" ]]; then
  # shellcheck source=/dev/null
  source "$ENV_FILE"
fi
if [[ -n "${CLAUDE_ENV_FILE:-}" && -n "${BRAIN_PATH:-}" ]]; then
  printf 'export BRAIN_PATH=%q\n' "$BRAIN_PATH" >> "$CLAUDE_ENV_FILE"
fi

# Hook JSON is on stdin; do not rely on jq (may be missing in hook PATH).
INPUT=$(cat || true)
SOURCE="startup"
if [[ "$INPUT" =~ \"source\"[[:space:]]*:[[:space:]]*\"([^\"]+)\" ]]; then
  SOURCE="${BASH_REMATCH[1]}"
fi

if [[ "$SOURCE" == "startup" || "$SOURCE" == "resume" ]]; then
  "$SYNC" start >>"$LOG_FILE" 2>&1 || true
fi

# Always emit BRAIN_PATH so Bash tool processes can use it
echo "BRAIN_PATH=${BRAIN_PATH:-unset}"

# BRAIN_LOAD_SLIM=1: skip project note entirely (fast sessions, throwaway work)
if [[ "${BRAIN_LOAD_SLIM:-0}" == "1" ]]; then
  echo "[brain-load] slim mode — project note skipped"
  exit 0
fi

# Run load.sh; cap context injection at 30 lines; redirect verbose stderr to log
"$LOAD" 2>>"$LOG_FILE" | head -30 || true

# Inject operational constraints from ai-agents knowledge base
AI_AGENTS_DIR="${BRAIN_PATH}/resources/operational/ai-agents"

if [[ -f "$AI_AGENTS_DIR/pitfalls.md" ]]; then
  echo "--- AI-AGENTS PITFALLS (hard constraints) ---"
  cat "$AI_AGENTS_DIR/pitfalls.md"
  echo "--- END PITFALLS ---"
fi

if [[ -f "$AI_AGENTS_DIR/lessons-learned.md" ]]; then
  echo "--- AI-AGENTS LESSONS LEARNED (last 3 entries) ---"
  # Extract last 3 dated entries (## YYYY-MM-DD sections), cap at 45 lines
  python3 - "$AI_AGENTS_DIR/lessons-learned.md" <<'EOF' 2>/dev/null | head -45 || tail -45 "$AI_AGENTS_DIR/lessons-learned.md" | head -45
import sys, re
content = open(sys.argv[1]).read()
entries = [e.strip() for e in re.split(r'^---$', content, flags=re.MULTILINE) if re.match(r'^## \d{4}-\d{2}-\d{2}', e.strip())]
for e in entries[-3:]:
    print(e)
    print('---')
EOF
  echo "--- END LESSONS ---"
fi
