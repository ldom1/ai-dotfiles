#!/usr/bin/env bash
# Pre-bake Local Brain inject into ~/.cursor/rules (works from any cwd).
set -euo pipefail

AI_DOTFILES="${AI_DOTFILES:-$HOME/ai-dotfiles}"
HOOKS_DIR="${AI_DOTFILES}/.cursor/hooks"
LOG_DIR="${BRAIN_HOOKS_LOG_DIR:-$HOME/.cursor/logs}"
SIDECAR="$LOG_DIR/brain-hooks-last-context.md"
mkdir -p "$LOG_DIR"

# shellcheck source=/dev/null
source "$HOOKS_DIR/lib-inject-rule.sh"

ENV_FILE="${BRAIN_ENV_FILE:-$AI_DOTFILES/config/brain.env}"
# shellcheck source=/dev/null
[[ -f "$ENV_FILE" ]] && source "$ENV_FILE"
BRAIN_PATH="${BRAIN_PATH:-}"

# load.sh uses cwd for slug — run from caller's cwd (any project)
LOAD_OUT="$(bash "$AI_DOTFILES/skills/brain-load/scripts/load.sh" 2>>"$LOG_DIR/brain-hooks-session.log" | head -30 || true)"

CANARY="[brain-hooks] sessionStart OK reason=prewarm — Local Brain context injected (CLI)."
CTX="${CANARY}

${LOAD_OUT}

--- PITFALLS BEHAVIOR (CLI) ---
Canonical: ${BRAIN_PATH:-unset}/resources/operational/ai-agents/pitfalls.md
Before substantive work: Read that file (or @claude-pitfall); treat matches as hard constraints.
--- END PITFALLS BEHAVIOR ---"

printf '%s\n' "$CTX" >"$SIDECAR"
brain_hooks_write_inject_rule "$CTX"
bash "$AI_DOTFILES/scripts/log-skill-usage.sh" brain-load "cursor:prewarm" 2>/dev/null || true
echo "[brain-hooks] prewarm wrote user rule + sidecar (cwd=$(pwd))" >&2
