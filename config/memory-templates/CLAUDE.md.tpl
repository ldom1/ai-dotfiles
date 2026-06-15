# CLAUDE.md — VSCode / IDE fallback entry point
# Location: .claude/CLAUDE.md
# Do NOT edit manually — regenerate with `ai-dotfiles init <path>` when memory files change.
#
# How loading works:
#   CLI (terminal) : SessionStart hook reads AGENTS.md + memory files
#   VSCode / IDE   : hooks don't fire; this file @-imports AGENTS.md on every message
#
# This file only needs one line:

@../AGENTS.md
