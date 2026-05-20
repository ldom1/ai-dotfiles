#!/usr/bin/env bash
# sync-project.sh — manual bidirectional rsync for registered project brains
# Usage: sync-project.sh <project-path>
#        sync-project.sh --all
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
AI_DOTFILES="$(cd "$SCRIPT_DIR/.." && pwd)"
ENV_FILE="${BRAIN_ENV_FILE:-$AI_DOTFILES/config/brain.env}"
if [[ ! -f "$ENV_FILE" ]]; then
  echo "[sync-project] ERROR: brain.env not found at $ENV_FILE" >&2
  exit 1
fi
# shellcheck source=/dev/null
source "$ENV_FILE"
if [[ -z "${BRAIN_PATH:-}" ]]; then
  echo "[sync-project] ERROR: BRAIN_PATH not set in $ENV_FILE" >&2
  exit 1
fi

REGISTRY="$AI_DOTFILES/config/brain-projects.tsv"

sync_one() {
  local project_path="$1"

  if [[ ! -d "$project_path" ]]; then
    echo "[sync-project] WARNING: $project_path does not exist, skipping."
    return 0
  fi

  project_path="$(realpath "$project_path")"

  local project_brain="$project_path/.claude/brain"
  if [[ ! -d "$project_brain" ]]; then
    echo "[sync-project] WARNING: no .claude/brain/ in $project_path, skipping."
    return 0
  fi

  local brain_project="$project_path/.brain-project"
  if [[ ! -f "$brain_project" ]]; then
    echo "[sync-project] WARNING: no .brain-project in $project_path, skipping."
    return 0
  fi

  local slug
  slug="$(grep -m1 '[^[:space:]]' "$brain_project" | tr -d '[:space:]')"
  local vault_brain="$BRAIN_PATH/projects/$slug"
  mkdir -p "$vault_brain"

  echo "[sync-project] $slug: syncing $project_brain ↔ $vault_brain"

  # vault → project (pull newer vault files into project)
  rsync -a --update "$vault_brain/" "$project_brain/"

  # project → vault (push newer project files into vault)
  rsync -a --update "$project_brain/" "$vault_brain/"

  echo "[sync-project] $slug: done."
}

if [[ "${1:-}" == "--all" ]]; then
  if [[ ! -f "$REGISTRY" ]]; then
    echo "[sync-project] No registry at $REGISTRY — nothing to sync."
    exit 0
  fi
  while IFS=$'\t' read -r name abs_path _rest; do
    [[ "$name" == "name" ]] && continue
    [[ -z "$name" ]] && continue
    sync_one "$abs_path"
  done < "$REGISTRY"
else
  if [[ -z "${1:-}" ]]; then
    echo "Usage: $(basename "$0") <project-path> | --all" >&2
    exit 1
  fi
  sync_one "$1"
fi
