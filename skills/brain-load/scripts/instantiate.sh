#!/usr/bin/env bash
# Create the vault one-pager projects/<slug>.md if missing (idempotent).
# The skeleton below is the canonical shape; /brain-init-project fills it.
# Usage: instantiate.sh [--cap <basename>] [--slug <slug>] [--path <abs-repo-path>]
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=/dev/null
source "$SCRIPT_DIR/_brain_env.sh"

CAP=""
SLUG=""
PROJ_PATH=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --cap) CAP="$2"; shift 2 ;;
    --slug) SLUG="$2"; shift 2 ;;
    --path) PROJ_PATH="$2"; shift 2 ;;
    *) echo "Usage: $(basename "$0") [--cap <name>] [--slug <slug>] [--path <dir>]" >&2; exit 1 ;;
  esac
done

if [[ -n "$CAP" && ! -f "$BRAIN_PATH/caps/$CAP.md" ]]; then
  echo "[instantiate] ERROR: no note at caps/$CAP.md in vault. List caps: bash \"$SCRIPT_DIR/load.sh\" --list-caps" >&2
  exit 1
fi

REPO_ROOT=""
if [[ -z "$SLUG" || -z "$PROJ_PATH" ]]; then
  if git rev-parse --show-toplevel &>/dev/null; then
    REPO_ROOT="$(git rev-parse --show-toplevel)"
  fi
fi
if [[ -z "$PROJ_PATH" ]]; then
  PROJ_PATH="${REPO_ROOT:-$PWD}"
fi
if [[ -z "$SLUG" ]]; then
  if [[ -n "$REPO_ROOT" && -f "$REPO_ROOT/.brain-project" ]]; then
    SLUG="$(grep -m1 '[^[:space:]]' "$REPO_ROOT/.brain-project" | tr -d '[:space:]')"
  fi
fi
if [[ -z "$SLUG" ]]; then
  if REMOTE_URL="$(git remote get-url origin 2>/dev/null)"; then
    if [[ "$REMOTE_URL" == git@*:* ]]; then
      SLUG="${REMOTE_URL##*:}"
      SLUG="$(basename "$SLUG" .git)"
    else
      SLUG="$(basename "$REMOTE_URL" .git)"
    fi
  else
    SLUG="$(basename "$PROJ_PATH")"
  fi
fi

OUT="$BRAIN_PATH/projects/$SLUG.md"

if [[ -f "$OUT" ]]; then
  echo "[instantiate] Exists, skipped: $OUT"
  exit 0
fi

TODAY="$(date +%Y-%m-%d)"
CAPS_LINE='caps: ""'
[[ -n "$CAP" ]] && CAPS_LINE="caps: \"[[$CAP]]\""
# One-pager: stable description of the project, rewritten in place. No journal —
# current state is <repo>/.claude/memory/CONTEXT.md, history is inbox/daily/implementation/<slug>/.
cat >"$OUT" <<NOTE
---
title: $SLUG
created: $TODAY
updated: $TODAY
tags: [project]
$CAPS_LINE
status: draft
path: "$PROJ_PATH"
repo:
prod:
---

# $SLUG

> One sentence: what it is and for whom.

## Idea
<!-- 2–4 sentences: the problem, the key insight or approach, what makes it different. -->

## Objectives
- **Goal:**
- **Users:**
- **Success:**
- **Non-goals:**

## How it works
<!-- 3–6 bullets: core workflows and main components. Deep architecture lives in ARCHITECTURE.md. -->

## Where
- Repo: \`$PROJ_PATH\`

## Memory
- Current state, roadmap, decisions: \`$PROJ_PATH/.claude/memory/\` · session logs: \`inbox/daily/implementation/$SLUG/\`

## Links
NOTE

echo "[instantiate] Wrote $OUT"

if [[ -n "$REPO_ROOT" ]]; then
  echo "$SLUG" >"$REPO_ROOT/.brain-project"
  echo "[instantiate] Updated $REPO_ROOT/.brain-project"
fi
