#!/usr/bin/env bash
# Write/clear Local Brain CLI inject into user alwaysApply rule.
# Path is ~/.cursor/rules (via ai-dotfiles symlink) — works from any cwd; no cd required.
# Do NOT write repo-root AGENTS.md (reserved for Vibe symlink → .vibe/AGENTS.md).
# sourced by hooks / prewarm — do not execute alone.

brain_hooks_inject_rule_path() {
  local root="${AI_DOTFILES:-$HOME/ai-dotfiles}"
  printf '%s/.cursor/rules/brain-hooks-session-inject.mdc' "$root"
}

brain_hooks_clear_inject_rule() {
  local f
  f="$(brain_hooks_inject_rule_path)"
  mkdir -p "$(dirname "$f")"
  cat >"$f" <<'EOF'
---
description: Ephemeral Local Brain inject for Cursor Agent CLI (empty = inactive).
alwaysApply: true
---

<!-- inactive: no CLI brain session inject -->
EOF
}

brain_hooks_write_inject_rule() {
  local ctx="$1"
  local f
  f="$(brain_hooks_inject_rule_path)"
  mkdir -p "$(dirname "$f")"
  cat >"$f" <<EOF
---
description: Ephemeral Local Brain inject (CLI — auto-written; do not edit).
alwaysApply: true
---

# Local Brain session context (CLI)

You are **Cursor Agent CLI** (not IDE Composer). Do **not** apply IDE brain hard-off — sync/load via hooks/prewarm already ran.
This rule is global (user \`~/.cursor/rules\`) — valid from any working directory.

$ctx
EOF
}
