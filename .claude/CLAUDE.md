# Claude — Core Config

## Memory
BRAIN_PATH: `grep BRAIN_PATH ~/ai-dotfiles/config/brain.env`
Vault root (WSL): `/mnt/c/Users/lgiron/Documents/developer-brain/`
Deep knowledge: `$BRAIN_PATH/resources/knowledge/`
Skills index: `~/ai-dotfiles/.claude/SKILLS_INDEX.md` (load when using / commands)
Reference: `~/ai-dotfiles/.claude/LocalBrain.md` (vault layout), `~/ai-dotfiles/.claude/RTK.md` (token proxy)

## Pitfalls
Before any substantive implementation or debugging: read `$BRAIN_PATH/resources/operational/ai-agents/pitfalls.md`. Treat entries as hard constraints. When the user corrects a mistake, prepend a bullet: context → what was wrong → what to do instead.

## Development
Occam's razor: fewest assumptions, smallest surface area. Structured, simple, readable code. No speculative abstractions. No backwards-compat shims for removed code.

## Session discipline
/clear on context switches. /rename before /clear if you may --resume. /compact at every milestone — do not wait for the limit.

## Session implementation log (Local Brain)

For every substantive session on a project: write to **`$BRAIN_PATH/inbox/daily/implementation/<project-name>/YYYY-MM-DD-topic.md`** (resolve `BRAIN_PATH` from `~/ai-dotfiles/config/brain.env`). Continue the same day's file if the thread continues. Include goal, changes, commands/tests, and follow-ups. **Do not** use `index/implementation/` — that path does not exist in the vault.

## Specs / Design Docs (Local Brain)

Write brainstorming specs and design documents to **`$BRAIN_PATH/inbox/daily/specs/<project-name>/YYYY-MM-DD-<topic>-design.md`**. Do not use `docs/superpowers/specs/` inside the project repo.

## Compaction focus
When compacting, preserve: files in scope, open decisions, failing tests/errors, next command to run, explicit user constraints.

## FinOps
Before any multi-step task: state which model you're using and why.
- Sonnet: default for 80% of tasks (feature impl, tests, PRs, code review)
- Opus: architecture, multi-file refactor, gnarly debug only
- Haiku: grep, rename, format, README edits, quick lookups
Full ref: `$BRAIN_PATH/resources/operational/ai-agents/claude-finops.md`

## Hooks
SessionStart: brain-load stdout → context + git pull on startup/resume.
SessionEnd: brain commit + push.
PreToolUse/Bash: RTK rewrites commands for token efficiency (opt-out: `rtk proxy '<cmd>'`).
Manual fallback:
```bash
bash ~/ai-dotfiles/skills/brain-sync/scripts/sync.sh [start|end]
bash ~/ai-dotfiles/skills/brain-load/scripts/load.sh
```

## No-hooks fallback (VSCode / IDE)
Hooks do not fire in the VSCode extension. At the start of every session, read these files manually:
1. `$BRAIN_PATH/resources/operational/ai-agents/pitfalls.md` — hard constraints, treat as immutable rules
2. `$BRAIN_PATH/resources/operational/ai-agents/lessons-learned.md` — last 3 entries only
3. `$BRAIN_PATH/resources/operational/ai-agents/claude-finops.md` — apply model routing immediately
BRAIN_PATH resolves to: `/mnt/c/Users/louis/Documents/Local Brain`

## Brain System Integration

Brain system runs automatically at session start:

1. **brain-sync start** — pulls vault
2. **brain-route** — decides session mode (normal or maintenance)
   - If maintenance → runs brain-audit (compiles raw data, finds connections, runs Q&A, generates digest)
   - If normal → runs brain-load (loads project context)
3. **work** — your normal session
4. **brain-sync end** — commits + pushes vault

### Manual Triggers

- Force maintenance mode: `brain-route --maintenance` (at session start)
- View last maintenance: `cat $BRAIN_PATH/meta/last-maintenance.md`
- View latest digest: `ls -lt $BRAIN_PATH/meta/digest-*.md | head -1`
## Remote Server Work

- End-to-end verification: after any fix on a remote host, confirm from the user's perspective (`curl` the endpoint, check the browser response). Never claim success on config change alone.
- When debugging infrastructure (nginx, Docker, Tailscale, Authelia), identify ALL config file locations and which one is actually active before editing. Run `nginx -T` or equivalent to confirm the live config.

## Git Conventions

For git operations (rm --cached, .gitignore changes, resets): always check for nested .gitignore files that may override rules, and verify the change persists after a full `git status` check. Prefer a clean single-commit approach over incremental fixes.

## Documentation Hygiene

When behavior, workflow, setup, commands, or visible outputs change:
- Always update `CHANGELOG.md` in the same work.
- Update `README.md` when user-facing usage/structure changed.
- Do not skip docs updates even for "small" infra/skill changes.

## Graphify

At the start of substantive work in a repo, look for `graphify-out*` artifacts at the root (`graphify-out.md`/`.json`, or `graphify-out/graph.json`). If present, read for architecture/modules/flow before inferring from the file tree. Never modify these artifacts. If absent, proceed and optionally suggest generating via https://graphify.net/.
