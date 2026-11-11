#!/usr/bin/env bash
# upgrade-project.sh — add missing template files to an existing project brain
# Usage: upgrade-project.sh <project-path>
#        upgrade-project.sh --all
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
AI_DOTFILES="$(cd "$SCRIPT_DIR/.." && pwd)"
ENV_FILE="${BRAIN_ENV_FILE:-$AI_DOTFILES/config/brain.env}"
if [[ ! -f "$ENV_FILE" ]]; then
  echo "[upgrade-project] ERROR: brain.env not found at $ENV_FILE" >&2
  exit 1
fi
# shellcheck source=/dev/null
source "$ENV_FILE"
if [[ -z "${BRAIN_PATH:-}" ]]; then
  echo "[upgrade-project] ERROR: BRAIN_PATH not set in $ENV_FILE" >&2
  exit 1
fi

# shellcheck source=lib-mcp.sh
source "$SCRIPT_DIR/lib-mcp.sh"

TEMPLATE_DIR="$AI_DOTFILES/config/memory-templates"
REGISTRY="$AI_DOTFILES/config/brain-projects.tsv"

upgrade_one() {
  local project_path="$1"

  if [[ ! -d "$project_path" ]]; then
    echo "[upgrade-project] WARNING: $project_path does not exist, skipping."
    return 0
  fi

  project_path="$(realpath "$project_path")"

  local brain_project="$project_path/.brain-project"
  if [[ ! -f "$brain_project" ]]; then
    echo "[upgrade-project] WARNING: no .brain-project in $project_path, skipping."
    return 0
  fi

  local slug
  slug="$(grep -m1 '[^[:space:]]' "$brain_project" | tr -d '[:space:]')"

  local project_brain="$project_path/.claude/memory"
  # Migrate existing .claude/brain/ → .claude/memory/ if not yet migrated
  local old_brain="$project_path/.claude/brain"
  if [[ -d "$old_brain" && ! -d "$project_brain" ]]; then
    mv "$old_brain" "$project_brain"
    echo "[upgrade-project] Migrated $old_brain → $project_brain"
  fi
  local vault_brain="$BRAIN_PATH/projects/$slug"

  mkdir -p "$project_brain" "$vault_brain"
  bash "$AI_DOTFILES/skills/brain-load/scripts/instantiate.sh" --slug "$slug" --path "$project_path" | sed "s/^/[upgrade-project] /"

  local added=0
  for f in "$TEMPLATE_DIR"/*; do
    [[ -f "$f" && "$f" != *.tpl ]] || continue  # on-demand/ templates are copied by hand
    fname="$(basename "$f")"
    for dest in "$project_brain/$fname" "$vault_brain/$fname"; do
      if [[ ! -f "$dest" ]]; then
        cp "$f" "$dest"
        echo "[upgrade-project] Added: $dest"
        (( added++ )) || true
      elif [[ "$fname" == "settings.json" ]]; then
        # Merge: template provides defaults, existing values win
        merged="$(python3 - "$f" "$dest" <<'PY'
import json, sys
t = json.load(open(sys.argv[1]))
e = json.load(open(sys.argv[2]))
def deep_merge(base, override):
    result = dict(base)
    for k, v in override.items():
        if k in result and isinstance(result[k], dict) and isinstance(v, dict):
            result[k] = deep_merge(result[k], v)
        else:
            result[k] = v
    return result
print(json.dumps(deep_merge(t, e), indent=2))
PY
)" || { echo "[upgrade-project] ERROR: settings.json merge failed for $dest" >&2; return 1; }
        if [[ -n "$merged" ]]; then
          if [[ "$merged" != "$(cat "$dest")" ]]; then
            echo "$merged" > "$dest"
            echo "[upgrade-project] Merged: $dest"
            (( added++ )) || true
          fi
        fi
      elif [[ "$fname" == *.md ]]; then
        # Backfill frontmatter and append any ## sections the template gained since this file was written
        result="$(python3 "$SCRIPT_DIR/merge-memory-md.py" "$f" "$dest")"
        if [[ "$result" == "changed" ]]; then
          echo "[upgrade-project] Updated: $dest"
          (( added++ )) || true
        fi
      fi
    done
  done

  # Ensure registration
  if [[ -f "$REGISTRY" ]] && grep -qP "^${slug}\t" "$REGISTRY" 2>/dev/null; then
    : # already registered
  else
    if [[ ! -f "$REGISTRY" ]]; then
      printf 'name\tabs_path\tregistered_at\n' > "$REGISTRY"
    fi
    printf '%s\t%s\t%s\n' "$slug" "$project_path" "$(date -u '+%Y-%m-%dT%H:%M:%SZ')" >> "$REGISTRY"
    echo "[upgrade-project] Registered: $slug → $project_path"
  fi

  if [[ $added -eq 0 ]]; then
    echo "[upgrade-project] $slug: nothing to add."
  else
    echo "[upgrade-project] $slug: added $added file(s)."
  fi

  # Create AGENTS.md + CLAUDE.md symlink if missing
  local agents_md="$project_path/AGENTS.md"
  local claude_symlink="$project_path/CLAUDE.md"
  if [[ ! -f "$agents_md" && ! -L "$agents_md" ]]; then
    cp "$TEMPLATE_DIR/AGENTS.md.tpl" "$agents_md"
    echo "[upgrade-project] Created $agents_md"
    (( added++ )) || true
  fi
  if [[ ! -L "$claude_symlink" && ! -f "$claude_symlink" ]]; then
    ln -s AGENTS.md "$claude_symlink"
    echo "[upgrade-project] Created symlink $claude_symlink -> AGENTS.md"
    (( added++ )) || true
  fi

  # .claude/CLAUDE.md imports AGENTS.md when the root CLAUDE.md is not its symlink
  # (with the symlink, a second import would load AGENTS.md twice every session)
  local claude_md_tpl="$TEMPLATE_DIR/CLAUDE.md.tpl"
  local claude_md_dest="$project_path/.claude/CLAUDE.md"
  if [[ -f "$claude_md_tpl" && "$(readlink "$claude_symlink")" != "AGENTS.md" ]]; then
    if [[ ! -f "$claude_md_dest" ]] || ! grep -qF "@../AGENTS.md" "$claude_md_dest" 2>/dev/null; then
      cp "$claude_md_tpl" "$claude_md_dest"
      echo "[upgrade-project] Updated $claude_md_dest (imports AGENTS.md)"
      (( added++ )) || true
    fi
  fi
}

failed=()
if [[ "${1:-}" == "--all" ]]; then
  if [[ ! -f "$REGISTRY" ]]; then
    echo "[upgrade-project] No registry at $REGISTRY — nothing to upgrade."
    exit 0
  fi
  # Skip header line
  while IFS=$'\t' read -r name abs_path _rest; do
    [[ "$name" == "name" ]] && continue
    [[ -z "$name" ]] && continue
    upgrade_one "$abs_path" || failed+=("$name")
  done < "$REGISTRY"
else
  if [[ -z "${1:-}" ]]; then
    echo "Usage: $(basename "$0") <project-path> | --all" >&2
    exit 1
  fi
  upgrade_one "$1"
fi

# ── Sync centrally-managed MCP servers (qmd, code-index, graphify) ──────────
# Runs once per invocation (not once per project) since it's a global, not
# per-project, operation.
setup_central_mcp

if [[ ${#failed[@]} -gt 0 ]]; then
  echo "[upgrade-project] upgrade failed for: ${failed[*]}" >&2
  exit 1
fi
