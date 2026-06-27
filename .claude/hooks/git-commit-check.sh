#!/usr/bin/env bash
# PreToolUse (Bash): validate git commit message convention.
# Format: type(scope): description
# Types: feat | fix | enh | doc | ci
# Scope: free-form

set -euo pipefail

if ! command -v jq &>/dev/null; then
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
  # Heredoc or EOF form — can't extract, allow through
  exit 0
fi

# Valid format: type(scope): description  OR  type: description
VALID_PATTERN='^(feat|fix|enh|doc|ci)(\([^)]+\))?: .+'
if echo "$MSG" | grep -qP "$VALID_PATTERN" 2>/dev/null || echo "$MSG" | grep -qE "$VALID_PATTERN"; then
  exit 0
fi

# Invalid — block and show convention
jq -n \
  --arg reason "$(cat <<'REASON'
Commit message does not follow the required convention.

Required: type(scope): imperative description
  Types:   feat · fix · enh · doc · ci
  Scope:   free-form (chore, design, ci, vulnerability, …)

Example:  feat(chore): apply ruff formatting across codebase
Example:  fix(vulnerability): sanitize SQL input before query

Please fix the message and retry.
REASON
)" \
  '{
    "hookSpecificOutput": {
      "hookEventName": "PreToolUse",
      "permissionDecision": "deny",
      "permissionDecisionReason": $reason
    }
  }'
