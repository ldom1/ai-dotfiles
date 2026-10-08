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

# Claude Code swaps hook output over ~10,000 characters for a file path and a
# 2 KB preview, so none of it reaches the model. Buffer stdout; pitfalls (printed
# last) get whatever budget the rest leaves.
OUTPUT_MAX_BYTES=9500
OUT_BUF=$(mktemp)
exec 3>&1 >"$OUT_BUF"
trap 'exec 1>&3; cat "$OUT_BUF"; rm -f "$OUT_BUF"' EXIT

# ── Settings drift (e.g. after a git pull that changed settings.json.tpl).
# merge-settings.py --dry-run lists what install.sh would add. Plugin and
# marketplace drift alone auto-runs install.sh. Drift in permissions, env or
# hooks is only reported: it changes behavior, so the user runs install.sh.
# Changes take effect from the *next* session — Claude Code has already read
# settings.json by the time this hook runs.
TPL_FILE="$AI_DOTFILES/.claude/settings.json.tpl"
SETTINGS_FILE="$AI_DOTFILES/.claude/settings.json"
MERGE="$AI_DOTFILES/scripts/merge-settings.py"
if [[ -f "$TPL_FILE" && -f "$MERGE" ]]; then
  # Key paths of planned additions, e.g. enabledPlugins.x, permissions.deny, hooks.Stop
  ADDS=$(python3 "$MERGE" --dry-run "$TPL_FILE" "$SETTINGS_FILE" 2>/dev/null | sed -n 's/^add \([^:]*\):.*/\1/p' | awk '!seen[$0]++' || true)
  NEW_KEYS=$(grep -v -E '^(enabledPlugins|extraKnownMarketplaces)\.' <<<"$ADDS" | paste -sd, - | sed 's/,/, /g' || true)
  if [[ -n "$NEW_KEYS" ]]; then
    echo "[install-check] template adds: $NEW_KEYS — run scripts/install.sh" | tee -a "$LOG_FILE"
  elif [[ -n "$ADDS" ]]; then
    echo "[install-check] settings.json missing: $(paste -sd, - <<<"$ADDS") — running scripts/install.sh" | tee -a "$LOG_FILE"
    RC=0
    RUN_OUT=$(bash "$AI_DOTFILES/scripts/install.sh" 2>&1) || RC=$?
    echo "$RUN_OUT" >>"$LOG_FILE"
    if (( RC == 0 )); then
      echo "[install-check] install.sh done — new plugins active from next session"
    else
      grep '^CONFLICT ' <<<"$RUN_OUT" || true
      echo "[install-check] install.sh failed (exit $RC) — see $LOG_FILE"
    fi
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
  # Summarize the last exit log before pulling (so user sees what happened on /exit)
  # One status line (+ ≤ 5 notable lines); the full log stays readable as .prev.
  EXIT_LOG="$HOME/.claude/logs/brain-sync-end.log"
  if [[ -f "$EXIT_LOG" ]]; then
    python3 "$AI_DOTFILES/scripts/summarize-sync-log.py" "$EXIT_LOG" || tail -5 "$EXIT_LOG"
    mv -f "$EXIT_LOG" "$EXIT_LOG.prev"
  fi
  "$SYNC" start >>"$LOG_FILE" 2>&1 || true
  bash "$AI_DOTFILES/scripts/log-skill-usage.sh" brain-sync "claude:sessionStart" 2>/dev/null || true
fi

# Always emit BRAIN_PATH so Bash tool processes can use it
echo "BRAIN_PATH=${BRAIN_PATH:-unset}"

# BRAIN_LOAD_SLIM=1: skip project note entirely (fast sessions, throwaway work)
if [[ "${BRAIN_LOAD_SLIM:-0}" == "1" ]]; then
  echo "[brain-load] slim mode — project note skipped"
  exit 0
fi

# Run load.sh; cap context injection at 30 lines; redirect verbose stderr to log
# Claude Code already @-imports .claude/memory/ via the project CLAUDE.md
BRAIN_LOAD_SKIP_MEMORY=1 "$LOAD" 2>>"$LOG_FILE" | head -30 || true
bash "$AI_DOTFILES/scripts/log-skill-usage.sh" brain-load "claude:sessionStart" 2>/dev/null || true

# Vendored skill pins vs GitHub latest (cached ≤24h, fail-open)
bash "$AI_DOTFILES/scripts/check-vendored-skill-updates.sh" --inject 2>>"$LOG_FILE" || true

# local-ci runner manifest vs latest ubuntu24 release (cached 7d, report only, fail-open)
bash "$AI_DOTFILES/scripts/check-ci-runner-drift.sh" 2>/dev/null || true

# Maintenance nudge: /brain-audit is manual; its digest step writes meta/last-maintenance.md.
LAST_MAINT=$(grep -oP '\*\*Epoch Seconds:\*\* \K[0-9]+' "${BRAIN_PATH}/meta/last-maintenance.md" 2>/dev/null || echo 0)
if (( $(date +%s) - LAST_MAINT > 7 * 86400 )); then
  echo "[brain] maintenance due — last /brain-audit: $(date -d "@$LAST_MAINT" +%F 2>/dev/null || echo never). Offer it to the user."
fi

# Inject operational constraints from ai-agents knowledge base
AI_AGENTS_DIR="${BRAIN_PATH}/resources/operational/ai-agents"

# pitfalls.md is a distilled rule list (lessons-learned merged into it).
PITFALLS="$AI_AGENTS_DIR/pitfalls.md"
if [[ -f "$PITFALLS" ]]; then
  PITFALLS_MAX_BYTES=$(( OUTPUT_MAX_BYTES - $(wc -c <"$OUT_BUF") - 200 ))
  (( PITFALLS_MAX_BYTES > 0 )) || PITFALLS_MAX_BYTES=0
  echo "--- AI-AGENTS PITFALLS (constraints) ---"
  # Write-time gate: scripts/check-pitfalls-budget.sh. This is the last-resort cut: whole sections only.
  python3 "$AI_DOTFILES/scripts/fit-sections.py" "$PITFALLS" "$PITFALLS_MAX_BYTES" \
    || head -c "$PITFALLS_MAX_BYTES" "$PITFALLS"
  echo "--- END PITFALLS ---"
fi
