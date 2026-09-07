#!/usr/bin/env bash
# Cursor Agent CLI entry: prewarm global user-rule inject, then agent.
# Works from any cwd — no cd required. Alias (not export) in ~/.zshrc.
set -euo pipefail
export BRAIN_AGENT_HOOKS=1
bash "${AI_DOTFILES:-$HOME/ai-dotfiles}/scripts/brain-hooks-prewarm.sh"
exec agent "$@"
