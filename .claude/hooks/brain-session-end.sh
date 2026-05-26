#!/usr/bin/env bash
# SessionEnd: check for implementation notes → warn in log → brain-sync end
#
# NOTE: SessionEnd hooks do NOT give Claude a final turn. The /capture skill is the
# primary path for end-of-session work (notes, pitfalls, lessons). This hook is a
# fallback that surfaces a warning in LAST EXIT at next session start if notes were
# skipped, and always commits+pushes whatever is already on disk.
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

# ── Sync vault (commit + push whatever is on disk) ────────────────────────────
"$AI_DOTFILES/skills/brain-sync/scripts/sync.sh" end 2>&1 | tee -a "$LOG" >&2 || true

# ── Warn if implementation notes are missing (written AFTER sync so tail -20 shows it) ──
if [[ -n "$BRAIN_PATH" ]]; then
  IMPL_DIR="$BRAIN_PATH/inbox/daily/implementation"
  if ! find "$IMPL_DIR" -name "${TODAY}-*.md" 2>/dev/null | grep -q .; then
    {
      echo ""
      echo "⚠️  [brain-session-end] No implementation notes found for ${TODAY}"
      echo "    Next session: run /capture skill or write manually to:"
      echo "    ${BRAIN_PATH}/inbox/daily/implementation/<project>/${TODAY}-<topic>.md"
    } | tee -a "$LOG" >&2
  fi
fi
