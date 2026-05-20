#!/usr/bin/env bash
# init-project.sh — initialise a per-project brain folder and register it
# Usage: init-project.sh <project-path>
set -euo pipefail

PROJECT_PATH="${1:-}"
if [[ -z "$PROJECT_PATH" ]]; then
  echo "Usage: $(basename "$0") <project-path>" >&2
  exit 1
fi

if [[ ! -d "$PROJECT_PATH" ]]; then
  echo "[init-project] ERROR: $PROJECT_PATH does not exist" >&2
  exit 1
fi

PROJECT_PATH="$(realpath "$PROJECT_PATH")"

# ── Load BRAIN_PATH ───────────────────────────────────────────────────────────
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
AI_DOTFILES="$(cd "$SCRIPT_DIR/.." && pwd)"
ENV_FILE="${BRAIN_ENV_FILE:-$AI_DOTFILES/config/brain.env}"
if [[ ! -f "$ENV_FILE" ]]; then
  echo "[init-project] ERROR: brain.env not found at $ENV_FILE" >&2
  exit 1
fi
source "$ENV_FILE"
if [[ -z "${BRAIN_PATH:-}" ]]; then
  echo "[init-project] ERROR: BRAIN_PATH not set in $ENV_FILE" >&2
  exit 1
fi

# ── Read project slug ─────────────────────────────────────────────────────────
BRAIN_PROJECT_FILE="$PROJECT_PATH/.brain-project"
if [[ ! -f "$BRAIN_PROJECT_FILE" ]]; then
  echo "[init-project] ERROR: .brain-project not found in $PROJECT_PATH" >&2
  echo "[init-project] Create it first:  echo 'my-project-name' > $PROJECT_PATH/.brain-project" >&2
  exit 1
fi

SLUG="$(grep -m1 '[^[:space:]]' "$BRAIN_PROJECT_FILE" | tr -d '[:space:]')"
if [[ -z "$SLUG" ]]; then
  echo "[init-project] ERROR: .brain-project is empty" >&2
  exit 1
fi
echo "[init-project] Slug: $SLUG"

# ── Paths ─────────────────────────────────────────────────────────────────────
TEMPLATE_DIR="$AI_DOTFILES/config/brain-templates"
PROJECT_BRAIN="$PROJECT_PATH/.claude/brain"
VAULT_BRAIN="$BRAIN_PATH/projects/$SLUG"
REGISTRY="$AI_DOTFILES/config/brain-projects.tsv"

# ── Create project .claude/brain/ ─────────────────────────────────────────────
mkdir -p "$PROJECT_BRAIN"
for f in "$TEMPLATE_DIR"/*; do
  [[ "$f" == *.tpl ]] && continue
  fname="$(basename "$f")"
  dest="$PROJECT_BRAIN/$fname"
  if [[ ! -f "$dest" ]]; then
    cp "$f" "$dest"
    echo "[init-project] Created $PROJECT_BRAIN/$fname"
  else
    echo "[init-project] Skipped (exists): $PROJECT_BRAIN/$fname"
  fi
done

# ── Create vault projects/<slug>/ ─────────────────────────────────────────────
mkdir -p "$VAULT_BRAIN"
for f in "$TEMPLATE_DIR"/*; do
  [[ "$f" == *.tpl ]] && continue
  fname="$(basename "$f")"
  dest="$VAULT_BRAIN/$fname"
  if [[ ! -f "$dest" ]]; then
    cp "$f" "$dest"
    echo "[init-project] Created $VAULT_BRAIN/$fname"
  else
    echo "[init-project] Skipped (exists): $VAULT_BRAIN/$fname"
  fi
done

# ── Register in brain-projects.tsv ───────────────────────────────────────────
if [[ ! -f "$REGISTRY" ]]; then
  printf 'name\tabs_path\tregistered_at\n' > "$REGISTRY"
fi

if grep -qP "^${SLUG}\t" "$REGISTRY" 2>/dev/null; then
  echo "[init-project] Already registered: $SLUG"
else
  printf '%s\t%s\t%s\n' "$SLUG" "$PROJECT_PATH" "$(date -u '+%Y-%m-%dT%H:%M:%SZ')" >> "$REGISTRY"
  echo "[init-project] Registered: $SLUG → $PROJECT_PATH"
fi

# ── Generate .claude/CLAUDE.md (VSCode / IDE fallback for brain-load) ────────
CLAUDE_MD_TPL="$TEMPLATE_DIR/CLAUDE.md.tpl"
CLAUDE_MD_DEST="$PROJECT_PATH/.claude/CLAUDE.md"
if [[ -f "$CLAUDE_MD_TPL" && ! -f "$CLAUDE_MD_DEST" ]]; then
  SESSION_FILES=()
  if command -v python3 &>/dev/null; then
    while IFS= read -r fname; do
      SESSION_FILES+=("$fname")
    done < <(python3 -c "import json; d=json.load(open('$PROJECT_BRAIN/settings.json')); [print(f) for f in d.get('read_on_session_start',[])]" 2>/dev/null)
  fi
  [[ ${#SESSION_FILES[@]} -eq 0 ]] && SESSION_FILES=("OBJECTIVES.md" "CONTEXT.md")
  {
    cat "$CLAUDE_MD_TPL"
    for fname in "${SESSION_FILES[@]}"; do
      echo "@brain/$fname"
    done
  } > "$CLAUDE_MD_DEST"
  echo "[init-project] Created $CLAUDE_MD_DEST"
fi

# ── Set up per-project MCP servers ───────────────────────────────────────────
source "$SCRIPT_DIR/lib-mcp.sh"
setup_project_mcp "$PROJECT_PATH"

echo ""
echo "[init-project] Structure ready. Run the following in Claude Code to populate the files:"
echo ""
echo "  /brain-init-project $PROJECT_PATH"
echo ""
echo "  The skill will read the vault, scan the project, and ask you targeted questions"
echo "  to write OBJECTIVES, ARCHITECTURE, DECISIONS, CONTEXT, ROADMAP, and API files."
