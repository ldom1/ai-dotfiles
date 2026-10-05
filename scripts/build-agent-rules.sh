#!/usr/bin/env bash
# Generate the Cursor and Vibe copies of AGENTS.md, the single source of shared agent rules.
# Claude Code imports AGENTS.md directly (.claude/CLAUDE.md: @~/ai-dotfiles/AGENTS.md).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SRC="$ROOT/AGENTS.md"
NOTE="<!-- Generated from AGENTS.md by scripts/build-agent-rules.sh. Do not edit. -->"

{
  printf -- '---\ndescription: Shared agent rules (generated from ~/ai-dotfiles/AGENTS.md).\nalwaysApply: true\n---\n\n%s\n\n' "$NOTE"
  cat "$SRC"
} >"$ROOT/.cursor/rules/agents.mdc"

{
  printf '%s\n\n' "$NOTE"
  cat "$ROOT/.vibe/bootstrap.md"
  printf '\n'
  cat "$SRC"
} >"$ROOT/.vibe/AGENTS.md"

echo "[build-agent-rules] .cursor/rules/agents.mdc and .vibe/AGENTS.md rebuilt from AGENTS.md"
