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
# shellcheck source=/dev/null
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
TEMPLATE_DIR="$AI_DOTFILES/config/memory-templates"
PROJECT_BRAIN="$PROJECT_PATH/.claude/memory"
VAULT_BRAIN="$BRAIN_PATH/projects/$SLUG"
REGISTRY="$AI_DOTFILES/config/brain-projects.tsv"

# ── Create project .claude/memory/ ────────────────────────────────────────────
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

# ── Ensure .gitignore excludes settings.local.json ───────────────────────────
GITIGNORE="$PROJECT_PATH/.gitignore"
GITIGNORE_ENTRY=".claude/settings.local.json"
if ! grep -qF "$GITIGNORE_ENTRY" "$GITIGNORE" 2>/dev/null; then
  echo "" >> "$GITIGNORE"
  echo "# Claude Code — local developer overrides" >> "$GITIGNORE"
  echo "$GITIGNORE_ENTRY" >> "$GITIGNORE"
  echo "[init-project] Added $GITIGNORE_ENTRY to .gitignore"
fi

# ── Create AGENTS.md + CLAUDE.md symlink at project root ─────────────────────
AGENTS_MD="$PROJECT_PATH/AGENTS.md"
CLAUDE_SYMLINK="$PROJECT_PATH/CLAUDE.md"
if [[ ! -f "$AGENTS_MD" && ! -L "$AGENTS_MD" ]]; then
  cat > "$AGENTS_MD" << 'EOF'
# AGENTS.md — Project instructions
# Location : project root (canonical). CLAUDE.md is a symlink → AGENTS.md.
# Scope    : all agents (Claude, Mistral, Codex, …). Claude Code loads it via the symlink.
# Length   : keep under 60 lines — agents read this every session.

---

## Description
<!-- One paragraph: what this project does, tech stack, deployment context. -->

## Key Files
<!-- 3–5 files an agent must know to orient itself. -->

## Task-Specific Behaviors
<!-- Commands to always run, files to read before touching a module, hard rules. -->

## Constraints
<!-- Protected files, dependency policy, hard limits. -->

## Standards
<!-- Reference shared coding standards. Uncomment the relevant line(s): -->
<!-- @.claude/standards/python.md -->

## Memory
# CLI  : memory files loaded at session start declared in .claude/memory/settings.json
# VSCode: uncomment the @-imports below as you create each file.
<!--
@.claude/memory/OBJECTIVES.md
@.claude/memory/CONTEXT.md
@.claude/memory/ARCHITECTURE.md
@.claude/memory/DECISIONS.md
@.claude/memory/ROADMAP.md
@.claude/memory/API.md
-->
EOF
  echo "[init-project] Created $AGENTS_MD"
fi
if [[ ! -L "$CLAUDE_SYMLINK" && ! -f "$CLAUDE_SYMLINK" ]]; then
  ln -s AGENTS.md "$CLAUDE_SYMLINK"
  echo "[init-project] Created symlink $CLAUDE_SYMLINK -> AGENTS.md"
fi

# ── Generate .claude/CLAUDE.md (VSCode / IDE fallback — loads AGENTS.md) ─────
CLAUDE_MD_TPL="$TEMPLATE_DIR/CLAUDE.md.tpl"
CLAUDE_MD_DEST="$PROJECT_PATH/.claude/CLAUDE.md"
if [[ -f "$CLAUDE_MD_TPL" && ! -f "$CLAUDE_MD_DEST" ]]; then
  cp "$CLAUDE_MD_TPL" "$CLAUDE_MD_DEST"
  echo "[init-project] Created $CLAUDE_MD_DEST"
fi

# ── Copy review checklist into .claude/review/ (if pratique-ia is available) ─
PRATIQUE_IA_PATH="${PRATIQUE_IA_PATH:-$HOME/pratique_artelys/pratique-ia}"
REVIEW_CHECKLIST_TPL="$PRATIQUE_IA_PATH/templates/review-checklist.md"
PROJECT_REVIEW_DIR="$PROJECT_PATH/.claude/review"
if [[ -f "$REVIEW_CHECKLIST_TPL" ]]; then
  mkdir -p "$PROJECT_REVIEW_DIR"
  if [[ ! -f "$PROJECT_REVIEW_DIR/checklist.md" ]]; then
    cp "$REVIEW_CHECKLIST_TPL" "$PROJECT_REVIEW_DIR/checklist.md"
    echo "[init-project] Copied review checklist: $PROJECT_REVIEW_DIR/checklist.md"
  fi
fi

# ── Copy Artelys standards into .claude/standards/ (if pratique-ia is available) ─
PRATIQUE_IA_STANDARDS="$PRATIQUE_IA_PATH/standards"
PROJECT_STANDARDS="$PROJECT_PATH/.claude/standards"
if [[ -d "$PRATIQUE_IA_STANDARDS" ]]; then
  mkdir -p "$PROJECT_STANDARDS"
  for f in "$PRATIQUE_IA_STANDARDS"/*.md; do
    [[ -f "$f" ]] || continue
    fname="$(basename "$f")"
    dest="$PROJECT_STANDARDS/$fname"
    if [[ ! -f "$dest" ]]; then
      cp "$f" "$dest"
      echo "[init-project] Copied standard: $dest"
    fi
  done
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
