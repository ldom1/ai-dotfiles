#!/usr/bin/env bash
# brain-load/load.sh — resolve project slug, locate vault note, print content
# Usage: load.sh [--list-caps] [--slug-only]
#   --list-caps   print cap ids (basenames of caps/*.md), then exit 0
#   --slug-only   print slug, note path, mode, template paths; then exit 0
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=/dev/null
source "$SCRIPT_DIR/_brain_env.sh"

cmd_list_caps() {
  if [[ ! -d "$BRAIN_PATH/caps" ]]; then
    echo "[brain-load] No caps/ directory in vault." >&2
    exit 0
  fi
  local f base
  for f in "$BRAIN_PATH/caps"/*.md; do
    [[ -e "$f" ]] || continue
    base="$(basename "$f" .md)"
    echo "cap:$base"
  done
  exit 0
}

if [[ "${1:-}" == "--list-caps" ]]; then
  cmd_list_caps
fi

# ── Slug resolution ───────────────────────────────────────────────────────────
SLUG=""
REPO_ROOT=""
if git rev-parse --show-toplevel &>/dev/null; then
  REPO_ROOT="$(git rev-parse --show-toplevel)"
fi

if [[ -n "$REPO_ROOT" && -f "$REPO_ROOT/.brain-project" ]]; then
  SLUG="$(grep -m1 '[^[:space:]]' "$REPO_ROOT/.brain-project" | tr -d '[:space:]')"
  echo "[brain-load] Slug from .brain-project: $SLUG" >&2
fi
if [[ -z "$SLUG" ]]; then
  if REMOTE_URL="$(git remote get-url origin 2>/dev/null)"; then
    if [[ "$REMOTE_URL" == git@*:* ]]; then
      SLUG="${REMOTE_URL##*:}"
      SLUG="$(basename "$SLUG" .git)"
    else
      SLUG="$(basename "$REMOTE_URL" .git)"
    fi
    echo "[brain-load] Slug from git remote: $SLUG" >&2
  fi
fi
if [[ -z "$SLUG" ]]; then
  SLUG="$(basename "$PWD")"
  echo "[brain-load] Slug from directory name: $SLUG" >&2
fi

# ── Note path (Obsidian PARA projects/*.md vs legacy Projects/<slug>/brief.md)
NOTE_PARA="$BRAIN_PATH/projects/$SLUG.md"
NOTE_LEGACY="$BRAIN_PATH/Projects/$SLUG/brief.md"
TEMPLATE_VAULT="$BRAIN_PATH/projects/_template.md"
SKILL_BRIEF_TEMPLATE="$SCRIPT_DIR/templates/brief.md"
CAPS_DIR="$BRAIN_PATH/caps"

NOTE_PATH=""
NOTE_MODE=""

if [[ -f "$NOTE_PARA" ]]; then
  NOTE_PATH="$NOTE_PARA"
  NOTE_MODE="para"
elif [[ -f "$NOTE_LEGACY" ]]; then
  NOTE_PATH="$NOTE_LEGACY"
  NOTE_MODE="legacy"
elif [[ -f "$TEMPLATE_VAULT" ]] || [[ -d "$BRAIN_PATH/projects" ]]; then
  NOTE_PATH="$NOTE_PARA"
  NOTE_MODE="para_missing"
else
  NOTE_PATH="$NOTE_LEGACY"
  NOTE_MODE="legacy_missing"
fi

if [[ "${1:-}" == "--slug-only" ]]; then
  echo "slug=$SLUG"
  echo "note=$NOTE_PATH"
  echo "mode=$NOTE_MODE"
  echo "template_vault=$TEMPLATE_VAULT"
  echo "template_skill=$SKILL_BRIEF_TEMPLATE"
  echo "caps_dir=$CAPS_DIR"
  exit 0
fi

# ── Output note ─────────────────────────────────────────────────────────────
if [[ "$NOTE_MODE" == "para" || "$NOTE_MODE" == "legacy" ]]; then
  echo "[brain-load] Loading note: $NOTE_PATH" >&2
  echo "--- PROJECT NOTE: $SLUG ---"
  cat "$NOTE_PATH"
  echo "--- END NOTE ---"
fi

# ── Load .claude/brain session files (if present) ────────────────────────────
if [[ -n "$REPO_ROOT" && -f "$REPO_ROOT/.claude/brain/settings.json" ]]; then
  BRAIN_DIR="$REPO_ROOT/.claude/brain"
  echo "[brain-load] Found project brain: $BRAIN_DIR" >&2

  # Parse read_on_session_start from settings.json (requires python3 or jq)
  SESSION_FILES=()
  if command -v jq &>/dev/null; then
    while IFS= read -r fname; do
      SESSION_FILES+=("$fname")
    done < <(jq -r '.read_on_session_start[]?' "$BRAIN_DIR/settings.json" 2>/dev/null)
  elif command -v python3 &>/dev/null; then
    while IFS= read -r fname; do
      SESSION_FILES+=("$fname")
    done < <(python3 -c "import json,sys; d=json.load(open('$BRAIN_DIR/settings.json')); [print(f) for f in d.get('read_on_session_start',[])]" 2>/dev/null)
  fi

  # Default if parsing failed or list is empty
  if [[ ${#SESSION_FILES[@]} -eq 0 ]]; then
    SESSION_FILES=("OBJECTIVES.md" "CONTEXT.md")
  fi

  echo "--- PROJECT BRAIN: $SLUG ---"
  for fname in "${SESSION_FILES[@]}"; do
    fpath="$BRAIN_DIR/$fname"
    if [[ -f "$fpath" ]]; then
      echo "### $fname"
      cat "$fpath"
      echo ""
    fi
  done
  echo "--- END PROJECT BRAIN ---"
fi

if [[ "$NOTE_MODE" != "para" && "$NOTE_MODE" != "legacy" ]]; then
  echo "[brain-load] MISSING: no project note for slug **$SLUG** (mode=$NOTE_MODE)" >&2
  echo "[brain-load] PROJECT_NOTE_MISSING mode=$NOTE_MODE slug=$SLUG note=$NOTE_PATH template_vault=$TEMPLATE_VAULT template_skill=$SKILL_BRIEF_TEMPLATE caps_dir=$CAPS_DIR" >&2
  exit 2
fi
