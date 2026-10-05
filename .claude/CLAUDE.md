@~/ai-dotfiles/AGENTS.md

# Claude Code only

## Hooks
- SessionStart: exports `BRAIN_PATH`, pulls the vault, injects the project note and pitfalls. SessionEnd: vault commit + push, warns if today has no session log. PreToolUse/Bash: RTK shrinks command output (`rtk proxy '<cmd>'` bypasses; `~/ai-dotfiles/.claude/RTK.md`) and the commit-message check rejects off-list scopes. Stop: runs the repo's `.claude/stop-check` command when the tree has changes, and blocks on failure.
- If no `BRAIN_PATH=` line is in context, hooks did not run: run `bash ~/ai-dotfiles/skills/brain-sync/scripts/sync.sh start`. If the pitfalls block is missing, truncated, or replaced by a file preview, read pitfalls.md yourself.
- `/exit` quits without writing notes: SessionEnd gives you no turn.

## Session
- User habits: `/clear` on context switches, `/rename` before `/clear` to `--resume` later, `/compact` at milestones.
- When compacting, preserve: files in scope, open decisions, failing tests/errors, next command to run, explicit user constraints.
