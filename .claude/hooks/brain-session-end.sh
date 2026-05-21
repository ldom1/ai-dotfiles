#!/usr/bin/env bash
# SessionEnd: check for implementation notes → systemMessage if missing → brain-sync end
set -euo pipefail

AI_DOTFILES="${AI_DOTFILES:-$HOME/ai-dotfiles}"
LOG="$HOME/.claude/logs/brain-sync-end.log"
mkdir -p "$(dirname "$LOG")"

# Load BRAIN_PATH
ENV_FILE="${BRAIN_ENV_FILE:-$AI_DOTFILES/config/brain.env}"
[[ -f "$ENV_FILE" ]] && source "$ENV_FILE"
BRAIN_PATH="${BRAIN_PATH:-}"
TODAY=$(date +%Y-%m-%d)

# Consume stdin (SessionEnd may provide hook JSON — not used here)
INPUT=$(cat || true)

# ── Check for today's implementation notes ────────────────────────────────────
MISSING_NOTES=false
if [[ -n "$BRAIN_PATH" ]]; then
  IMPL_DIR="$BRAIN_PATH/inbox/daily/implementation"
  if ! find "$IMPL_DIR" -name "${TODAY}-*.md" 2>/dev/null | grep -q .; then
    MISSING_NOTES=true
  fi
fi

# ── Emit systemMessage if notes are missing ───────────────────────────────────
# Claude Code injects this as a system message — gives Claude a final turn to
# write missing notes before the session closes. Also written to the end-session
# log so it surfaces in LAST EXIT at the next session start (fallback).
if [[ "$MISSING_NOTES" == "true" && -n "$BRAIN_PATH" ]]; then
  MSG="No implementation notes were written for this session (${TODAY}). If this session had substantive work, write a brief note to: ${BRAIN_PATH}/inbox/daily/implementation/<project-name>/${TODAY}-<topic>.md — covering goal, changes made, commands/tests run, and follow-ups. Add macro lessons learned or pitfalls to the brain if applicable (keep them high-level, not issue-specific). When done, run: bash ~/ai-dotfiles/skills/brain-sync/scripts/sync.sh end"
  # JSON to stdout → Claude Code picks it up as systemMessage
  printf '{"systemMessage": "%s"}\n' "$(printf '%s' "$MSG" | sed 's/\\/\\\\/g; s/"/\\"/g')"
  # Also write to end-session log → shown in LAST EXIT at next SessionStart (fallback)
  {
    echo ""
    echo "⚠️  [brain-session-end] No implementation notes found for ${TODAY}"
    echo "    Write to: ${BRAIN_PATH}/inbox/daily/implementation/<project>/${TODAY}-<topic>.md"
    echo "    Then run: bash ~/ai-dotfiles/skills/brain-sync/scripts/sync.sh end"
  } >> "$LOG"
fi

# ── Sync vault (commit + push whatever is on disk) ────────────────────────────
# If Claude responded to the systemMessage and wrote notes, a second sync is
# needed — the systemMessage instructs Claude to call sync.sh end explicitly.
"$AI_DOTFILES/skills/brain-sync/scripts/sync.sh" end 2>&1 | tee -a "$LOG" >&2 || true
