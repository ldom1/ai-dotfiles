# Claude — Core Config

## Memory
BRAIN_PATH: `grep BRAIN_PATH ~/ai-dotfiles/config/brain.env`
Vault root (WSL): `/mnt/c/Users/lgiron/Documents/developer-brain/`
Deep knowledge: `$BRAIN_PATH/resources/knowledge/`
Skills index: `~/ai-dotfiles/.claude/SKILLS_INDEX.md` (load when using / commands)

## Pitfalls
Before any substantive implementation or debugging: read `$BRAIN_PATH/resources/knowledge/operational/claude-pitfalls.md`. Treat entries as hard constraints. When the user corrects a mistake, prepend a bullet: context → what was wrong → what to do instead.

## Development
Occam's razor: fewest assumptions, smallest surface area. Structured, simple, readable code. No speculative abstractions. No backwards-compat shims for removed code.

## Session discipline
/clear on context switches. /rename before /clear if you may --resume. /compact at every milestone — do not wait for the limit.

## Compaction focus
When compacting, preserve: files in scope, open decisions, failing tests/errors, next command to run, explicit user constraints.

## FinOps
Before any multi-step task: state which model you're using and why.
- Sonnet: default for 80% of tasks (feature impl, tests, PRs, code review)
- Opus: architecture, multi-file refactor, gnarly debug only
- Haiku: grep, rename, format, README edits, quick lookups
Full ref: `$BRAIN_PATH/resources/knowledge/operational/claude-finops.md`

## Hooks
SessionStart: brain-load stdout → context + git pull on startup/resume.
SessionEnd: brain commit + push.
PreToolUse/Bash: RTK rewrites commands for token efficiency (opt-out: `rtk proxy '<cmd>'`).
Manual fallback:
```bash
bash ~/ai-dotfiles/skills/brain-sync/scripts/sync.sh [start|end]
bash ~/ai-dotfiles/skills/brain-load/scripts/load.sh
```
## Remote Server Work

When working on remote servers via SSH, always verify the fix actually works from the user's perspective (e.g., curl the endpoint, check browser response) before declaring success. Never assume a config change resolved the issue without end-to-end verification.

## Git Conventions

For git operations (rm --cached, .gitignore changes, resets): always check for nested .gitignore files that may override rules, and verify the change persists after a full `git status` check. Prefer a clean single-commit approach over incremental fixes.

## Remote Server Work 

When debugging infrastructure (nginx, Docker, Tailscale, Authelia), identify ALL config file locations and which one is actually active before making changes. Run `nginx -T` or equivalent to confirm the live config.