#!/usr/bin/env bash
# brain-sync/sync.sh — sync Local Brain and ai-dotfiles git repos
# Usage: sync.sh start | end
set -euo pipefail

# ── Pretty logger ─────────────────────────────────────────────────────────────
_RED='\033[0;31m'; _GRN='\033[0;32m'; _YLW='\033[0;33m'
_CYN='\033[0;36m'; _DIM='\033[2m'; _BLD='\033[1m'; _RST='\033[0m'

_log()  { printf "${_BLD}%-10s${_RST} %s\n"      "$1" "$2" >&2; }
_ok()   { printf "${_GRN}✓${_RST} %-10s %s\n"    "$1" "$2" >&2; }
_warn() { printf "${_YLW}⚠${_RST} %-10s %s\n"    "$1" "$2" >&2; }
_err()  { printf "${_RED}✗${_RST} %-10s %s\n"    "$1" "$2" >&2; }
_info() { printf "${_CYN}▸${_RST} %-10s %s\n"    "$1" "$2" >&2; }
_dim()  { printf "  ${_DIM}%-10s %s${_RST}\n"    "$1" "$2" >&2; }

_header() {
  local ts; ts="$(date '+%Y-%m-%dT%H:%M:%S')"
  printf "\n${_BLD}${_CYN}━━━ brain-sync · %s · %s ━━━${_RST}\n\n" "$1" "$ts" >&2
}
_footer() {
  printf "\n${_DIM}━━━ done in %ss ━━━${_RST}\n\n" "$1" >&2
}
_SYNC_START_TS=$(date +%s)

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
  _err "brain-sync" "brain config not found."
  _err "brain-sync" "Set BRAIN_ENV_FILE, or add brain.env beside this script, or use ai-dotfiles. Tried: ${BRAIN_ENV_FILE:-}(env), $SCRIPT_DIR/brain.env, $(cd "$SCRIPT_DIR/../../.." && pwd)/config/brain.env"
  exit 1
fi

# shellcheck source=/dev/null
source "$ENV_FILE"

if [[ -z "${BRAIN_PATH:-}" ]]; then
  _err "brain-sync" "BRAIN_PATH is not set in $ENV_FILE"
  exit 1
fi

if [[ ! -d "$BRAIN_PATH/.git" ]]; then
  _err "brain-sync" "$BRAIN_PATH is not a git repository"
  exit 1
fi

AI_DOTFILES_PATH="$(cd "$SCRIPT_DIR/../../.." && pwd)"

# ── Helpers ───────────────────────────────────────────────────────────────────
repo_has_remote() {
  git -C "$1" remote | grep -q .
}

pull_repo() {
  local label="$1"
  local path="$2"

  if [[ ! -d "$path/.git" ]]; then
    _warn "$label" "$path is not a git repo, skipping pull."
    return 0
  fi

  if ! repo_has_remote "$path"; then
    _warn "$label" "no remote configured, skipping pull."
    return 0
  fi

  local stashed=false
  if ! git -C "$path" diff --quiet || ! git -C "$path" diff --cached --quiet; then
    _info "$label" "dirty working tree — stashing before pull"
    git -C "$path" stash push -m "brain-sync: pre-pull stash $(date '+%Y-%m-%dT%H:%M:%S')" &>/dev/null
    stashed=true
  fi

  local branch
  branch="$(git -C "$path" rev-parse --abbrev-ref HEAD)"

  # Retry up to 3 times to handle transient Windows file locks (e.g. GitKraken background fetch)
  local pull_ok=false
  local attempt
  for attempt in 1 2 3; do
    if git -C "$path" pull --rebase origin "$branch" &>/dev/null; then
      pull_ok=true
      break
    fi
    if git -C "$path" rev-parse --verify -q REBASE_HEAD &>/dev/null \
        || [[ -d "$path/.git/rebase-merge" ]] \
        || [[ -d "$path/.git/rebase-apply" ]]; then
      _err "$label" "rebase conflict detected — aborting"
      git -C "$path" rebase --abort 2>/dev/null || true
      break
    fi
    if [[ $attempt -lt 3 ]]; then
      _warn "$label" "pull attempt $attempt failed (transient lock?), retrying in 3s…"
      sleep 3
    fi
  done

  if ! $pull_ok; then
    if $stashed; then
      git -C "$path" stash pop &>/dev/null || true
    fi
    _err "$label" "git pull failed after 3 attempts — run 'git pull' in $path manually"
    return 1
  fi

  if $stashed; then
    if ! git -C "$path" stash pop &>/dev/null; then
      _warn "$label" "stash pop had conflicts — changes are in git stash"
    fi
  fi

  _ok "$label" "up to date → $branch"
}

commit_push_repo() {
  local label="$1"
  local path="$2"
  local commit_msg="${3:-"$label: session sync $(date '+%Y-%m-%dT%H:%M:%S')"}"

  if [[ ! -d "$path/.git" ]]; then
    _warn "$label" "$path is not a git repo, skipping."
    return 0
  fi

  if git -C "$path" diff --quiet \
      && git -C "$path" diff --cached --quiet \
      && [[ -z "$(git -C "$path" ls-files --others --exclude-standard)" ]]; then
    _dim "$label" "no changes to commit"
  else
    local changed
    changed="$(git -C "$path" status --short | wc -l | tr -d ' ')"
    git -C "$path" add -A
    git -C "$path" commit -m "$commit_msg" &>/dev/null
    _ok "$label" "committed · ${changed} file(s) changed"
  fi

  if ! repo_has_remote "$path"; then
    _warn "$label" "no remote configured, skipping push."
    return 0
  fi

  local branch
  branch="$(git -C "$path" rev-parse --abbrev-ref HEAD)"

  if ! git -C "$path" push origin "$branch" &>/dev/null; then
    _err "$label" "push failed (remote rejected or no network)"
    _err "$label" "your commit is local — run 'git push' in $path when ready"
    return 1
  fi

  _ok "$label" "pushed → $branch"
}

# ── Commands ──────────────────────────────────────────────────────────────────
cmd_start() {
  _header "session start"

  pull_repo "brain"    "$BRAIN_PATH"       || _warn "brain-sync" "brain pull failed — continuing with local state."
  pull_repo "dotfiles" "$AI_DOTFILES_PATH" || true

  local sync_script="$AI_DOTFILES_PATH/scripts/sync-project.sh"
  if [[ -f "$sync_script" ]]; then
    _info "projects" "syncing project brains (vault → project)…"
    bash "$sync_script" --all 2>&1 || _warn "projects" "project brain sync had errors."
  fi

  _info "brain-route" "deciding session mode…"
  bash ~/ai-dotfiles/skills/brain-route/scripts/route.sh

  local elapsed=$(( $(date +%s) - _SYNC_START_TS ))
  _footer "$elapsed"
}

cmd_end() {
  _header "session end"

  local ts
  ts="$(date '+%Y-%m-%dT%H:%M:%S')"

  local sync_script="$AI_DOTFILES_PATH/scripts/sync-project.sh"
  if [[ -f "$sync_script" ]]; then
    _info "projects" "syncing project brains (project → vault)…"
    bash "$sync_script" --all 2>&1 || _warn "projects" "project brain sync had errors."
  fi

  commit_push_repo "brain"    "$BRAIN_PATH"       "brain: session sync $ts"

  if command -v qmd &>/dev/null && [[ -n "${QMD_INDEX_PATH:-}" ]]; then
    _info "qmd" "updating brain index…"
    INDEX_PATH="$QMD_INDEX_PATH" qmd update --collection brain 2>/dev/null || \
      _warn "qmd" "update failed (non-blocking)"
    _info "qmd" "refreshing brain embeddings…"
    INDEX_PATH="$QMD_INDEX_PATH" qmd embed --collection brain 2>/dev/null || \
      _warn "qmd" "embed failed (non-blocking)"
  fi

  local elapsed=$(( $(date +%s) - _SYNC_START_TS ))
  _footer "$elapsed"
}

# ── Dispatch ─────────────────────────────────────────────────────────────────
case "${1:-}" in
  start) cmd_start ;;
  end)   cmd_end   ;;
  *)
    printf "Usage: %s start|end\n" "$(basename "$0")" >&2
    exit 1
    ;;
esac
