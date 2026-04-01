#!/usr/bin/env bash
# brain-sync/sync.sh — sync Local Brain git repo
# Usage: sync.sh start | end
set -euo pipefail

# ── Load config ──────────────────────────────────────────────────────────────
# Priority: $BRAIN_ENV_FILE → ./brain.env next to this script → ai-dotfiles config/brain.env
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_FILE=""
if [[ -n "${BRAIN_ENV_FILE:-}" ]]; then
  ENV_FILE="${BRAIN_ENV_FILE}"
elif [[ -f "$SCRIPT_DIR/brain.env" ]]; then
  ENV_FILE="$SCRIPT_DIR/brain.env"
else
  ENV_FILE="$(cd "$SCRIPT_DIR/../.." && pwd)/config/brain.env"
fi

if [[ ! -f "$ENV_FILE" ]]; then
  echo "[brain-sync] ERROR: brain config not found." >&2
  echo "[brain-sync] Set BRAIN_ENV_FILE, or add brain.env beside this script, or use ai-dotfiles (config/brain.env). Tried: ${BRAIN_ENV_FILE:-}(env), $SCRIPT_DIR/brain.env, $(cd "$SCRIPT_DIR/../.." && pwd)/config/brain.env" >&2
  exit 1
fi

# shellcheck source=/dev/null
source "$ENV_FILE"

if [[ -z "${BRAIN_PATH:-}" ]]; then
  echo "[brain-sync] ERROR: BRAIN_PATH is not set in $ENV_FILE" >&2
  exit 1
fi

if [[ ! -d "$BRAIN_PATH/.git" ]]; then
  echo "[brain-sync] ERROR: $BRAIN_PATH is not a git repository" >&2
  exit 1
fi

cd "$BRAIN_PATH"

# ── Helpers ───────────────────────────────────────────────────────────────────
has_remote() {
  git remote | grep -q .
}

# ── Commands ──────────────────────────────────────────────────────────────────
cmd_start() {
  echo "[brain-sync] Session start — pulling brain..."

  if ! has_remote; then
    echo "[brain-sync] WARNING: no remote configured, skipping pull."
    return 0
  fi

  # Stash any uncommitted changes so pull can proceed cleanly
  local stashed=false
  if ! git diff --quiet || ! git diff --cached --quiet; then
    echo "[brain-sync] Dirty working tree detected — stashing before pull."
    git stash push -m "brain-sync: pre-pull stash $(date '+%Y-%m-%dT%H:%M:%S')"
    stashed=true
  fi

  # Pull with rebase
  if ! git pull --rebase origin "$(git rev-parse --abbrev-ref HEAD)" 2>&1; then
    echo "[brain-sync] ERROR: rebase conflict detected." >&2
    git rebase --abort 2>/dev/null || true
    if $stashed; then
      git stash pop || true
    fi
    echo "[brain-sync] Rebase aborted. Brain is at its last clean state." >&2
    echo "[brain-sync] ACTION REQUIRED: resolve conflicts in $BRAIN_PATH manually." >&2
    return 1
  fi

  # Re-apply stash if we stashed
  if $stashed; then
    if ! git stash pop; then
      echo "[brain-sync] WARNING: stash pop had conflicts — your changes are in git stash." >&2
    fi
  fi

  echo "[brain-sync] Brain is up to date."
}

cmd_end() {
  echo "[brain-sync] Session end — committing and pushing brain..."

  # Nothing to commit?
  if git diff --quiet && git diff --cached --quiet && [[ -z "$(git ls-files --others --exclude-standard)" ]]; then
    echo "[brain-sync] No changes to commit."
  else
    git add -A
    git commit -m "brain: session sync $(date '+%Y-%m-%dT%H:%M:%S')"
    echo "[brain-sync] Committed."
  fi

  if ! has_remote; then
    echo "[brain-sync] WARNING: no remote configured, skipping push."
    return 0
  fi

  if ! git push origin "$(git rev-parse --abbrev-ref HEAD)" 2>&1; then
    echo "[brain-sync] ERROR: push failed (remote rejected or no network)." >&2
    echo "[brain-sync] Your commit is local — run 'git push' in $BRAIN_PATH when ready." >&2
    return 1
  fi

  echo "[brain-sync] Brain pushed successfully."
}

# ── Dispatch ─────────────────────────────────────────────────────────────────
case "${1:-}" in
  start) cmd_start ;;
  end)   cmd_end   ;;
  *)
    echo "Usage: $(basename "$0") start|end" >&2
    exit 1
    ;;
esac
