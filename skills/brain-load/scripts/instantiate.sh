#!/usr/bin/env bash
# Instantiate projects/<slug>.md from vault projects/_template.md + chosen cap.
# Usage: instantiate.sh --cap <basename> [--slug <slug>] [--path <abs-repo-path>]
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
    *) echo "Usage: $(basename "$0") --cap <name> [--slug <slug>] [--path <dir>]" >&2; exit 1 ;;
  esac
done

if [[ -z "$CAP" ]]; then
  echo "[instantiate] ERROR: --cap is required. List caps: bash \"$SCRIPT_DIR/load.sh\" --list-caps" >&2
  exit 1
fi

if [[ ! -f "$BRAIN_PATH/caps/$CAP.md" ]]; then
  echo "[instantiate] ERROR: no note at caps/$CAP.md in vault." >&2
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

TEMPLATE_VAULT="$BRAIN_PATH/projects/_template.md"
OUT="$BRAIN_PATH/projects/$SLUG.md"
CAP_WIKI="caps/$CAP"

if [[ ! -f "$TEMPLATE_VAULT" ]]; then
  echo "[instantiate] ERROR: vault template missing: $TEMPLATE_VAULT" >&2
  exit 1
fi

if [[ -f "$OUT" ]]; then
  echo "[instantiate] ERROR: already exists: $OUT" >&2
  exit 1
fi

TODAY="$(date +%Y-%m-%d)"

export _INST_TEMPLATE="$TEMPLATE_VAULT" _INST_OUT="$OUT" _INST_CAP_WIKI="$CAP_WIKI" \
  _INST_PATH="$PROJ_PATH" _INST_TODAY="$TODAY" _INST_SLUG="$SLUG"
python3 - <<'PY'
import os, re
from pathlib import Path

template = Path(os.environ["_INST_TEMPLATE"]).read_text(encoding="utf-8")
title = os.environ["_INST_SLUG"].replace("-", " ").title()
cap_wiki = os.environ["_INST_CAP_WIKI"]
proj_path = os.environ["_INST_PATH"]
today = os.environ["_INST_TODAY"]

template = template.replace("{{project-name}}", title)
template = template.replace("{{caps-name}}", cap_wiki)
template = template.replace("{{project-path}}", proj_path)
template = template.replace("{{start}}", today)
template = template.replace("{{end}}", today)
template = template.replace("{{status}}", "draft")
template = template.replace("YYYY-MM-DD", today)
template = re.sub(
    r"^title: project-template\s*$",
    f'title: "{title.replace(chr(34), "")}"',
    template,
    flags=re.MULTILINE,
)

Path(os.environ["_INST_OUT"]).write_text(template, encoding="utf-8")
PY

echo "[instantiate] Wrote $OUT"

if [[ -n "$REPO_ROOT" ]]; then
  echo "$SLUG" >"$REPO_ROOT/.brain-project"
  echo "[instantiate] Updated $REPO_ROOT/.brain-project"
fi
