# Claude — Core Config

## Local Brain (Obsidian vault)
`$BRAIN_PATH` comes from `~/ai-dotfiles/config/brain.env` (the SessionStart hook exports it). Layout: `~/ai-dotfiles/.claude/LocalBrain.md`.

- **Pitfalls** — `$BRAIN_PATH/resources/operational/ai-agents/pitfalls.md`, injected at session start: distilled cross-project rules; treat them as constraints. When the user corrects a mistake that would recur in *other* projects, add one rule there (format in the `capture` skill). Project-specific gotchas go to the project's `.claude/memory/CONTEXT.md`.
- **Where to write** — in the vault, never in the project repo's `docs/`:

  | Kind | Path |
  |---|---|
  | Session log | `inbox/daily/implementation/<project>/YYYY-MM-DD-<topic>.md` (same thread today → append) |
  | Spec / design doc | `inbox/daily/specs/<project>/YYYY-MM-DD-<topic>-design.md` |
  | Implementation plan (step-by-step tasks) | `inbox/daily/plans/<project>/YYYY-MM-DD-<topic>-plan.md` |

- **History only in session logs** — vault `projects/<slug>.md` notes and repo `.claude/memory/*` are snapshots rewritten in place: never add a journal, changelog or dated-entry section to them.
- **Links** — reference vault files with `[[slug]]` (filename, no folder, no `.md`), never a path: Obsidian backlinks and graph only see wikilinks.
- **Session end** — finish substantive sessions with `/capture` (`/exit` quits without writing notes).
- **Maintenance** is manual: run `/brain-audit` when the SessionStart hook says it is due.

## Hooks
- SessionStart: vault pull, project note, pitfalls. SessionEnd: vault commit + push, warns if today has no session log. PreToolUse/Bash: RTK shrinks command output (`rtk proxy '<cmd>'` bypasses; `~/ai-dotfiles/.claude/RTK.md`) and the commit-message check.
- If no `BRAIN_PATH=` / pitfalls block is in context, hooks did not run: run `bash ~/ai-dotfiles/skills/brain-sync/scripts/sync.sh start`, then read pitfalls.md yourself.

## Development
- Occam's razor: fewest assumptions, smallest surface area. Structured, simple, readable code. No speculative abstractions. No backwards-compat shims for removed code.
- When behavior, setup, commands or visible output change, update `CHANGELOG.md` in the same change (small infra/skill changes included) and `README.md` when user-facing usage or structure changed.
- If the repo root has `graphify-out*` (`graphify-out.md`/`.json`, `graphify-out/graph.json`), read it for architecture before inferring from the file tree; never modify it.

## Git
- Run the `/git-commit` skill before every `git commit`: it picks the scope from the locked per-project list, and the PreToolUse hook rejects anything else.
- Merge PRs with `gh pr merge <PR> --squash --delete-branch` — keeps history linear, no "Merge pull request #N" commits.
- For `rm --cached`, `.gitignore` changes and resets: check nested `.gitignore` files and confirm with a full `git status`. Prefer one clean commit over incremental fixes.

## Remote servers
- Verify a fix from the user's side (`curl` the endpoint, check the browser response) — a config change alone is not success.
- Before editing nginx/Docker/Tailscale/Authelia config, find every config location and which one is live (`nginx -T` or equivalent).

## FinOps
Before a multi-step task, state the model you are on and why. When delegating: Haiku for grep/rename/format/lookups, Sonnet for implementation/tests/review (default), Opus for architecture, multi-file refactors, hard debugging. Details: `$BRAIN_PATH/resources/operational/ai-agents/claude-finops.md`.

## Session
- User habits: `/clear` on context switches, `/rename` before `/clear` to `--resume` later, `/compact` at milestones.
- When compacting, preserve: files in scope, open decisions, failing tests/errors, next command to run, explicit user constraints.

## ai-dotfiles init
`ai-dotfiles init <path>` means the user already ran the script: invoke the `brain-init-project` skill with the path — not the `init` skill, which writes CLAUDE.md files.
