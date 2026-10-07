<!-- Generated from AGENTS.md by scripts/build-agent-rules.sh. Do not edit. -->

# Vibe bootstrap (Local Brain)

Vibe does not run hooks. Before your first substantive action on a codebase or on the vault:

```bash
bash ~/ai-dotfiles/skills/brain-sync/scripts/sync.sh start
bash ~/ai-dotfiles/skills/brain-load/scripts/load.sh
```

- If `sync.sh start` fails, warn the user and continue. Do not call a permission error a rebase conflict.
- If `load.sh` exits 2 with `PROJECT_NOTE_MISSING`, follow `skills/brain-load/SKILL.md`.
- At session end: `bash ~/ai-dotfiles/skills/brain-sync/scripts/sync.sh end`.

# Agent rules (Claude Code, Cursor, Mistral Vibe)

<!-- Single source. After editing, run scripts/build-agent-rules.sh. -->

## Soul of the Agent

When reporting information to me, always be extremely concise and to the point; sacrifice grammar and structure for sake of conciseness. Always prefer source & facts over inference.

## Local Brain (Obsidian vault)
`$BRAIN_PATH` comes from `~/ai-dotfiles/config/brain.env`. Layout: `~/ai-dotfiles/.claude/LocalBrain.md`.

- **Pitfalls** — `$BRAIN_PATH/resources/operational/ai-agents/pitfalls.md` is a list of cross-project rules: treat them as constraints, and read it if no hook injected it. A user correction that would recur elsewhere becomes one rule there (format: `capture` skill). Stack rules go to `resources/knowledge/patterns/*-patterns.md`, project gotchas to `.claude/memory/CONTEXT.md`.
- **Where to write** — in the vault, never in the project repo's `docs/`. Move a misplaced spec or plan there and tell the user.

  | Kind | Path |
  |---|---|
  | Session log | `inbox/daily/implementation/<project>/YYYY-MM-DD-<topic>.md` (same thread today → append) |
  | Spec / design doc | `inbox/daily/specs/<project>/YYYY-MM-DD-<topic>-design.md` |
  | Implementation plan (step-by-step tasks) | `inbox/daily/plans/<project>/YYYY-MM-DD-<topic>-plan.md` |

- **History only in session logs** — vault `projects/<slug>.md` notes and repo `.claude/memory/*` are snapshots rewritten in place. Never add a journal, changelog or dated-entry section to them.
- **Links** — reference vault files with `[[slug]]` (filename, no folder, no `.md`), never a path. Obsidian backlinks and graph only see wikilinks.
- **Session end** — finish substantive sessions with `/capture`.
- **Maintenance** is manual: run `/brain-audit` when told it is due.

## Development
- Occam's razor: fewest assumptions, smallest surface area. Structured, simple, readable code. No speculative abstractions. No backwards-compat shims for removed code.
- Read only what the answer needs.
- When behavior, setup, commands or visible output change, update `CHANGELOG.md` in the same change (small infra/skill changes included). Update `README.md` when user-facing usage or structure changed.
- If the repo root has `graphify-out*` (`graphify-out.md`/`.json`, `graphify-out/graph.json`), read it for architecture before inferring from the file tree. Never modify it: Graphify regenerates it.
- Prefer the smallest change that works. Use the `ponytail` skill on coding tasks: YAGNI first, then reuse, stdlib, and already-installed deps before new code.

## Docs style (80% ASD-STE100)
- Prose docs: sentences ≤ 20 words (procedures), ≤ 25 (descriptions).
- Active voice. Simple tenses. One instruction per sentence.
- Noun clusters ≤ 3 words. One term per concept.
- Keep technical names, code, commands and quotes exactly as they are.
- Vertical lists for 3+ items. One topic per paragraph.
- Never drop a fact to shorten a sentence: split it.
- Full rewrite pass on an existing doc: `asd-ste100` skill.

## Git
- Run the `/git-commit` skill before every `git commit`: it picks the scope from the locked per-project list.
- Merge PRs with `gh pr merge <PR> --squash --delete-branch` (linear history).
- For `rm --cached`, `.gitignore` changes and resets: check nested `.gitignore` files and confirm with a full `git status`. Prefer one clean commit over incremental fixes.

## Remote servers
- Verify a fix from the user's side (`curl` the endpoint, check the browser response). A config change alone is not success.
- Before editing nginx/Docker/Tailscale/Authelia config, find every config location and which one is live (`nginx -T` or equivalent).

## FinOps
Before a multi-step task, state the model you are on and why.
- Claude Code: delegation models are set in `.claude/agents/` and `CLAUDE_CODE_SUBAGENT_MODEL`.
- Cursor / Vibe, when delegating: Haiku for grep/rename/format/lookups, Sonnet for implementation/tests/review (default), Opus for architecture, multi-file refactors, hard debugging.

Details: `$BRAIN_PATH/resources/operational/ai-agents/claude-finops.md`.

## ai-dotfiles init
`ai-dotfiles init <path>` means the user already ran the script: invoke the `brain-init-project` skill with the path. Do not use the `init` skill, which writes CLAUDE.md files.
