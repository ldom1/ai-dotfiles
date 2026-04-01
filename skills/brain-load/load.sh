#!/usr/bin/env bash
# brain-load/load.sh — resolve project slug and print brief content
# Usage: load.sh [--slug-only]
#   --slug-only   print only the resolved slug and brief path, not the content
set -euo pipefail

# ── Load config ───────────────────────────────────────────────────────────────
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_FILE="$(cd "$SCRIPT_DIR/../.." && pwd)/config/brain.env"

if [[ ! -f "$ENV_FILE" ]]; then
  echo "[brain-load] ERROR: config not found at $ENV_FILE" >&2
  exit 1
fi

# shellcheck source=/dev/null
source "$ENV_FILE"

if [[ -z "${BRAIN_PATH:-}" ]]; then
  echo "[brain-load] ERROR: BRAIN_PATH is not set in $ENV_FILE" >&2
  exit 1
fi

# ── Slug resolution ───────────────────────────────────────────────────────────
SLUG=""

# 1. .brain-project file at repo root
REPO_ROOT=""
if git rev-parse --show-toplevel &>/dev/null; then
  REPO_ROOT="$(git rev-parse --show-toplevel)"
fi

if [[ -n "$REPO_ROOT" && -f "$REPO_ROOT/.brain-project" ]]; then
  SLUG="$(grep -m1 '[^[:space:]]' "$REPO_ROOT/.brain-project" | tr -d '[:space:]')"
  echo "[brain-load] Slug from .brain-project: $SLUG" >&2
fi

# 2. Git remote origin
if [[ -z "$SLUG" ]]; then
  if REMOTE_URL="$(git remote get-url origin 2>/dev/null)"; then
    # Handle both HTTPS and SSH remotes, strip .git suffix
    SLUG="$(basename "$REMOTE_URL" .git)"
    echo "[brain-load] Slug from git remote: $SLUG" >&2
  fi
fi

# 3. Current directory name
if [[ -z "$SLUG" ]]; then
  SLUG="$(basename "$PWD")"
  echo "[brain-load] Slug from directory name: $SLUG" >&2
fi

# ── Locate brief ──────────────────────────────────────────────────────────────
BRIEF_PATH="$BRAIN_PATH/Projects/$SLUG/brief.md"

if [[ "${1:-}" == "--slug-only" ]]; then
  echo "slug=$SLUG"
  echo "brief=$BRIEF_PATH"
  exit 0
fi

# ── Output brief ──────────────────────────────────────────────────────────────
if [[ ! -f "$BRIEF_PATH" ]]; then
  echo "[brain-load] MISSING: no brief found at $BRIEF_PATH" >&2
  echo "[brain-load] BRIEF_MISSING slug=$SLUG path=$BRIEF_PATH"
  exit 2
fi

echo "[brain-load] Loading brief: $BRIEF_PATH" >&2
echo "--- PROJECT BRIEF: $SLUG ---"
cat "$BRIEF_PATH"
echo "--- END BRIEF ---"
