#!/usr/bin/env bash
# merge-memory.sh — backfill OKF-style frontmatter and missing ## sections into
# existing .claude/memory/ files without touching their content.
# Usage: merge-memory.sh <project-path>
#        merge-memory.sh --all
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
AI_DOTFILES="$(cd "$SCRIPT_DIR/.." && pwd)"
TEMPLATE_DIR="$AI_DOTFILES/config/memory-templates"
ENV_FILE="${BRAIN_ENV_FILE:-$AI_DOTFILES/config/brain.env}"

if [[ ! -f "$ENV_FILE" ]]; then
  echo "[merge-memory] ERROR: brain.env not found at $ENV_FILE" >&2
  exit 1
fi
# shellcheck source=/dev/null
source "$ENV_FILE"

REGISTRY="$AI_DOTFILES/config/brain-projects.tsv"

merge_one() {
  local project_path="$1"
  local memory_dir="$project_path/.claude/memory"

  if [[ ! -d "$memory_dir" ]]; then
    echo "[merge-memory] SKIP: no .claude/memory/ at $project_path" >&2
    return 0
  fi

  local changed=0
  for tpl in "$TEMPLATE_DIR"/*.md; do
    local fname
    fname="$(basename "$tpl")"
    local dest="$memory_dir/$fname"
    [[ -f "$dest" ]] || continue
    result="$(python3 "$SCRIPT_DIR/merge-memory-md.py" "$tpl" "$dest")"
    if [[ "$result" == "changed" ]]; then
      echo "[merge-memory] Updated: $dest"
      (( changed++ )) || true
    fi
  done

  if (( changed == 0 )); then
    echo "[merge-memory] $project_path — already up to date"
  else
    echo "[merge-memory] $project_path — $changed file(s) updated"
  fi
}

ARG="${1:-}"

if [[ "$ARG" == "--all" ]]; then
  if [[ ! -f "$REGISTRY" ]]; then
    echo "[merge-memory] ERROR: registry not found at $REGISTRY" >&2
    exit 1
  fi
  while IFS=$'\t' read -r slug path _rest; do
    [[ "$slug" == "slug" ]] && continue
    [[ -z "$path" ]] && continue
    merge_one "$path"
  done < "$REGISTRY"
elif [[ -n "$ARG" ]]; then
  merge_one "$ARG"
else
  echo "Usage: merge-memory.sh <project-path>" >&2
  echo "       merge-memory.sh --all" >&2
  exit 1
fi
