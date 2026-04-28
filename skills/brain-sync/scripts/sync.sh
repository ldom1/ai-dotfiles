#!/usr/bin/env bash
# brain-sync/sync.sh — sync Local Brain, ai-dotfiles, and clawvis git repos
# Usage: sync.sh start | end
set -euo pipefail

# ── Load config ──────────────────────────────────────────────────────────────
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_FILE=""
if [[ -n "${BRAIN_ENV_FILE:-}" ]]; then
  ENV_FILE="${BRAIN_ENV_FILE}"
elif [[ -f "$SCRIPT_DIR/brain.env" ]]; then
  ENV_FILE="$SCRIPT_DIR/brain.env"
else
  ENV_FILE="$(cd "$SCRIPT_DIR/../../.." && pwd)/config/brain.env"
fi

if [[ ! -f "$ENV_FILE" ]]; then
  echo "[brain-sync] ERROR: brain config not found." >&2
  echo "[brain-sync] Set BRAIN_ENV_FILE, or add brain.env beside this script, or use ai-dotfiles (config/brain.env). Tried: ${BRAIN_ENV_FILE:-}(env), $SCRIPT_DIR/brain.env, $(cd "$SCRIPT_DIR/../../.." && pwd)/config/brain.env" >&2
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

AI_DOTFILES_PATH="$(cd "$SCRIPT_DIR/../../.." && pwd)"
CLAWVIS_PATH="${CLAWVIS_PATH:-$HOME/lab/clawvis}"

# ── Helpers ───────────────────────────────────────────────────────────────────
repo_has_remote() {
  git -C "$1" remote | grep -q .
}

pull_repo() {
  local label="$1"
  local path="$2"

  if [[ ! -d "$path/.git" ]]; then
    echo "[$label] WARNING: $path is not a git repo, skipping pull."
    return 0
  fi

  if ! repo_has_remote "$path"; then
    echo "[$label] WARNING: no remote configured, skipping pull."
    return 0
  fi

  local stashed=false
  if ! git -C "$path" diff --quiet || ! git -C "$path" diff --cached --quiet; then
    echo "[$label] Dirty working tree — stashing before pull."
    git -C "$path" stash push -m "brain-sync: pre-pull stash $(date '+%Y-%m-%dT%H:%M:%S')"
    stashed=true
  fi

  local branch
  branch="$(git -C "$path" rev-parse --abbrev-ref HEAD)"

  if ! git -C "$path" pull --rebase origin "$branch" 2>&1; then
    if git -C "$path" rev-parse --verify -q REBASE_HEAD &>/dev/null \
        || [[ -d "$path/.git/rebase-merge" ]] \
        || [[ -d "$path/.git/rebase-apply" ]]; then
      echo "[$label] ERROR: rebase conflict detected." >&2
      git -C "$path" rebase --abort 2>/dev/null || true
    else
      echo "[$label] ERROR: git pull failed." >&2
    fi
    if $stashed; then
      git -C "$path" stash pop || true
    fi
    echo "[$label] Fix access to $path or run git pull manually." >&2
    return 1
  fi

  if $stashed; then
    if ! git -C "$path" stash pop; then
      echo "[$label] WARNING: stash pop had conflicts — changes are in git stash." >&2
    fi
  fi

  echo "[$label] Up to date."
}

commit_push_repo() {
  local label="$1"
  local path="$2"

  if [[ ! -d "$path/.git" ]]; then
    echo "[$label] WARNING: $path is not a git repo, skipping."
    return 0
  fi

  if git -C "$path" diff --quiet \
      && git -C "$path" diff --cached --quiet \
      && [[ -z "$(git -C "$path" ls-files --others --exclude-standard)" ]]; then
    echo "[$label] No changes to commit."
  else
    git -C "$path" add -A
    git -C "$path" commit -m "$label: session sync $(date '+%Y-%m-%dT%H:%M:%S')"
    echo "[$label] Committed."
  fi

  if ! repo_has_remote "$path"; then
    echo "[$label] WARNING: no remote configured, skipping push."
    return 0
  fi

  local branch
  branch="$(git -C "$path" rev-parse --abbrev-ref HEAD)"

  if ! git -C "$path" push origin "$branch" 2>&1; then
    echo "[$label] ERROR: push failed (remote rejected or no network)." >&2
    echo "[$label] Your commit is local — run 'git push' in $path when ready." >&2
    return 1
  fi

  echo "[$label] Pushed successfully."
}

# ── Commands ──────────────────────────────────────────────────────────────────
cmd_start() {
  echo "[brain-sync] Session start — pulling repos..."

  pull_repo "brain"      "$BRAIN_PATH"
  pull_repo "dotfiles"   "$AI_DOTFILES_PATH"
  pull_repo "clawvis"    "$CLAWVIS_PATH"

  # After successful brain pull, call brain-route for session mode decision
  echo "[brain-sync] Calling brain-route for session mode decision..."
  bash ~/ai-dotfiles/skills/brain-route/scripts/route.sh
}

cmd_end() {
  echo "[brain-sync] Session end — committing and pushing repos..."

  commit_push_repo "brain"    "$BRAIN_PATH"
  commit_push_repo "dotfiles" "$AI_DOTFILES_PATH"
  commit_push_repo "clawvis"  "$CLAWVIS_PATH"
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
