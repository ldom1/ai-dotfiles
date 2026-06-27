#!/usr/bin/env bash
# PreToolUse (Bash): validate git commit message convention.
# Format: type(scope): description
# Types: feat | fix | enh | doc | ci
# Scopes: finite list per project type, defined in scopes.json

set -euo pipefail

SCOPES_FILE="$HOME/ai-dotfiles/skills/git-commit/scopes.json"

if ! command -v jq &>/dev/null || ! command -v python3 &>/dev/null; then
  exit 0
fi

INPUT=$(cat)
CMD=$(echo "$INPUT" | jq -r '.tool_input.command // empty')

if [ -z "$CMD" ]; then
  exit 0
fi

# Only check git commit commands
if ! echo "$CMD" | grep -qE 'git\s+commit'; then
  exit 0
fi

# Extract commit message from -m flag
MSG=$(echo "$CMD" | python3 -c "
import re, sys
cmd = sys.stdin.read()
m = re.search(r'-m\s+[\"\'](.*?)[\"\']', cmd, re.DOTALL)
if m:
    print(m.group(1).strip())
" 2>/dev/null || true)

if [ -z "$MSG" ]; then
  # Heredoc or EOF form — inject skill reminder and allow
  jq -n '{
    "hookSpecificOutput": {
      "hookEventName": "PreToolUse",
      "permissionDecision": "allow",
      "permissionDecisionReason": "git-commit skill reminder: validate type(scope): description before committing"
    }
  }'
  exit 0
fi

# Validate format: type(scope): description  OR  type: description
if ! echo "$MSG" | grep -qE '^(feat|fix|enh|doc|ci)(\([^)]+\))?: .+'; then
  jq -n --arg msg "$MSG" '{
    "hookSpecificOutput": {
      "hookEventName": "PreToolUse",
      "permissionDecision": "deny",
      "permissionDecisionReason": ("Commit message format invalid: \"" + $msg + "\"\n\nRequired: type(scope): imperative description\nTypes:    feat · fix · enh · doc · ci\nExample:  feat(core): add silver delta injection\n\nRun /git-commit skill before committing.")
    }
  }'
  exit 0
fi

# Extract scope (may be absent)
SCOPE=$(echo "$MSG" | python3 -c "
import re, sys
m = re.match(r'^[a-z]+\(([^)]+)\):', sys.stdin.read().strip())
print(m.group(1) if m else '')
" 2>/dev/null || true)

if [ -z "$SCOPE" ]; then
  # No scope — allowed (e.g. 'ci: ...')
  exit 0
fi

# Detect project type from repo root
REPO_ROOT=$(git rev-parse --show-toplevel 2>/dev/null || echo "")

if [ -z "$REPO_ROOT" ] || [ ! -f "$SCOPES_FILE" ]; then
  exit 0
fi

RESULT=$(python3 - <<PYEOF
import json, os, sys

root = "$REPO_ROOT"
scope = "$SCOPE"

with open("$SCOPES_FILE") as f:
    data = json.load(f)

project_type = None
for ptype, info in data["project_types"].items():
    for marker in info.get("detect", []):
        if os.path.exists(os.path.join(root, marker)):
            project_type = ptype
            break
    if project_type:
        break

if project_type is None:
    print("UNKNOWN_PROJECT")
elif scope not in data["project_types"][project_type]["scopes"]:
    valid = ", ".join(data["project_types"][project_type]["scopes"])
    print(f"INVALID_SCOPE:{project_type}:{valid}")
else:
    print("OK")
PYEOF
)

case "$RESULT" in
  OK)
    exit 0
    ;;
  UNKNOWN_PROJECT)
    jq -n --arg scope "$SCOPE" '{
      "hookSpecificOutput": {
        "hookEventName": "PreToolUse",
        "permissionDecision": "deny",
        "permissionDecisionReason": "Unknown project type — run /git-commit skill to define the scope list for this repo before committing."
      }
    }'
    exit 0
    ;;
  INVALID_SCOPE:*)
    PROJECT_TYPE=$(echo "$RESULT" | cut -d: -f2)
    VALID_SCOPES=$(echo "$RESULT" | cut -d: -f3)
    jq -n --arg scope "$SCOPE" --arg ptype "$PROJECT_TYPE" --arg valid "$VALID_SCOPES" '{
      "hookSpecificOutput": {
        "hookEventName": "PreToolUse",
        "permissionDecision": "deny",
        "permissionDecisionReason": ("Scope \"" + $scope + "\" is not in the locked list for project type \"" + $ptype + "\".\n\nValid scopes: " + $valid + "\n\nRun /git-commit skill to propose a new scope and get user validation before committing.")
      }
    }'
    exit 0
    ;;
esac
