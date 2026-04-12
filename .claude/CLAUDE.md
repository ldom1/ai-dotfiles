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

## Session implementation log (Local Brain)

For every substantive session on a project: write to **`$BRAIN_PATH/inbox/daily/implementation/<project-name>/YYYY-MM-DD-topic.md`** (resolve `BRAIN_PATH` from `~/ai-dotfiles/config/brain.env`). Continue the same day's file if the thread continues. Include goal, changes, commands/tests, and follow-ups. **Do not** use `index/implementation/` — that path does not exist in the vault.

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

When working on remote servers via SSH, always verify the fix actually works from the user's perspective (e.g., curl the endpoint, check browser response) before declaring success. Never assume a config change resolved the issue without end-to-end verification.

## Git Conventions

For git operations (rm --cached, .gitignore changes, resets): always check for nested .gitignore files that may override rules, and verify the change persists after a full `git status` check. Prefer a clean single-commit approach over incremental fixes.

## Remote Server Work 

When debugging infrastructure (nginx, Docker, Tailscale, Authelia), identify ALL config file locations and which one is actually active before making changes. Run `nginx -T` or equivalent to confirm the live config.

## Documentation Hygiene

When behavior, workflow, setup, commands, or visible outputs change:
- Always update `CHANGELOG.md` in the same work.
- Update `README.md` when user-facing usage/structure changed.
- Do not skip docs updates even for "small" infra/skill changes.

## Graphify

### Project context (`graphify-out*`)

At the **start of substantive work** in a project repo, check the **repository root** for Graphify output:

- `graphify-out.md`, `graphify-out.json`, or any **file** whose name starts with `graphify-out`
- If there is a **`graphify-out/`** directory at the root (common CLI layout), treat **`graphify-out/graph.json`** as the canonical graph when present; otherwise read the clearest summary **`.md` or `.json`** in that directory (not the whole folder blindly)

**If found:** read enough to ground architecture, modules, dependencies, entry points, data flow, naming, and stated constraints. **Prefer this over inferring structure from raw file trees** when it does not contradict the task. Proceed **silently** after loading unless something conflicts with the request or needs clarification.

**If not found:** work as usual; context may be incomplete. You may suggest generating output via [Graphify](https://graphify.net/).

**Never** modify, overwrite, or delete `graphify-out*` artifacts.

### Skill (`/graphify`)

- **graphify** (`~/.claude/skills/graphify/SKILL.md` → `~/ai-dotfiles/skills/graphify/SKILL.md`) — corpus → knowledge graph. Trigger: `/graphify`.
- When the user types `/graphify`, invoke the Skill tool with `skill: "graphify"` before doing anything else.
