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

# ── Auto-heal settings.json if it's behind settings.json.tpl (e.g. after a
# git pull that enabled new plugins but install.sh wasn't re-run). Only
# checks keys install.sh actually templates (enabledPlugins,
# extraKnownMarketplaces); local-only additions in settings.json are left
# untouched. Takes effect from the *next* session — Claude Code has already
# read settings.json by the time this hook runs.
TPL_FILE="$AI_DOTFILES/.claude/settings.json.tpl"
SETTINGS_FILE="$AI_DOTFILES/.claude/settings.json"
if [[ -f "$TPL_FILE" ]]; then
  DRIFT=$(python3 - "$TPL_FILE" "$SETTINGS_FILE" 2>/dev/null <<'EOF' || true
import json, sys
tpl_path, cur_path = sys.argv[1], sys.argv[2]
tpl = json.load(open(tpl_path))
try:
    cur = json.load(open(cur_path))
except (FileNotFoundError, json.JSONDecodeError):
    cur = {}
missing = []
for name, enabled in tpl.get("enabledPlugins", {}).items():
    if cur.get("enabledPlugins", {}).get(name) != enabled:
        missing.append(name)
for name in tpl.get("extraKnownMarketplaces", {}):
    if name not in cur.get("extraKnownMarketplaces", {}):
        missing.append(f"marketplace:{name}")
print(",".join(missing))
EOF
  )
  if [[ -n "$DRIFT" ]]; then
    echo "[install-check] settings.json missing: $DRIFT — running scripts/install.sh" | tee -a "$LOG_FILE"
    bash "$AI_DOTFILES/scripts/install.sh" >>"$LOG_FILE" 2>&1 \
      && echo "[install-check] install.sh done — new plugins active from next session" \
      || echo "[install-check] install.sh failed — see $LOG_FILE"
  fi
fi

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
  # Show last exit log before pulling (so user sees what happened on /exit)
  EXIT_LOG="$HOME/.claude/logs/brain-sync-end.log"
  if [[ -f "$EXIT_LOG" ]]; then
    echo "--- LAST EXIT (brain-sync) ---"
    tail -30 "$EXIT_LOG"
    echo "--- END LAST EXIT ---"
    rm -f "$EXIT_LOG"
  fi
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
